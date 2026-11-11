"""Tests en seams confirmados (skill tdd): motor, vault, auth, procesador+auditoría.

Cada check ejercita una conducta por la interfaz pública del módulo; las
fronteras de sistema (PostgreSQL, filesystem de datos, entorno) se sustituyen
por sustitutos en tempdir/mock, nunca los módulos internos.

Ejecutar:  python tests/check_seams.py
"""
import copy
import json
import os
import sys
import tempfile
import time
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

# Los avisos de Streamlit ("No runtime found", "missing ScriptRunContext") van a
# stderr y PowerShell los vuelve un falso "Exited with code 1"; sus loggers hijas
# tienen propagate=False: solo sirve este corte global, antes de importar core.*.
logging.disable(logging.WARNING)

import core.auth as auth
import core.vault as vault
import core.auditoria as aud
import core.motor as motor
import core.procesador as procesador
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def check_auth_desactivado_no_entra():
    """Especificación: un usuario desactivado en PostgreSQL no puede iniciar
    sesión, ni con su hash local válido ni con la contraseña maestra del entorno."""
    with tempfile.TemporaryDirectory() as td:
        users = os.path.join(td, "users.json")
        pwd_hash = auth.generar_hash_password("clave_valida_1", salt="sal_unica_c1")
        with open(users, "w", encoding="utf-8") as f:
            json.dump({"op_prueba": {"nombre": "Op", "rol": "Operador", "hash": pwd_hash, "activo": True}}, f)

        pg_inactivo = {"op_prueba": {"nombre": "Op", "rol": "Operador", "hash": pwd_hash, "activo": False}}
        with mock.patch.object(auth, "AUTH_USERS_PATH", users), \
             mock.patch.object(auth, "ES_PRODUCCION", False), \
             mock.patch.object(auth, "es_postgres_disponible", lambda: True), \
             mock.patch.object(auth, "obtener_usuarios_pg", lambda: pg_inactivo), \
             mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPERADOR_PASSWORD", None)
            assert auth.verificar_credenciales("op_prueba", "clave_valida_1") is None, \
                "desactivado en PG no debe entrar aunque su hash local siga válido"
            os.environ["OPERADOR_PASSWORD"] = "master_op_1"
            assert auth.verificar_credenciales("op_prueba", "master_op_1") is None, \
                "la contraseña maestra del entorno no bypasea la desactivación en PG"


def check_auth_fallback_local():
    """Especificación: sin PostgreSQL disponible, el almacén local users.json
    autentica con hash válido y devuelve el rol registrado."""
    with tempfile.TemporaryDirectory() as td:
        users = os.path.join(td, "users.json")
        pwd_hash = auth.generar_hash_password("clave_valida_2", salt="sal_unica_c2")
        with open(users, "w", encoding="utf-8") as f:
            json.dump({"aud_prueba": {"nombre": "Aud", "rol": "Auditor", "hash": pwd_hash, "activo": True}}, f)

        with mock.patch.object(auth, "AUTH_USERS_PATH", users), \
             mock.patch.object(auth, "ES_PRODUCCION", False), \
             mock.patch.object(auth, "es_postgres_disponible", lambda: False), \
             mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUDITOR_PASSWORD", None)
            info = auth.verificar_credenciales("aud_prueba", "clave_valida_2")
            assert info is not None and info["rol"] == "Auditor", \
                "el fallback local debe autenticar con hash válido y devolver el rol"
            assert auth.verificar_credenciales("aud_prueba", "otra_clave") is None, \
                "una contraseña incorrecta debe rechazarse"


def check_vault_ciclo_vida_listar_eliminar():
    """Especificación: la bóveda persiste secretos cifrados entre operaciones,
    `listar` expone su estado sin valores, y `eliminar` retira solo lo pedido."""
    with tempfile.TemporaryDirectory() as td:
        aud_log = aud.AUDIT_LOG_PATH
        try:
            vault.VAULT_FILE_PATH = os.path.join(td, ".vault.enc")
            vault.VAULT_KEY_PATH = os.path.join(td, ".vault.key")
            aud.AUDIT_LOG_PATH = os.path.join(td, "audit_log.json")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("VAULT_MASTER_KEY", None)

                assert vault.guardar_secreto("ALPHA", "valor_secreto")
                assert vault.guardar_secreto("BETA", "otro_valor")

                estado = {s["clave"]: s for s in vault.listar_secretos_disponibles()}
                assert estado["ALPHA"]["estado"] == "[CONFIGURADO]", "el secreto guardado debe aparecer configurado"
                assert "valor_secreto" not in json.dumps(estado), "listar nunca debe exponer valores"

                assert vault.eliminar_secreto("ALPHA"), "eliminar un secreto existente debe reportar éxito"
                assert vault.obtener_secreto("ALPHA") == "", "el secreto eliminado ya no debe resolverse"
                assert vault.obtener_secreto("BETA") == "otro_valor", "eliminar ALPHA no debe afectar a BETA"
        finally:
            aud.AUDIT_LOG_PATH = aud_log


def check_busqueda_multitermino_requiere_ambos():
    """Especificación: una búsqueda de varios términos solo devuelve filas donde
    TODOS los términos aparecen; un término que no coexiste con otro no empareja."""
    with tempfile.TemporaryDirectory() as td:
        csv_path = os.path.join(td, "mantenimientos.csv")
        pd.DataFrame([
            {"servidor_id": "BALANCER001", "numero_serie": "SN-9999", "ip": "10.24.0.125",
             "vcloud_vm": "VM-BAL-01", "nivel_arquitectura": "L3 - Middleware", "componente": "F5",
             "fecha": "2026-10-01", "tipo_mantenimiento": "Preventivo", "tecnico": "ana",
             "descripcion": "upgrade firmware", "estado": "Operativo", "nagios_check": "OK"},
            {"servidor_id": "SWITCH01", "numero_serie": "SN-1111", "ip": "10.24.0.2",
             "vcloud_vm": "-", "nivel_arquitectura": "L1 - Hardware", "componente": "switch",
             "fecha": "2026-09-15", "tipo_mantenimiento": "Correctivo", "tecnico": "luis",
             "descripcion": "cambio puerto", "estado": "En revisión", "nagios_check": "WARN"},
        ]).to_csv(csv_path, index=False)

        with mock.patch.object(motor, "CSV_PATH", csv_path), \
             mock.patch.object(motor, "es_postgres_disponible", lambda: False):
            motor._DUCKDB_CON = None
            motor._DUCKDB_LAST_MTIME = -1.0
            motor._DUCKDB_LAST_LOAD_TS = 0.0

            assert len(motor.buscar_servidores_duckdb("balancer001 sn-9999")) == 1, \
                "ambos términos en la misma fila deben emparejar"
            assert motor.buscar_servidores_duckdb("balancer001 sn-1111").empty, \
                "términos que no coexisten en una fila no deben devolver nada (AND, no OR)"
            assert len(motor.buscar_servidores_duckdb("balancer001")) == 1, \
                "un término único sigue emparejando"


def check_ruta_original_no_escapa_de_data():
    """Especificación: la ruta resuelta desde el Markdown queda siempre dentro
    de data/; una referencia con `..\\` a un archivo del sistema no se resuelve."""
    with tempfile.TemporaryDirectory() as td:
        docs = os.path.join(td, "docs")
        os.makedirs(docs)
        informe = os.path.join(docs, "informe.pdf")
        with open(informe, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        with mock.patch.object(procesador, "DOCS_DIR", docs), \
             mock.patch.object(procesador, "ASSETS_DIR", os.path.join(td, "assets")), \
             mock.patch.object(procesador, "ORIGINALS_DIR", os.path.join(td, "originals")), \
             mock.patch.object(procesador, "INBOX_DIR", os.path.join(td, "inbox")):
            md_ok = "# Ficha\n**Archivo Binario:** `informe.pdf`\n"
            assert procesador.obtener_ruta_original("ficha.md", md_ok) == os.path.realpath(informe), \
                "una referencia legítima dentro de data/ debe resolverse"

            md_evil = "# Ficha\n**Archivo Binario:** `..\\..\\.env`\n"
            assert procesador.obtener_ruta_original("ficha.md", md_evil) is None, \
                "una referencia con traversal fuera de data/ no debe resolverse"
            md_abs = "# Ficha\n**Archivo Binario:** `C:\\Windows\\win.ini`\n"
            assert procesador.obtener_ruta_original("ficha.md", md_abs) is None, \
                "una ruta absoluta del sistema no debe resolverse"


def check_diagrama_ingesta_clave_unica():
    """Especificación: ingestar una imagen crea una única ficha versionada y la
    recarga de documentos no duplica el mismo diagrama bajo otro nombre."""
    with tempfile.TemporaryDirectory() as td:
        docs = os.path.join(td, "docs")
        assets = os.path.join(td, "assets")
        history = os.path.join(td, "history")
        os.makedirs(docs)

        aud_hist, aud_docs, aud_log = aud.HISTORY_DIR, aud.DOCS_DIR, aud.AUDIT_LOG_PATH
        try:
            aud.HISTORY_DIR = history
            aud.DOCS_DIR = docs
            aud.AUDIT_LOG_PATH = os.path.join(td, "audit_log.json")
            aud._obtener_historial_versiones_cached.cache_clear()
            with mock.patch.object(procesador, "DOCS_DIR", docs), \
                 mock.patch.object(procesador, "ASSETS_DIR", assets), \
                 mock.patch.object(procesador, "ORIGINALS_DIR", os.path.join(td, "originals")):
                store = {}
                st_res, _msg = procesador.procesar_e_ingestar_binario(
                    "topologia.png", b"\x89PNG\r\n\x1a\nfake", store
                )
                assert st_res == "nuevo"
                assert list(store.keys()) == ["DIAGRAMA__topologia.png.md"], \
                    "la ingesta debe generar exactamente una clave de ficha"

                procesador.cargar_documentos_locales(store)
                assert list(store.keys()) == ["DIAGRAMA__topologia.png.md"], \
                    "la recarga no debe duplicar el diagrama con otro nombre"

                historial = aud.obtener_historial_versiones("DIAGRAMA__topologia.png.md")
                assert len(historial) == 1 and historial[0]["version"] == 1, \
                    "la ficha nueva debe quedar versionada como v1"
        finally:
            aud.HISTORY_DIR, aud.DOCS_DIR, aud.AUDIT_LOG_PATH = aud_hist, aud_docs, aud_log
            aud._obtener_historial_versiones_cached.cache_clear()


def check_arquitectura_html():
    """El HTML de arquitectura trae las dos vistas, el tema se aplica y los SVG son validos."""
    import re
    import xml.etree.ElementTree as ET

    from core.ui_arquitectura import cargar_html_arquitectura

    claro = cargar_html_arquitectura("Claro")
    assert "%%TEMA%%" not in claro and 'class="tema-claro"' in claro, "el tema claro debe aplicarse"
    assert "Arquitectura de plataforma" in claro, "falta el esquema"
    assert 'id="vista-capas"' in claro and 'id="vista-flujo"' in claro, "faltan las dos vistas"
    assert claro.count('class="tab"') == 2, "faltan las pestañas"
    assert claro.count('data-capa="') == 8, "faltan capas interactivas"
    assert claro.count('data-flujo="') == 5, "faltan los flujos"
    assert "data-desde=" in claro and "data-hasta=" in claro, "faltan flechas trazables"
    assert "data-h0=" in claro and "data-h1=" in claro, "faltan alturas de foco"
    assert 'class="preview"' in claro and ".capa.on .preview" in claro, "falta la vista previa"
    assert "svg text { fill: var(--text); }" in claro, "el texto SVG debe seguir el tema"
    assert 'class="paso" style="--i:' in claro, "los pasos del flujo deben escalonarse"
    assert "prefers-reduced-motion" in claro, "el movimiento debe respetar la preferencia"
    assert "addEventListener('wheel'" in claro and "passive: false" in claro, "falta el zoom con rueda"
    assert "function resetZoom" in claro and "#escena, #escena-flujo" in claro, "falta el paneo"
    assert 'class="idx"' in claro and 'class="regla"' in claro, "falta la numeracion de capa"
    assert 'class="banda"' in claro, "falta la franja de encabezado"
    assert 'id="zoom"' in claro and "Borde punteado: ecosistema externo" in claro, \
        "faltan el reset de zoom y la leyenda util"
    assert 'role="img"' not in claro, "el SVG no debe ocultar los controles al lector de pantalla"
    assert claro.count('role="tabpanel"') == 2, "faltan los paneles de las pestañas"
    assert 'aria-controls="vista-capas"' in claro and 'aria-controls="vista-flujo"' in claro, \
        "las pestañas deben declarar su panel"
    assert 'class="d"' in claro, "falta la descripcion de servicio en el foco"
    assert 'preserveAspectRatio="xMidYMin meet"' in claro, "la vista debe anclarse arriba"
    assert "http://" not in claro and "https://" not in claro, "el HTML debe ser autocontenido"
    for svg in re.findall(r"<svg .*?</svg>", claro, re.S):
        ET.fromstring(svg)
    flujo_svg = re.search(r'<svg id="vista-flujo".*?</svg>', claro, re.S).group(0)
    assert ">ISO 8583</text>" in flujo_svg and ">JDBC</text>" in flujo_svg, \
        "faltan las etiquetas de enlace en los flujos"
    import json
    fichas = json.loads(re.search(r'<script type="application/json" id="datos">(.*?)</script>',
                                  claro, re.S).group(1))
    assert len(fichas) == 70 and all(f["n"] and f["d"] for f in fichas.values()), \
        "faltan fichas de servicio"
    assert 'class="srv"' in claro and 'id="detalle"' in claro, "falta la ficha por servicio"
    assert flujo_svg.count('data-servicio=') == 26, "los nodos del flujo deben abrir ficha"
    oscuro = cargar_html_arquitectura("Oscuro")
    assert 'class="tema-oscuro"' in oscuro and "%%TEMA%%" not in oscuro, "el tema oscuro debe aplicarse"
    assert oscuro == claro.replace('<html class="tema-claro"', '<html class="tema-oscuro"'), \
        "solo debe variar el tema"


def check_arquitectura_modelo():
    """El modelo generado del Excel es coherente y cubre el inventario completo."""
    import json

    from core.configuracion import APP_DIR

    ruta = os.path.join(APP_DIR, "assets", "arquitectura", "modelo.json")
    with open(ruta, encoding="utf-8") as f:
        modelo = json.load(f)

    capas = {c["id"]: c for c in modelo["capas"]}
    assert sorted(capas) == list(range(1, 9)), "deben existir las 8 capas"
    assert all(c["nombre"] for c in capas.values()), "toda capa necesita nombre"
    total_servicios = sum(len(c["servicios"]) for c in capas.values())
    assert total_servicios == modelo["meta"]["total_servicios"] == 70, \
        f"servicios inconsistentes: {total_servicios}"
    assert len(modelo["hosts"]) == modelo["meta"]["total_servidores"] == 58, "hosts inconsistentes"
    assert sum(1 for h in modelo["hosts"] if h["critico"]) == modelo["meta"]["total_criticos"] == 43, \
        "criticos inconsistentes"
    assert sum(c["servidores"] for c in capas.values()) == 58, "los badges deben sumar el inventario"

    con_desc = sum(1 for c in capas.values() for s in c["servicios"] if s.get("descripcion"))
    assert con_desc >= 65, f"faltan descripciones: {con_desc} de {total_servicios}"

    ips = [h["ip"] for h in modelo["hosts"]]
    assert len(set(ips)) == len(ips), "IP duplicada: dos filas describen el mismo equipo"
    assert all(ips), "todo servidor necesita IP como identidad"
    hostnames = [h["hostname"] for h in modelo["hosts"]]
    if len(set(hostnames)) != len(hostnames):
        print("  aviso: hostname repetido en el inventario "
              f"({sorted({h for h in hostnames if hostnames.count(h) > 1})})")
    ids = [s["id"] for c in capas.values() for s in c["servicios"]]
    assert len(set(ids)) == len(ids), "id de servicio duplicado"
    assert all(h["capa"] in capas for h in modelo["hosts"]), "servidor en capa inexistente"

    for rel in modelo["relaciones"]:
        assert rel["desde"] in capas and rel["hasta"] in capas, f"relacion invalida: {rel}"

    assert len(modelo["flujos"]) == 5, "deben existir los 5 flujos"
    for flujo in modelo["flujos"]:
        assert len(flujo["pasos"]) >= 2, f"flujo corto: {flujo['id']}"
        capas_flujo = [p["capa"] for p in flujo["pasos"]]
        assert capas_flujo == sorted(capas_flujo), f"flujo no avanza por capas: {flujo['id']}"
        for paso in flujo["pasos"]:
            nombres = {s["id"] for s in capas[paso["capa"]]["servicios"]}
            assert paso["servicio"] in nombres, \
                f"{flujo['id']}: {paso['servicio']} no pertenece a la capa {paso['capa']}"
            assert "via" in paso, f"{flujo['id']}: falta la etiqueta del enlace"
    assert sum(1 for f in modelo["flujos"] for p in f["pasos"] if p["via"]) == 16, \
        "cada enlace confirmado necesita su protocolo"


def check_arquitectura_render():
    """El HTML versionado es exactamente lo que produce el render del modelo."""
    import html as _html
    import re

    from core.arq_render import cargar_modelo, render_html
    from core.configuracion import ARQ_HTML_PATH, ARQ_MODELO_PATH

    modelo = cargar_modelo(ARQ_MODELO_PATH)
    generado = render_html(modelo)
    with open(ARQ_HTML_PATH, encoding="utf-8") as f:
        versionado = f.read().replace("\r\n", "\n")
    assert generado == versionado, "arquitectura.html desincronizado: correr tools/gen_arq.py"
    assert "%%TEMA%%" in generado, "el loader necesita el marcador de tema"
    assert ">None<" not in generado, "el render filtro un None"
    texto = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", generado)).split())
    for capa in modelo["capas"]:
        for servicio in capa["servicios"]:
            assert " ".join(servicio["nombre"].split()) in texto, \
                f"servicio ausente en el render: {servicio['nombre']}"


def _app_test(cuerpo: str) -> AppTest:
    """Construye un AppTest cuyo script corre en este proceso (patches de módulos aplican)."""
    script = f"import sys\nsys.path.insert(0, {ROOT!r})\n{cuerpo}"
    return AppTest.from_string(script, default_timeout=60)


def check_ui_busqueda_limpiable():
    """Especificación (ui_consultas): buscar un término y reenviar la búsqueda
    vacía limpia la búsqueda; la interfaz vuelve al estado vacío inicial."""
    at = _app_test(
        "import streamlit as st\n"
        "st.session_state.setdefault('historial_busquedas', [])\n"
        "from core.ui_consultas import renderizar_modulo_consultas\n"
        "renderizar_modulo_consultas({'doc_prueba.md': 'contenido de prueba'})\n"
    )
    at.run()

    at.text_input(key="duckdb_search_input").set_value("prueba")
    buscar = next(b for b in at.button if b.label == "Buscar")
    buscar.click().run()
    assert at.session_state["duckdb_active_term"] == "prueba", "el primer Buscar debe fijar el término"

    at.text_input(key="duckdb_search_input").set_value("")
    buscar = next(b for b in at.button if b.label == "Buscar")
    buscar.click().run()
    assert at.session_state["duckdb_active_term"] == "", "reenviar vacío debe limpiar el término activo"
    assert any("empty-state-container" in str(m.value) for m in at.markdown), \
        "la interfaz debe volver al estado vacío de búsqueda"


def check_ui_filtro_categoria_sin_reset():
    """Especificación (ui_documentos): clasificar un documento cambia el recuento
    de pendientes pero NO resetea el filtro "[Sin Categoría]" seleccionado
    (los recuentos viven en format_func, no en la opción)."""
    import core.tags as tags

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "history"))
        os.makedirs(os.path.join(td, "docs"))
        at = _app_test(
            f"import os\n"
            f"_TD = {td!r}\n"
            "import core.tags as tags\n"
            "tags.CATEGORIAS_PATH = os.path.join(_TD, 'categorias.json')\n"
            "import core.auditoria as aud\n"
            "aud.HISTORY_DIR = os.path.join(_TD, 'history')\n"
            "aud.DOCS_DIR = os.path.join(_TD, 'docs')\n"
            "aud.AUDIT_LOG_PATH = os.path.join(_TD, 'audit_log.json')\n"
            "aud._obtener_historial_versiones_cached.cache_clear()\n"
            "import streamlit as st\n"
            "st.session_state.setdefault('historial_busquedas', [])\n"
            "from core.ui_documentos import renderizar_pestana_documentacion\n"
            "renderizar_pestana_documentacion({'a.md': 'contenido uno de prueba', "
            "'b.md': 'contenido dos de prueba'})\n"
        )
        at.run()
        assert not at.exception, f"el render debe completarse: {at.exception}"

        assert tags.obtener_documentos_sin_categoria(["a.md", "b.md"]) == ["a.md", "b.md"], \
            "fixture: ambos documentos deben arrancar sin categoría"

        at.selectbox(key="tab4_cat_selector").set_value("[Sin Categoría]").run()
        assert at.selectbox(key="tab4_cat_selector").value == "[Sin Categoría]"

        # Clasificar uno de fuera del render: el recuento de pendientes cambia 2 -> 1.
        assert tags.asignar_tags_documento("a.md", ["Redes"])
        assert tags.obtener_documentos_sin_categoria(["a.md", "b.md"]) == ["b.md"], \
            "fixture: al clasificar a.md solo queda b.md pendiente"

        at.run()
        assert not at.exception, f"el render debe completarse: {at.exception}"
        assert at.selectbox(key="tab4_cat_selector").value == "[Sin Categoría]", \
            "cambiar el recuento no debe resetear el filtro a la primera opción"


def check_preflight_produccion():
    """En produccion el arranque exige claves maestras, boveda y PostgreSQL."""
    from core.preflight import VARIABLES_OBLIGATORIAS, problemas_de_entorno

    class _Conexion:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def exec_driver_sql(self, sql):
            return None

    class _Motor:
        def connect(self):
            return _Conexion()

    assert problemas_de_entorno(es_produccion=False) == [], "en desarrollo no debe validar"

    with mock.patch.dict(os.environ, {v: "" for v in VARIABLES_OBLIGATORIAS}), \
         mock.patch("core.db.obtener_engine", return_value=None):
        faltan = problemas_de_entorno(es_produccion=True)
    assert len(faltan) == len(VARIABLES_OBLIGATORIAS) + 1, faltan
    assert any("PostgreSQL" in motivo for motivo in faltan), "debe detectar la base"

    with mock.patch.dict(os.environ, {v: "x" for v in VARIABLES_OBLIGATORIAS}):
        assert problemas_de_entorno(es_produccion=True, engine=_Motor()) == [], \
            "con todo configurado no debe haber problemas"

        class _MotorCaido:
            def connect(self):
                raise OSError("sin red")

        faltan = problemas_de_entorno(es_produccion=True, engine=_MotorCaido())
        assert any("no responde" in motivo for motivo in faltan), faltan


def check_auth_sesion_expira_y_revalida():
    """La sesión revalida rol/estado cada minuto y se corta por inactividad."""
    estado = {
        "auth_activa": True,
        "usuario_actual": {"username": "op", "nombre": "Op", "rol": "Operador"},
        "auth_ultima_actividad": time.time(),
        "auth_chequeo": 0.0,
    }
    with mock.patch.object(auth.st, "session_state", estado), \
         mock.patch.object(auth, "es_postgres_disponible", lambda: True), \
         mock.patch.object(auth, "obtener_usuarios_pg",
                           lambda: {"op": {"nombre": "Op", "rol": "Auditor", "activo": True}}):
        assert auth.es_usuario_autenticado() is True
        assert estado["usuario_actual"]["rol"] == "Auditor", "debe tomar el rol vigente"

    estado = {
        "auth_activa": True,
        "usuario_actual": {"username": "op", "nombre": "Op", "rol": "Operador"},
        "auth_ultima_actividad": time.time(),
        "auth_chequeo": 0.0,
    }
    with mock.patch.object(auth.st, "session_state", estado), \
         mock.patch.object(auth, "es_postgres_disponible", lambda: True), \
         mock.patch.object(auth, "obtener_usuarios_pg",
                           lambda: {"op": {"nombre": "Op", "rol": "Operador", "activo": False}}):
        assert auth.es_usuario_autenticado() is False, "un usuario desactivado no sigue"
        assert estado["auth_activa"] is False

    estado = {
        "auth_activa": True,
        "usuario_actual": {"username": "op", "rol": "Operador"},
        "auth_ultima_actividad": time.time() - auth._MAX_INACTIVIDAD_SEG - 1,
        "auth_chequeo": time.time(),
    }
    with mock.patch.object(auth.st, "session_state", estado), \
         mock.patch.object(auth, "es_postgres_disponible", lambda: True):
        assert auth.es_usuario_autenticado() is False, "la inactividad debe cerrar la sesión"
        assert estado["auth_activa"] is False


def check_auth_bloqueo_por_origen():
    """El bloqueo es por usuario+IP y el ruido no borra una cuenta bloqueada."""
    with tempfile.TemporaryDirectory() as td:
        ruta = os.path.join(td, "users.json")
        password = "clave_valida_3"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"op": {"nombre": "Op", "rol": "Operador",
                              "hash": auth.generar_hash_password(password, salt="sal_unica_c3"),
                              "activo": True}}, f)
        auth._INTENTOS_FALLIDOS.clear()
        with mock.patch.object(auth, "AUTH_USERS_PATH", ruta), \
             mock.patch.object(auth, "ES_PRODUCCION", False), \
             mock.patch.object(auth, "es_postgres_disponible", lambda: False):
            for _ in range(auth._MAX_INTENTOS):
                assert auth.verificar_credenciales("op", "mala", origen="1.1.1.1") is None
            assert auth.verificar_credenciales("op", password, origen="1.1.1.1") is None, \
                "el origen bloqueado no debe entrar"
            assert auth.verificar_credenciales("op", password, origen="2.2.2.2") is not None, \
                "otro origen no debe heredar el bloqueo"

        auth._INTENTOS_FALLIDOS.clear()
        for _ in range(auth._MAX_INTENTOS):
            auth._registrar_fallo("op|1.1.1.1")
        for i in range(auth._MAX_CLAVES_INTENTOS + 100):
            auth._registrar_fallo(f"ruido{i}|9.9.9.9")
        assert auth._esta_bloqueado("op|1.1.1.1"), "el ruido no debe borrar el bloqueo"
    auth._INTENTOS_FALLIDOS.clear()


def check_auth_tiempo_constante():
    """Un usuario inexistente paga el mismo PBKDF2 que uno real."""
    auth._INTENTOS_FALLIDOS.clear()
    with mock.patch.object(auth, "es_postgres_disponible", lambda: False), \
         mock.patch.object(auth, "inicializar_almacen_usuarios", lambda: {}), \
         mock.patch.object(auth, "_verificar_hash", wraps=auth._verificar_hash) as verif:
        assert auth.verificar_credenciales("noexiste", "x", origen="9.9.9.9") is None
        assert verif.call_count == 1, "debe verificar contra el hash dummy"
    auth._INTENTOS_FALLIDOS.clear()


def check_auth_maestra_sin_pg_falla_cerrado():
    """En producción sin PostgreSQL la clave maestra no autentica."""
    auth._INTENTOS_FALLIDOS.clear()
    with mock.patch.object(auth, "ES_PRODUCCION", True), \
         mock.patch.object(auth, "es_postgres_disponible", lambda: False), \
         mock.patch.object(auth, "_obtener_password_maestra", lambda usuario: "clave_maestra_1"):
        assert auth.verificar_credenciales("admin", "clave_maestra_1", origen="9.9.9.9") is None
    auth._INTENTOS_FALLIDOS.clear()


def check_arquitectura_atributos():
    """Un nombre con comillas no debe inyectar atributos en el SVG."""
    import re
    import xml.etree.ElementTree as ET

    from core.arq_render import cargar_modelo, render_html
    from core.configuracion import ARQ_MODELO_PATH

    modelo = copy.deepcopy(cargar_modelo(ARQ_MODELO_PATH))
    modelo["capas"][0]["servicios"][0]["nombre"] = 'Servicio" onfocus="alert(1)'
    html = render_html(modelo)
    assert "&quot;" in html, "las comillas de los atributos deben escaparse"
    for svg in re.findall(r"<svg .*?</svg>", html, re.S):
        for nodo in ET.fromstring(svg).iter():
            assert "onfocus" not in nodo.attrib, "atributo inyectado por el nombre"


def check_arquitectura_modelo_incompleto():
    """Un modelo sin capa 4 o con un paso roto no debe tumbar el render."""
    from core.arq_render import cargar_modelo, render_html
    from core.configuracion import ARQ_MODELO_PATH

    base = cargar_modelo(ARQ_MODELO_PATH)

    sin_capa = copy.deepcopy(base)
    sin_capa["capas"] = [c for c in sin_capa["capas"] if c["id"] != 4]
    assert "<svg" in render_html(sin_capa), "sin capa 4 el render debe seguir"

    roto = copy.deepcopy(base)
    roto["flujos"][0]["pasos"][2]["servicio"] = "no-existe"
    html = render_html(roto)
    assert "no-existe" in html, "el paso roto debe verse como nodo, no romper el render"


def check_arquitectura_documentacion():
    """El clic del diagrama abre Modo Lectura o la lista de documentos relacionados."""
    from core import ui_arquitectura as ua
    from core.arq_render import cargar_modelo, render_html
    from core.configuracion import ARQ_MODELO_PATH

    html = render_html(cargar_modelo(ARQ_MODELO_PATH))
    for marca in ('id="d-lectura"', 'id="d-relacionados"', 'id="d-aviso"', "function lanzar("):
        assert marca in html, f"falta {marca} en la ficha del visor"

    doc_store = {
        "matriz_alertamiento.md": "nagios newrelic alertamiento de incidentes",
        "sin_relacion.md": "archivo aparte",
    }

    class _StFalso:
        def __init__(self, params):
            self.query_params = dict(params)
            self.session_state = {"nav_seccion_activa": "Arquitectura"}

    def correr(params):
        falso = _StFalso(params)
        with mock.patch.object(ua, "st", falso):
            ua.procesar_parametros_arquitectura(doc_store)
        return falso

    # Coincidencia fuerte: abre Modo Lectura en el mismo rerun y limpia la URL.
    falso = correr({"arq_lee": "nagios"})
    assert falso.session_state.get("zen_studio_activo") is True, "debe abrir Modo Lectura"
    assert falso.session_state["zen_doc_sel"] == "matriz_alertamiento.md"
    assert falso.query_params == {}, "el parámetro debe limpiarse tras leerlo"
    assert "arq_docs_relacionados" not in falso.session_state

    # Sin coincidencia: no fuerza un documento, cae a la lista de relacionados.
    falso = correr({"arq_lee": "termine-inexistente"})
    assert "zen_studio_activo" not in falso.session_state, "sin umbral no se abre nada"
    rel = falso.session_state["arq_docs_relacionados"]
    assert rel["docs"] == [] and rel["etiqueta"] == "termine-inexistente"
    assert falso.session_state["nav_seccion_activa"] == "Documentación Técnica"

    # Lista de relacionados con top 5 y filtros de la pestaña en su valor neutro.
    falso = correr({"arq_rel": "nagios"})
    assert falso.session_state["arq_docs_relacionados"]["docs"] == ["matriz_alertamiento.md"]
    assert falso.session_state["tab4_cat_selector"] == "Todas"
    assert falso.session_state["tab4_type_selector"] == "Todos"

    # La categoría del modelo actúa como tag: un doc sin el nombre del
    # servicio entra por la categoría y se fusiona por score máximo.
    doc_store["guia_monitoreo.md"] = "procedimiento de monitoreo de alertas"
    with mock.patch.object(ua, "_categoria_de_servicio", lambda n: "monitoreo"):
        falso = correr({"arq_rel": "servicio-falso"})
    assert falso.session_state["arq_docs_relacionados"]["docs"] == ["guia_monitoreo.md"], \
        "la categoría debe rescatar al documento"

    # Sin parámetro no se toca nada: el resto de la consola no debe enterarse.
    falso = correr({})
    assert falso.session_state == {"nav_seccion_activa": "Arquitectura"}
    assert falso.query_params == {}


def check_plantillas_permiso_y_escapes():
    """Ronda de agentes pares: Guardar Documento exige puede_editar_docs (rol
    Auditor no escribe nada) y los datos de usuario interpolados en HTML van escapados."""
    import inspect
    import core.ui_plantillas as ui_pl
    import core.ui_documentos as ui_doc
    import core.visor as vis
    import core.ui_sidebar as ui_sb

    with tempfile.TemporaryDirectory() as td:
        docs = os.path.join(td, "docs")
        hist = os.path.join(td, "history")
        os.makedirs(docs)
        os.makedirs(hist)
        at = _app_test(
            "import time\n"
            "import streamlit as st\n"
            "import core.ui_plantillas as pl\n"
            "import core.auditoria as aud\n"
            "import core.tags as tg\n"
            f"pl.DOCS_DIR = {docs!r}\n"
            f"aud.HISTORY_DIR = {hist!r}\n"
            f"aud.AUDIT_LOG_PATH = {os.path.join(td, 'audit_log.json')!r}\n"
            f"aud.DOCS_DIR = {docs!r}\n"
            f"tg.CATEGORIAS_PATH = {os.path.join(td, 'categorias.json')!r}\n"
            "st.session_state['usuario_actual'] = {'username': 'aud', 'rol': 'Auditor', "
            "'nombre': 'Auditor', 'activo': True}\n"
            "st.session_state['auth_activa'] = True\n"
            "st.session_state['auth_ultima_actividad'] = time.time()\n"
            "st.session_state['auth_chequeo'] = time.time()\n"
            "pl.renderizar_pestana_plantillas({})\n"
        )
        at.run()
        assert not at.exception, f"el render de plantillas falló: {at.exception}"
        at.text_input(key="input_cat_proc_nueva").set_value("Categoria Pares")
        at.button(key="btn_guardar_doc_plantilla_final").click().run()
        assert not at.exception, f"el guardado falló con excepción: {at.exception}"
        assert os.listdir(docs) == [], f"el rol Auditor creó documentos: {os.listdir(docs)}"
        assert any("no permite editar documentos" in e.value for e in at.error), \
            "debe mostrar el error de permiso en lugar de guardar"

    for mod, marca in ((ui_doc, "html.escape(str(u_edit)"),
                       (ui_doc, "html.escape(str(t)"),
                       (vis, "html.escape(str(ultimo_editor)"),
                       (ui_sb, "html.escape(str(s['clave'])")):
        assert marca in inspect.getsource(mod), f"falta escape de usuario en {mod.__name__}: {marca}"


def _sesion_app(rol: str) -> str:
    """Precarga de sesión autenticada para AppTest (patrón de check_seams)."""
    return (
        "import time\n"
        f"st.session_state['usuario_actual'] = {{'username': 'prueba', 'rol': {rol!r}, "
        f"'nombre': 'Prueba', 'activo': True}}\n"
        "st.session_state['auth_activa'] = True\n"
        "st.session_state['auth_ultima_actividad'] = time.time()\n"
        "st.session_state['auth_chequeo'] = time.time()\n"
    )


def check_ronda_pares_escrituras():
    """Medias de la ronda de pares: un rol sin puede_editar_docs no escribe
    historial al consultar un doc ni activa plantillas con [+ Usar]."""
    with tempfile.TemporaryDirectory() as td:
        hist_md = os.path.join(td, "history", "consulta_aud.md")
        at = _app_test(
            "import os\n"
            "import streamlit as st\n"
            "import core.auditoria as aud\n"
            f"aud.HISTORY_DIR = {os.path.join(td, 'history')!r}\n"
            f"aud.DOCS_DIR = {os.path.join(td, 'docs')!r}\n"
            f"aud.AUDIT_LOG_PATH = {os.path.join(td, 'audit_log.json')!r}\n"
            "aud._obtener_historial_versiones_cached.cache_clear()\n"
            "h1 = aud.inicializar_version_inicial_si_no_existe('sin_sesion.md', 'hola')\n"
            "assert len(h1) == 1, h1\n"
            + _sesion_app("Auditor") +
            "h2 = aud.inicializar_version_inicial_si_no_existe('consulta_aud.md', 'hola')\n"
            "assert h2 == [], f'el Auditor no debe recibir historial que no existe: {h2}'\n"
            f"assert not os.path.exists({hist_md!r}), 'consultar no debe escribir historial'\n"
        )
        at.run()
        assert not at.exception, f"falla la inicializacion condicionada: {at.exception}"

    with tempfile.TemporaryDirectory() as td2:
        custom = os.path.join(td2, "plantillas_custom.json")
        at = _app_test(
            "import time\n"
            "import streamlit as st\n"
            "import core.ui_plantillas as pl\n"
            "import core.plantillas as plant\n"
            "import core.auditoria as aud\n"
            "import core.tags as tg\n"
            f"pl.DOCS_DIR = {os.path.join(td2, 'docs')!r}\n"
            f"plant.PLANTILLAS_CUSTOM_PATH = {custom!r}\n"
            f"aud.HISTORY_DIR = {os.path.join(td2, 'history')!r}\n"
            f"aud.DOCS_DIR = {os.path.join(td2, 'docs')!r}\n"
            f"aud.AUDIT_LOG_PATH = {os.path.join(td2, 'audit_log.json')!r}\n"
            f"tg.CATEGORIAS_PATH = {os.path.join(td2, 'categorias.json')!r}\n"
            + _sesion_app("Auditor") +
            "pl.renderizar_pestana_plantillas({})\n"
        )
        at.run()
        assert not at.exception, f"el render de plantillas falló: {at.exception}"
        at.button(key="btn_activar_plantilla_base").click().run()
        assert not at.exception, f"[+ Usar] falló con excepción: {at.exception}"
        assert not os.path.exists(custom), "el rol Auditor escribió plantillas_custom.json"
        assert any("no permite editar documentos" in e.value for e in at.error), \
            "[+ Usar] debe cortar con el mensaje de permiso"


def check_ronda_pares_sidebar():
    """Medias de la ronda de pares: una extensión ajena no revienta el run ni se
    ingestea, la bóveda rechaza valor en blanco y sus callbacks exigen
    puede_editar_vault (clave que antes no consultaba nadie)."""
    import inspect
    import core.ui_sidebar as ui_sb

    # (a) "../../x.py" sin `type=` en el widget: antes reventaba el run con
    # StreamlitAPIException ANTES de ejecutar el script (no alcanza ningún try).
    with tempfile.TemporaryDirectory() as td:
        dirs = {n: os.path.join(td, n) for n in ("docs", "assets", "orig", "inbox")}
        for d in dirs.values():
            os.makedirs(d)
        at = _app_test(
            "import streamlit as st\n"
            "import core.procesador as proc\n"
            "import core.tags as tg\n"
            "import core.ui_sidebar as sb\n"
            f"proc.DOCS_DIR = {dirs['docs']!r}\n"
            f"proc.ASSETS_DIR = {dirs['assets']!r}\n"
            f"proc.ORIGINALS_DIR = {dirs['orig']!r}\n"
            f"proc.INBOX_DIR = {dirs['inbox']!r}\n"
            f"tg.CATEGORIAS_PATH = {os.path.join(td, 'categorias.json')!r}\n"
            "sb.listar_secretos_disponibles = lambda: []\n"
            + _sesion_app("Administrador") +
            "sb.renderizar_sidebar({'username': 'admin', 'rol': 'Administrador', "
            "'nombre': 'Admin'}, {})\n"
        )
        at.run()
        assert not at.exception, at.exception
        at.file_uploader(key="uploader_files_0").set_value(
            [("../../x.py", b"print('no debe salir')\n", "text/x-python")])
        at.run()
        assert not at.exception, f"una extensión ajena rompió el run: {at.exception}"
        at.text_input(key="sb_nueva_cat_ini_0").set_value("CatPar")
        at.button(key="btn_confirmar_ingesta_tags").click().run()
        assert not at.exception, f"la ingesta falló con excepción: {at.exception}"
        assert not any(os.listdir(d) for d in dirs.values()), \
            "un archivo con extensión ajena no debe ingestarse"

    # (b) Valor en blanco: sin la validación se guardaba "" con toast de éxito.
    with tempfile.TemporaryDirectory() as td2:
        at = _app_test(
            "import streamlit as st\n"
            "import core.ui_sidebar as sb\n"
            "sb._prueba_llamadas = []\n"
            "sb.listar_secretos_disponibles = lambda: [{'clave': 'API_KEY', "
            "'estado': '[CONFIGURADO]', 'vista_previa': '***', 'origen': 'env'}]\n"
            "sb.guardar_secreto = lambda k, v: (sb._prueba_llamadas.append((k, v)), True)[1]\n"
            "sb.eliminar_secreto = lambda k: True\n"
            + _sesion_app("Administrador") +
            "sb.renderizar_sidebar({'username': 'admin', 'rol': 'Administrador', "
            "'nombre': 'Admin'}, {})\n"
        )
        at.run()
        assert not at.exception, at.exception
        at.text_input(key="sb_vault_val_0").set_value("   ")
        at.button(key="sb_btn_guardar_key").click().run()
        assert not at.exception, at.exception
        assert ui_sb._prueba_llamadas == [], \
            f"un valor en blanco no debe guardarse: {ui_sb._prueba_llamadas}"
        assert any("Escribe un nombre y un valor" in e.value for e in at.error), \
            "la bóveda debe rechazar el valor en blanco con mensaje claro"

    assert inspect.getsource(ui_sb).count('tiene_permiso("puede_editar_vault")') >= 2, \
        "los callbacks de bóveda deben revalidar puede_editar_vault"


def check_ronda_pares_bajas():
    """Bajas de la ronda de pares: sin permiso no se renderizan controles de
    edición/ingesta, el Registro de Actividad exige puede_ver_auditoria, el
    rollback sólo aparece con puede_rollback y el login distingue cuenta
    bloqueada de credenciales inválidas."""
    import inspect
    import core.ui_documentos as ui_doc

    # (a)+(d) Editor y Registro de Actividad por rol, sobre el mismo historial.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "history"))
        docs = os.path.join(td, "docs")
        os.makedirs(docs)

        def _docs_app(rol):
            return _app_test(
                "import os\n"
                "import streamlit as st\n"
                "import core.tags as tags\n"
                "import core.auditoria as aud\n"
                f"tags.CATEGORIAS_PATH = {os.path.join(td, 'categorias.json')!r}\n"
                f"aud.HISTORY_DIR = {os.path.join(td, 'history')!r}\n"
                f"aud.DOCS_DIR = {docs!r}\n"
                f"aud.AUDIT_LOG_PATH = {os.path.join(td, 'audit_log.json')!r}\n"
                "aud._obtener_historial_versiones_cached.cache_clear()\n"
                "aud._obtener_todos_los_eventos_auditoria_cached.cache_clear()\n"
                "st.session_state.setdefault('historial_busquedas', [])\n"
                + _sesion_app(rol) +
                "from core.ui_documentos import renderizar_pestana_documentacion\n"
                "renderizar_pestana_documentacion({'a.md': 'contenido de prueba'})\n"
            )

        # Operador: sí ve editor, no ve Registro de Actividad (y su init crea
        # historial + evento que luego consumirá la pasada del Auditor).
        at = _docs_app("Operador")
        at.run()
        at.run()
        assert not at.exception, f"render Operador: {at.exception}"
        at.text_area(key="textarea_edit_a.md")
        assert not any(cb.key == "chk_aud_a.md" for cb in at.checkbox), \
            "el Operador no debe ver el Registro de Actividad"

        # Auditor: nada editable y el Registro de Actividad sí está disponible.
        at = _docs_app("Auditor")
        at.run()
        at.run()
        assert not at.exception, f"render Auditor: {at.exception}"
        assert any("no permite editar documentos" in i.value for i in at.info), \
            "la pestaña de edición debe mostrar el aviso de permiso"
        assert not any(w.key == "textarea_edit_a.md" for w in at.text_area), \
            "el Auditor no debe recibir el textarea del editor"
        assert not any("Guardar Versión" in b.label for b in at.button), \
            "el Auditor no debe ver el botón de guardar versión"
        at.checkbox(key="chk_aud_a.md")

    # (b) El bloque de rollback no se renderiza sin puede_rollback.
    assert 'it_sel["version"] != u_ver and tiene_permiso("puede_rollback")' in inspect.getsource(ui_doc), \
        "la sección de rollback debe exigir puede_rollback al renderizar"

    # (c) Sidebar: el Auditor no ve el uploader, sólo el aviso de permiso.
    with tempfile.TemporaryDirectory() as td2:
        at = _app_test(
            "import streamlit as st\n"
            "import core.ui_sidebar as sb\n"
            + _sesion_app("Auditor") +
            "sb.renderizar_sidebar({'username': 'aud', 'rol': 'Auditor', "
            "'nombre': 'Auditor'}, {})\n"
        )
        at.run()
        assert not at.exception, f"sidebar Auditor: {at.exception}"
        assert len(at.file_uploader) == 0, "el Auditor no debe ver el uploader"
        assert any("no permite subir archivos" in c.value for c in at.caption), \
            "el expander de ingesta debe explicar el permiso"

    # (e) Login: malas credenciales → mensaje genérico; bloqueo → aviso explícito.
    auth._INTENTOS_FALLIDOS.clear()
    with tempfile.TemporaryDirectory() as td3:
        def _login_app(bloqueado):
            return _app_test(
                "import streamlit as st\n"
                "import core.auth as auth\n"
                "import core.auditoria as aud\n"
                f"aud.AUDIT_LOG_PATH = {os.path.join(td3, 'audit_log.json')!r}\n"
                + (("for _ in range(auth._MAX_INTENTOS):\n"
                    "    auth._registrar_fallo(auth._clave_intentos('op', auth._origen_actual()))\n")
                   if bloqueado else "")
                + "auth.renderizar_pantalla_login()\n"
            )

        at = _login_app(False)
        at.run()
        assert not at.exception, f"login: {at.exception}"
        at.text_input(key="login_username_val").set_value("op")
        at.text_input(key="login_password_val").set_value("clave_mala")
        next(b for b in at.button if b.label == "Iniciar Sesión").click().run()
        assert not at.exception, f"login fallido: {at.exception}"
        assert any("Usuario o contraseña incorrectos" in e.value for e in at.error), \
            "un intento normal debe dar el mensaje genérico"

        at = _login_app(True)
        at.run()
        at.text_input(key="login_username_val").set_value("op")
        at.text_input(key="login_password_val").set_value("la_correcta")
        next(b for b in at.button if b.label == "Iniciar Sesión").click().run()
        assert not at.exception, f"login bloqueado: {at.exception}"
        assert any("bloqueada" in e.value for e in at.error), \
            "una cuenta bloqueada debe avisarlo en lugar de fallar en silencio"
    auth._INTENTOS_FALLIDOS.clear()

    # (f) La descripción del Operador refleja sus permisos reales.
    desc_op = auth.ROLES_PERMISOS["Operador"]["descripcion"]
    assert "Registro de Incidencias" not in desc_op, "la descripción del Operador está desalineada"
    assert "Ingesta" in desc_op, "la descripción debe mencionar la ingesta que sí puede"


def check_ingesta_zip_crea_categoria():
    """Al subir sólo un ZIP, el nombre del paquete crea la categoría y se asigna
    a sus entradas; el lote sin categoría elegida no debe quedar bloqueado."""
    import io
    import zipfile as zf

    buf = io.BytesIO()
    with zf.ZipFile(buf, "w") as z:
        z.writestr("nota_carpeta.md", "# Nota de prueba\n\nContenido de la carpeta.\n")
    zip_bytes = buf.getvalue()

    with tempfile.TemporaryDirectory() as td:
        dirs = {n: os.path.join(td, n) for n in ("docs", "assets", "orig", "inbox")}
        for d in dirs.values():
            os.makedirs(d)
        cats_path = os.path.join(td, "categorias.json")
        at = _app_test(
            "import streamlit as st\n"
            "import core.procesador as proc\n"
            "import core.auditoria as aud\n"
            "import core.tags as tg\n"
            "import core.ui_sidebar as sb\n"
            f"proc.DOCS_DIR = {dirs['docs']!r}\n"
            f"proc.ASSETS_DIR = {dirs['assets']!r}\n"
            f"proc.ORIGINALS_DIR = {dirs['orig']!r}\n"
            f"proc.INBOX_DIR = {dirs['inbox']!r}\n"
            f"aud.HISTORY_DIR = {os.path.join(td, 'history')!r}\n"
            f"aud.DOCS_DIR = {dirs['docs']!r}\n"
            f"aud.AUDIT_LOG_PATH = {os.path.join(td, 'audit_log.json')!r}\n"
            f"tg.CATEGORIAS_PATH = {cats_path!r}\n"
            "sb.listar_secretos_disponibles = lambda: []\n"
            + _sesion_app("Administrador") +
            "sb.renderizar_sidebar({'username': 'admin', 'rol': 'Administrador', "
            "'nombre': 'Admin'}, {})\n"
        )
        at.run()
        assert not at.exception, at.exception
        at.file_uploader(key="uploader_files_0").set_value(
            [("Carpeta Prueba.zip", zip_bytes, "application/zip")])
        at.run()
        assert not at.exception, at.exception
        # Sin categoría elegida: el lote sólo de ZIP pasa la validación.
        at.button(key="btn_confirmar_ingesta_tags").click().run()
        assert not at.exception, f"la ingesta del ZIP falló: {at.exception}"

        assert os.listdir(dirs["docs"]), "la entrada del ZIP debe ingestarse"
        with open(cats_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "Carpeta Prueba" in data["categorias"], \
            f"el nombre del ZIP debe crear la categoría: {data['categorias']}"
        docs_cat = data.get("documentos", {})
        assert any("Carpeta Prueba" in v for v in docs_cat.values()), \
            f"las entradas del ZIP deben quedar clasificadas: {docs_cat}"


if __name__ == "__main__":
    check_preflight_produccion()
    check_auth_desactivado_no_entra()
    check_auth_fallback_local()
    check_auth_sesion_expira_y_revalida()
    check_auth_bloqueo_por_origen()
    check_auth_tiempo_constante()
    check_auth_maestra_sin_pg_falla_cerrado()
    check_vault_ciclo_vida_listar_eliminar()
    check_busqueda_multitermino_requiere_ambos()
    check_ruta_original_no_escapa_de_data()
    check_diagrama_ingesta_clave_unica()
    check_arquitectura_html()
    check_arquitectura_modelo()
    check_arquitectura_render()
    check_arquitectura_atributos()
    check_arquitectura_modelo_incompleto()
    check_arquitectura_documentacion()
    check_ui_busqueda_limpiable()
    check_ui_filtro_categoria_sin_reset()
    check_plantillas_permiso_y_escapes()
    check_ronda_pares_escrituras()
    check_ronda_pares_sidebar()
    check_ronda_pares_bajas()
    check_ingesta_zip_crea_categoria()
    print("[OK] check_seams")

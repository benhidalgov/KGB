"""Tests en seams confirmados (skill tdd): motor, vault, auth, procesador+auditoría.

Cada check ejercita una conducta por la interfaz pública del módulo; las
fronteras de sistema (PostgreSQL, filesystem de datos, entorno) se sustituyen
por sustitutos en tempdir/mock, nunca los módulos internos.

Ejecutar:  python tests/check_seams.py
"""
import json
import os
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

# Sin runtime de Streamlit, sus avisos (cache_data "No runtime found" y
# "missing ScriptRunContext") van a stderr y PowerShell los convierte en un
# falso "Exited with code 1" tras el [OK]. Van por logging normal, pero sus
# loggers hijas tienen nivel propio y propagate=False: solo sirve el corte
# global de stdlib, y ANTES de importar core.* (que ya avisa al importar).
# ERROR sigue visible; los fallos de AppTest llegan por at.exception.
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


if __name__ == "__main__":
    check_auth_desactivado_no_entra()
    check_auth_fallback_local()
    check_vault_ciclo_vida_listar_eliminar()
    check_busqueda_multitermino_requiere_ambos()
    check_ruta_original_no_escapa_de_data()
    check_diagrama_ingesta_clave_unica()
    check_ui_busqueda_limpiable()
    check_ui_filtro_categoria_sin_reset()
    print("[OK] check_seams")

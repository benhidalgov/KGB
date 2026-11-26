"""Verificación funcional de los botones de la consola.

Cada escenario abre una vista real en AppTest, pulsa sus botones uno a uno y
exige que el run termine sin excepción; cuando el botón tiene un efecto
observable (guarda una versión, limpia el historial, navega, autentica), ese
efecto se afirma aquí. Las descargas (st.download_button) sólo se comprueban
presentes: entregan bytes, no hay nada que pulsar.

Ejecutar:  python tests/check_botones.py
"""
import logging
import os
import sys
import tempfile
import time

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_TESTS, "..")))
sys.path.insert(0, _TESTS)

# Mismos avisos de Streamlit a stderr que en check_seams: PowerShell los
# convierte en un falso "Exited with code 1".
logging.disable(logging.WARNING)

from streamlit.testing.v1 import AppTest

from check_seams import ROOT, _app_test, _parches_aud_tags, _sesion_app

PNG_1x1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _boton(at, key=None, label=None):
    """Devuelve el botón por clave o etiqueta; si no existe, falla con el listado."""
    for b in at.button:
        if key is not None and b.key == key:
            return b
        if label is not None and b.label == label:
            return b
    raise AssertionError(
        f"no existe el botón key={key!r} label={label!r}; "
        f"disponibles: {[(b.key, b.label) for b in at.button]}"
    )


def _pulsar(at, key=None, label=None):
    """Pulsa un botón y exige un run sin excepciones."""
    _boton(at, key=key, label=label).click().run()
    assert not at.exception, f"el botón {key or label!r} falló: {at.exception}"
    return at


def _versiones(doc: str) -> list:
    """Historial del documento desde el proceso de test, sin caché obsoleta."""
    import core.auditoria as aud
    aud._obtener_historial_versiones_cached.cache_clear()
    return aud.obtener_historial_versiones(doc)


def _autenticar(at, rol: str = "Administrador") -> None:
    """Precarga la sesión en el AppTest (fuera del script): sembrarla dentro
    la repondría en cada run y el logout parecería no funcionar."""
    import time
    at.session_state["usuario_actual"] = {"username": "prueba", "rol": rol,
                                          "nombre": "Prueba", "activo": True}
    at.session_state["auth_activa"] = True
    at.session_state["auth_ultima_actividad"] = time.time()
    at.session_state["auth_chequeo"] = time.time()


def check_botones_login():
    """Atajos de cuenta del login, envío del formulario y sesión resultante."""
    import core.auth as auth

    with tempfile.TemporaryDirectory() as td:
        at = _app_test(
            "import streamlit as st\n"
            "import core.auth as auth\n"
            "import core.auditoria as aud\n"
            f"aud.AUDIT_LOG_PATH = {os.path.join(td, 'audit_log.json')!r}\n"
            "auth.renderizar_pantalla_login()\n"
        )
        at.run()
        assert not at.exception, f"el login debe renderizar: {at.exception}"

        for cuenta in ("admin", "operador", "auditor"):
            _pulsar(at, key=f"btn_fill_{cuenta}")
            assert at.text_input(key="login_username_val").value == cuenta, \
                f"el atajo {cuenta!r} no rellenó el usuario"

        _pulsar(at, key="btn_fill_admin")
        _pulsar(at, label="Iniciar Sesión")
        assert at.session_state["auth_activa"] is True, \
            "Iniciar Sesión con la cuenta demo debe autenticar"
        assert at.session_state["usuario_actual"]["rol"] == "Administrador", \
            "la sesión debe quedar con el rol de la cuenta elegida"
        auth._INTENTOS_FALLIDOS.clear()


def check_botones_sidebar():
    """Sidebar: recargar, cancelar ingesta, bóveda, colapsar y salir."""
    with tempfile.TemporaryDirectory() as td:
        dirs = {n: os.path.join(td, n) for n in ("docs", "assets", "orig", "inbox", "cache")}
        for d in dirs.values():
            os.makedirs(d)
        at = _app_test(
            _parches_aud_tags(td)
            + "import core.procesador as proc\n"
            "import core.ui_sidebar as sb\n"
            f"proc.DOCS_DIR = {dirs['docs']!r}\n"
            f"proc.ASSETS_DIR = {dirs['assets']!r}\n"
            f"proc.ORIGINALS_DIR = {dirs['orig']!r}\n"
            f"proc.INBOX_DIR = {dirs['inbox']!r}\n"
            f"proc.DOCS_CACHE_DIR = {dirs['cache']!r}\n"
            "sb.listar_secretos_disponibles = lambda: [{'clave': 'API_KEY', "
            "'estado': '[CONFIGURADO]', 'vista_previa': '***', 'origen': 'env'}]\n"
            "sb.guardar_secreto = lambda k, v: True\n"
            "sb.eliminar_secreto = lambda k: True\n"
            "sb.renderizar_sidebar({'username': 'admin', 'rol': 'Administrador', "
            "'nombre': 'Admin'}, {})\n"
        )
        _autenticar(at)
        at.run()
        assert not at.exception, f"el sidebar debe renderizar: {at.exception}"

        _pulsar(at, key="btn_sidebar_reindexar")

        # Cancelar ingesta: la selección del uploader se descarta con una versión nueva.
        at.file_uploader(key="uploader_files_0").set_value(
            [("nota.md", b"# nota de prueba", "text/markdown")])
        at.run()
        assert not at.exception, f"el uploader debe aceptar el archivo: {at.exception}"
        ver_antes = at.session_state["uploader_key_ver"]
        _pulsar(at, key="btn_cancelar_ingesta")
        assert at.session_state["uploader_key_ver"] == ver_antes + 1, \
            "Cancelar debe descartar la selección (versión nueva del uploader)"

        # Bóveda: guardar y eliminar con los secretos sustituidos por un doble.
        at.text_input(key="sb_vault_val_0").set_value("valor_de_prueba")
        _pulsar(at, key="sb_btn_guardar_key")
        _pulsar(at, key="sb_btn_eliminar_key")

        _pulsar(at, key="btn_colapsar_sidebar")
        assert at.session_state["sidebar_colapsado"] is True, \
            "Colapsar menú debe ocultar el panel lateral"
        at.session_state["sidebar_colapsado"] = False
        at.run()
        assert not at.exception, at.exception

        _pulsar(at, key="btn_logout_sidebar")
        assert at.session_state["auth_activa"] is False, \
            "Salir debe cerrar la sesión"


def check_botones_consultas():
    """Búsqueda, puente al asistente y limpieza del historial de chat."""
    with tempfile.TemporaryDirectory() as td:
        at = _app_test(
            "import streamlit as st\n"
            "import core.ui_consultas as uc\n"
            "uc.generar_respuesta_asistente = lambda term, store: 'respuesta de prueba'\n"
            "st.session_state.setdefault('historial_busquedas', [])\n"
            "from core.ui_consultas import renderizar_modulo_consultas\n"
            "renderizar_modulo_consultas({'a.md': 'contenido de prueba'})\n"
        )
        at.run()
        assert not at.exception, f"el módulo de consultas debe renderizar: {at.exception}"

        at.text_input(key="duckdb_search_input").set_value("prueba")
        _pulsar(at, label="Buscar")
        assert at.session_state["duckdb_active_term"] == "prueba", \
            "Buscar debe fijar el término activo"

        _pulsar(at, key="btn_bridge_to_asistente")
        assert len(at.session_state["historial_busquedas"]) == 1, \
            "Analizar con Asistente debe guardar la respuesta en el historial"

        _pulsar(at, key="btn_clear_search_history")
        assert at.session_state["historial_busquedas"] == [], \
            "Limpiar Chat debe vaciar el historial"


def check_botones_documentos():
    """Documentación: quitar filtro, guardar versión, rollback y clasificación en lote."""
    import core.tags as tags

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "history"))
        os.makedirs(os.path.join(td, "docs"))
        os.makedirs(os.path.join(td, "cache"))
        at = _app_test(
            _parches_aud_tags(td)
            + "import core.procesador as proc\n"
            f"proc.DOCS_CACHE_DIR = {os.path.join(td, 'cache')!r}\n"
            "import core.auditoria as aud\n"
            # El sembrado sólo corre si el documento no tiene historial: en cada
            # run volvería a crear su versión y pisaría la edición del test.
            "if not aud.obtener_historial_versiones('a.md'):\n"
            "    aud.inicializar_version_inicial_si_no_existe('a.md', 'contenido base')\n"
            "    aud.guardar_nueva_version('a.md', 'contenido modificado', 'tester', "
            "'cambio de prueba', {})\n"
            + _sesion_app("Administrador") +
            "from core.ui_documentos import renderizar_pestana_documentacion\n"
            "renderizar_pestana_documentacion({'a.md': 'contenido modificado'})\n"
        )
        at.session_state["arq_docs_relacionados"] = {"etiqueta": "prueba", "docs": ["a.md"]}
        at.run()
        assert not at.exception, f"la pestaña de documentación debe renderizar: {at.exception}"

        # Filtro que llega del diagrama.
        _pulsar(at, key="arq_quitar_relacionados")
        assert "arq_docs_relacionados" not in at.session_state, \
            "Quitar filtro debe limpiar el filtro del diagrama"
        assert any(b.key == "dl_act_a.md" for b in at.download_button), \
            "falta la descarga de la versión activa"

        # Guardar una versión nueva desde el editor de texto.
        at.radio(key="pestana_documentos_activa").set_value("Editar Documento").run()
        assert not at.exception, at.exception
        at.text_input(key="author_input_a.md").set_value("tester")
        at.text_input(key="motive_input_a.md").set_value("motivo de prueba")
        # El contenido debe cambiar: guardar sin editar no crea versión (sha igual).
        at.text_area(key="textarea_edit_a.md").set_value("contenido modificado\n\neditado en el test")
        vers_antes = len(_versiones("a.md"))
        _pulsar(at, key="btn_save_a.md")
        assert len(_versiones("a.md")) == vers_antes + 1, (
            f"Guardar Versión debe crear una versión (antes={vers_antes}, "
            f"ahora={len(_versiones('a.md'))}, errores={[e.value for e in at.error]})")

        # Rollback a la versión más antigua desde el Historial de Cambios.
        at.radio(key="pestana_documentos_activa").set_value("Ver Documentos").run()
        assert not at.exception, at.exception
        sel = at.selectbox(key="select_hist_ver_a.md")
        at.selectbox(key="select_hist_ver_a.md").set_value(sel.options[-1])
        at.run()
        assert not at.exception, at.exception
        at.text_input(key="author_rb_a.md_1").set_value("tester")
        at.text_input(key="motive_rb_a.md_1").set_value("vuelta atras")
        vers_antes = len(_versiones("a.md"))
        _pulsar(at, key="btn_rb_a.md_1")
        assert len(_versiones("a.md")) == vers_antes + 1, \
            "Volver a la Versión debe crear una versión nueva (rollback)"

        # Clasificación en lote: marcar, desearmar y aplicar una categoría nueva.
        lbl_lote = next(o for o in at.radio(key="pestana_documentos_activa").options
                        if o.startswith("Clasificación en Lote"))
        at.radio(key="pestana_documentos_activa").set_value(lbl_lote).run()
        assert not at.exception, at.exception
        _pulsar(at, key="btn_batch_sel_all")
        assert at.session_state["batch_select_default"] is True, \
            "Marcar Todos debe seleccionar toda la fila"
        _pulsar(at, key="btn_batch_desel_all")
        assert at.session_state["batch_select_default"] is False, \
            "Deseleccionar Todos debe vaciar la selección"
        _pulsar(at, key="btn_batch_sel_all")
        lbl_nueva = next(o for o in at.selectbox(key="batch_cat_dest_sel").options
                         if o.startswith("[NUEVA]"))
        at.selectbox(key="batch_cat_dest_sel").set_value(lbl_nueva)
        at.run()
        assert not at.exception, at.exception
        at.text_input(key="batch_new_cat_input").set_value("Cat Botones")
        _pulsar(at, key="btn_apply_batch_tags")
        assert tags.obtener_tags_documento("a.md") == ["Cat Botones"], \
            f"Clasificar Seleccionados debe asignar la categoría: {tags.obtener_tags_documento('a.md')}"


def check_botones_plantillas():
    """Plantillas: activar una plantilla de ejemplo y guardar el documento generado."""
    with tempfile.TemporaryDirectory() as td:
        docs = os.path.join(td, "docs")
        os.makedirs(docs)
        custom = os.path.join(td, "plantillas_custom.json")
        at = _app_test(
            _parches_aud_tags(td)
            + "import core.ui_plantillas as pl\n"
            "import core.plantillas as plant\n"
            f"pl.DOCS_DIR = {docs!r}\n"
            f"plant.PLANTILLAS_CUSTOM_PATH = {custom!r}\n"
            + _sesion_app("Administrador") +
            "pl.renderizar_pestana_plantillas({})\n"
        )
        at.run()
        assert not at.exception, f"plantillas debe renderizar: {at.exception}"

        _pulsar(at, key="btn_activar_plantilla_base")
        assert os.path.exists(custom), "[+ Usar] debe crear la plantilla personalizada"

        at.text_input(key="input_cat_proc_nueva").set_value("Cat Botones")
        _pulsar(at, key="btn_guardar_doc_plantilla_final")
        assert os.listdir(docs), "Guardar Documento debe escribir el .md generado"


def check_botones_mantenimientos():
    """Consulta SQL libre: el botón Ejecutar devuelve resultados con la consulta sustituida."""
    with tempfile.TemporaryDirectory() as td:
        at = _app_test(
            "import streamlit as st\n"
            "import pandas as pd\n"
            "import core.ui_mantenimientos as um\n"
            "um.ES_PRODUCCION = False\n"
            "um.ejecutar_consulta_sql = lambda q: pd.DataFrame({'total': [3]})\n"
            + _sesion_app("Administrador") +
            "um.renderizar_modulo_mantenimientos(pd.DataFrame({\n"
            "    'fecha': ['2026-01-05'],\n"
            "    'nivel_arquitectura': ['L1 - Hardware'],\n"
            "    'estado': ['Operativo'],\n"
            "    'tecnico': ['ana'],\n"
            "}))\n"
        )
        at.run()
        assert not at.exception, f"el módulo de mantenimientos debe renderizar: {at.exception}"

        _pulsar(at, label="Ejecutar")
        assert any(list(d.value.columns) == ["total"] for d in at.dataframe), \
            "Ejecutar debe mostrar el resultado de la consulta"


def check_botones_visor():
    """Visor lado a lado y ficha de diagrama: entrar en modo lectura y guardar descripción."""
    import base64

    with tempfile.TemporaryDirectory() as td:
        docs = os.path.join(td, "docs")
        os.makedirs(docs)
        png = os.path.join(td, "diagrama.png")
        with open(png, "wb") as f:
            f.write(base64.b64decode(PNG_1x1))

        at = _app_test(
            _parches_aud_tags(td)
            + "import core.visor as vis\n"
            f"vis.DOCS_DIR = {docs!r}\n"
            f"vis._ZEN_PREFS_PATH = {os.path.join(td, 'zen_prefs.json')!r}\n"
            # Ficha sin historial: el primer guardado crearía además la versión
            # base y el recuento saltaría; aquí sólo se mide la versión nueva.
            "aud.inicializar_version_inicial_si_no_existe('DIAGRAMA__demo.png', "
            "'Pie de imagen de prueba')\n"
            + _sesion_app("Operador") +
            "vis.renderizar_lado_a_lado('a.md', '# Contenido', None, 1, 'Tester', 'hoy', "
            "key_suffix='prueba')\n"
            f"vis.renderizar_diagrama_limpio({png!r}, 'DIAGRAMA__demo.png', "
            "'Pie de imagen de prueba', 1, 'Tester', 'hoy', key_suffix='diag')\n"
        )
        at.run()
        assert not at.exception, f"el visor debe renderizar: {at.exception}"

        _pulsar(at, key="btn_zen_enter_a.md_prueba")
        assert at.session_state["zen_studio_activo"] is True, \
            "Abrir en Modo Lectura debe activar el modo lectura"
        at.session_state["zen_studio_activo"] = False

        at.text_input(key="input_author_caption_DIAGRAMA__demo.png_diag").set_value("tester")
        at.text_area(key="textarea_caption_DIAGRAMA__demo.png_diag").set_value("Descripción nueva")
        vers_antes = len(_versiones("DIAGRAMA__demo.png"))
        _pulsar(at, key="btn_save_caption_DIAGRAMA__demo.png_diag")
        assert len(_versiones("DIAGRAMA__demo.png")) == vers_antes + 1, (
            f"Guardar Descripción debe crear una versión (antes={vers_antes}, "
            f"ahora={len(_versiones('DIAGRAMA__demo.png'))}, "
            f"errores={[e.value for e in at.error]})")
        with open(os.path.join(docs, "DIAGRAMA__demo.png"), encoding="utf-8") as f:
            assert "Descripción nueva" in f.read(), \
                "Guardar Descripción debe reescribir la ficha Markdown"


def check_botones_zen():
    """Modo lectura: limpiar búsqueda, atajos de teclado, salir y selector de tema."""
    with tempfile.TemporaryDirectory() as td:
        docs = {"a.md": "# Contenido de a", "b.md": "# Contenido de b"}
        at = _app_test(
            _parches_aud_tags(td)
            + "import core.visor as vis\n"
            f"vis.DOCS_DIR = {os.path.join(td, 'docs')!r}\n"
            f"vis._ZEN_PREFS_PATH = {os.path.join(td, 'zen_prefs.json')!r}\n"
            + _sesion_app("Operador") +
            "vis.renderizar_zen_studio('a.md', '# Contenido de a', None, 1, 'Tester', "
            f"'hoy', {docs!r})\n"
        )
        at.run()
        assert not at.exception, f"el modo lectura debe renderizar: {at.exception}"

        at.text_input(key="zen_search_in_doc_0").set_value("contenido")
        _pulsar(at, key="zen_buscar_limpiar")
        assert at.session_state["zen_search_version"] == 1, \
            "Limpiar debe descartar la búsqueda en curso"

        for atajo in ("zen_atajo_prev", "zen_atajo_next", "zen_atajo_font_bigger",
                      "zen_atajo_font_smaller", "zen_atajo_font_reset"):
            _pulsar(at, key=atajo)

        at.selectbox(key="zen_theme_selector").set_value("Sepia")
        at.run()
        assert not at.exception, at.exception

        _pulsar(at, key="btn_exit_zen_studio")
        assert at.session_state["zen_studio_activo"] is False, \
            "Salir del modo lectura debe desactivarlo"
        assert at.session_state["nav_seccion_activa"] == "Consultas y Búsqueda", \
            "Salir debe devolver la consola a la sección de consultas"

        _pulsar(at, key="zen_atajo_exit")


def check_botones_manual():
    """Manual de uso: avanzar, retroceder y el CTA de módulo final."""
    with tempfile.TemporaryDirectory() as td:
        at = _app_test("from core.manual import renderizar_manual_usuario\n"
                       "renderizar_manual_usuario()\n")
        at.run()
        assert not at.exception, f"el manual debe renderizar: {at.exception}"

        _pulsar(at, key="btn_top_next_1")
        assert at.session_state["manual_paso_actual"] == 2, \
            "Siguiente debe avanzar al módulo 2"
        _pulsar(at, key="btn_top_prev_2")
        assert at.session_state["manual_paso_actual"] == 1, \
            "Anterior debe volver al módulo 1"

        at.session_state["manual_paso_actual"] = 8
        at.run()
        assert not at.exception, at.exception
        _pulsar(at, key="btn_top_finish_8")
        assert at.session_state["_ir_consola"] is True, \
            "el CTA del módulo final debe enlazar con la consola"


def check_botones_notificaciones():
    """Notificaciones del sidebar: limpiar la bandeja de la sesión."""
    at = _app_test("import core.notificaciones as nt\n"
                   "nt.renderizar_notificaciones_sidebar()\n")
    at.run()
    assert not at.exception, at.exception

    at.session_state["notificaciones_sesion"] = [
        {"timestamp": "2026-01-01 10:00:00", "tipo": "exito", "mensaje": "prueba"}]
    at.run()
    assert not at.exception, at.exception
    _pulsar(at, key="btn_limpiar_notificaciones")
    assert at.session_state["notificaciones_sesion"] == [], \
        "Limpiar notificaciones debe vaciar la bandeja"


def check_botones_app_lateral():
    """app.py: expandir y colapsar el menú lateral con la sesión ya autenticada."""
    at = AppTest.from_file(os.path.join(ROOT, "app.py"))
    at.session_state["usuario_actual"] = {"username": "admin", "rol": "Administrador",
                                          "nombre": "Admin", "activo": True}
    at.session_state["auth_activa"] = True
    at.session_state["auth_ultima_actividad"] = time.time()
    at.session_state["auth_chequeo"] = time.time()
    at.session_state["sidebar_colapsado"] = True
    at.run(timeout=60)
    assert not at.exception, f"app.py con sesión debe arrancar: {at.exception}"

    _pulsar(at, key="btn_expandir_sidebar")
    assert at.session_state["sidebar_colapsado"] is False, \
        "Expandir menú debe mostrar el panel lateral"

    _pulsar(at, key="btn_colapsar_sidebar")
    assert at.session_state["sidebar_colapsado"] is True, \
        "Colapsar menú debe ocultar el panel lateral"


if __name__ == "__main__":
    check_botones_login()
    check_botones_sidebar()
    check_botones_consultas()
    check_botones_documentos()
    check_botones_plantillas()
    check_botones_mantenimientos()
    check_botones_visor()
    check_botones_zen()
    check_botones_manual()
    check_botones_notificaciones()
    check_botones_app_lateral()
    print("[OK] check_botones")

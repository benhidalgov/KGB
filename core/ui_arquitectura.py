"""Sección Arquitectura: embebe el diagrama versionado del repositorio.

El HTML vive en `assets/arquitectura/arquitectura.html` (versionado, fuera de
`data/`) y se sirve sin transformarlo salvo por el tema activo, sustituido en
`%%TEMA%%`. Si el archivo se actualiza, basta con commitearlo: se recarga por mtime.
"""
import os
import streamlit as st

from core.configuracion import ARQ_HTML_PATH

_CACHE = {"mtime": 0.0, "html": ""}

# Umbral "Alta" que ya usa core/motor.py para una coincidencia de documento.
_UMBRAL_ALTA = 20


def procesar_parametros_arquitectura(doc_store: dict) -> None:
    """Convierte un clic del diagrama (?arq_lee / ?arq_rel) en navegación de la consola.

    El visor vive en un iframe y Streamlit no devuelve valores desde uno: el único
    canal hacia Python es la URL. El visor escribe el parámetro y fuerza el rerun
    con un clic en la radio del sidebar; aquí se lee y se limpia.

    Limpiar es obligatorio: con el parámetro plantado, Streamlit deja de reenviar
    la URL viva y el siguiente clic del diagrama se pierde.
    """
    leer = str(st.query_params.get("arq_lee") or "").strip()
    relacionar = str(st.query_params.get("arq_rel") or "").strip()
    if not leer and not relacionar:
        return
    try:
        st.query_params.clear()
    except Exception:
        pass

    from core.motor import buscar_en_documentos

    servicio = leer or relacionar
    encontrados = buscar_en_documentos(servicio, doc_store)

    # Modo lectura directo solo con coincidencia fuerte: con ruido de contenido
    # se abre un documento equivocado; sin umbral se prefiere la lista.
    if leer and encontrados and encontrados[0][2] >= _UMBRAL_ALTA:
        st.session_state["zen_doc_sel"] = encontrados[0][0]
        st.session_state["zen_studio_activo"] = True
        return

    st.session_state["arq_docs_relacionados"] = {
        "etiqueta": servicio,
        "docs": [nombre for nombre, _, _ in encontrados[:5]],
    }
    st.session_state["nav_seccion_activa"] = "Documentación Técnica"
    st.session_state["tab4_cat_selector"] = "Todas"
    st.session_state["tab4_type_selector"] = "Todos"


def cargar_html_arquitectura(tema: str = "Claro") -> str:
    """Devuelve el HTML de arquitectura con el tema aplicado (vacío si no existe)."""
    if not os.path.exists(ARQ_HTML_PATH):
        return ""
    mtime = os.path.getmtime(ARQ_HTML_PATH)
    if mtime != _CACHE["mtime"]:
        with open(ARQ_HTML_PATH, "r", encoding="utf-8") as f:
            _CACHE["html"] = f.read()
        _CACHE["mtime"] = mtime
    return _CACHE["html"].replace("%%TEMA%%", "tema-oscuro" if tema == "Oscuro" else "tema-claro")


def renderizar_seccion_arquitectura():
    """Renderiza el esquema de arquitectura en un iframe autocontenido."""
    contenido = cargar_html_arquitectura(st.session_state.get("tema_visual", "Claro"))
    if not contenido:
        st.info("No se encontró el diagrama de arquitectura en `assets/arquitectura/arquitectura.html`.")
        return
    st.caption("Arquitectura de plataforma · versión del repositorio")
    st.components.v1.html(contenido, height=1120, scrolling=False)

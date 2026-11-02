"""Sección Arquitectura: embebe el diagrama versionado del repositorio.

El HTML vive en `assets/arquitectura/arquitectura.html` (versionado, fuera de
`data/`) y se sirve sin transformarlo salvo por el tema activo, sustituido en
`%%TEMA%%`. Si el archivo se actualiza, basta con commitearlo: se recarga por mtime.
"""
import os
import streamlit as st

from core.configuracion import ARQ_HTML_PATH

_CACHE = {"mtime": 0.0, "html": ""}


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
    st.components.v1.html(contenido, height=1020, scrolling=False)

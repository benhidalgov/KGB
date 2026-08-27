"""
Gestor de estilos visuales CSS para la interfaz de Streamlit.
Carga las reglas CSS desacopladas desde core/estilos.css.
"""
import os
import streamlit as st
from core.configuracion import ESTILOS_CSS_PATH


def cargar_estilos_css() -> str:
    """Lee el archivo CSS externo y retorna las reglas envueltas en <style> para Streamlit."""
    mtime = os.path.getmtime(ESTILOS_CSS_PATH) if os.path.exists(ESTILOS_CSS_PATH) else 0.0
    return _cargar_estilos_css_mtime(mtime)


@st.cache_data(show_spinner=False)
def _cargar_estilos_css_mtime(mtime: float) -> str:
    if os.path.exists(ESTILOS_CSS_PATH):
        try:
            with open(ESTILOS_CSS_PATH, "r", encoding="utf-8") as f:
                css_content = f.read()
            return f"<style>\n{css_content}\n</style>"
        except Exception:
            return ""
    return ""

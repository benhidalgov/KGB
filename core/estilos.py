"""
Gestor de estilos visuales CSS para la interfaz de Streamlit.
Carga las reglas CSS desacopladas desde core/estilos.css con soporte dinámico de temas Claro / Oscuro.
"""
import os
import streamlit as st
from core.configuracion import ESTILOS_CSS_PATH

# Reglas de sobrescritura para Modo Oscuro (se inyectan dentro de <style> sin sangría Markdown)
CSS_OSCURO_OVERRIDES = """
:root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
    --bg-canvas: #121315 !important;
    --bg-surface: #1E2024 !important;
    --bg-surface-subtle: #26292F !important;
    --bg-surface-hover: #2F333B !important;
    --border-subtle: rgba(255, 255, 255, 0.12) !important;
    --border-medium: rgba(255, 255, 255, 0.22) !important;
    --border-strong: rgba(255, 255, 255, 0.36) !important;
    --text-primary: #F0EFEA !important;
    --text-secondary: #ABA9A0 !important;
    --text-muted: #7A7870 !important;
    --btn-primary-bg: #F0EFEA !important;
    --btn-primary-text: #121315 !important;
    --btn-primary-hover: #FFFFFF !important;
    --btn-secondary-bg: #24272D !important;
    --btn-secondary-text: #F0EFEA !important;
    --btn-secondary-border: rgba(255, 255, 255, 0.18) !important;
    --btn-secondary-hover: #2E323A !important;
    --input-bg: #18191C !important;
    --input-border: rgba(255, 255, 255, 0.2) !important;
    --input-text: #F0EFEA !important;
    --pastel-green-bg: rgba(16, 185, 129, 0.16) !important;
    --pastel-green-text: #6EE7B7 !important;
    --pastel-green-border: rgba(16, 185, 129, 0.35) !important;
    --pastel-amber-bg: rgba(217, 119, 6, 0.16) !important;
    --pastel-amber-text: #FCD34D !important;
    --pastel-amber-border: rgba(217, 119, 6, 0.35) !important;
    --pastel-crit-bg: rgba(220, 38, 38, 0.16) !important;
    --pastel-crit-text: #FCA5A5 !important;
    --pastel-crit-border: rgba(239, 68, 68, 0.35) !important;
    --pastel-blue-bg: rgba(59, 130, 246, 0.16) !important;
    --pastel-blue-text: #93C5FD !important;
    --pastel-blue-border: rgba(59, 130, 246, 0.35) !important;
    --pastel-neutral-bg: rgba(255, 255, 255, 0.08) !important;
    --pastel-neutral-text: #D4D3CB !important;
    --pastel-neutral-border: rgba(255, 255, 255, 0.18) !important;
    background-color: #121315 !important;
    color: #F0EFEA !important;
}
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #121315 !important;
    color: #F0EFEA !important;
}
[data-testid="stSidebar"] {
    background-color: #181A1D !important;
    border-right-color: rgba(255, 255, 255, 0.12) !important;
}
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    background-color: #181A1D !important;
}
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"],
.bento-card, .search-result-card, [data-testid="stExpander"] {
    background-color: #1E2024 !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    background-color: #18191C !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: #F0EFEA !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #F0EFEA !important;
    box-shadow: 0 0 0 1px #F0EFEA !important;
}
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
label[data-testid="stWidgetLabel"] p,
.stTextInput label,
.stTextArea label,
.stSelectbox label {
    color: #F0EFEA !important;
    font-weight: 500 !important;
}
button:not([kind="primary"]):not([kind="primaryFormSubmit"]) {
    background-color: #24272D !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    color: #F0EFEA !important;
}
button:not([kind="primary"]):not([kind="primaryFormSubmit"]):hover {
    background-color: #2E323A !important;
    border-color: rgba(255, 255, 255, 0.32) !important;
    color: #FFFFFF !important;
}
div[data-testid="stAlert"] {
    background-color: rgba(220, 38, 38, 0.16) !important;
    border: 1px solid rgba(239, 68, 68, 0.4) !important;
    border-radius: 6px !important;
}
div[data-testid="stAlert"] * {
    color: #FCA5A5 !important;
    font-weight: 500 !important;
}
""".strip()


def cargar_estilos_css(tema: str = "Claro") -> str:
    """Lee el archivo CSS externo y retorna las reglas envueltas en <style> para Streamlit, aplicando el tema activo."""
    mtime = os.path.getmtime(ESTILOS_CSS_PATH) if os.path.exists(ESTILOS_CSS_PATH) else 0.0
    css_content = _cargar_estilos_css_mtime(mtime)
    if tema == "Oscuro":
        return f"<style>\n{css_content}\n\n/* OVERRIDES MODO OSCURO */\n{CSS_OSCURO_OVERRIDES}\n</style>"
    return f"<style>\n{css_content}\n</style>"


@st.cache_data(show_spinner=False)
def _cargar_estilos_css_mtime(mtime: float) -> str:
    if os.path.exists(ESTILOS_CSS_PATH):
        try:
            with open(ESTILOS_CSS_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

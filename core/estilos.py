"""
Gestor de estilos visuales CSS para la interfaz de Streamlit.
Carga las reglas CSS desacopladas desde core/estilos.css con soporte dinámico de temas Claro / Oscuro.
Garantiza transiciones bidireccionales completas con sobrescrituras prioritarias para cada tema.
"""
import os
import streamlit as st
from core.configuracion import ESTILOS_CSS_PATH

# Sobrescrituras obligatorias para Modo Claro
CSS_CLARO_OVERRIDES = """
:root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
    --bg-canvas: #FAF9F6 !important;
    --bg-surface: #FFFFFF !important;
    --bg-surface-subtle: #F4F3EE !important;
    --bg-surface-hover: #EFEFEA !important;
    --border-subtle: #E8E8E3 !important;
    --border-medium: #D5D5CE !important;
    --border-strong: #999990 !important;
    --text-primary: #18181B !important;
    --text-secondary: #404044 !important;
    --text-muted: #71717A !important;
    --btn-primary-bg: #18181B !important;
    --btn-primary-text: #FFFFFF !important;
    --btn-primary-hover: #27272A !important;
    --btn-secondary-bg: #FFFFFF !important;
    --btn-secondary-text: #18181B !important;
    --btn-secondary-border: #DCDCD7 !important;
    --btn-secondary-hover: #F4F4F0 !important;
    --input-bg: #FFFFFF !important;
    --input-border: #D5D5CE !important;
    --input-text: #18181B !important;
    --pastel-green-bg: #EBF5EE !important;
    --pastel-green-text: #276738 !important;
    --pastel-green-border: #CDE6D3 !important;
    --pastel-amber-bg: #FEF7E6 !important;
    --pastel-amber-text: #8C5900 !important;
    --pastel-amber-border: #F9E4B7 !important;
    --pastel-crit-bg: #FDF0F0 !important;
    --pastel-crit-text: #9C2A2A !important;
    --pastel-crit-border: #F7CACA !important;
    --pastel-blue-bg: #EEF4FE !important;
    --pastel-blue-text: #1D5CA8 !important;
    --pastel-blue-border: #C8DCFA !important;
    --pastel-neutral-bg: #F3F3F0 !important;
    --pastel-neutral-text: #52525B !important;
    --pastel-neutral-border: #E2E2DC !important;
    background-color: #FAF9F6 !important;
    color: #18181B !important;
}
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #FAF9F6 !important;
    color: #18181B !important;
}
[data-testid="stSidebar"] {
    background-color: #F4F3EE !important;
    border-right-color: #E8E8E3 !important;
}
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    background-color: #F4F3EE !important;
}
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"],
.bento-card, .search-result-card, [data-testid="stExpander"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E8E8E3 !important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border-color: #D5D5CE !important;
    color: #18181B !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #18181B !important;
    box-shadow: 0 0 0 1px #18181B !important;
}
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
label[data-testid="stWidgetLabel"] p,
.stTextInput label,
.stTextArea label,
.stSelectbox label {
    color: #18181B !important;
    font-weight: 500 !important;
}
button:not([kind="primary"]):not([kind="primaryFormSubmit"]) {
    background-color: #FFFFFF !important;
    border: 1px solid #DCDCD7 !important;
    color: #18181B !important;
}
button:not([kind="primary"]):not([kind="primaryFormSubmit"]):hover {
    background-color: #F4F4F0 !important;
    border-color: #999990 !important;
    color: #18181B !important;
}
div[data-testid="stAlert"] {
    background-color: #FDF0F0 !important;
    border: 1px solid #F7CACA !important;
    border-radius: 6px !important;
}
div[data-testid="stAlert"] * {
    color: #9C2A2A !important;
    font-weight: 500 !important;
}
""".strip()

# Sobrescrituras obligatorias para Modo Oscuro
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
    overrides = CSS_OSCURO_OVERRIDES if tema == "Oscuro" else CSS_CLARO_OVERRIDES
    return f"<style>\n{css_content}\n\n/* OVERRIDES TEMA {tema.upper()} */\n{overrides}\n</style>"


@st.cache_data(show_spinner=False)
def _cargar_estilos_css_mtime(mtime: float) -> str:
    if os.path.exists(ESTILOS_CSS_PATH):
        try:
            with open(ESTILOS_CSS_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

"""
Gestor de estilos visuales CSS para la interfaz de Streamlit.
Carga las reglas CSS desacopladas desde core/estilos.css con soporte dinámico de temas Claro / Oscuro.
"""
import os
import streamlit as st
from core.configuracion import ESTILOS_CSS_PATH

_PALETA = {
    "Claro": {
        "canvas": "#FAF9F6", "surface": "#FFFFFF", "subtle": "#F4F3EE", "hover": "#EFEFEA",
        "border_s": "#E8E8E3", "border_m": "#D5D5CE", "border_st": "#999990",
        "text_p": "#18181B", "text_s": "#404044", "text_m": "#71717A",
        "btn_p_bg": "#18181B", "btn_p_tx": "#FFFFFF", "btn_p_hv": "#27272A",
        "btn_s_bg": "#FFFFFF", "btn_s_tx": "#18181B", "btn_s_bd": "#DCDCD7", "btn_s_hv": "#F4F4F0",
        "inp_bg": "#FFFFFF", "inp_bd": "#D5D5CE", "inp_tx": "#18181B",
        "grn_bg": "#EBF5EE", "grn_tx": "#276738", "grn_bd": "#CDE6D3",
        "amb_bg": "#FEF7E6", "amb_tx": "#8C5900", "amb_bd": "#F9E4B7",
        "crit_bg": "#FDF0F0", "crit_tx": "#9C2A2A", "crit_bd": "#F7CACA",
        "blu_bg": "#EEF4FE", "blu_tx": "#1D5CA8", "blu_bd": "#C8DCFA",
        "neu_bg": "#F3F3F0", "neu_tx": "#52525B", "neu_bd": "#E2E2DC",
    },
    "Oscuro": {
        "canvas": "#121315", "surface": "#1E2024", "subtle": "#26292F", "hover": "#2F333B",
        "border_s": "rgba(255, 255, 255, 0.12)", "border_m": "rgba(255, 255, 255, 0.22)", "border_st": "rgba(255, 255, 255, 0.36)",
        "text_p": "#F0EFEA", "text_s": "#ABA9A0", "text_m": "#7A7870",
        "btn_p_bg": "#F0EFEA", "btn_p_tx": "#121315", "btn_p_hv": "#FFFFFF",
        "btn_s_bg": "#24272D", "btn_s_tx": "#F0EFEA", "btn_s_bd": "rgba(255, 255, 255, 0.18)", "btn_s_hv": "#2E323A",
        "inp_bg": "#18191C", "inp_bd": "rgba(255, 255, 255, 0.2)", "inp_tx": "#F0EFEA",
        "grn_bg": "rgba(16, 185, 129, 0.16)", "grn_tx": "#6EE7B7", "grn_bd": "rgba(16, 185, 129, 0.35)",
        "amb_bg": "rgba(217, 119, 6, 0.16)", "amb_tx": "#FCD34D", "amb_bd": "rgba(217, 119, 6, 0.35)",
        "crit_bg": "rgba(220, 38, 38, 0.16)", "crit_tx": "#FCA5A5", "crit_bd": "rgba(239, 68, 68, 0.4)",
        "blu_bg": "rgba(59, 130, 246, 0.16)", "blu_tx": "#93C5FD", "blu_bd": "rgba(59, 130, 246, 0.35)",
        "neu_bg": "rgba(255, 255, 255, 0.08)", "neu_tx": "#D4D3CB", "neu_bd": "rgba(255, 255, 255, 0.18)",
    },
}


def _generar_overrides_tema(t: str) -> str:
    c = _PALETA.get(t, _PALETA["Claro"])
    return f"""
:root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
    --bg-canvas: {c['canvas']} !important; --bg-surface: {c['surface']} !important;
    --bg-surface-subtle: {c['subtle']} !important; --bg-surface-hover: {c['hover']} !important;
    --border-subtle: {c['border_s']} !important; --border-medium: {c['border_m']} !important;
    --border-strong: {c['border_st']} !important; --text-primary: {c['text_p']} !important;
    --text-secondary: {c['text_s']} !important; --text-muted: {c['text_m']} !important;
    --btn-primary-bg: {c['btn_p_bg']} !important; --btn-primary-text: {c['btn_p_tx']} !important;
    --btn-primary-hover: {c['btn_p_hv']} !important; --btn-secondary-bg: {c['btn_s_bg']} !important;
    --btn-secondary-text: {c['btn_s_tx']} !important; --btn-secondary-border: {c['btn_s_bd']} !important;
    --btn-secondary-hover: {c['btn_s_hv']} !important; --input-bg: {c['inp_bg']} !important;
    --input-border: {c['inp_bd']} !important; --input-text: {c['inp_tx']} !important;
    --pastel-green-bg: {c['grn_bg']} !important; --pastel-green-text: {c['grn_tx']} !important;
    --pastel-green-border: {c['grn_bd']} !important; --pastel-amber-bg: {c['amb_bg']} !important;
    --pastel-amber-text: {c['amb_tx']} !important; --pastel-amber-border: {c['amb_bd']} !important;
    --pastel-crit-bg: {c['crit_bg']} !important; --pastel-crit-text: {c['crit_tx']} !important;
    --pastel-crit-border: {c['crit_bd']} !important; --pastel-blue-bg: {c['blu_bg']} !important;
    --pastel-blue-text: {c['blu_tx']} !important; --pastel-blue-border: {c['blu_bd']} !important;
    --pastel-neutral-bg: {c['neu_bg']} !important; --pastel-neutral-text: {c['neu_tx']} !important;
    --pastel-neutral-border: {c['neu_bd']} !important; background-color: {c['canvas']} !important; color: {c['text_p']} !important;
}}
.stApp, [data-testid="stAppViewContainer"] {{ background-color: {c['canvas']} !important; color: {c['text_p']} !important; }}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child, [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    background-color: {c['subtle']} !important; border-right-color: {c['border_s']} !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"],
.bento-card, .search-result-card, [data-testid="stExpander"] {{
    background-color: {c['surface']} !important; border: 1px solid {c['border_s']} !important;
}}
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {{
    background-color: {c['inp_bg']} !important; border-color: {c['inp_bd']} !important; color: {c['inp_tx']} !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{ border-color: {c['text_p']} !important; box-shadow: 0 0 0 1px {c['text_p']} !important; }}
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *, label[data-testid="stWidgetLabel"] p,
.stTextInput label, .stTextArea label, .stSelectbox label {{ color: {c['text_p']} !important; font-weight: 500 !important; }}
button:not([kind="primary"]):not([kind="primaryFormSubmit"]) {{
    background-color: {c['btn_s_bg']} !important; border: 1px solid {c['btn_s_bd']} !important; color: {c['btn_s_tx']} !important;
}}
button:not([kind="primary"]):not([kind="primaryFormSubmit"]):hover {{
    background-color: {c['btn_s_hv']} !important; color: {c['text_p']} !important;
}}
[data-testid="stSidebar"] .st-key-btn_logout_sidebar button,
[data-testid="stSidebar"] div[class*="st-key-btn_logout_sidebar"] button {{
    background-color: {c['subtle']} !important; border: 1px solid {c['border_m']} !important; color: {c['text_s']} !important;
}}
[data-testid="stSidebar"] .st-key-btn_logout_sidebar button:hover,
[data-testid="stSidebar"] div[class*="st-key-btn_logout_sidebar"] button:hover {{
    background-color: {c['hover']} !important; border-color: {c['border_st']} !important; color: {c['text_p']} !important;
}}
div[data-testid="stAlert"] {{ background-color: {c['crit_bg']} !important; border: 1px solid {c['crit_bd']} !important; border-radius: 6px !important; }}
div[data-testid="stAlert"] * {{ color: {c['crit_tx']} !important; font-weight: 500 !important; }}
""".strip()


def cargar_estilos_css(tema: str = "Claro") -> str:
    """Lee el archivo CSS externo y retorna las reglas envueltas en <style>, aplicando el tema activo."""
    mtime = os.path.getmtime(ESTILOS_CSS_PATH) if os.path.exists(ESTILOS_CSS_PATH) else 0.0
    css_base = _cargar_estilos_css_mtime(mtime)
    overrides = _generar_overrides_tema(tema)
    return f"<style>\n{css_base}\n\n/* TEMA {tema.upper()} */\n{overrides}\n</style>"


@st.cache_data(show_spinner=False)
def _cargar_estilos_css_mtime(mtime: float) -> str:
    if os.path.exists(ESTILOS_CSS_PATH):
        try:
            with open(ESTILOS_CSS_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

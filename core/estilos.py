"""
Gestor de estilos visuales CSS para la interfaz de Streamlit.
Carga las reglas CSS desacopladas desde core/estilos.css con soporte dinámico de temas Claro / Oscuro.
"""
import os
import streamlit as st
from core.configuracion import ESTILOS_CSS_PATH

# Sólo el tema Oscuro necesita overrides: la paleta Claro era idéntica al
# :root de estilos.css (35/35 variables) y todas las reglas (sidebar,
# botones, alertas, .stApp) ya leen var(), así que en Claro no había nada
# que sobreescribir — sólo el font-weight de alertas, que no está en el CSS.
_PALETA_OSCURO = {
    "canvas": "#0F172A", "surface": "#1E293B", "subtle": "#334155", "hover": "#475569",
    "border_s": "rgba(255, 255, 255, 0.12)", "border_m": "rgba(255, 255, 255, 0.22)", "border_st": "rgba(255, 255, 255, 0.36)",
    "text_p": "#F8FAFC", "text_s": "#CBD5E1", "text_m": "#94A3B8",
    "btn_p_bg": "#2563EB", "btn_p_tx": "#FFFFFF", "btn_p_hv": "#1D4ED8",
    "btn_s_bg": "#334155", "btn_s_tx": "#9CA3AF", "btn_s_bd": "rgba(255, 255, 255, 0.18)", "btn_s_hv": "#475569",
    "inp_bg": "#334155", "inp_bd": "rgba(255, 255, 255, 0.34)", "inp_tx": "#F8FAFC",
    "grn_bg": "rgba(16, 185, 129, 0.16)", "grn_tx": "#34D399", "grn_bd": "rgba(16, 185, 129, 0.35)",
    "amb_bg": "rgba(217, 119, 6, 0.16)", "amb_tx": "#F59E0B", "amb_bd": "rgba(217, 119, 6, 0.35)",
    "crit_bg": "rgba(220, 38, 38, 0.16)", "crit_tx": "#F87171", "crit_bd": "rgba(239, 68, 68, 0.4)",
    "blu_bg": "rgba(59, 130, 246, 0.16)", "blu_tx": "#60A5FA", "blu_bd": "rgba(59, 130, 246, 0.35)",
    "neu_bg": "rgba(255, 255, 255, 0.08)", "neu_tx": "#D1D5DB", "neu_bd": "rgba(255, 255, 255, 0.18)",
}

# Lo único que aplicaba en ambos temas y no está en estilos.css.
_ALERTAS_FONTWEIGHT = 'div[data-testid="stAlert"] * { font-weight: 500 !important; }'


def _generar_overrides_tema(t: str) -> str:
    if t != "Oscuro":
        return _ALERTAS_FONTWEIGHT
    c = _PALETA_OSCURO
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
    --pastel-neutral-border: {c['neu_bd']} !important;
}}
{_ALERTAS_FONTWEIGHT}""".strip()


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

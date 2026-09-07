"""
Consola Principal de Infraestructura y Operaciones.
Orquestador central con navegación lateral desacoplada para maximizar el espacio del panel principal.
"""
import os
import pandas as pd
import streamlit as st

from core.estilos import cargar_estilos_css
from core.configuracion import CSV_PATH
from core.auth import (
    es_usuario_autenticado,
    obtener_usuario_actual,
    renderizar_pantalla_login,
)
from core.procesador import (
    cargar_documentos_locales,
    limpiar_cache_documentos,
    obtener_ruta_original,
)
from core.auditoria import inicializar_version_inicial_si_no_existe
from core.visor import renderizar_zen_studio
from core.manual import renderizar_manual_usuario
from core.ui_sidebar import renderizar_sidebar
from core.ui_consultas import renderizar_modulo_consultas
from core.ui_mantenimientos import renderizar_modulo_mantenimientos
from core.ui_documentos import renderizar_pestana_documentacion
from core.ui_plantillas import renderizar_pestana_plantillas


@st.cache_data(show_spinner=False)
def obtener_dataframe_mantenimientos(mtime: float) -> pd.DataFrame:
    """Carga en caché el CSV de mantenimientos de la CMDB indexado por mtime."""
    if os.path.exists(CSV_PATH):
        try:
            return pd.read_csv(CSV_PATH)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


# -------------------------------------------------------------
# 1. CONFIGURACIÓN Y ESTILOS
# -------------------------------------------------------------
st.set_page_config(page_title="Consola de Infraestructura y Operaciones", layout="wide", initial_sidebar_state="expanded")
st.markdown(cargar_estilos_css(), unsafe_allow_html=True)
st.markdown('<div class="accent-top-bar"></div>', unsafe_allow_html=True)

# 1.1 Vista Directa del Manual en Nueva Pestaña del Navegador (?view=manual)
if st.query_params.get("view") == "manual" or st.query_params.get("manual") == "1":
    if st.session_state.pop("_ir_consola", False):
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.session_state["nav_seccion_activa"] = "Consultas y Búsqueda"
        st.rerun()
    st.markdown('<style>[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }</style>', unsafe_allow_html=True)
    renderizar_manual_usuario()
    st.stop()

# -------------------------------------------------------------
# 2. CONTROL DE AUTENTICACIÓN RBAC
# -------------------------------------------------------------
if not es_usuario_autenticado():
    renderizar_pantalla_login()
    st.stop()

# -------------------------------------------------------------
# 3. INICIALIZACIÓN DE ESTADO Y ALMACÉN DOCUMENTAL
# -------------------------------------------------------------
for k, default_v in [("historial_busquedas", []), ("messages", []), ("quick_pills_version", 0)]:
    if k not in st.session_state:
        st.session_state[k] = default_v

if "doc_store" not in st.session_state:
    st.session_state.doc_store = {}
    cargar_documentos_locales(st.session_state.doc_store)
elif any(len(v) > 150_000 for v in st.session_state.doc_store.values()):
    limpiar_cache_documentos()
    st.session_state.doc_store.clear()
    cargar_documentos_locales(st.session_state.doc_store, force=True)

# 3.1 Modo Zen Studio (Lector Inmersivo de Documentos)
if st.session_state.get("zen_studio_activo") and st.session_state.get("zen_doc_sel"):
    doc_z = st.session_state["zen_doc_sel"]
    if doc_z in st.session_state.doc_store:
        cont_z = st.session_state.doc_store[doc_z]
        hist_z = inicializar_version_inicial_si_no_existe(doc_z, cont_z)
        u_ver_z = len(hist_z)
        u_edit_z = hist_z[-1]["autor"] if hist_z else "Técnico"
        u_time_z = hist_z[-1]["timestamp"] if hist_z else "N/A"
        ruta_orig_z = obtener_ruta_original(doc_z, cont_z)
        renderizar_zen_studio(doc_z, cont_z, ruta_orig_z, u_ver_z, u_edit_z, u_time_z)
        st.stop()
    else:
        st.session_state["zen_studio_activo"] = False

# -------------------------------------------------------------
# 4. PANEL LATERAL (SIDEBAR) - NAVEGACIÓN Y CONTROL
# -------------------------------------------------------------
user_act = obtener_usuario_actual()
mtime_csv = os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0.0
df_mantenimientos_cache = obtener_dataframe_mantenimientos(mtime_csv)
total_srvs = len(df_mantenimientos_cache)

seccion_activa = renderizar_sidebar(user_act, st.session_state.doc_store, total_srvs)

# -------------------------------------------------------------
# 5. ENRUTAMIENTO DEL PANEL PRINCIPAL (ESPACIO 100% ENFOCADO)
# -------------------------------------------------------------
if "Consultas" in seccion_activa:
    renderizar_modulo_consultas(st.session_state.doc_store)

elif "Mantenimientos" in seccion_activa or "CMDB" in seccion_activa:
    renderizar_modulo_mantenimientos(df_mantenimientos_cache)

elif "Documentación" in seccion_activa:
    renderizar_pestana_documentacion(st.session_state.doc_store)

elif "Plantillas" in seccion_activa or "Runbook" in seccion_activa:
    renderizar_pestana_plantillas(st.session_state.doc_store)

elif "Zen" in seccion_activa:
    doc_zen_def = st.session_state.get("zen_doc_sel") or (sorted(st.session_state.doc_store.keys())[0] if st.session_state.doc_store else None)
    if doc_zen_def and doc_zen_def in st.session_state.doc_store:
        st.session_state["zen_studio_activo"] = True
        st.session_state["zen_doc_sel"] = doc_zen_def
        st.rerun()
    else:
        st.warning("No hay documentos indexados para previsualizar en Zen Studio.")

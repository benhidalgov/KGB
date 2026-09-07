"""
Consola Principal de Infraestructura y Operaciones.
Orquestador central de navegación, autenticación RBAC, consultas y módulos desacoplados.
"""
import os
import time
import html
import datetime
import duckdb
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
from core.motor import (
    ejecutar_consulta_sql,
    buscar_servidores_duckdb,
    buscar_en_documentos,
    extraer_fragmento_relevante,
    resaltar_terminos_en_html,
    generar_respuesta_asistente,
)
from core.ui_sidebar import renderizar_sidebar
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


def _render_kpi_grid(total_reg: int, cnt_op: int, cnt_rev: int, cnt_crit: int, tec_activo: str, pct_op: float, pct_crit: float):
    """Renderiza la cuadrícula de métricas operativas clave (KPIs) del parque de servidores."""
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card"><span class="kpi-label">Total Servidores</span><span class="kpi-value-primary">{total_reg}</span><span class="kpi-caption">Registros CMDB</span></div>
        <div class="kpi-card"><span class="kpi-label">Operativos</span><span class="kpi-value-ok">{cnt_op}</span><span class="kpi-caption">{pct_op}% del parque</span></div>
        <div class="kpi-card"><span class="kpi-label">En Revisión</span><span class="kpi-value-warn">{cnt_rev}</span><span class="kpi-caption">Atención requerida</span></div>
        <div class="kpi-card"><span class="kpi-label">Críticos</span><span class="kpi-value-crit">{cnt_crit}</span><span class="kpi-caption">{pct_crit}% del parque</span></div>
        <div class="kpi-card"><span class="kpi-label">Técnico Principal</span><span class="kpi-value-neutral" style="font-size:1.05rem;padding-top:4px;">{tec_activo}</span><span class="kpi-caption">Mayor asignación</span></div>
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------------------
# 1. CONFIGURACIÓN Y ESTILOS DE STREAMLIT
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
        st.session_state["top_navbar_view_selector"] = "Consola"
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
# 4. PANEL LATERAL (SIDEBAR) MODULARIZADO
# -------------------------------------------------------------
user_act = obtener_usuario_actual()
renderizar_sidebar(user_act, st.session_state.doc_store)

# -------------------------------------------------------------
# 5. BARRA DE NAVEGACIÓN SUPERIOR
# -------------------------------------------------------------
cant_docs = len(st.session_state.doc_store)
mtime_csv = os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0.0
df_mantenimientos_cache = obtener_dataframe_mantenimientos(mtime_csv)
total_srvs = len(df_mantenimientos_cache)

with st.container(border=True):
    col_brand, col_nav_mode, col_stats = st.columns([1.5, 1.4, 1.3], gap="small", vertical_alignment="center")
    with col_brand:
        st.markdown('<div class="navbar-brand-container"><span class="navbar-brand-badge">[CLI]</span><span class="navbar-brand-title">Consola de Infraestructura y Operaciones</span><div class="navbar-brand-badges"><span class="badge-pulse-online"><span class="pulse-dot"></span>ONLINE</span></div></div>', unsafe_allow_html=True)
    with col_nav_mode:
        if st.session_state.pop("_ir_consola", False):
            st.session_state["top_navbar_view_selector"] = "Consola"
        if "top_navbar_view_selector" not in st.session_state:
            st.session_state["top_navbar_view_selector"] = "Manual de Uso" if st.session_state.get("manual_lanzamiento") else "Consola"
        vista_seleccionada = st.segmented_control("Vista", ["Consola", "Zen Studio", "Manual de Uso"], label_visibility="collapsed", key="top_navbar_view_selector") or "Consola"
    with col_stats:
        st.markdown(f'''<div class="navbar-stats-container" style="gap:8px;">
            <div class="navbar-stat-chip"><span class="navbar-stat-label">Docs:</span><span class="navbar-stat-value-ok">{cant_docs}</span></div>
            <a href="?view=manual" target="_blank" style="text-decoration:none; font-size:0.75rem; font-weight:600; color:#6366F1; border:1px solid rgba(99,102,241,0.3); padding:4px 8px; border-radius:5px; background:rgba(99,102,241,0.06); white-space:nowrap;" title="Abre el manual paso a paso en una pestaña nueva del navegador">>_ Manual [Ext]</a>
        </div>''', unsafe_allow_html=True)

if "Manual" in str(vista_seleccionada):
    renderizar_manual_usuario()
    st.stop()

if "Zen" in str(vista_seleccionada):
    doc_zen_def = st.session_state.get("zen_doc_sel") or (sorted(st.session_state.doc_store.keys())[0] if st.session_state.doc_store else None)
    if doc_zen_def and doc_zen_def in st.session_state.doc_store:
        st.session_state["zen_studio_activo"] = True
        st.session_state["zen_doc_sel"] = doc_zen_def
        st.rerun()

# -------------------------------------------------------------
# 6. PESTAÑAS PRINCIPALES DE LA CONSOLA
# -------------------------------------------------------------
tab_chat, tab_analytics, tab_docs, tab_templates = st.tabs([
    "Consultas y Búsqueda",
    f"Historial de Mantenimientos ({total_srvs})",
    f"Documentación Técnica ({cant_docs})",
    "Plantillas y Runbooks",
])

# ----------------- TAB 1: CONSULTAS Y BÚSQUEDA -----------------
with tab_chat:
    subtab_duckdb, subtab_asistente = st.tabs(["Búsqueda Textual (DuckDB & Docs)", "Asistente Técnico (Gemini RAG)"])

    with subtab_duckdb:
        st.markdown("#### Búsqueda Textual en Inventario CMDB y Documentación")
        st.caption("Búsqueda indexada instantánea en memoria RAM (< 2 ms) sobre la CMDB y los documentos técnicos.")

        with st.form(key="form_duckdb_search", clear_on_submit=False):
            col_din, col_dbtn = st.columns([5, 1])
            with col_din:
                query_duckdb_in = st.text_input("Término:", value=st.session_state.get("duckdb_active_term", ""), placeholder="IP (10.24.0.125), servidor (BALANCER001), serie (SN-8842-A) o palabra clave...", label_visibility="collapsed")
            with col_dbtn:
                sub_duckdb = st.form_submit_button("Buscar", type="primary", width="stretch")

        active_duck_term = query_duckdb_in.strip() if sub_duckdb and query_duckdb_in.strip() else st.session_state.get("duckdb_active_term", "")
        st.session_state["duckdb_active_term"] = active_duck_term

        if not active_duck_term:
            st.markdown("""
            <div class="empty-state-container">
                <div class="empty-state-console-icon">&gt;_ Buscador :1</div>
                <div class="empty-state-title">Motor de Búsqueda Textual en RAM</div>
                <div class="empty-state-subtitle">Búsqueda ultrarrápida indexada directamente sobre los documentos técnicos locales.</div>
            </div>""", unsafe_allow_html=True)
        else:
            t0_d = time.perf_counter()
            df_srv_found = buscar_servidores_duckdb(active_duck_term)
            doc_matches_found = buscar_en_documentos(active_duck_term, st.session_state.doc_store)
            t_ms = (time.perf_counter() - t0_d) * 1000

            st.markdown(f"""
            <div style="background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.2);border-radius:6px;padding:8px 14px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div><b>Término:</b> <code>{active_duck_term}</code></div>
                <div><b>Servidores CMDB:</b> <span class="badge-ok">{len(df_srv_found)}</span></div>
                <div><b>Documentos:</b> <span class="badge-info">{len(doc_matches_found)}</span></div>
                <div><b>Tiempo:</b> <span class="badge-tag">{t_ms:.2f} ms [RAM]</span></div>
            </div>""", unsafe_allow_html=True)

            st.markdown(f"##### Servidores Coincidentes en CMDB ({len(df_srv_found)})")
            if not df_srv_found.empty:
                cols_s = [c for c in ["servidor_id", "ip", "numero_serie", "vcloud_vm", "nivel_arquitectura", "componente", "estado", "nagios_check"] if c in df_srv_found.columns]
                st.dataframe(df_srv_found[cols_s].rename(columns={"servidor_id": "Servidor", "ip": "IP", "numero_serie": "N° Serie", "vcloud_vm": "VM vCloud", "nivel_arquitectura": "Capa", "componente": "Componente", "estado": "Estado", "nagios_check": "Nagios / Chequeo"}), width="stretch", hide_index=True)
            else:
                st.info(f"No se registraron servidores para '{active_duck_term}' en la CMDB.")

            st.markdown(f"##### Documentación Técnica Coincidente ({len(doc_matches_found)})")
            if doc_matches_found:
                for doc_n, cont, sc in doc_matches_found[:5]:
                    snip = resaltar_terminos_en_html(html.escape(extraer_fragmento_relevante(cont, active_duck_term, max_chars=350)), active_duck_term)
                    st.markdown(f"""
                    <div class="search-result-card" style="margin-bottom:10px;padding:12px 14px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><div><b>Documento:</b> <code>{doc_n}</code></div><span class="badge-info">{sc} pts</span></div>
                        <div style="font-size:0.83rem;line-height:1.5;opacity:0.9;background:rgba(128,128,128,0.05);padding:8px 10px;border-radius:4px;border-left:3px solid #6366F1;">{snip}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info(f"No se encontraron coincidencias en la documentación para '{active_duck_term}'.")

            st.markdown("---")
            col_bt, col_bb = st.columns([3.5, 1.5], vertical_alignment="center")
            with col_bt:
                st.caption("¿Deseas un análisis técnico y diagnóstico asistido con IA?")
            with col_bb:
                if st.button(">_ Analizar con Asistente", width="stretch", type="primary", key="btn_bridge_to_asistente"):
                    with st.spinner("Generando análisis..."):
                        resp_c = generar_respuesta_asistente(active_duck_term, st.session_state.doc_store)
                        st.session_state.historial_busquedas.insert(0, {"query": active_duck_term, "response": resp_c, "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")})
                    st.rerun()

    with subtab_asistente:
        st.markdown("#### Asistente de Infraestructura y Operaciones (Gemini RAG)")
        st.caption("Asistente técnico especializado con inyección contextual RAG (CMDB + Documentación).")

        with st.form(key="top_asistente_form", clear_on_submit=True):
            col_cin, col_cbtn = st.columns([5, 1])
            with col_cin:
                query_asistente_in = st.text_input("Consulta:", placeholder="Ej: Explícame el procedimiento de failover de Redis y sus dependencias...", label_visibility="collapsed")
            with col_cbtn:
                sub_asistente = st.form_submit_button("Consultar Asistente", type="primary", width="stretch")

        query_c_exec = query_asistente_in.strip() if sub_asistente and query_asistente_in.strip() else None
        if query_c_exec:
            with st.spinner("Analizando infraestructura..."):
                resp = generar_respuesta_asistente(query_c_exec, st.session_state.doc_store)
                st.session_state.historial_busquedas.insert(0, {"query": query_c_exec, "response": resp, "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")})
            st.rerun()

        st.markdown("---")
        if not st.session_state.historial_busquedas:
            st.markdown("""
            <div class="empty-state-container">
                <div class="empty-state-console-icon">&gt;_ infra::rag_engine</div>
                <div class="empty-state-title">Asistente de Infraestructura y Operaciones</div>
                <div class="empty-state-subtitle">Realiza preguntas analíticas y operativas fundamentadas estrictamente en la evidencia técnica.</div>
            </div>""", unsafe_allow_html=True)
        else:
            col_rt, col_rb = st.columns([4, 1])
            with col_rt:
                st.markdown(f"<div style='font-size:0.95rem;font-weight:600;'>Historial de Consultas ({len(st.session_state.historial_busquedas)}):</div>", unsafe_allow_html=True)
            with col_rb:
                if st.button(">_ Limpiar Chat", width="stretch", key="btn_clear_search_history"):
                    st.session_state.historial_busquedas = []
                    st.session_state.messages = []
                    st.toast("[INFO] Historial reiniciado")
                    st.rerun()

            for idx, it in enumerate(st.session_state.historial_busquedas):
                badge_o = '<span class="badge-ok">[ÚLTIMA CONSULTA]</span>' if idx == 0 else f'<span class="badge-tag">[{it["timestamp"]}]</span>'
                st.markdown(f'<div style="margin-top:12px;margin-bottom:4px;font-size:0.9rem;">{badge_o} <span style="font-weight:600;margin-left:6px;">Consulta:</span> <code>{it["query"]}</code></div>', unsafe_allow_html=True)
                st.markdown(it["response"], unsafe_allow_html=True)

# ----------------- TAB 2: HISTORIAL DE MANTENIMIENTOS -----------------
with tab_analytics:
    st.subheader("Motor SQL DuckDB - Historial de Mantenimientos e Inventario")
    st.caption("Consultas analíticas estructuradas con filtrado multidimensional por fecha, nivel, estado y técnico.")

    min_date, max_date = datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)
    if not df_mantenimientos_cache.empty and 'fecha' in df_mantenimientos_cache.columns:
        try:
            fechas_dt = pd.to_datetime(df_mantenimientos_cache['fecha'], errors='coerce')
            if pd.notnull(fechas_dt.min()):
                min_date = fechas_dt.min().date()
            if pd.notnull(fechas_dt.max()):
                max_date = fechas_dt.max().date()
        except Exception:
            pass

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.1, 1.2, 1.5], gap="small")
    with col_f1:
        filtro_nivel = st.selectbox("Nivel de Arquitectura", ["Todos", "L1 - Hardware", "L2 - Virtualización", "L3 - Middleware", "L4 - Aplicación"])
    with col_f2:
        filtro_estado = st.selectbox("Estado Operativo", ["Todos", "Operativo", "En Revision", "Critico"])
    with col_f3:
        filtro_tec = st.text_input("Filtrar por Técnico", placeholder="Nombre del técnico...")
    with col_f4:
        rango_fechas = st.date_input("Rango de Fechas:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="filtro_rango_fechas_mantenimientos")

    if not os.path.exists(CSV_PATH):
        st.warning("[WARN] El archivo data/mantenimientos.csv no existe en el entorno actual.")
    else:
        conds = ["1=1"]
        if filtro_nivel != "Todos":
            conds.append(f"nivel_arquitectura = '{filtro_nivel}'")
        if filtro_estado != "Todos":
            conds.append(f"estado = '{filtro_estado}'")
        if filtro_tec.strip():
            conds.append(f"LOWER(tecnico) LIKE LOWER('%{filtro_tec.strip()}%')")
        if isinstance(rango_fechas, (tuple, list)) and len(rango_fechas) == 2:
            conds.append(f"fecha >= '{rango_fechas[0].strftime('%Y-%m-%d')}' AND fecha <= '{rango_fechas[1].strftime('%Y-%m-%d')}'")
        elif isinstance(rango_fechas, datetime.date):
            conds.append(f"fecha = '{rango_fechas.strftime('%Y-%m-%d')}'")

        try:
            df_filtrado = duckdb.sql(f"SELECT * FROM read_csv_auto('{CSV_PATH}') WHERE {' AND '.join(conds)} ORDER BY fecha DESC").df()
        except Exception as e_sql:
            st.error(f"[CRIT] Error al ejecutar consulta SQL: {e_sql}")
            df_filtrado = pd.DataFrame()

        total_reg = len(df_filtrado)
        cnt_op = int((df_filtrado['estado'] == 'Operativo').sum()) if 'estado' in df_filtrado.columns else 0
        cnt_rev = int((df_filtrado['estado'] == 'En Revision').sum()) if 'estado' in df_filtrado.columns else 0
        cnt_crit = int((df_filtrado['estado'] == 'Critico').sum()) if 'estado' in df_filtrado.columns else 0
        tec_activo = df_filtrado['tecnico'].value_counts().idxmax() if ('tecnico' in df_filtrado.columns and total_reg > 0) else "N/D"
        pct_op = round(cnt_op / total_reg * 100, 1) if total_reg > 0 else 0
        pct_crit = round(cnt_crit / total_reg * 100, 1) if total_reg > 0 else 0

        _render_kpi_grid(total_reg, cnt_op, cnt_rev, cnt_crit, tec_activo, pct_op, pct_crit)
        st.markdown(f"<div style='font-size:0.85rem;margin-bottom:8px;font-weight:500;'><span class='badge-info'>{total_reg} registros coincidentes</span></div>", unsafe_allow_html=True)
        st.dataframe(df_filtrado, width="stretch", hide_index=True)

    with st.expander("Ejecutar Consulta SQL Personalizada"):
        custom_sql = st.text_area("Sentencia SQL", value=f"SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM read_csv_auto('{CSV_PATH}') GROUP BY nivel_arquitectura")
        if st.button("Ejecutar") and os.path.exists(CSV_PATH):
            st.dataframe(ejecutar_consulta_sql(custom_sql), width="stretch")

# ----------------- TAB 3: DOCUMENTACIÓN TÉCNICA -----------------
with tab_docs:
    renderizar_pestana_documentacion(st.session_state.doc_store)

# ----------------- TAB 4: PLANTILLAS Y RUNBOOKS -----------------
with tab_templates:
    renderizar_pestana_plantillas(st.session_state.doc_store)

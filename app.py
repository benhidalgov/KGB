from core.visor import (
    renderizar_lado_a_lado,
    renderizar_original_adaptativo,
    mostrar_pdf_embebido,
)
from core.plantillas import (
    generar_doc_plantilla,
    obtener_todos_los_tipos_plantillas,
    guardar_plantilla_personalizada,
    cargar_plantillas_personalizadas,
    PLANTILLAS_BASE_RESERVADAS,
)
from core.topologia import TOPOLOGY_MERMAID, PLANTILLAS_DIAGRAMAS, INFRA_SPECS
from core.procesador import (
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    cargar_documentos_locales,
    cargar_documento_individual,
    calcular_sha256,
    sanitizar_nombre_descarga,
    generar_ficha_diagrama,
    obtener_ruta_original,
)
from core.motor import (
    ejecutar_consulta_sql,
    generar_respuesta_asistente,
)
from core.auditoria import (
    obtener_historial_versiones,
    inicializar_version_inicial_si_no_existe,
    guardar_nueva_version,
    guardar_nueva_version_excel,
    obtener_contenido_version,
    obtener_bytes_snapshot,
    cargar_hoja_excel_dataframe,
    obtener_nombres_hojas_excel,
    generar_diff_texto,
    generar_diff_lado_a_lado_html,
    obtener_todos_los_eventos_auditoria,
    generar_timeline_versiones_html,
    obtener_fecha_carga_documento,
)
from core.estilos import cargar_estilos_css
from core.configuracion import (
    CSV_PATH,
    DOCS_DIR,
    ASSETS_DIR,
    ORIGINALS_DIR,
    HISTORY_DIR,
)
from core.manual import renderizar_manual_usuario
from excel_cleaner import procesar_excel_limpio
import os
import re
import shutil
import datetime
import duckdb
import pandas as pd
import streamlit as st
import streamlit_antd_components as sac


@st.cache_data(show_spinner=False)
def obtener_dataframe_mantenimientos(mtime: float) -> pd.DataFrame:
    """Carga mantenimientos.csv en cache evitando accesos repetitivos a disco."""
    if os.path.exists(CSV_PATH):
        try:
            return pd.read_csv(CSV_PATH)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


# 1. Configuracion de Streamlit
st.set_page_config(
    page_title="Consultadora de documentos IG",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(cargar_estilos_css(), unsafe_allow_html=True)
# Eje 1: Linea de acento superior (gradiente indigo -> verde)
st.markdown('<div class="accent-top-bar"></div>', unsafe_allow_html=True)

# 2. Inicializacion de Estado y Documentos
if "historial_busquedas" not in st.session_state:
    st.session_state.historial_busquedas = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "doc_store" not in st.session_state:
    st.session_state.doc_store = {}
    cargar_documentos_locales(st.session_state.doc_store)

if "quick_pills_version" not in st.session_state:
    st.session_state.quick_pills_version = 0


# 3. Sidebar (Panel de Control e Ingesta)
with st.sidebar:
    st.markdown("""
<div class="sidebar-header-card">
    <div class="sidebar-header-title-row">
        <span class="sidebar-header-title">Panel de Control</span>
        <span class="badge-info" style="font-size:0.68rem;padding:1px 6px;">[OPERACIONES]</span>
    </div>
    <div class="sidebar-header-sub">Ingesta de activos, explorador de base documental y telemetría de motores.</div>
</div>
""", unsafe_allow_html=True)

    # Ingesta de Archivos
    st.markdown("#### Ingesta de Archivos")
    st.markdown("""
<div class="sidebar-format-tags">
    <span class="sidebar-format-tag">[PDF]</span>
    <span class="sidebar-format-tag">[DOCX]</span>
    <span class="sidebar-format-tag">[XLSX]</span>
    <span class="sidebar-format-tag">[DIAGRAMAS]</span>
    <span class="sidebar-format-tag">[MD]</span>
    <span class="sidebar-format-tag">[CSV]</span>
</div>
""", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Arrastra o selecciona tus archivos:",
        type=["pdf", "docx", "xlsx", "xls", "csv", "txt",
              "md", "pptx", "png", "jpg", "jpeg", "svg", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Formatos soportados: PDF, Word (.docx), Excel (.xlsx/.xls), Markdown (.md), Diagramas e Imágenes (.png, .jpg, .svg), CSV, TXT, PPTX."
    )

    if uploaded_files:
        for uf in uploaded_files:
            clean_name = uf.name
            clean_name = re.sub(
                r'^v\d+[-_]', '', clean_name, flags=re.IGNORECASE)
            ext_uf = os.path.splitext(clean_name)[1].lower()

            buf = uf.getbuffer().tobytes()
            nuevo_hash = calcular_sha256(buf)

            # Preservar siempre una copia del binario original en data/originals/
            orig_save_path = os.path.join(ORIGINALS_DIR, clean_name)
            with open(orig_save_path, "wb") as f_orig:
                f_orig.write(buf)

            # Caso 1: Imágenes y Diagramas
            if ext_uf in IMAGE_EXTENSIONS:
                asset_save_path = os.path.join(ASSETS_DIR, clean_name)
                with open(asset_save_path, "wb") as f_asset:
                    f_asset.write(buf)

                doc_md_name = f"DIAGRAMA__{clean_name}.md"
                md_save_path = os.path.join(DOCS_DIR, doc_md_name)

                ficha_content = generar_ficha_diagrama(
                    image_filename=clean_name,
                    orig_rel_path=f"assets/{clean_name}",
                    sha256_hash=nuevo_hash,
                    categoria="Subida desde Panel Lateral"
                )

                if os.path.exists(md_save_path):
                    with open(md_save_path, "r", encoding="utf-8", errors="ignore") as f_ex:
                        ex_content = f_ex.read()
                    if calcular_sha256(ex_content.encode("utf-8")) == calcular_sha256(ficha_content.encode("utf-8")):
                        st.toast(f"[INFO] Diagrama '{clean_name}' ya registrado sin cambios.")
                    else:
                        with open(md_save_path, "w", encoding="utf-8") as f_out:
                            f_out.write(ficha_content)
                        st.session_state.doc_store[doc_md_name] = ficha_content
                        nueva_v = guardar_nueva_version(
                            doc_name=doc_md_name,
                            nuevo_contenido=ficha_content,
                            autor="Técnico / Panel Lateral",
                            comentario=f"Actualización de activo gráfico '{clean_name}'",
                            doc_store=st.session_state.doc_store
                        )
                        st.toast(f"[OK] Diagrama '{clean_name}' actualizado [Version v{nueva_v}]")
                else:
                    with open(md_save_path, "w", encoding="utf-8") as f_out:
                        f_out.write(ficha_content)
                    st.session_state.doc_store[doc_md_name] = ficha_content
                    inicializar_version_inicial_si_no_existe(
                        doc_name=doc_md_name,
                        contenido_actual=ficha_content,
                        autor="Técnico / Panel Lateral",
                        comentario=f"Carga inicial de activo gráfico '{clean_name}'"
                    )
                    st.toast(f"[OK] Diagrama '{clean_name}' indexado como Version v1")

            # Caso 2: Documentos Ofimáticos, Excel, PDF, Texto y Markdown
            else:
                save_path = os.path.join(DOCS_DIR, clean_name)
                if os.path.exists(save_path):
                    with open(save_path, "rb") as f:
                        existente_bytes = f.read()
                    existente_hash = calcular_sha256(existente_bytes)

                    if nuevo_hash == existente_hash:
                        st.toast(f"[INFO] Archivo '{clean_name}' ya indexado sin cambios.")
                    else:
                        with open(save_path, "wb") as f:
                            f.write(buf)
                        content = cargar_documento_individual(save_path)
                        st.session_state.doc_store[clean_name] = content
                        nueva_v = guardar_nueva_version(
                            doc_name=clean_name,
                            nuevo_contenido=content,
                            autor="Técnico / Panel Lateral",
                            comentario=f"Actualización de archivo '{clean_name}' mediante carga en panel lateral",
                            doc_store=st.session_state.doc_store
                        )
                        st.toast(f"[OK] Archivo '{clean_name}' actualizado [Version v{nueva_v}]")
                else:
                    with open(save_path, "wb") as f:
                        f.write(buf)
                    content = cargar_documento_individual(save_path)
                    st.session_state.doc_store[clean_name] = content
                    inicializar_version_inicial_si_no_existe(
                        doc_name=clean_name,
                        contenido_actual=content,
                        autor="Técnico / Panel Lateral",
                        comentario="Carga inicial de archivo en panel lateral"
                    )
                    st.toast(f"[OK] Documento '{clean_name}' indexado como Version v1")

    st.markdown("---")

    # Resumen y Filtro de Base Documental
    cant_docs_side = len(st.session_state.doc_store)
    st.markdown(f"#### Explorador Documental <span class='badge-info' style='font-size:0.68rem;padding:1px 6px;'>[{cant_docs_side}]</span>", unsafe_allow_html=True)

    if cant_docs_side > 0:
        conteo_img = sum(1 for d in st.session_state.doc_store if d.startswith(
            "DIAGRAMA__") or any(d.lower().endswith(ext) for ext in IMAGE_EXTENSIONS))
        conteo_excel = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[
            1].lower() in ('.xlsx', '.xls'))
        conteo_doc = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[
            1].lower() in ('.docx', '.pdf', '.pptx', '.doc'))
        conteo_txt = sum(1 for d in st.session_state.doc_store if os.path.splitext(
            d)[1].lower() in ('.md', '.txt', '.csv') and not d.startswith("DIAGRAMA__"))

        with st.expander("Filtrar e inspeccionar archivos", expanded=False):
            opciones_filtro = [
                f"Todos ({cant_docs_side})",
                f"Diagramas ({conteo_img})",
                f"Excel ({conteo_excel})",
                f"Documentos ({conteo_doc})",
                f"Markdown ({conteo_txt})",
            ]
            tipo_filtro = st.pills(
                "Filtrar por tipo:",
                options=opciones_filtro,
                default=opciones_filtro[0],
                label_visibility="visible",
                key="sb_type_pill_filter"
            )
            if not tipo_filtro:
                tipo_filtro = opciones_filtro[0]

            doc_filter = st.text_input(
                "Buscar por nombre...", key="sb_doc_filter", placeholder="Nombre de archivo...")

            docs_filtrados = []
            for d in sorted(st.session_state.doc_store.keys()):
                ext = os.path.splitext(d)[1].lower()
                es_diag = d.startswith("DIAGRAMA__") or ext in IMAGE_EXTENSIONS

                if tipo_filtro.startswith("Diagramas") and not es_diag:
                    continue
                if tipo_filtro.startswith("Excel") and ext not in ('.xlsx', '.xls'):
                    continue
                if tipo_filtro.startswith("Documentos") and ext not in ('.docx', '.pdf', '.pptx', '.doc'):
                    continue
                if tipo_filtro.startswith("Markdown") and (es_diag or ext not in ('.md', '.txt', '.csv')):
                    continue
                if doc_filter and doc_filter.lower() not in d.lower():
                    continue
                docs_filtrados.append(d)

            if docs_filtrados:
                doc_items_html = ['<div class="sidebar-doc-list">']
                for d in docs_filtrados:
                    ext = os.path.splitext(d)[1].lower()
                    if d.startswith("DIAGRAMA__") or ext in IMAGE_EXTENSIONS:
                        tag = '<span class="badge-ok" style="font-size:0.64rem;padding:1px 4px;">[DIAGRAMA]</span>'
                        display_name = d.replace("DIAGRAMA__", "").replace(".md", "")
                    elif ext in ('.xlsx', '.xls'):
                        tag = '<span class="badge-info" style="font-size:0.64rem;padding:1px 4px;">[EXCEL]</span>'
                        display_name = d
                    elif ext in ('.pdf', '.docx', '.pptx', '.doc'):
                        tag = '<span class="badge-warn" style="font-size:0.64rem;padding:1px 4px;">[DOC]</span>'
                        display_name = d
                    else:
                        tag = '<span class="badge-tag" style="font-size:0.64rem;padding:1px 4px;">[MD]</span>'
                        display_name = d

                    size_kb = len(st.session_state.doc_store[d]) / 1024
                    f_d = obtener_fecha_carga_documento(d)
                    fecha_str = f_d.strftime('%Y-%m-%d')

                    doc_items_html.append(f"""
<div class="sidebar-doc-card">
    <div class="sidebar-doc-card-header">
        <span class="sidebar-doc-name">{display_name}</span>
        {tag}
    </div>
    <div class="sidebar-doc-meta">
        <span>{fecha_str}</span>
        <span>{size_kb:.1f} KB</span>
    </div>
</div>
""")
                doc_items_html.append('</div>')
                st.markdown("".join(doc_items_html), unsafe_allow_html=True)
            else:
                st.caption("No hay documentos que coincidan con el filtro.")
    else:
        st.info("No hay documentos indexados aún.")

    st.markdown("---")

    # Acciones Rapidas
    st.markdown("#### Acciones de Consola")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button(">_ Reindexar", help="Recarga todos los documentos desde data/docs/ y data/docs/assets/", use_container_width=True):
            cargar_documentos_locales(st.session_state.doc_store, force=True)
            st.toast("[OK] Base documental y assets reindexados con éxito")
            st.rerun()
    with col_btn2:
        if st.button(">_ Limpiar Chat", help="Reinicia el historial de búsquedas y chat", use_container_width=True):
            st.session_state.historial_busquedas = []
            st.session_state.messages = []
            st.toast("[INFO] Historial de consultas reiniciado")
            st.rerun()

    st.markdown("---")

    # Estado del Sistema
    st.markdown("#### Telemetría de Motores")
    st.markdown(f"""
<div class="sidebar-telemetry-box">
    <div class="sidebar-telemetry-row">
        <span class="sidebar-telemetry-engine">DuckDB SQL:</span>
        <span class="sidebar-status-dot-ok">ONLINE</span>
    </div>
    <div class="sidebar-telemetry-row">
        <span class="sidebar-telemetry-engine">MarkItDown Parser:</span>
        <span class="sidebar-status-dot-ok">ACTIVO</span>
    </div>
    <div class="sidebar-telemetry-row">
        <span class="sidebar-telemetry-engine">Visor Lado a Lado:</span>
        <span class="sidebar-status-dot-ok">HABILITADO</span>
    </div>
    <div class="sidebar-telemetry-row">
        <span class="sidebar-telemetry-engine">Docs en Memoria:</span>
        <span class="badge-ok" style="font-size:0.68rem;padding:1px 6px;">{cant_docs_side} docs</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # Footer del Sidebar
    session_ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    st.markdown(f"""
<div class="sidebar-footer">
    <span class="sidebar-footer-version">[v1.0] Copilot</span>
    <span class="sidebar-footer-ts">Sesion: {session_ts}</span>
</div>
""", unsafe_allow_html=True)


# 4. Navbar Hero Card (Barra Flotante con Relieve)
cant_docs = len(st.session_state.doc_store)
mtime_csv = os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0.0
df_mantenimientos_cache = obtener_dataframe_mantenimientos(mtime_csv)
total_srvs = len(df_mantenimientos_cache)

with st.container(border=True):
    st.markdown('<div class="navbar-anchor" style="display:none;"></div>', unsafe_allow_html=True)
    col_brand, col_nav_mode, col_stats = st.columns([1.8, 1.3, 1.0], gap="small", vertical_alignment="center")

    with col_brand:
        st.markdown("""
        <div class="navbar-brand-container">
            <span class="navbar-brand-badge">[CLI]</span>
            <span class="navbar-brand-title">Copilot de Infraestructura</span>
            <div class="navbar-brand-badges">
                <span class="badge-pulse-online"><span class="pulse-dot"></span>ONLINE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_nav_mode:
        vista_seleccionada = st.segmented_control(
            label="Vista de Navegación",
            options=["Consola", "Manual de Uso"],
            default="Consola",
            label_visibility="collapsed",
            key="top_navbar_view_selector"
        )
        if not vista_seleccionada:
            vista_seleccionada = "Consola"

    with col_stats:
        st.markdown(f"""
        <div class="navbar-stats-container">
            <div class="navbar-stat-chip">
                <span class="navbar-stat-label">Documentos:</span>
                <span class="navbar-stat-value-ok">{cant_docs}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Verificación de Vista Seleccionada en Navbar
if "Manual" in str(vista_seleccionada):
    renderizar_manual_usuario()
    st.stop()


# 5. Pestañas Principales
tab_chat, tab_analytics, tab_docs, tab_templates = st.tabs([
    "Consultas y Búsqueda",
    f"Historial de Mantenimientos ({total_srvs})",
    f"Documentación Técnica ({cant_docs})",
    "Plantillas y Runbooks"
])

# ----------------- TAB 1: BUSCADOR Y ASISTENTE  -----------------
with tab_chat:
    # 1. Barra de Búsqueda Superior (Always on Top)
    with st.form(key="top_search_form", clear_on_submit=True):
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            query_input = st.text_input(
                "Buscar en infraestructura y documentación:",
                placeholder="Ingrese su consulta técnica (ej: BALANCER001, JWT, 10.24.0.125, Failover Redis, SN-8842-A)...",
                label_visibility="collapsed"
            )
        with col_btn:
            submitted = st.form_submit_button(
                "Buscar", type="primary", use_container_width=True)

    # 2. Chips de consultas rapidas responsivos
    st.markdown("<div style='margin-top: -6px; margin-bottom: 6px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.7;'>Consultas rapidas:</div>", unsafe_allow_html=True)
    quick_queries = [
        ">_ BALANCER001",
        ">_ Autenticacion JWT",
        ">_ 10.24.0.125",
        ">_ Failover Redis",
        ">_ SN-8842-A",
        ">_ PureStorage SAN",
    ]
    if "quick_pills_version" not in st.session_state:
        st.session_state.quick_pills_version = 0

    pills_key = f"tab1_quick_query_pills_{st.session_state.quick_pills_version}"
    selected_quick = st.pills(
        "Consultas rapidas",
        options=quick_queries,
        default=None,
        label_visibility="collapsed",
        key=pills_key
    )
    prompt_rapido = None
    if selected_quick:
        prompt_rapido = selected_quick.replace(">_ ", "").strip()
        st.session_state.quick_pills_version += 1

    query_a_ejecutar = prompt_rapido if prompt_rapido else (
        query_input.strip() if submitted and query_input.strip() else None)

    if query_a_ejecutar:
        with st.spinner("Procesando consulta..."):
            respuesta = generar_respuesta_asistente(
                query_a_ejecutar, st.session_state.doc_store)
            # Guardar al inicio (índice 0) para que aparezca primero arriba
            st.session_state.historial_busquedas.insert(0, {
                "query": query_a_ejecutar,
                "response": respuesta,
                "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
            })
        st.rerun()

    st.markdown("---")

    # 3. Resultados: Los mas nuevos se muestran ARRIBA
    if not st.session_state.historial_busquedas:
        st.markdown("""
<div class="empty-state-container">
    <div class="empty-state-console-icon">&gt;_ infraestructura</div>
    <div class="empty-state-title">Consola de Busqueda Unificada</div>
    <div class="empty-state-subtitle">
        Consulta el inventario CMDB, procedimientos tecnicos, diagramas de topologia
        y documentacion de contingencia desde un unico punto de acceso.
    </div>
    <div class="empty-state-caps-grid">
        <div class="empty-cap-card" style="background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.22);">
            <div class="empty-cap-card-label" style="color:#6366F1;">[INFO] Inventario CMDB</div>
            <div class="empty-cap-card-title">Consulta analitica SQL</div>
            <div class="empty-cap-card-desc">Por numero de serie, IP, servidor, tecnico o nivel de arquitectura L1-L4.</div>
        </div>
        <div class="empty-cap-card" style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.22);">
            <div class="empty-cap-card-label" style="color:#10B981;">[OK] Procedimientos</div>
            <div class="empty-cap-card-title">Recuperacion semantica</div>
            <div class="empty-cap-card-desc">Manuales de contingencia, runbooks, rollback y procedimientos operativos estandar.</div>
        </div>
        <div class="empty-cap-card" style="background:rgba(217,119,6,0.07);border:1px solid rgba(217,119,6,0.22);">
            <div class="empty-cap-card-label" style="color:#D97706;">[DOC] Diagramas</div>
            <div class="empty-cap-card-title">Topologia y arquitectura</div>
            <div class="empty-cap-card-desc">Inspeccion visual de diagramas con visor lado a lado (Side-by-Side) y control de versiones.</div>
        </div>
    </div>
</div>
        """, unsafe_allow_html=True)
    else:
        col_res_t, col_res_btn = st.columns([4, 1])
        with col_res_t:
            st.markdown(
                f"<div style='font-size: 0.95rem; font-weight: 600;'>Historial de Resultados ({len(st.session_state.historial_busquedas)} consultas):</div>", unsafe_allow_html=True)
        with col_res_btn:
            if st.button("Limpiar Resultados", use_container_width=True, key="btn_clear_search_history_top"):
                st.session_state.historial_busquedas = []
                st.rerun()

        for idx, item in enumerate(st.session_state.historial_busquedas):
            es_ultimo = (idx == 0)
            badge_orden = '<span class="badge-ok">[ÚLTIMA CONSULTA]</span>' if es_ultimo else f'<span class="badge-tag">[{item["timestamp"]}]</span>'

            st.markdown(f"""
            <div style="margin-top: 12px; margin-bottom: 4px; font-size: 0.9rem;">
                {badge_orden} <span style="font-weight: 600; margin-left: 6px;">Consulta:</span> <code>{item['query']}</code>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(item["response"], unsafe_allow_html=True)

# ----------------- TAB 2: ANALITICA DUCKDB -----------------
with tab_analytics:
    st.subheader("Motor SQL DuckDB - Historial de Mantenimientos e Inventario")
    st.caption(
        "Consultas analíticas estructuradas con filtrado multidimensional por fecha, nivel, estado y técnico.")

    # Límites temporales desde el dataset
    min_date = datetime.date(2026, 1, 1)
    max_date = datetime.date(2026, 12, 31)
    if not df_mantenimientos_cache.empty and 'fecha' in df_mantenimientos_cache.columns:
        try:
            fechas_dt = pd.to_datetime(df_mantenimientos_cache['fecha'], errors='coerce')
            val_min = fechas_dt.min()
            val_max = fechas_dt.max()
            if pd.notnull(val_min):
                min_date = val_min.date()
            if pd.notnull(val_max):
                max_date = val_max.date()
        except Exception:
            pass

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.1, 1.2, 1.5], gap="small")
    with col_f1:
        filtro_nivel = st.selectbox("Nivel de Arquitectura", [
                                    "Todos", "L1 - Hardware", "L2 - Virtualización", "L3 - Middleware", "L4 - Aplicación"])
    with col_f2:
        filtro_estado = st.selectbox(
            "Estado Operativo", ["Todos", "Operativo", "En Revision", "Critico"])
    with col_f3:
        filtro_tec = st.text_input("Filtrar por Técnico", placeholder="Nombre del técnico...")
    with col_f4:
        rango_fechas = st.date_input(
            "Rango de Fechas:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="filtro_rango_fechas_mantenimientos"
        )

    if not os.path.exists(CSV_PATH):
        st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(217,119,6,0.08) 0%, rgba(217,119,6,0.03) 100%);
    border: 1px solid rgba(217,119,6,0.30);
    border-left: 4px solid #D97706;
    border-radius: 0 10px 10px 0;
    padding: 16px 20px;
    margin: 16px 0;
">
    <div style="font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #D97706; margin-bottom: 6px;">[WARN] Inventario no disponible</div>
    <div style="font-size: 0.9rem; line-height: 1.6;">
        El archivo <code>data/mantenimientos.csv</code> no existe en el entorno actual.<br/>
        Suba el archivo CSV de mantenimientos mediante el <b>Panel de Ingesta</b> en el sidebar,
        o copie el archivo a <code>data/mantenimientos.csv</code> y use el boton <b>Reindexar</b>.
    </div>
</div>
        """, unsafe_allow_html=True)
    else:
        condiciones = ["1=1"]
        if filtro_nivel != "Todos":
            condiciones.append(f"nivel_arquitectura = '{filtro_nivel}'")
        if filtro_estado != "Todos":
            condiciones.append(f"estado = '{filtro_estado}'")
        if filtro_tec.strip():
            condiciones.append(
                f"LOWER(tecnico) LIKE LOWER('%{filtro_tec.strip()}%')")

        if isinstance(rango_fechas, (tuple, list)):
            if len(rango_fechas) == 2:
                f_ini, f_fin = rango_fechas
                condiciones.append(f"fecha >= '{f_ini.strftime('%Y-%m-%d')}' AND fecha <= '{f_fin.strftime('%Y-%m-%d')}'")
            elif len(rango_fechas) == 1:
                f_ini = rango_fechas[0]
                condiciones.append(f"fecha >= '{f_ini.strftime('%Y-%m-%d')}'")
        elif isinstance(rango_fechas, datetime.date):
            condiciones.append(f"fecha = '{rango_fechas.strftime('%Y-%m-%d')}'")

        sql_query = f"SELECT * FROM read_csv_auto('{CSV_PATH}') WHERE {' AND '.join(condiciones)} ORDER BY fecha DESC"
        try:
            df_filtrado = duckdb.sql(sql_query).df()
        except Exception as e:
            st.error(f"[CRIT] Error al ejecutar la consulta SQL: {e}")
            df_filtrado = pd.DataFrame()

        # KPI Dashboard: Fila de metricas dinamicas
        total_reg = len(df_filtrado)
        cnt_op = int((df_filtrado['estado'] == 'Operativo').sum()) if 'estado' in df_filtrado.columns else 0
        cnt_rev = int((df_filtrado['estado'] == 'En Revision').sum()) if 'estado' in df_filtrado.columns else 0
        cnt_crit = int((df_filtrado['estado'] == 'Critico').sum()) if 'estado' in df_filtrado.columns else 0

        tec_activo = "N/D"
        if 'tecnico' in df_filtrado.columns and total_reg > 0:
            try:
                tec_activo = df_filtrado['tecnico'].value_counts().idxmax()
            except Exception:
                pass

        pct_op = round((cnt_op / total_reg * 100), 1) if total_reg > 0 else 0
        pct_crit = round((cnt_crit / total_reg * 100), 1) if total_reg > 0 else 0

        st.markdown(f"""
<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 14px 0 18px 0;">

  <div style="
    background: linear-gradient(135deg, rgba(99,102,241,0.10) 0%, rgba(99,102,241,0.04) 100%);
    border: 1px solid rgba(99,102,241,0.28);
    border-top: 3px solid #6366F1;
    border-radius: 10px;
    padding: 14px 16px;
    animation: fadeInUp 0.3s ease both;
  ">
    <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.75; margin-bottom: 6px;">Total Registros</div>
    <div style="font-size: 1.85rem; font-weight: 700; line-height: 1; color: #6366F1;">{total_reg}</div>
    <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 4px;">en el periodo filtrado</div>
  </div>

  <div style="
    background: linear-gradient(135deg, rgba(16,185,129,0.10) 0%, rgba(16,185,129,0.04) 100%);
    border: 1px solid rgba(16,185,129,0.28);
    border-top: 3px solid #10B981;
    border-radius: 10px;
    padding: 14px 16px;
    animation: fadeInUp 0.35s ease both;
  ">
    <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.75; margin-bottom: 6px;">Operativos</div>
    <div style="font-size: 1.85rem; font-weight: 700; line-height: 1; color: #10B981;">{cnt_op}</div>
    <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 4px;">{pct_op}% del total</div>
  </div>

  <div style="
    background: linear-gradient(135deg, rgba(217,119,6,0.10) 0%, rgba(217,119,6,0.04) 100%);
    border: 1px solid rgba(217,119,6,0.28);
    border-top: 3px solid #D97706;
    border-radius: 10px;
    padding: 14px 16px;
    animation: fadeInUp 0.40s ease both;
  ">
    <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.75; margin-bottom: 6px;">En Revision</div>
    <div style="font-size: 1.85rem; font-weight: 700; line-height: 1; color: #D97706;">{cnt_rev}</div>
    <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 4px;">revision activa</div>
  </div>

  <div style="
    background: linear-gradient(135deg, rgba(106, 57, 123, 0.14) 0%, rgba(106, 57, 123, 0.04) 100%);
    border: 1px solid rgba(106, 57, 123, 0.30);
    border-top: 3px solid rgb(106, 57, 123);
    border-radius: 10px;
    padding: 14px 16px;
    animation: fadeInUp 0.45s ease both;
  ">
    <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.75; margin-bottom: 6px;">Criticos</div>
    <div style="font-size: 1.85rem; font-weight: 700; line-height: 1; color: rgb(106, 57, 123);">{cnt_crit}</div>
    <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 4px;">{pct_crit}% del total</div>
  </div>

  <div style="
    background: linear-gradient(135deg, rgba(128,128,128,0.08) 0%, rgba(128,128,128,0.03) 100%);
    border: 1px solid rgba(128,128,128,0.22);
    border-top: 3px solid rgba(128,128,128,0.45);
    border-radius: 10px;
    padding: 14px 16px;
    animation: fadeInUp 0.50s ease both;
  ">
    <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.75; margin-bottom: 6px;">Tecnico Mas Activo</div>
    <div style="font-size: 1.05rem; font-weight: 700; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{tec_activo}</div>
    <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 4px;">mayor cantidad de registros</div>
  </div>

</div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div style='font-size: 0.85rem; margin-bottom: 8px; font-weight: 500;'><span class='badge-info'>{total_reg} registros coincidentes</span></div>", unsafe_allow_html=True)
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    with st.expander("Ejecutar Consulta SQL Personalizada"):
        custom_sql = st.text_area(
            "Sentencia SQL",
            value=f"SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM read_csv_auto('{CSV_PATH}') GROUP BY nivel_arquitectura"
        )
        if st.button("Ejecutar"):
            if not os.path.exists(CSV_PATH):
                st.warning("[WARN] El archivo mantenimientos.csv no esta disponible. Cargue el CSV primero.")
            else:
                df_custom = ejecutar_consulta_sql(custom_sql)
                st.dataframe(df_custom, use_container_width=True)


# ----------------- TAB 3: DOCUMENTACION TECNICA Y VERSIONADO -----------------
with tab_docs:
    st.subheader(
        "Repositorio de Documentacion Tecnica, Diagramas y Versionado")
    st.caption(
        "Manuales de contingencia, procedimientos operativos, visor Lado a Lado (Side-by-Side) y control de cambios.")

    if st.session_state.doc_store:
        # Mapa de fechas de carga / indexación
        mapa_fechas_docs = {d: obtener_fecha_carga_documento(d) for d in st.session_state.doc_store.keys()}
        fechas_validas = [f for f in mapa_fechas_docs.values() if f]
        min_doc_date = min(fechas_validas) if fechas_validas else datetime.date.today()
        max_doc_date = max(fechas_validas) if fechas_validas else datetime.date.today()

        col_tipo_t4, col_fecha_t4, col_doc_sel = st.columns([1.1, 1.3, 2.2], gap="small")
        with col_tipo_t4:
            filtro_t4 = st.selectbox(
                "Tipo de Documento",
                [
                    "Todos",
                    "Diagramas e Imágenes (.png, .jpg, .svg)",
                    "Excel (.xlsx, .xls)",
                    "Documentos (.docx, .pdf, .pptx)",
                    "Markdown / Texto (.md, .txt)"
                ],
                key="tab4_type_selector"
            )

        with col_fecha_t4:
            rango_fecha_doc = st.date_input(
                "Fecha de Carga / Modificación:",
                value=(min_doc_date, max_doc_date),
                min_value=min_doc_date,
                max_value=max_doc_date,
                key="tab4_date_range_selector"
            )

        docs_disponibles_t4 = []
        for d in sorted(st.session_state.doc_store.keys()):
            ext = os.path.splitext(d)[1].lower()
            es_diag = d.startswith("DIAGRAMA__") or ext in IMAGE_EXTENSIONS

            if filtro_t4.startswith("Diagramas") and not es_diag:
                continue
            if filtro_t4.startswith("Excel") and ext not in ('.xlsx', '.xls'):
                continue
            if filtro_t4.startswith("Documentos") and ext not in ('.docx', '.pdf', '.pptx', '.doc'):
                continue
            if filtro_t4.startswith("Markdown") and (es_diag or ext not in ('.md', '.txt', '.csv')):
                continue

            # Filtrar por fecha de carga / modificacion
            f_doc = mapa_fechas_docs.get(d)
            if f_doc:
                if isinstance(rango_fecha_doc, (tuple, list)) and len(rango_fecha_doc) == 2:
                    if not (rango_fecha_doc[0] <= f_doc <= rango_fecha_doc[1]):
                        continue
                elif isinstance(rango_fecha_doc, datetime.date):
                    if f_doc != rango_fecha_doc:
                        continue

            docs_disponibles_t4.append(d)

        with col_doc_sel:
            if docs_disponibles_t4:
                doc_seleccionado = st.selectbox(
                    f"Seleccione Documento ({len(docs_disponibles_t4)} disponibles)",
                    docs_disponibles_t4,
                    key="tab4_doc_selector"
                )
            else:
                doc_seleccionado = None
                st.warning("No hay documentos que coincidan con el tipo y rango de fechas seleccionados.")

        if doc_seleccionado:
            doc_content = st.session_state.doc_store.get(doc_seleccionado, "")
            historial = inicializar_version_inicial_si_no_existe(
                doc_seleccionado, doc_content)
            ultima_version = len(historial)
            ultimo_editor = historial[-1]["autor"] if historial else "Desconocido"
            ultimo_timestamp = historial[-1]["timestamp"] if historial else "N/A"
            fecha_carga_inicial = historial[0]["timestamp"] if historial else "N/A"
            fecha_carga_corta = fecha_carga_inicial.split()[0] if " " in fecha_carga_inicial else fecha_carga_inicial
            ruta_original = obtener_ruta_original(
                doc_seleccionado, doc_content)

            st.markdown(f"""
<div style="background-color: rgba(128, 128, 128, 0.08); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 6px; padding: 8px 14px; margin-bottom: 12px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
    <div><b>Documento:</b> <span style="color:#6366F1; font-weight: 600; font-family: monospace;">{doc_seleccionado}</span></div>
    <div><b>Versión Activa:</b> <span class="badge-ok">v{ultima_version}</span></div>
    <div><b>Fecha de Carga:</b> <span class="badge-tag">[{fecha_carga_corta}]</span></div>
    <div><b>Último Editor:</b> <span style="color:#10B981; font-weight: 500;">{ultimo_editor}</span></div>
    <div><b>Actualizado:</b> <span style="opacity: 0.75;">{ultimo_timestamp}</span></div>
</div>
""", unsafe_allow_html=True)

            subtab_view, subtab_edit, subtab_hist = st.tabs([
                "Visualización Lado a Lado",
                "Editar Documento",
                f"Historial de Versiones ({ultima_version})"
            ])

            # SUBTAB 1: VISUALIZACION LADO A LADO
            with subtab_view:
                renderizar_lado_a_lado(
                    doc_name=doc_seleccionado,
                    md_content=doc_content,
                    ruta_original=ruta_original,
                    ultima_version=ultima_version,
                    ultimo_editor=ultimo_editor,
                    ultimo_timestamp=ultimo_timestamp,
                    key_suffix="tab3_view"
                )

                st.markdown("---")
                col_dl_act, col_dl_info = st.columns([1.5, 2.5])
                with col_dl_act:
                    excel_orig_path = os.path.join(DOCS_DIR, doc_seleccionado)
                    es_excel = doc_seleccionado.lower().endswith(
                        ('.xlsx', '.xls')) and os.path.exists(excel_orig_path)

                    if es_excel:
                        with open(excel_orig_path, "rb") as f:
                            excel_bytes = f.read()
                        st.download_button(
                            label=f"Descargar Versión Activa v{ultima_version} (.xlsx)",
                            data=excel_bytes,
                            file_name=sanitizar_nombre_descarga(
                                doc_seleccionado, ultima_version, ".xlsx"),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key=f"dl_active_excel_{doc_seleccionado}"
                        )
                    else:
                        st.download_button(
                            label=f"Descargar Versión Activa v{ultima_version} (.md)",
                            data=doc_content.encode("utf-8"),
                            file_name=sanitizar_nombre_descarga(
                                doc_seleccionado, ultima_version, ".md"),
                            mime="text/markdown",
                            use_container_width=True,
                            key=f"dl_active_md_{doc_seleccionado}"
                        )
                with col_dl_info:
                    st.caption(
                        f"Descarga una copia local del documento en su versión activa actual (**v{ultima_version}**). Para descargar versiones históricas anteriores, utilice la pestaña **Historial de Versiones**.")

            # SUBTAB 2: EDICION
            with subtab_edit:
                excel_orig_path = os.path.join(DOCS_DIR, doc_seleccionado)
                es_excel = doc_seleccionado.lower().endswith(
                    ('.xlsx', '.xls')) and os.path.exists(excel_orig_path)

                if es_excel:
                    mtime_excel = os.path.getmtime(excel_orig_path) if os.path.exists(excel_orig_path) else 0.0
                    sheet_names_edit = obtener_nombres_hojas_excel(excel_orig_path, mtime_excel)

                    st.markdown("#### Edición en Vivo de Libro Excel")
                    st.caption(
                        "Modifique los valores de las celdas directamente en la cuadrícula o inserte nuevas filas. Al guardar se creará una versión incremental.")

                    col_es1, col_es2 = st.columns([1.5, 2.5])
                    with col_es1:
                        hoja_editar = st.selectbox("Seleccionar Hoja a Modificar:", sheet_names_edit if sheet_names_edit else [
                                                   "Hoja1"], key=f"edit_sheet_sel_{doc_seleccionado}")
                    with col_es2:
                        col_ae1, col_ae2 = st.columns(2)
                        with col_ae1:
                            autor_edit = st.text_input(
                                "Editor / Técnico Responsable (*)", placeholder="Ej: Juan Pérez / DevOps", key=f"author_input_grid_{doc_seleccionado}")
                        with col_ae2:
                            motivo_edit = st.text_input(
                                "Motivo del Cambio (*)", placeholder="Ej: Actualización de IP de nodo", key=f"motive_input_grid_{doc_seleccionado}")

                    df_to_edit = cargar_hoja_excel_dataframe(
                        excel_orig_path, hoja_editar, mtime_excel)
                    st.markdown(
                        f"**Cuadrícula de la Hoja:** `{hoja_editar}` *(Doble clic en una celda para editar, use el botón final para agregar filas)*")
                    df_modificado = st.data_editor(
                        df_to_edit, use_container_width=True, num_rows="dynamic", height=480, key=f"grid_editor_{doc_seleccionado}_{hoja_editar}")

                    col_btn_save, col_btn_info = st.columns([2, 3])
                    with col_btn_save:
                        if st.button(f"Guardar y Publicar Versión v{ultima_version + 1}", type="primary", use_container_width=True, key=f"btn_save_grid_{doc_seleccionado}"):
                            if not autor_edit or not autor_edit.strip():
                                st.error(
                                    "Error de Auditoría: Debe ingresar el Editor / Técnico Responsable para guardar la nueva versión.")
                            elif not motivo_edit or not motivo_edit.strip():
                                st.error(
                                    "Error de Auditoría: Debe ingresar el Motivo del Cambio para mantener la trazabilidad.")
                            else:
                                nueva_v = guardar_nueva_version_excel(
                                    doc_name=doc_seleccionado,
                                    sheet_name=hoja_editar,
                                    df_nuevo=df_modificado,
                                    autor=autor_edit.strip(),
                                    comentario=motivo_edit.strip(),
                                    doc_store=st.session_state.doc_store
                                )
                                st.toast(
                                    f"Versión v{nueva_v} guardada y reindexada exitosamente")
                                st.success(
                                    f"¡Versión [Version v{nueva_v}] creada con éxito! Responsable: {autor_edit.strip()}. La hoja '{hoja_editar}' y el Copilot han sido actualizados.")
                                st.rerun()
                    with col_btn_info:
                        st.caption(
                            "*Al guardar, se preservará un snapshot del libro Excel y la base documental se reindexará automáticamente con registro de auditoría.*")

                else:
                    st.markdown(
                        "#### Edición en Vivo y Generación de Nueva Versión")
                    st.caption(
                        "Modifique los procedimientos, especificaciones o diagramas. Al guardar, se preservará una copia histórica inmutable.")

                    col_e1, col_e2 = st.columns([1, 2])
                    with col_e1:
                        autor_edit = st.text_input(
                            "Editor / Técnico Responsable (*)", placeholder="Ej: Juan Pérez / DevOps", key=f"author_input_{doc_seleccionado}")
                    with col_e2:
                        motivo_edit = st.text_input(
                            "Motivo o Resumen del Cambio (*)", placeholder="Ej: Actualización de parámetros técnicos", key=f"motive_input_{doc_seleccionado}")

                    texto_editado = st.text_area(
                        "Contenido del Documento (Markdown)", value=doc_content, height=450, key=f"textarea_edit_{doc_seleccionado}")

                    col_btn_save, col_btn_info = st.columns([2, 3])
                    with col_btn_save:
                        if st.button(f"Guardar y Publicar Versión v{ultima_version + 1}", type="primary", use_container_width=True, key=f"btn_save_{doc_seleccionado}"):
                            if not autor_edit or not autor_edit.strip():
                                st.error(
                                    "Error de Auditoría: Debe ingresar el Editor / Técnico Responsable para guardar la nueva versión.")
                            elif not motivo_edit or not motivo_edit.strip():
                                st.error(
                                    "Error de Auditoría: Debe ingresar el Motivo del Cambio para mantener la trazabilidad.")
                            else:
                                nueva_v = guardar_nueva_version(
                                    doc_name=doc_seleccionado,
                                    nuevo_contenido=texto_editado,
                                    autor=autor_edit.strip(),
                                    comentario=motivo_edit.strip(),
                                    doc_store=st.session_state.doc_store
                                )
                                if nueva_v == ultima_version:
                                    st.toast("[INFO] El contenido no presenta cambios respecto a la versión actual")
                                    st.info("[INFO] No se generó un nuevo snapshot porque el contenido es idéntico a la versión actual.")
                                else:
                                    st.toast(
                                        f"[OK] Versión v{nueva_v} guardada y reindexada exitosamente")
                                    st.success(
                                        f"¡Versión [Version v{nueva_v}] creada con éxito! Responsable: {autor_edit.strip()}. El Copilot y el RAG han sido actualizados en memoria.")
                                    st.rerun()
                    with col_btn_info:
                        st.caption(
                            "*Al guardar, la versión actual pasará al historial inmutable con firma SHA-256 y el asistente Copilot responderá con la información actualizada inmediatamente.*")

            # SUBTAB 3: HISTORIAL Y CONTROL DE VERSIONES
            with subtab_hist:
                st.markdown("#### Historial de Revisiones y Control de Cambios")
                st.caption(
                    "Registro cronológico inmutable de revisiones con firma criptográfica SHA-256, descarga de snapshots y reversión controlada (Rollback).")

                # 1. Tabla de Historial
                columnas_hist = ["version", "timestamp", "autor", "comentario", "caracteres"]
                tiene_sha = any("sha256" in item and item["sha256"] for item in historial)
                if tiene_sha:
                    columnas_hist.append("sha256")
                
                df_hist = pd.DataFrame(historial)
                cols_presentes = [c for c in columnas_hist if c in df_hist.columns]
                df_hist = df_hist[cols_presentes]
                
                map_nombres = {
                    "version": "Versión",
                    "timestamp": "Fecha y Hora",
                    "autor": "Editor / Responsable",
                    "comentario": "Motivo del Cambio",
                    "caracteres": "Tamaño (chars)",
                    "sha256": "Firma SHA-256"
                }
                df_hist.columns = [map_nombres.get(c, c) for c in cols_presentes]
                st.dataframe(df_hist, use_container_width=True, hide_index=True)

                st.markdown("---")

                # 2. Inspección y Descarga de Versiones
                st.markdown("##### Inspeccionar y Descargar Versión Previa")
                opciones_versiones = {
                    f"v{item['version']} - {item['timestamp']} ({item['autor']}): {item['comentario']}": item
                    for item in reversed(historial)
                }

                v_sel_label = st.selectbox(
                    "Seleccione una versión para inspeccionar o descargar:",
                    list(opciones_versiones.keys()),
                    key=f"select_hist_ver_{doc_seleccionado}"
                )
                item_seleccionado = opciones_versiones[v_sel_label]
                contenido_snapshot = obtener_contenido_version(
                    doc_seleccionado, item_seleccionado["archivo_snapshot"]
                )

                excel_snap = item_seleccionado.get("archivo_excel_snapshot")
                col_dl_v1, col_dl_v2 = st.columns([1, 1])

                with col_dl_v1:
                    if excel_snap:
                        excel_snap_bytes = obtener_bytes_snapshot(doc_seleccionado, excel_snap)
                        if excel_snap_bytes:
                            st.download_button(
                                label=f"Descargar Versión v{item_seleccionado['version']} (.xlsx)",
                                data=excel_snap_bytes,
                                file_name=sanitizar_nombre_descarga(
                                    doc_seleccionado, item_seleccionado['version'], ".xlsx"
                                ),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key=f"btn_dl_excel_hist_{doc_seleccionado}_{item_seleccionado['version']}"
                            )
                        else:
                            st.info("Archivo snapshot Excel no disponible en disco.")
                    else:
                        st.download_button(
                            label=f"Descargar Versión v{item_seleccionado['version']} (.md)",
                            data=contenido_snapshot.encode("utf-8"),
                            file_name=sanitizar_nombre_descarga(
                                doc_seleccionado, item_seleccionado['version'], ".md"
                            ),
                            mime="text/markdown",
                            use_container_width=True,
                            key=f"btn_dl_md_hist_{doc_seleccionado}_{item_seleccionado['version']}"
                        )

                with col_dl_v2:
                    if excel_snap:
                        st.download_button(
                            label=f"Descargar Representación v{item_seleccionado['version']} (.md)",
                            data=contenido_snapshot.encode("utf-8"),
                            file_name=sanitizar_nombre_descarga(
                                doc_seleccionado, item_seleccionado['version'], ".md"
                            ),
                            mime="text/markdown",
                            use_container_width=True,
                            key=f"btn_dl_md_rep_{doc_seleccionado}_{item_seleccionado['version']}"
                        )
                    else:
                        st.caption(
                            f"Snapshot generado el **{item_seleccionado['timestamp']}** por **{item_seleccionado['autor']}**."
                        )

                with st.expander(f"Previsualizar contenido de la Versión v{item_seleccionado['version']}", expanded=False):
                    st.markdown(contenido_snapshot)

                # 3. Rollback
                if item_seleccionado["version"] != ultima_version:
                    st.markdown("---")
                    st.markdown(f"##### Revertir Documento a la Versión v{item_seleccionado['version']} (Rollback)")
                    st.caption("Especifique el Editor responsable y la justificación técnica para mantener la trazabilidad de auditoría.")

                    col_rb_a, col_rb_m = st.columns([1, 2])
                    with col_rb_a:
                        autor_rb = st.text_input(
                            "Editor / Técnico que ejecuta el Rollback (*)",
                            placeholder="Ej: Juan Pérez / SysAdmin",
                            key=f"author_rb_{doc_seleccionado}_{item_seleccionado['version']}"
                        )
                    with col_rb_m:
                        motivo_rb = st.text_input(
                            "Motivo o Justificación del Rollback (*)",
                            placeholder=f"Ej: Reversión por inconsistencia en v{ultima_version}",
                            key=f"motive_rb_{doc_seleccionado}_{item_seleccionado['version']}"
                        )

                    if st.button(
                        f"Confirmar y Ejecutar Rollback a la Versión v{item_seleccionado['version']}",
                        type="primary",
                        key=f"btn_confirm_rollback_{doc_seleccionado}_{item_seleccionado['version']}"
                    ):
                        if not autor_rb or not autor_rb.strip():
                            st.error("Error de Auditoría: Debe ingresar el Editor / Técnico responsable de ejecutar el Rollback.")
                        elif not motivo_rb or not motivo_rb.strip():
                            st.error("Error de Auditoría: Debe ingresar la justificación técnica del Rollback.")
                        else:
                            excel_snap = item_seleccionado.get("archivo_excel_snapshot")
                            snap_full_path = os.path.join(
                                HISTORY_DIR, doc_seleccionado, excel_snap
                            ) if excel_snap else ""
                            if excel_snap and os.path.exists(snap_full_path):
                                shutil.copy2(snap_full_path, os.path.join(DOCS_DIR, doc_seleccionado))
                                nuevo_md = procesar_excel_limpio(os.path.join(DOCS_DIR, doc_seleccionado))
                                nueva_v = guardar_nueva_version(
                                    doc_name=doc_seleccionado,
                                    nuevo_contenido=nuevo_md,
                                    autor=autor_rb.strip(),
                                    comentario=f"[Rollback a v{item_seleccionado['version']}] {motivo_rb.strip()}",
                                    doc_store=st.session_state.doc_store
                                )
                            else:
                                nueva_v = guardar_nueva_version(
                                    doc_name=doc_seleccionado,
                                    nuevo_contenido=contenido_snapshot,
                                    autor=autor_rb.strip(),
                                    comentario=f"[Rollback a v{item_seleccionado['version']}] {motivo_rb.strip()}",
                                    doc_store=st.session_state.doc_store
                                )
                            st.toast(f"Documento restaurado a v{item_seleccionado['version']} (Registrado como v{nueva_v})")
                            st.success(
                                f"Rollback completado con éxito. Se generó la versión [Version v{nueva_v}] restaurando la versión [Version v{item_seleccionado['version']}]. Responsable: {autor_rb.strip()}"
                            )
                            st.rerun()

                # 4. Herramientas Complementarias en Expanders
                if len(historial) >= 2:
                    with st.expander("Comparar diferencias de texto entre dos versiones (Diff simple)", expanded=False):
                        col_cmp1, col_cmp2 = st.columns(2)
                        nombres_versiones = [
                            f"v{item['version']} - {item['timestamp']} ({item['autor']})" for item in historial
                        ]
                        mapa_versiones = {
                            f"v{item['version']} - {item['timestamp']} ({item['autor']})": item for item in historial
                        }
                        with col_cmp1:
                            ver_base_sel = st.selectbox(
                                "Versión Base (Anterior):",
                                nombres_versiones,
                                index=0,
                                key=f"diff_base_simple_{doc_seleccionado}"
                            )
                        with col_cmp2:
                            ver_comp_sel = st.selectbox(
                                "Versión a Comparar (Nueva):",
                                nombres_versiones,
                                index=len(nombres_versiones) - 1,
                                key=f"diff_comp_simple_{doc_seleccionado}"
                            )

                        item_base = mapa_versiones[ver_base_sel]
                        item_comp = mapa_versiones[ver_comp_sel]
                        texto_base = obtener_contenido_version(doc_seleccionado, item_base["archivo_snapshot"])
                        texto_comp = obtener_contenido_version(doc_seleccionado, item_comp["archivo_snapshot"])

                        diff_unificado = generar_diff_texto(
                            texto_ant=texto_base,
                            texto_nuevo=texto_comp,
                            label_ant=f"v{item_base['version']} ({item_base['autor']})",
                            label_nuevo=f"v{item_comp['version']} ({item_comp['autor']})"
                        )
                        st.code(diff_unificado, language="diff")

                with st.expander("Registro Central de Auditoría Global (Audit Log)", expanded=False):
                    eventos_globales = obtener_todos_los_eventos_auditoria()
                    if eventos_globales:
                        df_aud = pd.DataFrame(eventos_globales)
                        df_aud["fecha_dt"] = pd.to_datetime(df_aud["timestamp"], errors="coerce")
                        min_d_aud = df_aud["fecha_dt"].min().date() if not df_aud["fecha_dt"].dropna().empty else datetime.date.today()
                        max_d_aud = df_aud["fecha_dt"].max().date() if not df_aud["fecha_dt"].dropna().empty else datetime.date.today()

                        col_fa, col_fd, col_fdate = st.columns([1.1, 1.4, 1.5])
                        with col_fa:
                            acciones_disp = ["Todas"] + sorted(list(set(df_aud["accion"].dropna().unique())))
                            filtro_acc = st.selectbox("Filtrar por Acción:", acciones_disp, key=f"filter_aud_acc_s_{doc_seleccionado}")
                        with col_fd:
                            docs_disp = ["Todos los Documentos", f"Solo este documento ({doc_seleccionado})"]
                            filtro_doc_aud = st.selectbox("Filtrar por Documento:", docs_disp, key=f"filter_aud_doc_s_{doc_seleccionado}")
                        with col_fdate:
                            rango_aud_fecha = st.date_input(
                                "Rango de Fechas:",
                                value=(min_d_aud, max_d_aud),
                                min_value=min_d_aud,
                                max_value=max_d_aud,
                                key=f"filter_aud_date_s_{doc_seleccionado}"
                            )

                        df_aud_filtrado = df_aud.copy()
                        if filtro_acc != "Todas":
                            df_aud_filtrado = df_aud_filtrado[df_aud_filtrado["accion"] == filtro_acc]
                        if filtro_doc_aud.startswith("Solo este"):
                            df_aud_filtrado = df_aud_filtrado[df_aud_filtrado["documento"] == doc_seleccionado]
                        if isinstance(rango_aud_fecha, (tuple, list)) and len(rango_aud_fecha) == 2:
                            fa_ini, fa_fin = rango_aud_fecha
                            df_aud_filtrado = df_aud_filtrado[(df_aud_filtrado["fecha_dt"].dt.date >= fa_ini) & (df_aud_filtrado["fecha_dt"].dt.date <= fa_fin)]
                        elif isinstance(rango_aud_fecha, datetime.date):
                            df_aud_filtrado = df_aud_filtrado[df_aud_filtrado["fecha_dt"].dt.date == rango_aud_fecha]

                        st.markdown(f"<div style='font-size: 0.82rem; margin-bottom: 6px; font-weight: 500;'><span class='badge-info'>{len(df_aud_filtrado)} eventos de auditoría</span></div>", unsafe_allow_html=True)
                        df_aud_display = df_aud_filtrado[["timestamp", "documento", "accion", "version_anterior", "version_nueva", "editor_responsable", "motivo_justificacion"]]
                        df_aud_display.columns = ["Timestamp", "Documento", "Acción", "Versión Ant.", "Versión Nueva", "Editor Responsable", "Motivo / Justificación"]
                        st.dataframe(df_aud_display, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay eventos registrados en el log de auditoría global.")
    else:
        st.warning(
            "No hay documentos indexados. Cargue un archivo en el panel lateral.")

# ----------------- TAB 4: PLANTILLAS Y RUNBOOKS -----------------
with tab_templates:
    st.subheader("Generador Rápido de Documentación y Runbooks")
    st.caption(
        "Crea y publica procedimientos técnicos estandarizados o define nuevos tipos personalizados en 2 minutos.")

    sac.steps(
        items=[
            sac.StepsItem(title="Paso 1", subtitle="Selección y Metadatos"),
            sac.StepsItem(title="Paso 2", subtitle="Parámetros Técnicos"),
            sac.StepsItem(title="Paso 3",
                          subtitle="Previsualización y Publicación"),
        ],
        size="sm",
        return_index=False
    )
    st.markdown("---")

    col_t1, col_t2 = st.columns([1, 1], gap="large")

    with col_t1:
        st.markdown("#### 1. Configuración del Procedimiento")

        lista_tipos = obtener_todos_los_tipos_plantillas()
        tipo_plantilla_sel = st.selectbox(
            "Plantilla / Tipo de Procedimiento",
            lista_tipos,
            key="select_tipo_procedimiento_gen"
        )

        es_crear_nuevo = "[+ Crear" in tipo_plantilla_sel

        if es_crear_nuevo:
            st.info(
                "[NUEVA PLANTILLA] Ingrese el nombre y parámetros de la plantilla que desea crear y documentar.")
            nuevo_tipo_nombre = st.text_input("Nombre de la Plantilla / Tipo de Procedimiento (*)",
                                              placeholder="Ej: Auditoría de Accesos y Permisos", key="input_nuevo_tipo_proc")
            guardar_catalogo = st.checkbox(
                "Guardar este tipo de plantilla en el catálogo permanente", value=True)
            tipo_plantilla = nuevo_tipo_nombre.strip(
            ) if nuevo_tipo_nombre.strip() else "Procedimiento Personalizado"
        else:
            tipo_plantilla = tipo_plantilla_sel.replace("[Plantilla]", "").replace("[Personalizado]", "").strip()
            guardar_catalogo = False
            nuevo_tipo_nombre = ""

        # Catálogo base reservado en expander opcional
        with st.expander("Explorar catálogo de plantillas base reservadas (Opcional)", expanded=False):
            st.caption("Estas plantillas predefinidas se encuentran reservadas para su uso opcional. Puede activar cualquiera para integrarla a su catálogo:")
            col_res_sel, col_res_btn = st.columns([3, 1])
            with col_res_sel:
                base_a_activar = st.selectbox(
                    "Seleccionar plantilla base a activar:",
                    PLANTILLAS_BASE_RESERVADAS,
                    key="sel_plantilla_base_res"
                )
            with col_res_btn:
                st.write("")
                st.write("")
                if st.button("[+ Activar]", key="btn_activar_plantilla_base", use_container_width=True):
                    guardar_plantilla_personalizada(
                        nombre=base_a_activar,
                        descripcion=f"Plantilla activada desde catálogo base: {base_a_activar}",
                        campos=["criterio", "pasos", "verif"]
                    )
                    st.toast(f"[OK] Plantilla '{base_a_activar}' activada en el catálogo")
                    st.rerun()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            autor = st.text_input("Autor / Técnico Responsable (*)",
                                  value="Developer / DevOps", key="proc_autor_input")
            nombre_servicio = st.text_input(
                "Servicio o Componente (*)", value="Booking Core Engine", key="proc_srv_input")
        with col_g2:
            nivel_arq = st.selectbox("Nivel de Arquitectura", [
                "L4 - Aplicación y Negocio",
                "L3 - Middleware e Integración",
                "L2 - Virtualización y Cómputo",
                "L1 - Hardware e Infraestructura Base"
            ], key="proc_nivel_input")
            ambiente = st.selectbox("Ambiente Objetivo", [
                                    "Producción", "Staging / QA", "Desarrollo", "Datacenter DR", "Todos los Ambientes"], key="proc_amb_input")

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            criticidad = st.selectbox(
                "Criticidad / SLA", ["Crítico 7x24 (P1)", "Alta (P2)", "Media (P3)", "Baja (P4)"], index=2, key="proc_crit_input")
        with col_g4:
            ventana = st.text_input(
                "Ventana de Mantenimiento", value="02:00 a 04:00 AM (Horario no hábil)", key="proc_vent_input")

        servidores = st.text_input("Servidores / Nodos / IPs Involucrados",
                                   value="BALANCER001, 10.24.0.125, VM-BOOKING-01", key="proc_srvs_input")

        st.markdown("---")
        st.markdown("##### Parámetros Específicos del Procedimiento")

        params = {
            "ambiente": ambiente,
            "criticidad": criticidad,
            "ventana": ventana,
            "servidores": servidores,
        }

        # Formulario dinámico según tipo
        if "Rollback" in tipo_plantilla:
            params["criterio"] = st.text_area(
                "Criterio de Activación de Rollback", value="Latencia > 500ms en New Relic por más de 3 min o Error Rate 5xx > 2%")
            params["pasos"] = st.text_area("Pasos de Reversión (Comandos / Acciones)",
                                           value="1. Ejecutar pipeline de Rollback en Azure DevOps release-v2.4.1\n2. Revertir cambios de esquema en BD Postgres si aplica\n3. Limpiar caché en Redis Sentinel: redis-cli FLUSHDB")
            params["verif"] = st.text_area("Comandos de Verificación de Salud",
                                           value="curl -I https://api.booking.internal/health\nsystemctl status booking-service")
        elif "Paso a Producción" in tipo_plantilla:
            params["version"] = st.text_input(
                "Versión / Tag de Release", value="v2.5.0")
            params["pipeline"] = st.text_input(
                "Pipeline Azure DevOps / Release ID", value="https://dev.azure.com/smucorp/pipelines/142")
            params["variables"] = st.text_area(
                "Variables de Entorno / Configuración", value="REDIS_HOST=10.24.0.126\nJWT_SECRET=[CONFIGURADO EN KEYVAULT]\nLOG_LEVEL=INFO")
            params["smoke"] = st.text_area("Checklist de Validación (Smoke Tests)",
                                           value="- [ ] Endpoint /health respondiendo HTTP 200\n- [ ] Transacciones fluyendo en VZOR Suite\n- [ ] Cero alertas críticas en Nagios")
        elif "Postmortem" in tipo_plantilla:
            params["incidente_id"] = st.text_input(
                "ID del Ticket / Incidente", value="INC-88912")
            params["impacto"] = st.text_area(
                "Resumen del Impacto", value="Indisponibilidad del servicio de autorización por 14 minutos. 120 transacciones rechazadas.")
            params["causa"] = st.text_area(
                "Diagnóstico de Causa Raíz (RCA)", value="Agotamiento de pool de conexiones JDBC en WSO2 Enterprise Integrator debido a query no indexada.")
            params["solucion"] = st.text_area(
                "Solución Inmediata Aplicada", value="Reinicio del nodo worker WSO2 y ampliación de maxConnections a 150.")
            params["preventiva"] = st.text_area("Medida Preventiva para Evitar Recurrencia",
                                                value="Creación de índice en tabla t_auth_tokens y ajuste de timeout en WSO2.")
        elif "Microservicio" in tipo_plantilla:
            params["endpoint"] = st.text_input(
                "Endpoint Base / Ruta API", value="/api/v1/booking")
            params["auth"] = st.text_input(
                "Método de Autenticación", value="OAuth2 Bearer Token (Redis Sentinel)")
            params["dependencias"] = st.text_area(
                "Dependencias Backend y Nodos", value="* VM: VM-BOOKING-01 (10.24.0.125)\n* DB: Postgres HA (10.24.0.130)\n* Gateway: WSO2 API Manager")
        elif "Parchado" in tipo_plantilla or "Mantenimiento de SO" in tipo_plantilla:
            params["paquetes"] = st.text_area(
                "Alcance y Paquetes a Actualizar", value="Actualización de seguridad mensual del kernel y paquetes críticos de OpenSSL.")
            params["pasos_parchado"] = st.text_area(
                "Pasos de Aplicación de Parches", value="1. Tomar snapshot de VM en VMware vCloud Director\n2. yum update -y / apt-get update && apt-get upgrade -y\n3. Reinicio controlado de nodo secundario\n4. Validación de servicios")
            params["rollback_parchado"] = st.text_area(
                "Plan de Reversión en caso de Fallo", value="Revertir al snapshot de VM en VMware vCloud Director.")
        elif "Certificados" in tipo_plantilla or "SSL" in tipo_plantilla:
            params["dominio"] = st.text_input(
                "Dominio / CN del Certificado", value="*.smucorp.internal")
            params["ruta_cert"] = st.text_input(
                "Ruta de Instalación en el Servidor", value="/etc/ssl/certs/api_smucorp.crt")
            params["comandos_renov"] = st.text_area(
                "Comandos de Generación y Carga", value="openssl req -new -newkey rsa:2048 -nodes -keyout api.key -out api.csr\n# Copiar certificado firmado a /etc/ssl/certs/")
            params["validacion_ssl"] = st.text_area(
                "Comandos de Validación SSL", value="echo | openssl s_client -connect localhost:443 -servername api.smucorp.internal 2>/dev/null | openssl x509 -noout -dates")
        elif "Disaster Recovery" in tipo_plantilla or "DRP" in tipo_plantilla:
            params["rpo_rto"] = st.text_input(
                "Objetivos RPO / RTO", value="RPO: 15 minutos | RTO: 1 hora")
            params["activacion_drp"] = st.text_area(
                "Criterios de Activación del DRP", value="Indisponibilidad total del Datacenter Principal por más de 30 minutos.")
            params["pasos_drp"] = st.text_area(
                "Pasos de Conmutación a Datacenter DR", value="1. Conmutar DNS externo al Datacenter Secundario\n2. Promover réplica de Base de Datos PostgreSQL a Primario\n3. Iniciar workers de WSO2 en sitio secundario")
        elif "Respaldo" in tipo_plantilla or "Base de Datos" in tipo_plantilla:
            params["motor_bd"] = st.text_input(
                "Motor de Base de Datos", value="PostgreSQL 15 HA / Oracle 19c RAC")
            params["comando_backup"] = st.text_area(
                "Comando / Script de Respaldo", value="pg_dump -h 10.24.0.130 -U admin -Fc db_booking > /backups/booking_$(date +%F).dump")
            params["comando_restore"] = st.text_area(
                "Comando / Script de Restauración", value="pg_restore -h 10.24.0.130 -U admin -d db_booking /backups/booking_snapshot.dump")
        elif "Contingencia" in tipo_plantilla or "Failover" in tipo_plantilla:
            params["sintoma"] = st.text_area("Síntoma de Falla / Alerta Disparadora",
                                             value="Host ESXi no responde en vCloud o alerta CRITICAL en Nagios por ping timeout.")
            params["pasos"] = st.text_area("Procedimiento de Conmutación (Failover)",
                                           value="1. Conmutar tráfico en HAProxy a BALANCER002 (10.24.0.126)\n2. Activar réplica en VMware vCloud Director\n3. Validar resolución DNS interna")
        else:
            params["objetivo"] = st.text_area("Objetivo y Alcance del Procedimiento",
                                              value=f"Procedimiento estandarizado para la ejecución segura de {tipo_plantilla} en los componentes de {nombre_servicio}.")
            params["prerequisitos"] = st.text_area("Requisitos Previos y Permisos Necesarios",
                                                   value="* Acceso SSH con privilegios sudo en los servidores\n* Notificación previa a Mesa de Ayuda / Operaciones 7x24\n* Snapshot o backup preventivo verificado")
            params["pasos_custom"] = st.text_area("Pasos de Ejecución Detallados (Comandos / Acciones)",
                                                  value="1. Validar estado previo del servicio: systemctl status servicio\n2. Ejecutar script de actualización o mantenimiento\n3. Verificar logs en /var/log/syslog o New Relic")
            params["verificacion_custom"] = st.text_area(
                "Validación y Criterios de Aceptación", value="* Transacciones operativas sin errores 5xx\n* Métricas de CPU y Memoria dentro de umbrales normales (<70%)\n* Nagios check_http reportando estado OK")
            params["rollback_custom"] = st.text_area("Plan de Contingencia / Reversión en caso de Fallo",
                                                     value="1. Detener ejecución de scripts de inmediato\n2. Restaurar archivos de configuración desde backup local\n3. Reiniciar servicio y notificar al líder técnico")

        doc_generado_md, nombre_archivo_sugerido = generar_doc_plantilla(
            tipo_plantilla, autor, nombre_servicio, nivel_arq, params)

    with col_t2:
        st.markdown("#### 2. Previsualización en Vivo del Documento")
        nombre_final = st.text_input("Nombre de Archivo Final (.md)",
                                     value=nombre_archivo_sugerido, key="input_nombre_archivo_proc_final")

        with st.container(border=True):
            st.markdown(doc_generado_md)

        st.divider()
        if st.button("Guardar y Publicar en Base de Conocimiento", type="primary", use_container_width=True, key="btn_guardar_doc_plantilla_final"):
            if not nombre_final.endswith(".md"):
                nombre_final += ".md"

            if es_crear_nuevo and guardar_catalogo and nuevo_tipo_nombre.strip():
                guardar_plantilla_personalizada(
                    nombre=nuevo_tipo_nombre.strip(),
                    descripcion=f"Plantilla personalizada para {nuevo_tipo_nombre.strip()}",
                    campos=["objetivo", "prerequisitos", "pasos_custom",
                            "verificacion_custom", "rollback_custom"]
                )

            ruta_destino = os.path.join(DOCS_DIR, nombre_final)
            os.makedirs(DOCS_DIR, exist_ok=True)
            with open(ruta_destino, "w", encoding="utf-8") as f:
                f.write(doc_generado_md)

            st.session_state.doc_store[nombre_final] = doc_generado_md
            inicializar_version_inicial_si_no_existe(
                doc_name=nombre_final,
                contenido_actual=doc_generado_md,
                autor=autor,
                comentario=f"Creación inicial mediante plantilla: {tipo_plantilla}"
            )
            st.toast(f"Procedimiento guardado como {nombre_final}")
            st.success(
                f"¡Procedimiento guardado e indexado exitosamente como **{nombre_final}** (Versión [Version v1])!")
            st.info(
                "El Chat Copilot, DuckDB y el visualizador Lado a Lado ya pueden consultar y renderizar este nuevo procedimiento.")
            st.rerun()

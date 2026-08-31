import os
import io
import json
import time
import html
import shutil
import zipfile
import datetime
import duckdb
import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

from core.visor import renderizar_lado_a_lado
from core.plantillas import (
    generar_doc_plantilla,
    obtener_todos_los_tipos_plantillas,
    guardar_plantilla_personalizada,
    PLANTILLAS_BASE_RESERVADAS,
)
from core.procesador import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    cargar_documentos_locales,
    cargar_documento_individual,
    calcular_sha256,
    sanitizar_nombre_descarga,
    normalizar_nombre_archivo,
    normalizar_titulo_display,
    generar_ficha_diagrama,
    obtener_ruta_original,
    limpiar_cache_documentos,
)
from core.motor import (
    ejecutar_consulta_sql,
    buscar_servidores_duckdb,
    buscar_en_documentos,
    extraer_fragmento_relevante,
    resaltar_terminos_en_html,
    generar_respuesta_asistente,
    limpiar_cache_consultas,
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
    obtener_todos_los_eventos_auditoria,
    obtener_fecha_carga_documento,
)
from core.estilos import cargar_estilos_css
from core.configuracion import CSV_PATH, DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR, HISTORY_DIR
from core.manual import renderizar_manual_usuario
from core.conector_sap import (
    probar_conexion_api_sap,
    obtener_inventario_sap_df,
    obtener_alertas_sap,
    generar_payload_json_sap,
    generar_topologia_sap_mermaid,
    sincronizar_servidores_sap_cmdb,
)
from core.vault import (
    obtener_secreto,
    guardar_secreto,
    eliminar_secreto,
    listar_secretos_disponibles,
)
from core.auth import (
    es_usuario_autenticado,
    obtener_usuario_actual,
    tiene_permiso,
    cerrar_sesion,
    renderizar_pantalla_login,
)
from excel_cleaner import procesar_excel_limpio


def procesar_e_ingestar_binario(
    clean_name: str,
    buf: bytes,
    doc_store: dict,
    autor: str = "Técnico / Panel Lateral",
    origen_detalle: str = "Carga en panel lateral"
) -> tuple[str, str]:
    """Procesa e ingesta un archivo binario, versionándolo y actualizando doc_store."""
    ext = os.path.splitext(clean_name)[1].lower()
    nuevo_hash = calcular_sha256(buf)

    # 1. Preservar siempre en data/originals/
    with open(os.path.join(ORIGINALS_DIR, clean_name), "wb") as f_orig:
        f_orig.write(buf)

    # 2. Imágenes y Diagramas
    if ext in IMAGE_EXTENSIONS:
        with open(os.path.join(ASSETS_DIR, clean_name), "wb") as f_asset:
            f_asset.write(buf)

        doc_md_name = f"DIAGRAMA__{clean_name}.md"
        md_save_path = os.path.join(DOCS_DIR, doc_md_name)
        ficha_content = generar_ficha_diagrama(
            image_filename=clean_name,
            orig_rel_path=f"assets/{clean_name}",
            sha256_hash=nuevo_hash,
            categoria=origen_detalle
        )
        if os.path.exists(md_save_path):
            with open(md_save_path, "r", encoding="utf-8", errors="ignore") as f_ex:
                ex_content = f_ex.read()
            if calcular_sha256(ex_content.encode("utf-8")) == calcular_sha256(ficha_content.encode("utf-8")):
                return "sin_cambios", f"Diagrama '{clean_name}' ya registrado sin cambios."
            with open(md_save_path, "w", encoding="utf-8") as f_out:
                f_out.write(ficha_content)
            doc_store[doc_md_name] = ficha_content
            nueva_v = guardar_nueva_version(
                doc_name=doc_md_name,
                nuevo_contenido=ficha_content,
                autor=autor,
                comentario=f"Actualización de activo gráfico '{clean_name}'",
                doc_store=doc_store
            )
            return "actualizado", f"Diagrama '{clean_name}' actualizado [Version v{nueva_v}]"
        else:
            with open(md_save_path, "w", encoding="utf-8") as f_out:
                f_out.write(ficha_content)
            doc_store[doc_md_name] = ficha_content
            inicializar_version_inicial_si_no_existe(
                doc_name=doc_md_name,
                contenido_actual=ficha_content,
                autor=autor,
                comentario=f"Carga inicial de activo gráfico '{clean_name}'"
            )
            return "nuevo", f"Diagrama '{clean_name}' indexado como Version v1"

    # 3. Documentos Ofimáticos, Excel, PDF y Texto
    else:
        save_path = os.path.join(DOCS_DIR, clean_name)
        if os.path.exists(save_path):
            with open(save_path, "rb") as f:
                existente_bytes = f.read()
            if nuevo_hash == calcular_sha256(existente_bytes):
                return "sin_cambios", f"Archivo '{clean_name}' ya indexado sin cambios."
            with open(save_path, "wb") as f:
                f.write(buf)
            content = cargar_documento_individual(save_path)
            doc_store[clean_name] = content
            nueva_v = guardar_nueva_version(
                doc_name=clean_name,
                nuevo_contenido=content,
                autor=autor,
                comentario=f"Actualización de archivo '{clean_name}' ({origen_detalle})",
                doc_store=doc_store
            )
            return "actualizado", f"Archivo '{clean_name}' actualizado [Version v{nueva_v}]"
        else:
            with open(save_path, "wb") as f:
                f.write(buf)
            content = cargar_documento_individual(save_path)
            doc_store[clean_name] = content
            inicializar_version_inicial_si_no_existe(
                doc_name=clean_name,
                contenido_actual=content,
                autor=autor,
                comentario=f"Carga inicial de archivo ({origen_detalle})"
            )
            return "nuevo", f"Documento '{clean_name}' indexado como Version v1"


@st.cache_data(show_spinner=False)
def obtener_dataframe_mantenimientos(mtime: float) -> pd.DataFrame:
    """Carga mantenimientos.csv en cache evitando accesos repetitivos a disco."""
    if os.path.exists(CSV_PATH):
        try:
            return pd.read_csv(CSV_PATH)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _render_kpi_grid(total_reg: int, cnt_op: int, cnt_rev: int, cnt_crit: int, tec_activo: str, pct_op: float, pct_crit: float):
    """Renderiza las tarjetas KPI de analítica con diseño Obsidian & Indigo."""
    kpi_defs = [
        ("Total Registros", str(total_reg), "en el periodo filtrado", "#6366F1", "rgba(99,102,241,0.10)"),
        ("Operativos", str(cnt_op), f"{pct_op}% del total", "#10B981", "rgba(16,185,129,0.10)"),
        ("En Revision", str(cnt_rev), "revision activa", "#D97706", "rgba(217,119,6,0.10)"),
        ("Criticos", str(cnt_crit), f"{pct_crit}% del total", "rgb(106, 57, 123)", "rgba(106, 57, 123, 0.14)"),
        ("Tecnico Mas Activo", str(tec_activo), "mayor cantidad de registros", "#6366F1", "rgba(128,128,128,0.08)"),
    ]
    cards_html = []
    for titulo, valor, sub, color, bg in kpi_defs:
        cards_html.append(f"""
        <div style="background:{bg};border:1px solid rgba(128,128,128,0.22);border-top:3px solid {color};border-radius:10px;padding:14px 16px;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;opacity:0.75;margin-bottom:6px;">{titulo}</div>
            <div style="font-size:{'1.05rem' if len(valor) > 6 else '1.85rem'};font-weight:700;line-height:1.2;color:{color};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{valor}</div>
            <div style="font-size:0.72rem;opacity:0.6;margin-top:4px;">{sub}</div>
        </div>""")
    st.markdown(f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:14px 0 18px 0;">{"".join(cards_html)}</div>', unsafe_allow_html=True)


# 1. Configuración de Streamlit
st.set_page_config(page_title="KGB - Camarada de Infraestructura", layout="wide", initial_sidebar_state="expanded")
st.markdown(cargar_estilos_css(), unsafe_allow_html=True)
st.markdown('<div class="accent-top-bar"></div>', unsafe_allow_html=True)

# 2. Control de Autenticación RBAC
if not es_usuario_autenticado():
    renderizar_pantalla_login()
    st.stop()

# 3. Inicialización de Estado y Documentos
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

# 4. Sidebar (Panel de Control e Ingesta)
with st.sidebar:
    user_act = obtener_usuario_actual()
    st.markdown(f"""
    <div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.25);border-radius:6px;padding:10px 12px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.68rem;font-weight:700;color:#6366F1;text-transform:uppercase;">Sesión Activa</span>
            <span class="badge-ok" style="font-size:0.65rem;">{user_act.get('rol', 'Usuario')}</span>
        </div>
        <div style="font-size:0.9rem;font-weight:600;">{user_act.get('nombre', user_act.get('username'))}</div>
        <div style="font-size:0.68rem;opacity:0.6;font-family:monospace;">@{user_act.get('username')}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(">_ Cerrar Sesión", width="stretch", key="btn_logout_sidebar"):
        cerrar_sesion()

    st.markdown("---")
    st.markdown("""
    <div class="sidebar-header-card">
        <div class="sidebar-header-title-row">
            <span class="sidebar-header-title">Panel de Control</span>
            <span class="badge-info" style="font-size:0.68rem;padding:1px 6px;">[OPERACIONES]</span>
        </div>
        <div class="sidebar-header-sub">Ingesta de activos, base documental y telemetría de motores.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Ingesta de Archivos (Batch & Lotes)")
    st.markdown('<div class="sidebar-format-tags"><span class="sidebar-format-tag">[ZIP]</span><span class="sidebar-format-tag">[PDF]</span><span class="sidebar-format-tag">[DOCX]</span><span class="sidebar-format-tag">[XLSX]</span><span class="sidebar-format-tag">[DIAGRAMAS]</span><span class="sidebar-format-tag">[MD]</span></div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Arrastra archivos o paquetes ZIP en lote:", type=["pdf", "docx", "xlsx", "xls", "csv", "txt", "md", "pptx", "png", "jpg", "jpeg", "svg", "webp", "zip"], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded_files:
        proc_cnt, new_cnt, upd_cnt = 0, 0, 0
        for uf in uploaded_files:
            c_name = normalizar_nombre_archivo(uf.name)
            ext_u = os.path.splitext(c_name)[1].lower()
            buf = uf.getbuffer().tobytes()

            if ext_u == ".zip":
                try:
                    with zipfile.ZipFile(io.BytesIO(buf)) as z:
                        zip_cnt = 0
                        for zi in [i for i in z.infolist() if not i.is_dir()]:
                            in_fn = os.path.basename(zi.filename)
                            if not in_fn or in_fn.startswith(".") or "__MACOSX" in zi.filename:
                                continue
                            in_cl = normalizar_nombre_archivo(in_fn)
                            if os.path.splitext(in_cl)[1].lower() in SUPPORTED_EXTENSIONS:
                                st_res, _ = procesar_e_ingestar_binario(in_cl, z.read(zi), st.session_state.doc_store, autor="Técnico / Paquete ZIP", origen_detalle=f"Lote ZIP: {c_name}")
                                zip_cnt += 1
                                proc_cnt += 1
                                if st_res == "nuevo":
                                    new_cnt += 1
                                elif st_res == "actualizado":
                                    upd_cnt += 1
                        st.toast(f"[OK] ZIP '{c_name}': {zip_cnt} archivos indexados.")
                except Exception as e_z:
                    st.error(f"[ERROR] Error al procesar ZIP '{c_name}': {str(e_z)}")
            else:
                st_res, msg = procesar_e_ingestar_binario(c_name, buf, st.session_state.doc_store, autor="Técnico / Panel Lateral", origen_detalle="Carga en panel lateral")
                proc_cnt += 1
                if st_res == "nuevo":
                    new_cnt += 1
                    st.toast(f"[OK] {msg}")
                elif st_res == "actualizado":
                    upd_cnt += 1
                    st.toast(f"[OK] {msg}")
                elif st_res == "sin_cambios":
                    st.toast(f"[INFO] {msg}")

        if proc_cnt > 1:
            st.success(f"[OK] Lote: {proc_cnt} evaluados ({new_cnt} nuevos, {upd_cnt} actualizados).")

    st.markdown("---")
    cant_side = len(st.session_state.doc_store)
    st.markdown(f"#### Explorador Documental <span class='badge-info' style='font-size:0.68rem;padding:1px 6px;'>[{cant_side}]</span>", unsafe_allow_html=True)

    if cant_side > 0:
        c_img = sum(1 for d in st.session_state.doc_store if d.startswith("DIAGRAMA__") or any(d.lower().endswith(e) for e in IMAGE_EXTENSIONS))
        c_xls = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[1].lower() in ('.xlsx', '.xls'))
        c_doc = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[1].lower() in ('.docx', '.pdf', '.pptx', '.doc'))
        c_txt = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[1].lower() in ('.md', '.txt', '.csv') and not d.startswith("DIAGRAMA__"))

        with st.expander("Filtrar e inspeccionar archivos", expanded=False):
            filt_opts = [f"Todos ({cant_side})", f"Diagramas ({c_img})", f"Excel ({c_xls})", f"Documentos ({c_doc})", f"Markdown ({c_txt})"]
            tipo_f = st.pills("Filtrar por tipo:", options=filt_opts, default=filt_opts[0], label_visibility="visible", key="sb_type_pill_filter") or filt_opts[0]
            doc_filter = st.text_input("Buscar por nombre...", key="sb_doc_filter", placeholder="Nombre de archivo...")

            docs_f = []
            for d in sorted(st.session_state.doc_store.keys()):
                ext_d = os.path.splitext(d)[1].lower()
                is_diag = d.startswith("DIAGRAMA__") or ext_d in IMAGE_EXTENSIONS
                if tipo_f.startswith("Diagramas") and not is_diag:
                    continue
                if tipo_f.startswith("Excel") and ext_d not in ('.xlsx', '.xls'):
                    continue
                if tipo_f.startswith("Documentos") and ext_d not in ('.docx', '.pdf', '.pptx', '.doc'):
                    continue
                if tipo_f.startswith("Markdown") and (is_diag or ext_d not in ('.md', '.txt', '.csv')):
                    continue
                if doc_filter and doc_filter.lower() not in d.lower():
                    continue
                docs_f.append(d)

            if docs_f:
                items_h = ['<div class="sidebar-doc-list">']
                for d in docs_f:
                    ext_d = os.path.splitext(d)[1].lower()
                    tag = '<span class="badge-ok" style="font-size:0.64rem;padding:1px 4px;">[DIAGRAMA]</span>' if (d.startswith("DIAGRAMA__") or ext_d in IMAGE_EXTENSIONS) else ('<span class="badge-info" style="font-size:0.64rem;padding:1px 4px;">[EXCEL]</span>' if ext_d in ('.xlsx', '.xls') else ('<span class="badge-warn" style="font-size:0.64rem;padding:1px 4px;">[DOC]</span>' if ext_d in ('.pdf', '.docx', '.pptx', '.doc') else '<span class="badge-tag" style="font-size:0.64rem;padding:1px 4px;">[MD]</span>'))
                    f_d = obtener_fecha_carga_documento(d)
                    items_h.append(f"""
                    <div class="sidebar-doc-card">
                        <div class="sidebar-doc-card-header"><span class="sidebar-doc-name" title="{d}">{normalizar_titulo_display(d)}</span>{tag}</div>
                        <div class="sidebar-doc-meta"><span>{f_d.strftime('%Y-%m-%d')}</span><span>{len(st.session_state.doc_store[d])/1024:.1f} KB</span></div>
                        <div style="font-size:0.65rem;opacity:0.55;font-family:monospace;margin-top:2px;word-break:break-all;">{d}</div>
                    </div>""")
                items_h.append('</div>')
                st.markdown("".join(items_h), unsafe_allow_html=True)
            else:
                st.caption("No hay documentos que coincidan con el filtro.")

    st.markdown("---")
    st.markdown("#### Acciones de Consola")
    if st.button(">_ Reindexar", help="Recarga todos los documentos desde data/docs/", width="stretch", key="btn_sidebar_reindexar"):
        limpiar_cache_documentos()
        cargar_documentos_locales(st.session_state.doc_store, force=True)
        limpiar_cache_consultas()
        st.toast("[OK] Base documental reindexada con éxito")
        st.rerun()

    if tiene_permiso("puede_ver_vault"):
        st.markdown("---")
        with st.expander("Bóveda de Credenciales [VAULT]", expanded=False):
            sec_list = listar_secretos_disponibles()
            cfg_cnt = sum(1 for s in sec_list if s["estado"] == "[CONFIGURADO]")
            st.markdown(f"<div style='font-size:0.75rem;margin-bottom:8px;opacity:0.8;'>Estado: <b>{cfg_cnt} configurada(s)</b> bajo cifrado AES-256.</div>", unsafe_allow_html=True)
            for s in sec_list:
                badge_s = '<span class="badge-ok" style="font-size:0.62rem;padding:1px 4px;">[CONFIGURADO]</span>' if s["estado"] == "[CONFIGURADO]" else '<span class="badge-tag" style="font-size:0.62rem;padding:1px 4px;">[NO CONFIGURADO]</span>'
                prev_s = f"({s['vista_previa']})" if s['vista_previa'] != '-' else ""
                st.markdown(f"<div style='font-size:0.72rem;padding:3px 0;display:flex;justify-content:space-between;align-items:center;'><span style='font-family:monospace;font-weight:600;'>{s['clave']}</span>{badge_s}</div><div style='font-size:0.64rem;opacity:0.6;margin-bottom:4px;'>Origen: {s['origen']} {prev_s}</div>", unsafe_allow_html=True)

            st.markdown("<b style='font-size:0.75rem;'>Guardar o Actualizar Clave:</b>", unsafe_allow_html=True)
            sel_k = st.selectbox("Seleccionar Llave:", [s["clave"] for s in sec_list] + ["OTRA_CLAVE_PERSONALIZADA"], key="sb_vault_sel_key", label_visibility="collapsed")
            k_final = st.text_input("Nombre de la Clave:", value="", placeholder="EJ: MI_API_KEY", key="sb_vault_custom_key") if sel_k == "OTRA_CLAVE_PERSONALIZADA" else sel_k
            if "vault_input_version" not in st.session_state:
                st.session_state.vault_input_version = 0
            val_sec = st.text_input("Valor del Secreto:", value="", type="password", key=f"sb_vault_secret_val_{st.session_state.vault_input_version}", label_visibility="collapsed", placeholder="Pegar token / API key...")

            col_vg, col_vd = st.columns(2)
            with col_vg:
                if st.button(">_ Guardar", width="stretch", key="btn_vault_guardar"):
                    if k_final and val_sec and guardar_secreto(k_final, val_sec, autor=f"{user_act.get('username', 'admin')} ({user_act.get('rol', 'Admin')})"):
                        st.session_state.vault_input_version += 1
                        st.toast(f"[OK] Credencial '{k_final}' cifrada en bóveda.")
                        st.rerun()
            with col_vd:
                if st.button(">_ Revocar", width="stretch", key="btn_vault_eliminar"):
                    if k_final and eliminar_secreto(k_final, autor=f"{user_act.get('username', 'admin')} ({user_act.get('rol', 'Admin')})"):
                        st.session_state.vault_input_version += 1
                        st.toast(f"[INFO] Credencial '{k_final}' revocada.")
                        st.rerun()

    st.markdown(f'<div class="sidebar-footer"><span class="sidebar-footer-version">[v1.0] KGB Camarada</span><span class="sidebar-footer-ts">Sesion: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</span></div>', unsafe_allow_html=True)

# 5. Navbar Hero Card
cant_docs = len(st.session_state.doc_store)
mtime_csv = os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0.0
df_mantenimientos_cache = obtener_dataframe_mantenimientos(mtime_csv)
total_srvs = len(df_mantenimientos_cache)

with st.container(border=True):
    col_brand, col_nav_mode, col_stats = st.columns([1.8, 1.3, 1.0], gap="small", vertical_alignment="center")
    with col_brand:
        st.markdown('<div class="navbar-brand-container"><span class="navbar-brand-badge">[KGB]</span><span class="navbar-brand-title">KGB - Camarada de Infraestructura</span><div class="navbar-brand-badges"><span class="badge-pulse-online"><span class="pulse-dot"></span>ONLINE</span></div></div>', unsafe_allow_html=True)
    with col_nav_mode:
        vista_seleccionada = st.segmented_control("Vista", ["Consola", "Manual de Uso"], default="Consola", label_visibility="collapsed", key="top_navbar_view_selector") or "Consola"
    with col_stats:
        st.markdown(f'<div class="navbar-stats-container"><div class="navbar-stat-chip"><span class="navbar-stat-label">Documentos:</span><span class="navbar-stat-value-ok">{cant_docs}</span></div></div>', unsafe_allow_html=True)

if "Manual" in str(vista_seleccionada):
    renderizar_manual_usuario()
    st.stop()

# 6. Pestañas Principales
tab_chat, tab_analytics, tab_docs, tab_templates, tab_sap = st.tabs([
    "Consultas y Búsqueda",
    f"Historial de Mantenimientos ({total_srvs})",
    f"Documentación Técnica ({cant_docs})",
    "Plantillas y Runbooks",
    "Integración SAP (API)"
])

# ----------------- TAB 1: CONSULTAS Y BÚSQUEDA -----------------
with tab_chat:
    subtab_duckdb, subtab_camarada = st.tabs(["Búsqueda Textual (DuckDB & Docs)", "Camarada KGB (Gemini RAG)"])

    with subtab_duckdb:
        st.markdown("#### Búsqueda Textual en Inventario CMDB y Documentación")
        st.caption("Búsqueda indexada instantánea en memoria RAM (< 2 ms) sobre la CMDB y los documentos técnicos.")

        with st.form(key="form_duckdb_search", clear_on_submit=False):
            col_din, col_dbtn = st.columns([5, 1])
            with col_din:
                query_duckdb_in = st.text_input("Término:", value=st.session_state.get("duckdb_active_term", ""), placeholder="IP (10.24.0.125), servidor (BALANCER001), serie (SN-8842-A) o palabra clave...", label_visibility="collapsed")
            with col_dbtn:
                sub_duckdb = st.form_submit_button("Buscar", type="primary", width="stretch")

        st.markdown("<div style='margin-top:-6px;margin-bottom:8px;font-size:0.72rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;opacity:0.7;'>Búsquedas rápidas:</div>", unsafe_allow_html=True)
        if "quick_duck_ver" not in st.session_state:
            st.session_state.quick_duck_ver = 0
        sel_duck_pill = st.pills("Búsquedas rápidas", options=[">_ BALANCER001", ">_ 10.24.0.125", ">_ Autenticacion JWT", ">_ Failover Redis", ">_ SN-8842-A", ">_ PureStorage SAN"], default=None, label_visibility="collapsed", key=f"pills_duck_{st.session_state.quick_duck_ver}")
        prompt_duck_pill = sel_duck_pill.replace(">_ ", "").strip() if sel_duck_pill else None
        if sel_duck_pill:
            st.session_state.quick_duck_ver += 1

        active_duck_term = prompt_duck_pill or (query_duckdb_in.strip() if sub_duckdb and query_duckdb_in.strip() else st.session_state.get("duckdb_active_term", ""))
        st.session_state["duckdb_active_term"] = active_duck_term

        if not active_duck_term:
            st.markdown("""
            <div class="empty-state-container">
                <div class="empty-state-console-icon">&gt;_ Buscador :1</div>
                <div class="empty-state-title">Motor de Búsqueda Textual en RAM</div>
                <div class="empty-state-subtitle">Búsqueda ultrarrápida indexada directamente sobre la CMDB y los documentos técnicos locales.</div>
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
                st.caption("¿Deseas un análisis técnico y diagnóstico asistido con el Camarada?")
            with col_bb:
                if st.button(">_ Analizar con Camarada KGB", width="stretch", type="primary", key="btn_bridge_to_copilot"):
                    with st.spinner("Generando análisis..."):
                        resp_c = generar_respuesta_asistente(active_duck_term, st.session_state.doc_store)
                        st.session_state.historial_busquedas.insert(0, {"query": active_duck_term, "response": resp_c, "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")})
                    st.rerun()

    with subtab_camarada:
        st.markdown("#### Camarada KGB de Infraestructura y Operaciones (Gemini RAG)")
        st.caption("Asistente técnico especializado con inyección contextual RAG (CMDB + Documentación).")

        with st.form(key="top_copilot_form", clear_on_submit=True):
            col_cin, col_cbtn = st.columns([5, 1])
            with col_cin:
                query_copilot_in = st.text_input("Consulta:", placeholder="Ej: Explícame el procedimiento de failover de Redis y sus dependencias...", label_visibility="collapsed")
            with col_cbtn:
                sub_copilot = st.form_submit_button("Consultar al Camarada", type="primary", width="stretch")

        st.markdown("<div style='margin-top:-6px;margin-bottom:6px;font-size:0.72rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;opacity:0.7;'>Consultas recomendadas:</div>", unsafe_allow_html=True)
        if "quick_copilot_ver" not in st.session_state:
            st.session_state.quick_copilot_ver = 0
        sel_c_pill = st.pills("Consultas recomendadas", options=[">_ Diagnóstico y estado de BALANCER001", ">_ Procedimiento de Failover Redis", ">_ Arquitectura de Autenticación JWT", ">_ Servidores críticos en DMZ", ">_ Políticas de parche y antivirus", ">_ Topología y dependencias SAP"], default=None, label_visibility="collapsed", key=f"pills_copilot_{st.session_state.quick_copilot_ver}")
        p_c_rapido = sel_c_pill.replace(">_ ", "").strip() if sel_c_pill else None
        if sel_c_pill:
            st.session_state.quick_copilot_ver += 1

        query_c_exec = p_c_rapido or (query_copilot_in.strip() if sub_copilot and query_copilot_in.strip() else None)
        if query_c_exec:
            with st.spinner("Analizando infraestructura..."):
                resp = generar_respuesta_asistente(query_c_exec, st.session_state.doc_store)
                st.session_state.historial_busquedas.insert(0, {"query": query_c_exec, "response": resp, "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")})
            st.rerun()

        st.markdown("---")
        if not st.session_state.historial_busquedas:
            st.markdown("""
            <div class="empty-state-container">
                <div class="empty-state-console-icon">&gt;_ kgb::rag_engine</div>
                <div class="empty-state-title">Camarada KGB de Infraestructura y Operaciones</div>
                <div class="empty-state-subtitle">Realiza preguntas analíticas y operativas fundamentadas estrictamente en la evidencia técnica.</div>
            </div>""", unsafe_allow_html=True)
        else:
            col_rt, col_rb = st.columns([4, 1])
            with col_rt:
                st.markdown(f"<div style='font-size:0.95rem;font-weight:600;'>Historial de Consultas ({len(st.session_state.historial_busquedas)}):</div>", unsafe_allow_html=True)
            with col_rb:
                if st.button(">_ Limpiar Chat", width="stretch", key="btn_clear_search_history_copilot"):
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

# ----------------- TAB 3: DOCUMENTACION TECNICA -----------------
with tab_docs:
    st.subheader("Repositorio de Documentacion Tecnica, Diagramas y Versionado")
    st.caption("Manuales de contingencia, procedimientos operativos, visor Lado a Lado y control de cambios.")

    if st.session_state.doc_store:
        mapa_fechas = {d: obtener_fecha_carga_documento(d) for d in st.session_state.doc_store.keys()}
        fechas_v = [f for f in mapa_fechas.values() if f]
        min_doc_d = min(fechas_v) if fechas_v else datetime.date.today()
        max_doc_d = max(fechas_v) if fechas_v else datetime.date.today()

        col_t4_t, col_t4_d, col_t4_s = st.columns([1.1, 1.3, 2.2], gap="small")
        with col_t4_t:
            filtro_t4 = st.selectbox("Tipo", ["Todos", "Diagramas e Imágenes (.png, .jpg, .svg)", "Excel (.xlsx, .xls)", "Documentos (.docx, .pdf, .pptx)", "Markdown / Texto (.md, .txt)"], key="tab4_type_selector")
        with col_t4_d:
            rango_fecha_doc = st.date_input("Fecha:", value=(min_doc_d, max_doc_d), min_value=min_doc_d, max_value=max_doc_d, key="tab4_date_range_selector")

        docs_disp = []
        for d in sorted(st.session_state.doc_store.keys()):
            ext_d = os.path.splitext(d)[1].lower()
            is_diag = d.startswith("DIAGRAMA__") or ext_d in IMAGE_EXTENSIONS
            if filtro_t4.startswith("Diagramas") and not is_diag:
                continue
            if filtro_t4.startswith("Excel") and ext_d not in ('.xlsx', '.xls'):
                continue
            if filtro_t4.startswith("Documentos") and ext_d not in ('.docx', '.pdf', '.pptx', '.doc'):
                continue
            if filtro_t4.startswith("Markdown") and (is_diag or ext_d not in ('.md', '.txt', '.csv')):
                continue
            f_d = mapa_fechas.get(d)
            if f_d and isinstance(rango_fecha_doc, (tuple, list)) and len(rango_fecha_doc) == 2 and not (rango_fecha_doc[0] <= f_d <= rango_fecha_doc[1]):
                continue
            docs_disp.append(d)

        with col_t4_s:
            doc_sel = st.selectbox(f"Seleccione Documento ({len(docs_disp)} disponibles)", docs_disp, format_func=normalizar_titulo_display, key="tab4_doc_selector") if docs_disp else None

        if doc_sel:
            doc_cont = st.session_state.doc_store.get(doc_sel, "")
            historial = inicializar_version_inicial_si_no_existe(doc_sel, doc_cont)
            u_ver = len(historial)
            u_edit = historial[-1]["autor"] if historial else "Desconocido"
            u_time = historial[-1]["timestamp"] if historial else "N/A"
            f_carga = historial[0]["timestamp"].split()[0] if (historial and " " in historial[0]["timestamp"]) else "N/A"
            ruta_orig = obtener_ruta_original(doc_sel, doc_cont)

            st.markdown(f"""
            <div style="background-color:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2);border-radius:6px;padding:8px 14px;margin-bottom:12px;font-size:0.85rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div><b>Documento:</b> <span style="color:#6366F1;font-weight:600;">{normalizar_titulo_display(doc_sel)}</span> <span style="font-family:monospace;opacity:0.65;font-size:0.8rem;">({doc_sel})</span></div>
                <div><b>Versión:</b> <span class="badge-ok">v{u_ver}</span></div>
                <div><b>Fecha Carga:</b> <span class="badge-tag">[{f_carga}]</span></div>
                <div><b>Último Editor:</b> <span style="color:#10B981;font-weight:500;">{u_edit}</span></div>
                <div><b>Actualizado:</b> <span style="opacity:0.75;">{u_time}</span></div>
            </div>""", unsafe_allow_html=True)

            subtab_v, subtab_e, subtab_h = st.tabs(["Visualización Lado a Lado", "Editar Documento", f"Historial de Versiones ({u_ver})"])

            with subtab_v:
                renderizar_lado_a_lado(doc_sel, doc_cont, ruta_orig, u_ver, u_edit, u_time, key_suffix="tab3_view")
                st.markdown("---")
                col_dla, col_dli = st.columns([1.5, 2.5])
                with col_dla:
                    es_x = doc_sel.lower().endswith(('.xlsx', '.xls')) and os.path.exists(os.path.join(DOCS_DIR, doc_sel))
                    if es_x:
                        with open(os.path.join(DOCS_DIR, doc_sel), "rb") as fx:
                            st.download_button(label=f"Descargar Versión Activa v{u_ver} (.xlsx)", data=fx.read(), file_name=sanitizar_nombre_descarga(doc_sel, u_ver, ".xlsx"), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key=f"dl_act_x_{doc_sel}")
                    else:
                        st.download_button(label=f"Descargar Versión Activa v{u_ver} (.md)", data=doc_cont.encode("utf-8"), file_name=sanitizar_nombre_descarga(doc_sel, u_ver, ".md"), mime="text/markdown", width="stretch", key=f"dl_act_m_{doc_sel}")
                with col_dli:
                    st.caption(f"Descarga la versión activa actual (**v{u_ver}**).")

            with subtab_e:
                es_x = doc_sel.lower().endswith(('.xlsx', '.xls')) and os.path.exists(os.path.join(DOCS_DIR, doc_sel))
                if es_x:
                    p_xl = os.path.join(DOCS_DIR, doc_sel)
                    mt_xl = os.path.getmtime(p_xl) if os.path.exists(p_xl) else 0.0
                    sheets_e = obtener_nombres_hojas_excel(p_xl, mt_xl)
                    col_es1, col_es2 = st.columns([1.5, 2.5])
                    with col_es1:
                        hoja_e = st.selectbox("Seleccionar Hoja:", sheets_e or ["Hoja1"], key=f"edit_sheet_sel_{doc_sel}")
                    with col_es2:
                        col_ae1, col_ae2 = st.columns(2)
                        with col_ae1:
                            aut_e = st.text_input("Editor (*)", placeholder="Juan Pérez", key=f"author_input_grid_{doc_sel}")
                        with col_ae2:
                            mot_e = st.text_input("Motivo (*)", placeholder="Actualización de IP", key=f"motive_input_grid_{doc_sel}")

                    df_e = cargar_hoja_excel_dataframe(p_xl, hoja_e, mt_xl)
                    df_mod = st.data_editor(df_e, width="stretch", num_rows="dynamic", height=480, key=f"grid_editor_{doc_sel}_{hoja_e}")
                    if st.button(f"Guardar y Publicar Versión v{u_ver + 1}", type="primary", key=f"btn_save_grid_{doc_sel}"):
                        if not aut_e or not aut_e.strip() or not mot_e or not mot_e.strip():
                            st.error("Error de Auditoría: Editor y Motivo son obligatorios.")
                        else:
                            nv = guardar_nueva_version_excel(doc_sel, hoja_e, df_mod, aut_e.strip(), mot_e.strip(), st.session_state.doc_store)
                            st.toast(f"Versión v{nv} guardada exitosamente")
                            st.rerun()
                else:
                    col_e1, col_e2 = st.columns([1, 2])
                    with col_e1:
                        aut_e = st.text_input("Editor (*)", placeholder="Juan Pérez", key=f"author_input_{doc_sel}")
                    with col_e2:
                        mot_e = st.text_input("Motivo (*)", placeholder="Actualización técnica", key=f"motive_input_{doc_sel}")

                    val_txt = doc_cont[:100_000] if len(doc_cont) > 100_000 else doc_cont
                    txt_edit = st.text_area("Contenido (Markdown)", value=val_txt, height=450, key=f"textarea_edit_{doc_sel}")
                    if st.button(f"Guardar y Publicar Versión v{u_ver + 1}", type="primary", key=f"btn_save_{doc_sel}"):
                        if not aut_e or not aut_e.strip() or not mot_e or not mot_e.strip():
                            st.error("Error de Auditoría: Editor y Motivo son obligatorios.")
                        else:
                            nv = guardar_nueva_version(doc_sel, txt_edit, aut_e.strip(), mot_e.strip(), st.session_state.doc_store)
                            if nv == u_ver:
                                st.info("[INFO] Sin cambios respecto a la versión actual.")
                            else:
                                st.toast(f"[OK] Versión v{nv} publicada con éxito")
                                st.rerun()

            with subtab_h:
                st.markdown("#### Historial de Revisiones y Control de Cambios")
                df_h = pd.DataFrame(historial)
                cols_h = [c for c in ["version", "timestamp", "autor", "comentario", "caracteres", "sha256"] if c in df_h.columns]
                df_h = df_h[cols_h].rename(columns={"version": "Versión", "timestamp": "Fecha y Hora", "autor": "Editor / Responsable", "comentario": "Motivo del Cambio", "caracteres": "Caracteres", "sha256": "Firma SHA-256"})
                st.dataframe(df_h, width="stretch", hide_index=True)

                st.markdown("---")
                opts_ver = {f"v{i['version']} - {i['timestamp']} ({i['autor']}): {i['comentario']}": i for i in reversed(historial)}
                v_sel_lbl = st.selectbox("Seleccione versión para inspeccionar / descargar:", list(opts_ver.keys()), key=f"select_hist_ver_{doc_sel}")
                it_sel = opts_ver[v_sel_lbl]
                c_snap = obtener_contenido_version(doc_sel, it_sel["archivo_snapshot"])
                ex_snap = it_sel.get("archivo_excel_snapshot")

                col_hv1, col_hv2 = st.columns(2)
                with col_hv1:
                    if ex_snap:
                        b_xl = obtener_bytes_snapshot(doc_sel, ex_snap)
                        if b_xl:
                            st.download_button(f"Descargar v{it_sel['version']} (.xlsx)", b_xl, sanitizar_nombre_descarga(doc_sel, it_sel['version'], ".xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key=f"btn_dl_x_h_{doc_sel}_{it_sel['version']}")
                    else:
                        st.download_button(f"Descargar v{it_sel['version']} (.md)", c_snap.encode("utf-8"), sanitizar_nombre_descarga(doc_sel, it_sel['version'], ".md"), "text/markdown", width="stretch", key=f"btn_dl_m_h_{doc_sel}_{it_sel['version']}")
                with col_hv2:
                    st.caption(f"Snapshot generado el **{it_sel['timestamp']}** por **{it_sel['autor']}**.")

                if it_sel["version"] != u_ver:
                    st.markdown("---")
                    st.markdown(f"##### Revertir Documento a la Versión v{it_sel['version']} (Rollback)")
                    col_ra, col_rm = st.columns([1, 2])
                    with col_ra:
                        aut_rb = st.text_input("Técnico que ejecuta Rollback (*)", key=f"author_rb_{doc_sel}_{it_sel['version']}")
                    with col_rm:
                        mot_rb = st.text_input("Justificación del Rollback (*)", key=f"motive_rb_{doc_sel}_{it_sel['version']}")
                    if st.button(f"Confirmar Rollback a Versión v{it_sel['version']}", type="primary", key=f"btn_rb_{doc_sel}_{it_sel['version']}"):
                        if not aut_rb.strip() or not mot_rb.strip():
                            st.error("Error de Auditoría: Editor y Justificación son obligatorios.")
                        else:
                            if ex_snap and os.path.exists(os.path.join(HISTORY_DIR, doc_sel, ex_snap)):
                                shutil.copy2(os.path.join(HISTORY_DIR, doc_sel, ex_snap), os.path.join(DOCS_DIR, doc_sel))
                                nuevo_m = procesar_excel_limpio(os.path.join(DOCS_DIR, doc_sel))
                            else:
                                nuevo_m = c_snap
                            nv = guardar_nueva_version(doc_sel, nuevo_m, aut_rb.strip(), f"[Rollback a v{it_sel['version']}] {mot_rb.strip()}", st.session_state.doc_store)
                            st.toast(f"Restaurado a v{it_sel['version']} (v{nv})")
                            st.rerun()

                if len(historial) >= 2:
                    with st.expander("Comparar diferencias de texto entre dos versiones (Diff)", expanded=False):
                        c_d1, c_d2 = st.columns(2)
                        n_vers = [f"v{i['version']} - {i['timestamp']} ({i['autor']})" for i in historial]
                        map_v = {n_vers[idx]: historial[idx] for idx in range(len(historial))}
                        with c_d1:
                            v_base = st.selectbox("Versión Base:", n_vers, index=0, key=f"diff_base_{doc_sel}")
                        with c_d2:
                            v_comp = st.selectbox("Versión Comparada:", n_vers, index=len(n_vers)-1, key=f"diff_comp_{doc_sel}")
                        st.code(generar_diff_texto(obtener_contenido_version(doc_sel, map_v[v_base]["archivo_snapshot"]), obtener_contenido_version(doc_sel, map_v[v_comp]["archivo_snapshot"]), v_base, v_comp), language="diff")

                with st.expander("Registro Central de Auditoría Global (Audit Log)", expanded=False):
                    evs = obtener_todos_los_eventos_auditoria()
                    if evs:
                        df_aud = pd.DataFrame(evs)
                        df_aud_disp = df_aud[df_aud["documento"] == doc_sel] if st.checkbox("Filtrar solo este documento", value=True, key=f"chk_aud_{doc_sel}") else df_aud
                        st.dataframe(df_aud_disp.rename(columns={"timestamp": "Timestamp", "documento": "Documento", "accion": "Acción", "version_anterior": "Versión Ant.", "version_nueva": "Versión Nueva", "editor_responsable": "Editor", "motivo_justificacion": "Motivo"}), width="stretch", hide_index=True)
    else:
        st.warning("No hay documentos indexados.")

# ----------------- TAB 4: PLANTILLAS Y RUNBOOKS -----------------
with tab_templates:
    st.subheader("Generador Rápido de Documentación y Runbooks")
    st.caption("Crea y publica procedimientos técnicos estandarizados o define nuevos tipos personalizados en 2 minutos.")

    sac.steps(items=[sac.StepsItem(title="Paso 1", subtitle="Selección y Metadatos"), sac.StepsItem(title="Paso 2", subtitle="Parámetros Técnicos"), sac.StepsItem(title="Paso 3", subtitle="Previsualización y Publicación")], size="sm", return_index=False)
    st.markdown("---")

    col_t1, col_t2 = st.columns([1, 1], gap="large")
    with col_t1:
        st.markdown("#### 1. Configuración del Procedimiento")
        tipo_sel = st.selectbox("Plantilla / Tipo de Procedimiento", obtener_todos_los_tipos_plantillas(), key="select_tipo_procedimiento_gen")
        es_nuevo_t = "[+ Crear" in tipo_sel

        if es_nuevo_t:
            nuevo_t_nom = st.text_input("Nombre de la Plantilla (*)", placeholder="Ej: Auditoría de Accesos", key="input_nuevo_tipo_proc")
            guardar_cat = st.checkbox("Guardar en catálogo permanente", value=True)
            tipo_plantilla = nuevo_t_nom.strip() or "Procedimiento Personalizado"
        else:
            tipo_plantilla = tipo_sel.replace("[Plantilla]", "").replace("[Personalizado]", "").strip()
            guardar_cat, nuevo_t_nom = False, ""

        with st.expander("Explorar catálogo de plantillas base reservadas (Opcional)", expanded=False):
            col_rs, col_rb = st.columns([3, 1])
            with col_rs:
                base_act = st.selectbox("Seleccionar plantilla base a activar:", PLANTILLAS_BASE_RESERVADAS, key="sel_plantilla_base_res")
            with col_rb:
                st.write("")
                st.write("")
                if st.button("[+ Activar]", key="btn_activar_plantilla_base", width="stretch"):
                    guardar_plantilla_personalizada(base_act, f"Plantilla activada: {base_act}", ["criterio", "pasos", "verif"])
                    st.toast(f"[OK] Plantilla '{base_act}' activada")
                    st.rerun()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            autor = st.text_input("Autor (*)", value="Developer / DevOps", key="proc_autor_input")
            nombre_srv = st.text_input("Servicio (*)", value="Booking Core Engine", key="proc_srv_input")
        with col_g2:
            nivel_arq = st.selectbox("Nivel", ["L4 - Aplicación y Negocio", "L3 - Middleware e Integración", "L2 - Virtualización y Cómputo", "L1 - Hardware e Infraestructura Base"], key="proc_nivel_input")
            ambiente = st.selectbox("Ambiente", ["Producción", "Staging / QA", "Desarrollo", "Datacenter DR", "Todos los Ambientes"], key="proc_amb_input")

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            criticidad = st.selectbox("Criticidad / SLA", ["Crítico 7x24 (P1)", "Alta (P2)", "Media (P3)", "Baja (P4)"], index=2, key="proc_crit_input")
        with col_g4:
            ventana = st.text_input("Ventana", value="02:00 a 04:00 AM (Horario no hábil)", key="proc_vent_input")

        servidores = st.text_input("Servidores / VMs / IPs", value="BALANCER001, 10.24.0.125, VM-BOOKING-01", key="proc_srvs_input")

        st.markdown("---")
        st.markdown("##### Parámetros Específicos del Procedimiento")
        params = {"ambiente": ambiente, "criticidad": criticidad, "ventana": ventana, "servidores": servidores}

        if "Rollback" in tipo_plantilla:
            params["criterio"] = st.text_area("Criterio de Activación", value="Latencia > 500ms o Error Rate > 2%")
            params["pasos"] = st.text_area("Pasos de Reversión", value="1. Ejecutar pipeline rollback release-v2.4.1\n2. Revertir esquema BD\n3. redis-cli FLUSHDB")
            params["verif"] = st.text_area("Verificación de Salud", value="curl -I https://api.booking.internal/health\nsystemctl status booking-service")
        elif "Paso a Producción" in tipo_plantilla:
            params["version"] = st.text_input("Versión / Tag", value="v2.5.0")
            params["pipeline"] = st.text_input("Pipeline URL", value="https://dev.azure.com/smucorp/pipelines/142")
            params["variables"] = st.text_area("Variables de Entorno", value="REDIS_HOST=10.24.0.126\nLOG_LEVEL=INFO")
            params["smoke"] = st.text_area("Checklist Smoke Tests", value="- [ ] Endpoint /health HTTP 200\n- [ ] Cero alertas en Nagios")
        elif "Postmortem" in tipo_plantilla:
            params["incidente_id"] = st.text_input("Ticket ID", value="INC-88912")
            params["impacto"] = st.text_area("Impacto", value="Indisponibilidad de 14 minutos. 120 transacciones rechazadas.")
            params["causa"] = st.text_area("Causa Raíz (RCA)", value="Agotamiento de pool de conexiones JDBC.")
            params["solucion"] = st.text_area("Solución Inmediata", value="Reinicio worker WSO2 y ampliación de maxConnections.")
            params["preventiva"] = st.text_area("Medida Preventiva", value="Creación de índice y ajuste de timeout.")
        elif "Microservicio" in tipo_plantilla:
            params["endpoint"] = st.text_input("Endpoint Base", value="/api/v1/booking")
            params["auth"] = st.text_input("Autenticación", value="OAuth2 Bearer Token (Redis Sentinel)")
            params["dependencias"] = st.text_area("Dependencias", value="* VM: VM-BOOKING-01 (10.24.0.125)\n* DB: Postgres HA (10.24.0.130)")
        elif "Parchado" in tipo_plantilla or "Mantenimiento de SO" in tipo_plantilla:
            params["paquetes"] = st.text_area("Paquetes", value="Actualización mensual del kernel y OpenSSL.")
            params["pasos_parchado"] = st.text_area("Pasos de Parchado", value="1. Snapshot en vCloud\n2. yum update -y\n3. Reboot nodo secundario")
            params["rollback_parchado"] = st.text_area("Plan de Reversión", value="Revertir al snapshot de VM en vCloud.")
        elif "Certificados" in tipo_plantilla or "SSL" in tipo_plantilla:
            params["dominio"] = st.text_input("Dominio / CN", value="*.smucorp.internal")
            params["ruta_cert"] = st.text_input("Ruta de Instalación", value="/etc/ssl/certs/api_smucorp.crt")
            params["comandos_renov"] = st.text_area("Comandos Generación", value="openssl req -new -newkey rsa:2048 -nodes -keyout api.key -out api.csr")
            params["validacion_ssl"] = st.text_area("Validación SSL", value="echo | openssl s_client -connect localhost:443 -servername api.smucorp.internal 2>/dev/null | openssl x509 -noout -dates")
        elif "Disaster Recovery" in tipo_plantilla or "DRP" in tipo_plantilla:
            params["rpo_rto"] = st.text_input("RPO / RTO", value="RPO: 15 min | RTO: 1 hora")
            params["activacion_drp"] = st.text_area("Criterios Activación DRP", value="Indisponibilidad total del Datacenter Principal.")
            params["pasos_drp"] = st.text_area("Pasos Conmutación", value="1. Conmutar DNS\n2. Promover réplica PostgreSQL\n3. Iniciar workers")
        elif "Respaldo" in tipo_plantilla or "Base de Datos" in tipo_plantilla:
            params["motor_bd"] = st.text_input("Motor de BD", value="PostgreSQL 15 HA")
            params["comando_backup"] = st.text_area("Script Backup", value="pg_dump -h 10.24.0.130 -U admin -Fc db_booking > backup.dump")
            params["comando_restore"] = st.text_area("Script Restore", value="pg_restore -h 10.24.0.130 -U admin -d db_booking backup.dump")
        elif "Contingencia" in tipo_plantilla or "Failover" in tipo_plantilla:
            params["sintoma"] = st.text_area("Síntoma de Falla", value="Host ESXi no responde o alerta CRITICAL en Nagios.")
            params["pasos"] = st.text_area("Procedimiento Failover", value="1. Conmutar en HAProxy a BALANCER002\n2. Activar réplica en vCloud")
        else:
            params["objetivo"] = st.text_area("Objetivo y Alcance", value=f"Procedimiento para {tipo_plantilla} en {nombre_srv}.")
            params["prerequisitos"] = st.text_area("Requisitos Previos", value="* Acceso SSH con sudo\n* Notificación a Operaciones\n* Snapshot preventivo")
            params["pasos_custom"] = st.text_area("Pasos Detallados", value="1. Validar estado: systemctl status servicio\n2. Ejecutar script\n3. Verificar logs")
            params["verificacion_custom"] = st.text_area("Validación", value="* Cero errores 5xx\n* Nagios check_http en OK")
            params["rollback_custom"] = st.text_area("Plan de Contingencia", value="1. Detener script\n2. Restaurar backup\n3. Reiniciar servicio")

        doc_gen_md, fname_sug = generar_doc_plantilla(tipo_plantilla, autor, nombre_srv, nivel_arq, params)

    with col_t2:
        st.markdown("#### 2. Previsualización en Vivo")
        nom_f = st.text_input("Nombre de Archivo Final (.md)", value=fname_sug, key="input_nombre_archivo_proc_final")
        with st.container(border=True):
            st.markdown(doc_gen_md)

        st.divider()
        if st.button("Guardar y Publicar en Base de Conocimiento", type="primary", width="stretch", key="btn_guardar_doc_plantilla_final"):
            if not nom_f.endswith(".md"):
                nom_f += ".md"
            if es_nuevo_t and guardar_cat and nuevo_t_nom.strip():
                guardar_plantilla_personalizada(nuevo_t_nom.strip(), f"Plantilla personalizada {nuevo_t_nom.strip()}", ["objetivo", "prerequisitos", "pasos_custom", "verificacion_custom", "rollback_custom"])

            ruta_dest = os.path.join(DOCS_DIR, nom_f)
            os.makedirs(DOCS_DIR, exist_ok=True)
            with open(ruta_dest, "w", encoding="utf-8") as f_out:
                f_out.write(doc_gen_md)

            st.session_state.doc_store[nom_f] = doc_gen_md
            inicializar_version_inicial_si_no_existe(nom_f, doc_gen_md, autor=autor, comentario=f"Creación mediante plantilla: {tipo_plantilla}")
            st.toast(f"Procedimiento guardado como {nom_f}")
            st.success(f"¡Procedimiento guardado e indexado como **{nom_f}** [Version v1]!")
            st.rerun()

# ----------------- TAB 5: INTEGRACIÓN SAP (API) -----------------
with tab_sap:
    st.markdown("""
    <div class="search-result-card" style="margin-bottom: 18px; border-left: 4px solid #6366F1;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="badge-info">[SAP LANDSCAPE]</span>
                <span class="badge-ok">[API REST / ODATA]</span>
                <span class="badge-tag">[CONSOLA DE OPERACIONES]</span>
            </div>
            <div><span class="badge-pulse-online"><span class="pulse-dot"></span>CONECTOR OPERATIVO</span></div>
        </div>
        <div class="main-title" style="font-size:1.35rem; margin-bottom:4px;">Telemetría y Gestión de Infraestructura SAP</div>
        <div class="sub-title" style="margin-bottom:0; font-size:0.88rem;">Monitoreo del landscape SAP S/4HANA 2022, SAP HANA DB 2.0 (HSR), NetWeaver (ASCS/PAS/AAS) y Solution Manager (LMDB).</div>
    </div>""", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("#### Configuración del Endpoint y Conectividad")
        col_u, col_a, col_c = st.columns([2.2, 1.8, 1.5], gap="small")
        with col_u:
            sap_ep = st.text_input("Endpoint API Gateway SAP", value=obtener_secreto("SAP_ENDPOINT", ""), help="URL base del servicio SAP.")
        with col_a:
            sap_auth = st.selectbox("Autenticación", ["OAuth 2.0 (Client Credentials / mTLS)", "SAP Host Agent HTTPS (:1129)", "SAP Solution Manager / FRUN (OData)"])
        with col_c:
            sap_cid = st.text_input("Client ID", value=obtener_secreto("SAP_CLIENT_ID", ""), type="password")

        col_b1, col_b2, col_b3 = st.columns([1.2, 1.2, 1.0], gap="small")
        with col_b1:
            btn_t_sap = st.button(">_ Probar Conexión API", width="stretch", type="primary")
        with col_b2:
            btn_s_sap = st.button(">_ Sincronizar CMDB Local", width="stretch")
        with col_b3:
            st.download_button(label="Descargar Payload JSON", data=json.dumps(generar_payload_json_sap(sap_ep), indent=2, ensure_ascii=False), file_name="sap_landscape_payload.json", mime="application/json", width="stretch")

        if btn_t_sap:
            res_conn = probar_conexion_api_sap(sap_ep, sap_auth, sap_cid)
            st.session_state.sap_conn_result = res_conn

        if "sap_conn_result" in st.session_state:
            rc = st.session_state.sap_conn_result
            st.markdown(f"""
            <div style="background-color:rgba(16,185,129,0.08);border:1px solid #10B981;border-radius:6px;padding:10px 14px;margin-top:12px;font-size:0.85rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div><span class="badge-ok">[200 OK]</span> <b style="margin-left:6px;">Conexión Verificada:</b> {rc['endpoint']}</div>
                <div><span class="badge-tag">Latencia: {rc['latencia_ms']} ms</span><span class="badge-info" style="margin-left:4px;">{rc['protocolo']}</span><span class="badge-tag" style="margin-left:4px;">{rc['timestamp']}</span></div>
            </div>""", unsafe_allow_html=True)

        if btn_s_sap:
            ok, cnt, msg = sincronizar_servidores_sap_cmdb(autor="Conector API SAP")
            if ok:
                st.toast(f"[OK] {msg}")
                st.success(f"[OK] {msg}")
            else:
                st.warning(f"[WARN] {msg}")

    df_sap = obtener_inventario_sap_df()
    total_sap = len(df_sap)
    sids = df_sap["sid"].unique()

    kpi_sap_html = [
        f'<div class="search-result-card" style="padding:12px 14px;text-align:center;"><div style="font-size:0.75rem;opacity:0.7;font-weight:500;">SISTEMAS SAP (SIDs)</div><div style="font-size:1.4rem;font-weight:700;color:#6366F1;margin:4px 0;">{len(sids)} SIDs</div><div style="font-size:0.72rem;opacity:0.8;">PRD, HDB, SM1</div></div>',
        f'<div class="search-result-card" style="padding:12px 14px;text-align:center;"><div style="font-size:0.75rem;opacity:0.7;font-weight:500;">INSTANCIAS / NODOS</div><div style="font-size:1.4rem;font-weight:700;color:#10B981;margin:4px 0;">{total_sap} Hosts</div><div style="font-size:0.72rem;opacity:0.8;">HANA, NetWeaver, WDisp</div></div>',
        '<div class="search-result-card" style="padding:12px 14px;text-align:center;"><div style="font-size:0.75rem;opacity:0.7;font-weight:500;">REPLICACIÓN HANA HSR</div><div style="font-size:1.4rem;font-weight:700;color:#10B981;margin:4px 0;">IN-SYNC</div><div style="font-size:0.72rem;opacity:0.8;">Latencia réplica: 1.4 ms</div></div>',
        '<div class="search-result-card" style="padding:12px 14px;text-align:center;"><div style="font-size:0.75rem;opacity:0.7;font-weight:500;">ALERTAS ACTIVAS</div><div style="font-size:1.4rem;font-weight:700;color:#D97706;margin:4px 0;">1 Alerta</div><div style="font-size:0.72rem;opacity:0.8;">Memoria SolMan (89.2%)</div></div>',
    ]
    st.markdown(f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0;">{"".join(kpi_sap_html)}</div>', unsafe_allow_html=True)

    tab_sinv, tab_stopo, tab_sjson, tab_salert = st.tabs([f"Inventario de Servidores ({total_sap})", "Topología del Landscape SAP", "Payload API (JSON)", "Alertas y Eventos (2)"])

    with tab_sinv:
        col_fsid, col_fsrc = st.columns([1.5, 3.5])
        with col_fsid:
            filtro_sid = st.pills("Filtrar por SID:", options=["Todos"] + list(sids), default="Todos", key="pills_filtro_sid_sap") or "Todos"
        with col_fsrc:
            filtro_txt_sap = st.text_input("Buscar host, IP o componente:", key="txt_search_sap_inv")

        df_sm = df_sap.copy()
        if filtro_sid != "Todos":
            df_sm = df_sm[df_sm["sid"] == filtro_sid]
        if filtro_txt_sap:
            t = filtro_txt_sap.lower()
            df_sm = df_sm[df_sm["servidor_id"].str.lower().str.contains(t) | df_sm["ip"].str.lower().str.contains(t) | df_sm["componente"].str.lower().str.contains(t)]

        cols_sap_d = [c for c in ["servidor_id", "sid", "instancia", "ip", "nivel_arquitectura", "componente", "cpu_pct", "mem_pct", "disco_pct", "estado", "nagios_check"] if c in df_sm.columns]
        st.dataframe(df_sm[cols_sap_d].rename(columns={"servidor_id": "Servidor", "sid": "SID", "instancia": "Instancia", "ip": "IP", "nivel_arquitectura": "Capa", "componente": "Servicio / Componente", "cpu_pct": "CPU %", "mem_pct": "Mem %", "disco_pct": "Disco %", "estado": "Estado", "nagios_check": "Chequeo Host Agent"}), width="stretch", hide_index=True)

    with tab_stopo:
        with st.container(border=True):
            st.markdown(f"```mermaid\n{generar_topologia_sap_mermaid()}\n```")

    with tab_sjson:
        st.json(generar_payload_json_sap(sap_ep))

    with tab_salert:
        for al in obtener_alertas_sap():
            tag_s = '<span class="badge-warn">[ADVERTENCIA]</span>' if al["severidad"] == "Advertencia" else '<span class="badge-info">[INFO]</span>'
            border_c = '#D97706' if al['severidad'] == 'Advertencia' else '#6366F1'
            st.markdown(f"""
            <div class="search-result-card" style="margin-bottom:10px;border-left:3px solid {border_c};">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><div>{tag_s} <b style="margin-left:6px;">{al['id_alerta']}</b> - SID: <code>{al['sid']}</code> | Host: <code>{al['servidor_id']}</code></div><span class="badge-tag">{al['timestamp']}</span></div>
                <div style="font-size:0.88rem;margin-bottom:4px;"><b>Tipo:</b> {al['tipo']} - {al['mensaje']}</div>
                <div style="font-size:0.8rem;opacity:0.8;"><b>Acción:</b> {al['accion_recomendada']}</div>
            </div>""", unsafe_allow_html=True)

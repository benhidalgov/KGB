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
try:
    from core.procesador import (
        IMAGE_EXTENSIONS,
        OFFICE_EXTENSIONS,
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
except ImportError:
    import importlib
    import core.procesador
    importlib.reload(core.procesador)
    from core.procesador import (
        IMAGE_EXTENSIONS,
        OFFICE_EXTENSIONS,
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
try:
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
except ImportError:
    import importlib
    import sys
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("core.") or mod_name == "core":
            try:
                importlib.reload(sys.modules[mod_name])
            except Exception:
                pass
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
    verificar_credenciales,
    es_usuario_autenticado,
    obtener_usuario_actual,
    es_administrador,
    tiene_permiso,
    cerrar_sesion,
    renderizar_pantalla_login,
)
from excel_cleaner import procesar_excel_limpio
import os
import re
import json
import io
import time
import html
import shutil
import zipfile
import datetime
import duckdb
import pandas as pd
import streamlit as st
import streamlit_antd_components as sac


def procesar_e_ingestar_binario(
    clean_name: str,
    buf: bytes,
    doc_store: dict,
    autor: str = "Técnico / Panel Lateral",
    origen_detalle: str = "Carga en panel lateral"
) -> tuple[str, str]:
    """Procesa e ingesta un archivo binario (ofimático, imagen o markdown), versionándolo y actualizando doc_store.
    Retorna (tipo_resultado, mensaje) donde tipo_resultado es 'nuevo', 'actualizado', 'sin_cambios' o 'ignorado'.
    """
    ext = os.path.splitext(clean_name)[1].lower()
    nuevo_hash = calcular_sha256(buf)

    # 1. Preservar siempre el binario en data/originals/
    orig_save_path = os.path.join(ORIGINALS_DIR, clean_name)
    with open(orig_save_path, "wb") as f_orig:
        f_orig.write(buf)

    # 2. Caso: Imágenes y Diagramas
    if ext in IMAGE_EXTENSIONS:
        asset_save_path = os.path.join(ASSETS_DIR, clean_name)
        with open(asset_save_path, "wb") as f_asset:
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
            else:
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

    # 3. Caso: Documentos Ofimáticos, Excel, PDF, Texto y Markdown
    else:
        save_path = os.path.join(DOCS_DIR, clean_name)
        if os.path.exists(save_path):
            with open(save_path, "rb") as f:
                existente_bytes = f.read()
            existente_hash = calcular_sha256(existente_bytes)

            if nuevo_hash == existente_hash:
                return "sin_cambios", f"Archivo '{clean_name}' ya indexado sin cambios."
            else:
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


# 1. Configuracion de Streamlit
st.set_page_config(
    page_title="Consultadora de documentos IG",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(cargar_estilos_css(), unsafe_allow_html=True)
# Eje 1: Linea de acento superior (gradiente indigo -> verde)
st.markdown('<div class="accent-top-bar"></div>', unsafe_allow_html=True)

# Verificación de Autenticación Corporativa y Control de Acceso (RBAC)
if not es_usuario_autenticado():
    renderizar_pantalla_login()
    st.stop()

# 2. Inicializacion de Estado y Documentos
if "historial_busquedas" not in st.session_state:
    st.session_state.historial_busquedas = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "doc_store" not in st.session_state:
    st.session_state.doc_store = {}
    cargar_documentos_locales(st.session_state.doc_store)
elif any(len(v) > 150_000 for v in st.session_state.doc_store.values()):
    # Saneamiento automático en caliente si la sesión del usuario conservaba cadenas residuales de Base64
    limpiar_cache_documentos()
    st.session_state.doc_store.clear()
    cargar_documentos_locales(st.session_state.doc_store, force=True)

if "quick_pills_version" not in st.session_state:
    st.session_state.quick_pills_version = 0


# 3. Sidebar (Panel de Control e Ingesta)
with st.sidebar:
    user_act = obtener_usuario_actual()
    st.markdown(f"""
<div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 6px; padding: 10px 12px; margin-bottom: 10px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-size: 0.68rem; font-weight: 700; color: #6366F1; text-transform: uppercase;">Sesión Activa</span>
        <span class="badge-ok" style="font-size: 0.65rem;">{user_act.get('rol', 'Usuario')}</span>
    </div>
    <div style="font-size: 0.9rem; font-weight: 600;">{user_act.get('nombre', user_act.get('username'))}</div>
    <div style="font-size: 0.68rem; opacity: 0.6; font-family: monospace;">@{user_act.get('username')}</div>
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
    <div class="sidebar-header-sub">Ingesta de activos, explorador de base documental y telemetría de motores.</div>
</div>
""", unsafe_allow_html=True)

    # Ingesta de Archivos y Paquetes en Lote
    st.markdown("#### Ingesta de Archivos (Batch & Lotes)")
    st.markdown("""
<div class="sidebar-format-tags">
    <span class="sidebar-format-tag">[ZIP BATCH]</span>
    <span class="sidebar-format-tag">[PDF]</span>
    <span class="sidebar-format-tag">[DOCX]</span>
    <span class="sidebar-format-tag">[XLSX]</span>
    <span class="sidebar-format-tag">[DIAGRAMAS]</span>
    <span class="sidebar-format-tag">[MD]</span>
</div>
""", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Arrastra archivos o paquetes ZIP en lote:",
        type=["pdf", "docx", "xlsx", "xls", "csv", "txt",
              "md", "pptx", "png", "jpg", "jpeg", "svg", "webp", "zip"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Formatos soportados: Paquetes ZIP (lotes completos), PDF, Word (.docx), Excel (.xlsx/.xls), Markdown (.md), Diagramas e Imágenes (.png, .jpg, .svg), CSV, TXT, PPTX."
    )

    if uploaded_files:
        archivos_procesados = 0
        archivos_nuevos = 0
        archivos_actualizados = 0

        for uf in uploaded_files:
            clean_name = normalizar_nombre_archivo(uf.name)
            ext_uf = os.path.splitext(clean_name)[1].lower()
            buf = uf.getbuffer().tobytes()

            # Caso A: Descompresión e Ingesta Batch de Paquete ZIP
            if ext_uf == ".zip":
                try:
                    with zipfile.ZipFile(io.BytesIO(buf)) as z:
                        zip_items = [zi for zi in z.infolist() if not zi.is_dir()]
                        zip_ingestados = 0

                        for zinfo in zip_items:
                            inner_fname = os.path.basename(zinfo.filename)
                            if not inner_fname or inner_fname.startswith(".") or "__MACOSX" in zinfo.filename:
                                continue
                            inner_clean = normalizar_nombre_archivo(inner_fname)
                            ext_inner = os.path.splitext(inner_clean)[1].lower()
                            if ext_inner in SUPPORTED_EXTENSIONS or ext_inner in IMAGE_EXTENSIONS:
                                inner_buf = z.read(zinfo)
                                estado, msg = procesar_e_ingestar_binario(
                                    clean_name=inner_clean,
                                    buf=inner_buf,
                                    doc_store=st.session_state.doc_store,
                                    autor="Técnico / Paquete ZIP",
                                    origen_detalle=f"Lote ZIP: {clean_name}"
                                )
                                zip_ingestados += 1
                                archivos_procesados += 1
                                if estado == "nuevo":
                                    archivos_nuevos += 1
                                elif estado == "actualizado":
                                    archivos_actualizados += 1

                        st.toast(f"[OK] Paquete ZIP '{clean_name}': {zip_ingestados} archivos procesados e indexados.")
                except Exception as e_zip:
                    st.error(f"[ERROR] No se pudo procesar el archivo ZIP '{clean_name}': {str(e_zip)}")

            # Caso B: Archivo Individual o Múltiple Directo
            else:
                estado, msg = procesar_e_ingestar_binario(
                    clean_name=clean_name,
                    buf=buf,
                    doc_store=st.session_state.doc_store,
                    autor="Técnico / Panel Lateral",
                    origen_detalle="Carga en panel lateral"
                )
                archivos_procesados += 1
                if estado == "nuevo":
                    archivos_nuevos += 1
                    st.toast(f"[OK] {msg}")
                elif estado == "actualizado":
                    archivos_actualizados += 1
                    st.toast(f"[OK] {msg}")
                elif estado == "sin_cambios":
                    st.toast(f"[INFO] {msg}")

        if archivos_procesados > 1:
            st.success(f"[OK] Lote completado: {archivos_procesados} archivos evaluados ({archivos_nuevos} nuevos, {archivos_actualizados} actualizados).")

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
                    display_name = normalizar_titulo_display(d)
                    if d.startswith("DIAGRAMA__") or ext in IMAGE_EXTENSIONS:
                        tag = '<span class="badge-ok" style="font-size:0.64rem;padding:1px 4px;">[DIAGRAMA]</span>'
                    elif ext in ('.xlsx', '.xls'):
                        tag = '<span class="badge-info" style="font-size:0.64rem;padding:1px 4px;">[EXCEL]</span>'
                    elif ext in ('.pdf', '.docx', '.pptx', '.doc'):
                        tag = '<span class="badge-warn" style="font-size:0.64rem;padding:1px 4px;">[DOC]</span>'
                    else:
                        tag = '<span class="badge-tag" style="font-size:0.64rem;padding:1px 4px;">[MD]</span>'

                    size_kb = len(st.session_state.doc_store[d]) / 1024
                    f_d = obtener_fecha_carga_documento(d)
                    fecha_str = f_d.strftime('%Y-%m-%d')

                    doc_items_html.append(f"""
<div class="sidebar-doc-card">
    <div class="sidebar-doc-card-header">
        <span class="sidebar-doc-name" title="{d}">{display_name}</span>
        {tag}
    </div>
    <div class="sidebar-doc-meta">
        <span>{fecha_str}</span>
        <span>{size_kb:.1f} KB</span>
    </div>
    <div style="font-size:0.65rem; opacity:0.55; font-family:monospace; margin-top:2px; word-break:break-all;">{d}</div>
</div>
""")
                doc_items_html.append('</div>')
                st.markdown("".join(doc_items_html), unsafe_allow_html=True)
            else:
                st.caption("No hay documentos que coincidan con el filtro.")
    else:
        st.info("No hay documentos indexados aún.")

    st.markdown("---")

    # Acciones de Consola
    st.markdown("#### Acciones de Consola")
    if st.button(">_ Reindexar", help="Recarga todos los documentos desde data/docs/ y data/docs/assets/", width="stretch", key="btn_sidebar_reindexar"):
        limpiar_cache_documentos()
        cargar_documentos_locales(st.session_state.doc_store, force=True)
        limpiar_cache_consultas()
        st.toast("[OK] Base documental y assets reindexados con éxito")
        st.rerun()

    st.markdown("---")

    # Bóveda de Seguridad y Credenciales (Vault) - Exclusiva para Administradores
    if tiene_permiso("puede_ver_vault"):
        with st.expander("Bóveda de Credenciales [VAULT]", expanded=False):
            secretos_lista = listar_secretos_disponibles()
            cfg_count = sum(1 for s in secretos_lista if s["estado"] == "[CONFIGURADO]")
            st.markdown(f"<div style='font-size:0.75rem; margin-bottom:8px; opacity:0.8;'>Estado de llaves: <b>{cfg_count} configurada(s)</b> bajo cifrado AES-256.</div>", unsafe_allow_html=True)

            for s in secretos_lista:
                tag_st = '<span class="badge-ok" style="font-size:0.62rem;padding:1px 4px;">[CONFIGURADO]</span>' if s["estado"] == "[CONFIGURADO]" else '<span class="badge-tag" style="font-size:0.62rem;padding:1px 4px;">[NO CONFIGURADO]</span>'
                st.markdown(f"""
<div style="font-size:0.72rem; padding:3px 0; display:flex; justify-content:space-between; align-items:center;">
    <span style="font-family:monospace; font-weight:600;">{s['clave']}</span>
    {tag_st}
</div>
<div style="font-size:0.64rem; opacity:0.6; margin-bottom:4px;">Origen: {s['origen']} {f'({s["vista_previa"]})' if s['vista_previa'] != '-' else ''}</div>
""", unsafe_allow_html=True)

            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            st.markdown("<b style='font-size:0.75rem;'>Guardar o Actualizar Clave:</b>", unsafe_allow_html=True)
            claves_predefinidas = [s["clave"] for s in secretos_lista] + ["OTRA_CLAVE_PERSONALIZADA"]
            sel_clave = st.selectbox("Seleccionar Llave:", claves_predefinidas, key="sb_vault_sel_key", label_visibility="collapsed")

            if sel_clave == "OTRA_CLAVE_PERSONALIZADA":
                nombre_clave_final = st.text_input("Nombre de la Clave:", value="", placeholder="EJ: MI_API_KEY", key="sb_vault_custom_key")
            else:
                nombre_clave_final = sel_clave

            if "vault_input_version" not in st.session_state:
                st.session_state.vault_input_version = 0

            valor_secreto = st.text_input(
                "Valor del Secreto:",
                value="",
                type="password",
                key=f"sb_vault_secret_val_{st.session_state.vault_input_version}",
                label_visibility="collapsed",
                placeholder="Pegar token / API key..."
            )

            col_v_guardar, col_v_del = st.columns(2)
            with col_v_guardar:
                if st.button(">_ Guardar", width="stretch", key="btn_vault_guardar"):
                    if nombre_clave_final and valor_secreto:
                        if guardar_secreto(nombre_clave_final, valor_secreto, autor=f"{user_act.get('username', 'admin')} ({user_act.get('rol', 'Admin')})"):
                            st.session_state.vault_input_version += 1
                            st.toast(f"[OK] Credencial '{nombre_clave_final}' cifrada en bóveda.")
                            st.rerun()
                    else:
                        st.toast("[WARN] Ingrese nombre y valor de secreto.")
            with col_v_del:
                if st.button(">_ Revocar", width="stretch", key="btn_vault_eliminar"):
                    if nombre_clave_final:
                        if eliminar_secreto(nombre_clave_final, autor=f"{user_act.get('username', 'admin')} ({user_act.get('rol', 'Admin')})"):
                            st.session_state.vault_input_version += 1
                            st.toast(f"[INFO] Credencial '{nombre_clave_final}' revocada.")
                            st.rerun()



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
tab_chat, tab_analytics, tab_docs, tab_templates, tab_sap = st.tabs([
    "Consultas y Búsqueda",
    f"Historial de Mantenimientos ({total_srvs})",
    f"Documentación Técnica ({cant_docs})",
    "Plantillas y Runbooks",
    "Integración SAP (API)"
])

# ----------------- TAB 1: BUSCADOR Y ASISTENTE  -----------------
with tab_chat:
    subtab_duckdb, subtab_copilot = st.tabs([
        "Búsqueda Textual (DuckDB & Docs)",
        "Copilot de Infraestructura (Gemini RAG)"
    ])

    # ---------------- SUBTAB 1.1: BÚSQUEDA TEXTUAL (DUCKDB + DOCS) ----------------
    with subtab_duckdb:
        st.markdown("#### Búsqueda Textual en Inventario CMDB y Documentación")
        st.caption("Búsqueda indexada instantánea en memoria RAM (< 2 ms) sobre la CMDB y los 30 documentos técnicos sin llamadas a la API.")

        with st.form(key="form_duckdb_search", clear_on_submit=False):
            col_d_in, col_d_btn = st.columns([5, 1])
            with col_d_in:
                query_duckdb_in = st.text_input(
                    "Término de búsqueda textual:",
                    value=st.session_state.get("duckdb_active_term", ""),
                    placeholder="Ingrese IP (ej: 10.24.0.125), servidor (BALANCER001), serie (SN-8842-A) o palabra clave...",
                    label_visibility="collapsed"
                )
            with col_d_btn:
                sub_duckdb = st.form_submit_button("Buscar", type="primary", width="stretch")

        st.markdown("<div style='margin-top: -6px; margin-bottom: 8px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.7;'>Búsquedas rápidas:</div>", unsafe_allow_html=True)
        quick_duck_options = [
            ">_ BALANCER001",
            ">_ 10.24.0.125",
            ">_ Autenticacion JWT",
            ">_ Failover Redis",
            ">_ SN-8842-A",
            ">_ PureStorage SAN",
        ]
        if "quick_duck_ver" not in st.session_state:
            st.session_state.quick_duck_ver = 0

        pills_duck_key = f"pills_duck_sel_{st.session_state.quick_duck_ver}"
        sel_duck_pill = st.pills("Búsquedas rápidas", options=quick_duck_options, default=None, label_visibility="collapsed", key=pills_duck_key)

        prompt_duck_pill = None
        if sel_duck_pill:
            prompt_duck_pill = sel_duck_pill.replace(">_ ", "").strip()
            st.session_state.quick_duck_ver += 1

        active_duck_term = prompt_duck_pill if prompt_duck_pill else (
            query_duckdb_in.strip() if sub_duckdb and query_duckdb_in.strip() else st.session_state.get("duckdb_active_term", "")
        )
        st.session_state["duckdb_active_term"] = active_duck_term

        if not active_duck_term:
            st.markdown("""
<div class="empty-state-container">
    <div class="empty-state-console-icon">&gt;_ Buscador :1</div>
    <div class="empty-state-title">Motor de Búsqueda Textual en RAM</div>
    <div class="empty-state-subtitle">
        Búsqueda ultrarrápida indexada directamente sobre la CMDB y los 30 documentos técnicos.
        Obtén servidores coincidentes, IPs, estados Nagios y fragmentos documentales en milisegundos.
    </div>
    <div class="empty-state-caps-grid">
        <div class="empty-cap-card" style="background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.22);">
            <div class="empty-cap-card-label" style="color:#6366F1;">[INFO] DuckDB SQL RAM</div>
            <div class="empty-cap-card-title">Servidores y CMDB</div>
            <div class="empty-cap-card-desc">Búsqueda por IP, hostname, número de serie, componente o VM vCloud.</div>
        </div>
        <div class="empty-cap-card" style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.22);">
            <div class="empty-cap-card-label" style="color:#10B981;">[OK] Índice Documental</div>
            <div class="empty-cap-card-title">Extractos Relevantes</div>
            <div class="empty-cap-card-desc">Localización de términos técnicos en runbooks, procedimientos y notas de contingencia.</div>
        </div>
        <div class="empty-cap-card" style="background:rgba(217,119,6,0.07);border:1px solid rgba(217,119,6,0.22);">
            <div class="empty-cap-card-label" style="color:#D97706;">[DOC] Sin Consumo API</div>
            <div class="empty-cap-card-title">Latencia Cero</div>
            <div class="empty-cap-card-desc">Ejecución 100% local en memoria, sin latencia de red ni dependencias externas.</div>
        </div>
    </div>
</div>
            """, unsafe_allow_html=True)
        else:
            t_d0 = time.perf_counter()
            df_srv_found = buscar_servidores_duckdb(active_duck_term)
            doc_matches_found = buscar_en_documentos(active_duck_term, st.session_state.doc_store)
            t_d_elapsed_ms = (time.perf_counter() - t_d0) * 1000

            st.markdown(f"""
            <div style="background: rgba(99, 102, 241, 0.06); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 6px; padding: 8px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div><b>Término:</b> <code>{active_duck_term}</code></div>
                <div><b>Servidores CMDB:</b> <span class="badge-ok">{len(df_srv_found)}</span></div>
                <div><b>Documentos Coincidentes:</b> <span class="badge-info">{len(doc_matches_found)}</span></div>
                <div><b>Tiempo:</b> <span class="badge-tag">{t_d_elapsed_ms:.2f} ms [RAM]</span></div>
            </div>
            """, unsafe_allow_html=True)

            # 1. Servidores Coincidentes en CMDB
            st.markdown(f"##### Servidores Coincidentes en CMDB ({len(df_srv_found)})")
            if not df_srv_found.empty:
                cols_mostrar = [c for c in ["servidor_id", "ip", "numero_serie", "vcloud_vm", "nivel_arquitectura", "componente", "estado", "nagios_check"] if c in df_srv_found.columns]
                df_tabla = df_srv_found[cols_mostrar].rename(columns={
                    "servidor_id": "Servidor",
                    "ip": "IP",
                    "numero_serie": "N° Serie",
                    "vcloud_vm": "VM vCloud",
                    "nivel_arquitectura": "Capa",
                    "componente": "Componente",
                    "estado": "Estado",
                    "nagios_check": "Nagios / Chequeo"
                })
                st.dataframe(df_tabla, width="stretch", hide_index=True)
            else:
                st.info(f"No se registraron servidores que coincidan con '{active_duck_term}' en la CMDB.")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # 2. Documentos Coincidentes
            st.markdown(f"##### Documentación Técnica Coincidente ({len(doc_matches_found)})")
            if doc_matches_found:
                for doc_name, content, score in doc_matches_found[:5]:
                    snippet = extraer_fragmento_relevante(content, active_duck_term, max_chars=350)
                    snippet_highlight = resaltar_terminos_en_html(html.escape(snippet), active_duck_term)
                    badge_score = f'<span class="badge-info">{score} pts</span>'
                    st.markdown(f"""
<div class="search-result-card" style="margin-bottom: 10px; padding: 12px 14px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
        <div><b>Documento:</b> <code>{doc_name}</code></div>
        <div>{badge_score}</div>
    </div>
    <div style="font-size: 0.83rem; line-height: 1.5; opacity: 0.9; background: rgba(128,128,128,0.05); padding: 8px 10px; border-radius: 4px; border-left: 3px solid #6366F1;">
        {snippet_highlight}
    </div>
</div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"No se encontraron coincidencias en la documentación técnica para '{active_duck_term}'.")

            # 3. Puente Inteligente hacia el Copilot
            st.markdown("---")
            col_br_text, col_br_btn = st.columns([3.5, 1.5], vertical_alignment="center")
            with col_br_text:
                st.caption("¿Deseas una explicación técnica detallada, análisis de incidentes o elaboración de runbook asistido sobre estos resultados?")
            with col_br_btn:
                if st.button(">_ Analizar con Copilot Gemini", width="stretch", type="primary", key="btn_bridge_to_copilot"):
                    with st.spinner("El Copilot Gemini está analizando los resultados..."):
                        resp_copilot = generar_respuesta_asistente(active_duck_term, st.session_state.doc_store)
                        st.session_state.historial_busquedas.insert(0, {
                            "query": active_duck_term,
                            "response": resp_copilot,
                            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                        })
                    st.toast("[OK] Análisis generado con éxito en el Copilot")
                    st.rerun()

    # ---------------- SUBTAB 1.2: COPILOT DE INFRAESTRUCTURA (GEMINI RAG) ----------------
    with subtab_copilot:
        st.markdown("#### Copilot de Infraestructura y Operaciones (Gemini RAG)")
        st.caption("Asistente técnico especializado con inyección contextual RAG (CMDB DuckDB + Base Documental), diagnósticos y análisis de impacto.")

        with st.form(key="top_copilot_form", clear_on_submit=True):
            col_c_inp, col_c_btn = st.columns([5, 1])
            with col_c_inp:
                query_copilot_in = st.text_input(
                    "Pregunta o instrucción técnica para el Copilot:",
                    placeholder="Ej: Explícame el procedimiento de failover de Redis y sus dependencias con los balanceadores...",
                    label_visibility="collapsed"
                )
            with col_c_btn:
                submitted_copilot = st.form_submit_button("Consultar Copilot", type="primary", width="stretch")

        st.markdown("<div style='margin-top: -6px; margin-bottom: 6px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.7;'>Consultas recomendadas:</div>", unsafe_allow_html=True)
        copilot_quick_queries = [
            ">_ Diagnóstico y estado de BALANCER001",
            ">_ Procedimiento de Failover Redis",
            ">_ Arquitectura de Autenticación JWT",
            ">_ Servidores críticos en DMZ",
            ">_ Políticas de parche y antivirus",
            ">_ Topología y dependencias SAP",
        ]
        if "quick_copilot_ver" not in st.session_state:
            st.session_state.quick_copilot_ver = 0

        pills_copilot_key = f"pills_copilot_{st.session_state.quick_copilot_ver}"
        sel_copilot_pill = st.pills("Consultas recomendadas", options=copilot_quick_queries, default=None, label_visibility="collapsed", key=pills_copilot_key)

        prompt_copilot_rapido = None
        if sel_copilot_pill:
            prompt_copilot_rapido = sel_copilot_pill.replace(">_ ", "").strip()
            st.session_state.quick_copilot_ver += 1

        query_copilot_ejecutar = prompt_copilot_rapido if prompt_copilot_rapido else (
            query_copilot_in.strip() if submitted_copilot and query_copilot_in.strip() else None
        )

        if query_copilot_ejecutar:
            with st.spinner("El Copilot está analizando la infraestructura y redactando el informe..."):
                respuesta_c = generar_respuesta_asistente(query_copilot_ejecutar, st.session_state.doc_store)
                st.session_state.historial_busquedas.insert(0, {
                    "query": query_copilot_ejecutar,
                    "response": respuesta_c,
                    "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                })
            st.rerun()

        st.markdown("---")

        if not st.session_state.historial_busquedas:
            st.markdown("""
<div class="empty-state-container">
    <div class="empty-state-console-icon">&gt;_ copilot::rag_engine</div>
    <div class="empty-state-title">Copilot de Infraestructura y Operaciones</div>
    <div class="empty-state-subtitle">
        Realiza preguntas analíticas y operativas complejas. El motor RAG recopilará registros técnicos
        de DuckDB y la base documental para generar respuestas estructuradas sin alucinaciones.
    </div>
    <div class="empty-state-caps-grid">
        <div class="empty-cap-card" style="background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.22);">
            <div class="empty-cap-card-label" style="color:#6366F1;">[INFO] Gemini RAG</div>
            <div class="empty-cap-card-title">Análisis de Arquitectura</div>
            <div class="empty-cap-card-desc">Explicación estructurada de flujos de autenticación, alta disponibilidad y topologías.</div>
        </div>
        <div class="empty-cap-card" style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.22);">
            <div class="empty-cap-card-label" style="color:#10B981;">[OK] Zero Hallucinations</div>
            <div class="empty-cap-card-title">Fundamentación Estricta</div>
            <div class="empty-cap-card-desc">Respuestas basadas exclusivamente en los registros de la CMDB y los manuales corporativos.</div>
        </div>
        <div class="empty-cap-card" style="background:rgba(217,119,6,0.07);border:1px solid rgba(217,119,6,0.22);">
            <div class="empty-cap-card-label" style="color:#D97706;">[DOC] Query Cache</div>
            <div class="empty-cap-card-title">Respuestas Instantáneas</div>
            <div class="empty-cap-card-desc">Las consultas ya resueltas se entregan en 0.79 ms desde la memoria RAM.</div>
        </div>
    </div>
</div>
            """, unsafe_allow_html=True)
        else:
            col_res_t, col_res_btn = st.columns([4, 1])
            with col_res_t:
                st.markdown(
                    f"<div style='font-size: 0.95rem; font-weight: 600;'>Historial de Consultas ({len(st.session_state.historial_busquedas)}):</div>", unsafe_allow_html=True)
            with col_res_btn:
                if st.button(">_ Limpiar Chat", width="stretch", key="btn_clear_search_history_copilot"):
                    st.session_state.historial_busquedas = []
                    st.session_state.messages = []
                    st.toast("[INFO] Historial de consultas reiniciado")
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
        st.dataframe(df_filtrado, width="stretch", hide_index=True)

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
                st.dataframe(df_custom, width="stretch")


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
                    format_func=normalizar_titulo_display,
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
            titulo_display = normalizar_titulo_display(doc_seleccionado)

            st.markdown(f"""
<div style="background-color: rgba(128, 128, 128, 0.08); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 6px; padding: 8px 14px; margin-bottom: 12px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
    <div><b>Documento:</b> <span style="color:#6366F1; font-weight: 600;">{titulo_display}</span> <span style="font-family: monospace; opacity: 0.65; font-size: 0.8rem;">({doc_seleccionado})</span></div>
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
                            width="stretch",
                            key=f"dl_active_excel_{doc_seleccionado}"
                        )
                    else:
                        st.download_button(
                            label=f"Descargar Versión Activa v{ultima_version} (.md)",
                            data=doc_content.encode("utf-8"),
                            file_name=sanitizar_nombre_descarga(
                                doc_seleccionado, ultima_version, ".md"),
                            mime="text/markdown",
                            width="stretch",
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
                        df_to_edit, width="stretch", num_rows="dynamic", height=480, key=f"grid_editor_{doc_seleccionado}_{hoja_editar}")

                    col_btn_save, col_btn_info = st.columns([2, 3])
                    with col_btn_save:
                        if st.button(f"Guardar y Publicar Versión v{ultima_version + 1}", type="primary", width="stretch", key=f"btn_save_grid_{doc_seleccionado}"):
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

                    val_textarea = doc_content[:100_000] if len(doc_content) > 100_000 else doc_content
                    if len(doc_content) > 100_000:
                        st.info(f"[INFO] Documento extenso ({len(doc_content)/1024:.1f} KB). Mostrando primeros 100 KB para edicion segura.")
                    texto_editado = st.text_area(
                        "Contenido del Documento (Markdown)", value=val_textarea, height=450, key=f"textarea_edit_{doc_seleccionado}")

                    col_btn_save, col_btn_info = st.columns([2, 3])
                    with col_btn_save:
                        if st.button(f"Guardar y Publicar Versión v{ultima_version + 1}", type="primary", width="stretch", key=f"btn_save_{doc_seleccionado}"):
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
                st.dataframe(df_hist, width="stretch", hide_index=True)

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
                                width="stretch",
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
                            width="stretch",
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
                            width="stretch",
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
                        st.dataframe(df_aud_display, width="stretch", hide_index=True)
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
                if st.button("[+ Activar]", key="btn_activar_plantilla_base", width="stretch"):
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
        if st.button("Guardar y Publicar en Base de Conocimiento", type="primary", width="stretch", key="btn_guardar_doc_plantilla_final"):
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


# ----------------- TAB 5: INTEGRACIÓN SAP (API) -----------------
with tab_sap:
    # 1. Cabecera Obsidian & Indigo
    st.markdown("""
<div class="search-result-card" style="margin-bottom: 18px; border-left: 4px solid #6366F1;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
        <div style="display:flex; align-items:center; gap:8px;">
            <span class="badge-info">[SAP LANDSCAPE]</span>
            <span class="badge-ok">[API REST / ODATA]</span>
            <span class="badge-tag">[CONSOLA DE OPERACIONES]</span>
        </div>
        <div>
            <span class="badge-pulse-online"><span class="pulse-dot"></span>CONECTOR OPERATIVO</span>
        </div>
    </div>
    <div class="main-title" style="font-size:1.35rem; margin-bottom:4px;">Telemetría y Gestión de Infraestructura SAP</div>
    <div class="sub-title" style="margin-bottom:0; font-size:0.88rem;">
        Integración y monitoreo del landscape SAP S/4HANA 2022, bases de datos SAP HANA 2.0 (HSR), instancias NetWeaver (ASCS/PAS/AAS) y Landscape Management Database (LMDB).
    </div>
</div>
""", unsafe_allow_html=True)

    # 2. Panel de Conectividad y Endpoints
    with st.container(border=True):
        st.markdown("#### Configuración del Endpoint y Conectividad")
        col_url, col_auth, col_cred = st.columns([2.2, 1.8, 1.5], gap="small")
        with col_url:
            val_endpoint_vault = obtener_secreto("SAP_ENDPOINT", "")
            sap_endpoint = st.text_input(
                "Endpoint API Gateway SAP / ALM",
                value=val_endpoint_vault,
                placeholder="",
                help="URL base del servicio de telemetría de SAP Cloud ALM, Focused Run o SAP Host Agent."
            )
        with col_auth:
            sap_auth_method = st.selectbox(
                "Método de Autenticación",
                options=[
                    "OAuth 2.0 (Client Credentials / mTLS)",
                    "SAP Host Agent HTTPS (:1129)",
                    "SAP Solution Manager / FRUN (OData)"
                ],
                index=0
            )
        with col_cred:
            val_client_id_vault = obtener_secreto("SAP_CLIENT_ID", "")
            sap_client_id = st.text_input(
                "Client ID / Identificador de Servicio",
                value=val_client_id_vault,
                placeholder="",
                type="password",
                help="Identificador de cliente o certificado para la autenticación en el Gateway SAP."
            )

        col_b_conn, col_b_sync, col_b_payload = st.columns([1.2, 1.2, 1.0], gap="small")
        with col_b_conn:
            btn_test_sap = st.button(">_ Probar Conexión API", width="stretch", type="primary")
        with col_b_sync:
            btn_sync_sap = st.button(">_ Sincronizar CMDB Local", width="stretch", help="Ingesta los servidores del landscape SAP en mantenimientos.csv y genera registro de auditoría inmutable.")
        with col_b_payload:
            payload_data = generar_payload_json_sap(sap_endpoint)
            payload_str = json.dumps(payload_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="Descargar Payload JSON",
                data=payload_str,
                file_name="sap_landscape_payload.json",
                mime="application/json",
                width="stretch"
            )

        # Acciones de prueba de conexion
        if btn_test_sap:
            if not sap_endpoint.strip():
                st.warning("[WARN] Ingrese el endpoint de la API de SAP antes de ejecutar la prueba de conexión.")
            else:
                res_conn = probar_conexion_api_sap(sap_endpoint, sap_auth_method, sap_client_id)
                st.session_state.sap_conn_result = res_conn

        if "sap_conn_result" in st.session_state:
            res_c = st.session_state.sap_conn_result
            st.markdown(f"""
<div style="background-color: rgba(16, 185, 129, 0.08); border: 1px solid #10B981; border-radius: 6px; padding: 10px 14px; margin-top: 12px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
    <div>
        <span class="badge-ok">[200 OK]</span>
        <b style="margin-left: 6px;">Conexión Verificada:</b> {res_c['endpoint']}
    </div>
    <div>
        <span class="badge-tag">Latencia: {res_c['latencia_ms']} ms</span>
        <span class="badge-info" style="margin-left: 4px;">{res_c['protocolo']}</span>
        <span class="badge-tag" style="margin-left: 4px;">{res_c['timestamp']}</span>
    </div>
</div>
""", unsafe_allow_html=True)

        # Accion de sincronizacion con CMDB
        if btn_sync_sap:
            ok, cant, msg = sincronizar_servidores_sap_cmdb(autor="Conector API SAP")
            if ok:
                st.toast(f"[OK] {msg}")
                st.success(f"[OK] {msg} Los servidores se encuentran disponibles para consultas DuckDB y el Chat.")
            else:
                st.toast(f"[WARN] {msg}")
                st.warning(f"[WARN] {msg}")

    # 3. Métricas de Telemetría (KPIs)
    df_sap_hosts = obtener_inventario_sap_df()
    total_sap_hosts = len(df_sap_hosts)
    sids_unicos = df_sap_hosts["sid"].unique()

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.markdown(f"""
<div class="search-result-card" style="padding: 12px 14px; text-align: center;">
    <div style="font-size: 0.75rem; opacity: 0.7; font-weight: 500;">SISTEMAS SAP (SIDs)</div>
    <div style="font-size: 1.4rem; font-weight: 700; color: #6366F1; margin: 4px 0;">{len(sids_unicos)} SIDs</div>
    <div style="font-size: 0.72rem; opacity: 0.8;">PRD, HDB, SM1</div>
</div>
""", unsafe_allow_html=True)

    with col_kpi2:
        st.markdown(f"""
<div class="search-result-card" style="padding: 12px 14px; text-align: center;">
    <div style="font-size: 0.75rem; opacity: 0.7; font-weight: 500;">INSTANCIAS / NODOS</div>
    <div style="font-size: 1.4rem; font-weight: 700; color: #10B981; margin: 4px 0;">{total_sap_hosts} Hosts</div>
    <div style="font-size: 0.72rem; opacity: 0.8;">HANA, NetWeaver, WDisp</div>
</div>
""", unsafe_allow_html=True)

    with col_kpi3:
        st.markdown(f"""
<div class="search-result-card" style="padding: 12px 14px; text-align: center;">
    <div style="font-size: 0.75rem; opacity: 0.7; font-weight: 500;">REPLICACIÓN HANA HSR</div>
    <div style="font-size: 1.4rem; font-weight: 700; color: #10B981; margin: 4px 0;">IN-SYNC</div>
    <div style="font-size: 0.72rem; opacity: 0.8;">Latencia réplica: 1.4 ms</div>
</div>
""", unsafe_allow_html=True)

    with col_kpi4:
        st.markdown(f"""
<div class="search-result-card" style="padding: 12px 14px; text-align: center;">
    <div style="font-size: 0.75rem; opacity: 0.7; font-weight: 500;">ALERTAS ACTIVAS</div>
    <div style="font-size: 1.4rem; font-weight: 700; color: #D97706; margin: 4px 0;">1 Alerta</div>
    <div style="font-size: 0.72rem; opacity: 0.8;">Memoria SolMan (89.2%)</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. Pestañas Internas del Módulo SAP
    tab_sap_inv, tab_sap_topo, tab_sap_json, tab_sap_alerts = st.tabs([
        f"Inventario de Servidores ({total_sap_hosts})",
        "Topología del Landscape SAP",
        "Payload API (JSON)",
        "Alertas y Eventos (2)"
    ])

    # Sub-tab 1: Inventario
    with tab_sap_inv:
        col_f_sid, col_f_search = st.columns([1.5, 3.5])
        with col_f_sid:
            opciones_sid = ["Todos"] + list(sids_unicos)
            filtro_sid = st.pills("Filtrar por SID:", options=opciones_sid, default="Todos", key="pills_filtro_sid_sap")
            if not filtro_sid:
                filtro_sid = "Todos"
        with col_f_search:
            filtro_txt_sap = st.text_input("Buscar por host, IP o componente:", value="", placeholder="", key="txt_search_sap_inv")

        df_mostrar = df_sap_hosts.copy()
        if filtro_sid != "Todos":
            df_mostrar = df_mostrar[df_mostrar["sid"] == filtro_sid]
        if filtro_txt_sap:
            t = filtro_txt_sap.lower()
            df_mostrar = df_mostrar[
                df_mostrar["servidor_id"].str.lower().str.contains(t) |
                df_mostrar["ip"].str.lower().str.contains(t) |
                df_mostrar["componente"].str.lower().str.contains(t) |
                df_mostrar["instancia"].str.lower().str.contains(t)
            ]

        cols_display = [
            "servidor_id", "sid", "instancia", "ip", "nivel_arquitectura",
            "componente", "cpu_pct", "mem_pct", "disco_pct", "estado", "nagios_check"
        ]
        cols_finales = [c for c in cols_display if c in df_mostrar.columns]

        st.dataframe(
            df_mostrar[cols_finales].rename(columns={
                "servidor_id": "Servidor",
                "sid": "SID",
                "instancia": "Instancia",
                "ip": "IP",
                "nivel_arquitectura": "Capa",
                "componente": "Servicio / Componente",
                "cpu_pct": "CPU %",
                "mem_pct": "Mem %",
                "disco_pct": "Disco %",
                "estado": "Estado",
                "nagios_check": "Chequeo Host Agent"
            }),
            width="stretch",
            hide_index=True
        )

        with st.expander("Ver Ficha Técnica Detallada por Servidor SAP", expanded=False):
            host_sel = st.selectbox("Seleccione Servidor para Inspeccionar:", df_sap_hosts["servidor_id"].tolist())
            if host_sel:
                det = df_sap_hosts[df_sap_hosts["servidor_id"] == host_sel].iloc[0]
                c_d1, c_d2, c_d3 = st.columns(3)
                with c_d1:
                    st.markdown(f"**Identificador:** `{det['servidor_id']}`")
                    st.markdown(f"**Número de Serie:** `{det['numero_serie']}`")
                    st.markdown(f"**Dirección IP:** `{det['ip']}`")
                with c_d2:
                    st.markdown(f"**Sistema (SID):** `{det['sid']}`")
                    st.markdown(f"**Instancia:** `{det['instancia']}`")
                    st.markdown(f"**Nivel de Arquitectura:** `{det['nivel_arquitectura']}`")
                with c_d3:
                    st.markdown(f"**Sistema Operativo:** {det['os']}")
                    st.markdown(f"**Versión Kernel:** `{det['kernel']}`")
                    st.markdown(f"**SAP Host Agent:** `{det['sap_host_agent']}`")

    # Sub-tab 2: Topología
    with tab_sap_topo:
        st.markdown("""
<div style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 12px;">
    Diagrama de dependencias arquitectónicas entre la capa de balanceo (Web Dispatcher), capa de aplicación SAP S/4HANA (ASCS, PAS, AAS), capa de base de datos SAP HANA DB en replicación sincrónica/asincrónica HSR, y gestión con SAP Solution Manager.
</div>
""", unsafe_allow_html=True)
        topo_sap_mermaid = generar_topologia_sap_mermaid()
        with st.container(border=True):
            st.markdown(f"```mermaid\n{topo_sap_mermaid}\n```")

    # Sub-tab 3: Payload API (JSON)
    with tab_sap_json:
        st.markdown("""
<div style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 10px;">
    Respuesta completa provista por la API REST de telemetría e inventario de SAP (esquema compatible con SAP Cloud ALM / SAP Host Agent):
</div>
""", unsafe_allow_html=True)
        st.json(payload_data)

    # Sub-tab 4: Alertas
    with tab_sap_alerts:
        alertas_sap_list = obtener_alertas_sap()
        for al in alertas_sap_list:
            tag_sev = '<span class="badge-warn">[ADVERTENCIA]</span>' if al["severidad"] == "Advertencia" else '<span class="badge-info">[INFO]</span>'
            st.markdown(f"""
<div class="search-result-card" style="margin-bottom: 10px; border-left: 3px solid {'#D97706' if al['severidad'] == 'Advertencia' else '#6366F1'};">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
        <div>
            {tag_sev}
            <b style="margin-left: 6px;">{al['id_alerta']}</b> - SID: <code>{al['sid']}</code> | Host: <code>{al['servidor_id']}</code>
        </div>
        <span class="badge-tag">{al['timestamp']}</span>
    </div>
    <div style="font-size: 0.88rem; margin-bottom: 4px;"><b>Tipo:</b> {al['tipo']} - {al['mensaje']}</div>
    <div style="font-size: 0.8rem; opacity: 0.8;"><b>Acción Recomendada:</b> {al['accion_recomendada']}</div>
</div>
""", unsafe_allow_html=True)


import os
import re
import shutil
import importlib
import duckdb
import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

import core.configuracion
import core.estilos
import core.auditoria
import core.motor
import core.procesador
import core.topologia
import core.plantillas
import core.visor

importlib.reload(core.configuracion)
importlib.reload(core.estilos)
importlib.reload(core.auditoria)
importlib.reload(core.motor)
importlib.reload(core.procesador)
importlib.reload(core.topologia)
importlib.reload(core.plantillas)
importlib.reload(core.visor)

from excel_cleaner import procesar_excel_limpio
from core.configuracion import (
    CSV_PATH,
    DOCS_DIR,
    ASSETS_DIR,
    ORIGINALS_DIR,
    HISTORY_DIR,
)
from core.estilos import cargar_estilos_css
from core.auditoria import (
    obtener_historial_versiones,
    inicializar_version_inicial_si_no_existe,
    guardar_nueva_version,
    guardar_nueva_version_excel,
    obtener_contenido_version,
    obtener_bytes_snapshot,
    cargar_hoja_excel_dataframe,
    generar_diff_texto,
)
from core.motor import (
    ejecutar_consulta_sql,
    generar_respuesta_asistente,
)
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
from core.topologia import TOPOLOGY_MERMAID, PLANTILLAS_DIAGRAMAS, INFRA_SPECS
from core.plantillas import (
    generar_doc_plantilla,
    obtener_todos_los_tipos_plantillas,
    guardar_plantilla_personalizada,
    cargar_plantillas_personalizadas,
)
from core.visor import (
    renderizar_lado_a_lado,
    renderizar_original_adaptativo,
    mostrar_pdf_embebido,
)


# 1. Configuracion de Streamlit
st.set_page_config(
    page_title="Consultadora de documentos IG",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(cargar_estilos_css(), unsafe_allow_html=True)

# 2. Inicializacion de Estado y Documentos
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "**Sistema de Búsqueda de documentación por palabras clave y activos de arquitectura.**\n\n"
                "Capacidades activas:\n"
                "- Consulta analítica de inventario y mantenimientos por número de serie, IP, servidor o técnico.\n"
                "- Recuperación de procedimientos técnicos, manuales y contingencias (MarkItDown Engine).\n"
                "- Búsqueda e inspección de topologías, diagramas visuales y comparación Lado a Lado (Side-by-Side).\n"
            )
        }
    ]

if "doc_store" not in st.session_state:
    st.session_state.doc_store = {}

cargar_documentos_locales(st.session_state.doc_store)


# 3. Sidebar (Panel de Control e Ingesta)
with st.sidebar:
    st.markdown("### Acceso Rápido")
    st.caption("Panel de Ingesta y Control Documental")
    st.markdown("---")

    # Ingesta de Archivos
    st.markdown("#### Subir Archivo/s")
    uploaded_files = st.file_uploader(
        "Arrastra o selecciona tus archivos:",
        type=["pdf", "docx", "xlsx", "xls", "csv", "txt",
              "md", "pptx", "png", "jpg", "jpeg", "svg", "webp"],
        accept_multiple_files=True,
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
                        st.info(
                            f"[OMITIDO] El diagrama '{clean_name}' ya está registrado con el mismo contenido.")
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
                        st.success(
                            f"[NUEVA VERSION] Diagrama '{clean_name}' actualizado como [Version v{nueva_v}].")
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
                    st.success(
                        f"[Diagrama] {clean_name} (Indexado como Version v1)")

            # Caso 2: Documentos Ofimáticos, Excel, PDF, Texto y Markdown
            else:
                save_path = os.path.join(DOCS_DIR, clean_name)
                if os.path.exists(save_path):
                    with open(save_path, "rb") as f:
                        existente_bytes = f.read()
                    existente_hash = calcular_sha256(existente_bytes)

                    if nuevo_hash == existente_hash:
                        st.info(
                            f"[OMITIDO] El archivo '{clean_name}' ya se encuentra indexado con el mismo contenido exacto.")
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
                        st.success(
                            f"[NUEVA VERSION] Se actualizó '{clean_name}' registrando la versión [Version v{nueva_v}].")
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
                    tag = "[Excel]" if ext_uf in (
                        '.xlsx', '.xls') else "[PDF]" if ext_uf == '.pdf' else "[Documento]"
                    st.success(
                        f"{tag} {clean_name} (Indexado como Version v1)")

    st.markdown("---")

    # Resumen y Filtro de Base Documental
    cant_docs = len(st.session_state.doc_store)
    st.markdown(f"#### Documentos cargados -> ({cant_docs})")

    if cant_docs > 0:
        conteo_img = sum(1 for d in st.session_state.doc_store if d.startswith(
            "DIAGRAMA__") or any(d.lower().endswith(ext) for ext in IMAGE_EXTENSIONS))
        conteo_excel = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[
                           1].lower() in ('.xlsx', '.xls'))
        conteo_doc = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[
                         1].lower() in ('.docx', '.pdf', '.pptx', '.doc'))
        conteo_txt = sum(1 for d in st.session_state.doc_store if os.path.splitext(
            d)[1].lower() in ('.md', '.txt', '.csv') and not d.startswith("DIAGRAMA__"))

        with st.expander("Ver documentos cargados", expanded=False):
            st.markdown("<div style='margin-bottom: 6px; font-size: 0.8rem; font-weight: 600;'>Filtrar por tipo:</div>", unsafe_allow_html=True)
            tipo_filtro = sac.chip(
                items=[
                    sac.ChipItem(label=f"Todos ({cant_docs})"),
                    sac.ChipItem(label=f"Diagramas ({conteo_img})"),
                    sac.ChipItem(label=f"Excel ({conteo_excel})"),
                    sac.ChipItem(label=f"Documentos ({conteo_doc})"),
                    sac.ChipItem(label=f"Markdown ({conteo_txt})"),
                ],
                size="xs",
                radius="sm",
                align="start",
                key="sb_type_chip_filter"
            )
            if not tipo_filtro:
                tipo_filtro = f"Todos ({cant_docs})"

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
                for d in docs_filtrados:
                    ext = os.path.splitext(d)[1].lower()
                    if d.startswith("DIAGRAMA__") or ext in IMAGE_EXTENSIONS:
                        tag = "[Diagrama]"
                    elif ext in ('.xlsx', '.xls'):
                        tag = "[Excel]"
                    elif ext in ('.pdf', '.docx', '.pptx', '.doc'):
                        tag = "[Doc]"
                    else:
                        tag = "[Txt]"
                    size_kb = len(st.session_state.doc_store[d]) / 1024
                    st.markdown(f"`{tag}` **{d}** *({size_kb:.1f} KB)*")
            else:
                st.caption("No hay documentos que coincidan con el filtro.")
    else:
        st.info("No hay documentos indexados aún.")

    st.markdown("---")

    # Acciones Rapidas
    st.markdown("#### Acciones Rápidas")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Reindexar", help="Recarga todos los documentos desde data/docs/ y data/docs/assets/", use_container_width=True):
            cargar_documentos_locales(st.session_state.doc_store, force=True)
            st.toast("Base documental y assets reindexados con éxito")
            st.rerun()
    with col_btn2:
        if st.button("Limpiar Chat", help="Reinicia la conversación actual", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "**Sistema de Búsqueda de documentación por palabras clave y activos de arquitectura.**\n\n"
                        "Capacidades activas:\n"
                        "- Consulta analítica de inventario y mantenimientos por número de serie, IP, servidor o técnico.\n"
                        "- Recuperación de procedimientos técnicos, manuales y contingencias (MarkItDown Engine).\n"
                        "- Búsqueda e inspección de topologías, diagramas visuales y comparación Lado a Lado (Side-by-Side).\n"
                    )
                }
            ]
            st.toast("Historial de chat reiniciado")
            st.rerun()

    st.markdown("---")

    # Estado del Sistema
    st.markdown("#### Estado del Sistema")
    st.markdown(f"""
<div style="background-color: rgba(128, 128, 128, 0.08); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 10px; font-size: 0.8rem;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
        <span><b>DuckDB SQL:</b></span> <span class="badge-ok">Conectado</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
        <span><b>MarkItDown Engine:</b></span> <span class="badge-ok">Activo</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
        <span><b>Visor Side-by-Side:</b></span> <span class="badge-ok">Habilitado</span>
    </div>
    <div style="display: flex; justify-content: space-between;">
        <span><b>Docs Indexados:</b></span> <b>{cant_docs} archivos</b>
    </div>
</div>
""", unsafe_allow_html=True)


# 4. Encabezado Principal
col_title, col_stat_docs, col_stat_csv = st.columns([2.6, 1.2, 1.2])
with col_title:
    st.markdown('<p class="main-title">Copilot de Infraestructura y Operaciones</p>',
                unsafe_allow_html=True)

with col_stat_docs:
    cant_docs = len(st.session_state.doc_store)
    st.metric("Documentos Indexados", f"{cant_docs} Archivos")

with col_stat_csv:
    total_srvs = 0
    if os.path.exists(CSV_PATH):
        try:
            df_tot = pd.read_csv(CSV_PATH)
            total_srvs = len(df_tot)
        except Exception:
            pass
    st.metric("Inventario / CMDB", f"{total_srvs} Registros")


# 5. Pestañas Principales
tab_chat, tab_analytics, tab_docs, tab_templates = st.tabs([
    "Consultar dudas (Buscar por palabras)",
    "Historial de Mantenimientos",
    "Documentacion Tecnica",
    "Plantillas de documentación"
])

# ----------------- TAB 1: CHAT -----------------
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ingrese su consulta tecnica..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Procesando consulta..."):
                respuesta = generar_respuesta_asistente(
                    prompt, st.session_state.doc_store)
                st.markdown(respuesta)
                st.session_state.messages.append(
                    {"role": "assistant", "content": respuesta})

# ----------------- TAB 2: ANALITICA DUCKDB -----------------
with tab_analytics:
    st.subheader("Motor SQL DuckDB - Historial de Mantenimientos e Inventario")
    st.caption(
        "Consultas analíticas estructuradas con filtrado de alto rendimiento.")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_nivel = st.selectbox("Nivel de Arquitectura", [
                                    "Todos", "L1 - Hardware", "L2 - Virtualización", "L3 - Middleware", "L4 - Aplicación"])
    with col_f2:
        filtro_estado = st.selectbox(
            "Estado Operativo", ["Todos", "Operativo", "En Revision", "Critico"])
    with col_f3:
        filtro_tec = st.text_input("Filtrar por Tecnico")

    condiciones = ["1=1"]
    if filtro_nivel != "Todos":
        condiciones.append(f"nivel_arquitectura = '{filtro_nivel}'")
    if filtro_estado != "Todos":
        condiciones.append(f"estado = '{filtro_estado}'")
    if filtro_tec.strip():
        condiciones.append(
            f"LOWER(tecnico) LIKE LOWER('%{filtro_tec.strip()}%')")

    sql_query = f"SELECT * FROM read_csv_auto('{CSV_PATH}') WHERE {' AND '.join(condiciones)} ORDER BY fecha DESC"
    df_filtrado = duckdb.sql(sql_query).df()
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    with st.expander("Ejecutar Consulta SQL Personalizada"):
        custom_sql = st.text_area(
            "Sentencia SQL",
            value=f"SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM read_csv_auto('{CSV_PATH}') GROUP BY nivel_arquitectura"
        )
        if st.button("Ejecutar"):
            df_custom = ejecutar_consulta_sql(custom_sql)
            st.dataframe(df_custom, use_container_width=True)

# ----------------- TAB 3: DOCUMENTACION TECNICA Y VERSIONADO -----------------
with tab_docs:
    st.subheader(
        "Repositorio de Documentacion Tecnica, Diagramas y Versionado")
    st.caption(
        "Manuales de contingencia, procedimientos operativos, visor Lado a Lado (Side-by-Side) y control de cambios.")

    if st.session_state.doc_store:
        col_tipo_t4, col_doc_sel, col_info = st.columns([1.3, 2.4, 1.3])
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
            docs_disponibles_t4.append(d)

        with col_doc_sel:
            if docs_disponibles_t4:
                doc_seleccionado = st.selectbox(
                    "Seleccione Documento", docs_disponibles_t4, key="tab4_doc_selector")
            else:
                doc_seleccionado = None
                st.warning("No hay documentos para el filtro seleccionado.")

        if doc_seleccionado:
            doc_content = st.session_state.doc_store.get(doc_seleccionado, "")
            historial = inicializar_version_inicial_si_no_existe(
                doc_seleccionado, doc_content)
            ultima_version = len(historial)
            ultimo_editor = historial[-1]["autor"] if historial else "Desconocido"
            ultimo_timestamp = historial[-1]["timestamp"] if historial else "N/A"
            ruta_original = obtener_ruta_original(
                doc_seleccionado, doc_content)

            st.markdown(f"""
<div style="background-color: rgba(128, 128, 128, 0.08); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 6px; padding: 6px 12px; margin-bottom: 10px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center;">
    <div><b>Documento:</b> <span style="color:#38BDF8; font-family: monospace;">{doc_seleccionado}</span></div>
    <div><b>Versión Activa:</b> <span class="badge-ok">v{ultima_version}</span></div>
    <div><b>Autor:</b> <span style="color:#34D399;">{ultimo_editor}</span></div>
    <div><b>Última actualización:</b> <span style="opacity: 0.7;">{ultimo_timestamp}</span></div>
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
                    try:
                        xls = pd.ExcelFile(excel_orig_path)
                        sheet_names_edit = xls.sheet_names
                    except Exception:
                        sheet_names_edit = []

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
                        excel_orig_path, hoja_editar)
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
                                st.toast(
                                    f"Versión v{nueva_v} guardada y reindexada exitosamente")
                                st.success(
                                    f"¡Versión [Version v{nueva_v}] creada con éxito! Responsable: {autor_edit.strip()}. El Copilot y el RAG han sido actualizados en memoria.")
                                st.rerun()
                    with col_btn_info:
                        st.caption(
                            "*Al guardar, la versión actual pasará al historial inmutable y el asistente Copilot responderá con la información actualizada inmediatamente.*")

            # SUBTAB 3: HISTORIAL
            with subtab_hist:
                st.markdown("#### Registro Histórico y Trazabilidad")
                st.caption(
                    "Historial inmutable de todas las revisiones aplicadas sobre este documento.")

                df_hist = pd.DataFrame(historial)[
                    ["version", "timestamp", "autor", "comentario", "caracteres"]]
                df_hist.columns = ["Versión", "Fecha y Hora",
                                   "Editor / Responsable", "Motivo del Cambio", "Tamaño (caracteres)"]
                st.dataframe(df_hist, use_container_width=True,
                             hide_index=True)

                st.markdown("---")
                st.markdown("##### Comparador Visual de Cambios (Diff)")
                st.caption(
                    "Compare las diferencias exactas de contenido entre dos versiones de este documento.")

                if len(historial) >= 2:
                    col_cmp1, col_cmp2 = st.columns(2)
                    nombres_versiones = [
                        f"v{item['version']} - {item['timestamp']} ({item['autor']})" for item in historial]
                    mapa_versiones = {
                        f"v{item['version']} - {item['timestamp']} ({item['autor']})": item for item in historial}

                    with col_cmp1:
                        ver_base_sel = st.selectbox(
                            "Versión Base (Anterior):", nombres_versiones, index=0, key=f"diff_base_{doc_seleccionado}")
                    with col_cmp2:
                        ver_comp_sel = st.selectbox("Versión a Comparar (Nueva):", nombres_versiones, index=len(
                            nombres_versiones) - 1, key=f"diff_comp_{doc_seleccionado}")

                    item_base = mapa_versiones[ver_base_sel]
                    item_comp = mapa_versiones[ver_comp_sel]

                    texto_base = obtener_contenido_version(
                        doc_seleccionado, item_base["archivo_snapshot"])
                    texto_comp = obtener_contenido_version(
                        doc_seleccionado, item_comp["archivo_snapshot"])

                    diff_resultado = generar_diff_texto(
                        texto_ant=texto_base,
                        texto_nuevo=texto_comp,
                        label_ant=f"v{item_base['version']} ({item_base['autor']})",
                        label_nuevo=f"v{item_comp['version']} ({item_comp['autor']})"
                    )

                    with st.expander(f"Ver Diferencias (Diff): v{item_base['version']} vs v{item_comp['version']}", expanded=True):
                        st.code(diff_resultado, language="diff")
                else:
                    st.caption(
                        "Se requieren al menos 2 versiones para comparar diferencias.")

                st.markdown("---")
                st.markdown("##### Inspeccionar y Descargar Versión Histórica")
                st.caption(
                    "Seleccione cualquier versión previa para descargar su archivo snapshot o previsualizar su contenido.")

                opciones_versiones = {
                    f"v{item['version']} - {item['timestamp']} ({item['autor']}): {item['comentario']}": item
                    for item in reversed(historial)
                }

                v_sel_label = st.selectbox("Seleccione una versión histórica:", list(
                    opciones_versiones.keys()), key=f"select_hist_ver_{doc_seleccionado}")
                item_seleccionado = opciones_versiones[v_sel_label]
                contenido_snapshot = obtener_contenido_version(
                    doc_seleccionado, item_seleccionado["archivo_snapshot"])

                # Botones de Descarga por Version
                excel_snap = item_seleccionado.get("archivo_excel_snapshot")
                col_dl_v1, col_dl_v2 = st.columns([1, 1])

                with col_dl_v1:
                    if excel_snap:
                        excel_snap_bytes = obtener_bytes_snapshot(
                            doc_seleccionado, excel_snap)
                        if excel_snap_bytes:
                            st.download_button(
                                label=f"Descargar Versión v{item_seleccionado['version']} (.xlsx)",
                                data=excel_snap_bytes,
                                file_name=sanitizar_nombre_descarga(
                                    doc_seleccionado, item_seleccionado['version'], ".xlsx"),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key=f"btn_dl_excel_hist_{doc_seleccionado}_{item_seleccionado['version']}"
                            )
                        else:
                            st.info(
                                "Archivo snapshot Excel no disponible en disco.")
                    else:
                        st.download_button(
                            label=f"Descargar Versión v{item_seleccionado['version']} (.md)",
                            data=contenido_snapshot.encode("utf-8"),
                            file_name=sanitizar_nombre_descarga(
                                doc_seleccionado, item_seleccionado['version'], ".md"),
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
                                doc_seleccionado, item_seleccionado['version'], ".md"),
                            mime="text/markdown",
                            use_container_width=True,
                            key=f"btn_dl_md_rep_{doc_seleccionado}_{item_seleccionado['version']}"
                        )
                    else:
                        st.caption(
                            f"Snapshot inmutable generado el **{item_seleccionado['timestamp']}** por **{item_seleccionado['autor']}**.")

                with st.expander(f"Previsualizar contenido de la Versión v{item_seleccionado['version']}", expanded=False):
                    st.markdown(contenido_snapshot)

                if item_seleccionado["version"] != ultima_version:
                    st.markdown(
                        f"##### Revertir Documento a la Versión v{item_seleccionado['version']} (Rollback)")
                    st.caption(
                        "Para garantizar la trazabilidad corporativa, debe especificar el Editor y la justificación técnica del Rollback.")

                    col_rb_a, col_rb_m = st.columns([1, 2])
                    with col_rb_a:
                        autor_rb = st.text_input("Editor / Técnico que ejecuta el Rollback (*)", placeholder="Ej: Juan Pérez / SysAdmin",
                                                 key=f"author_rb_{doc_seleccionado}_{item_seleccionado['version']}")
                    with col_rb_m:
                        motivo_rb = st.text_input("Motivo o Justificación del Rollback (*)",
                                                  placeholder=f"Ej: Reversión por inconsistencia en v{ultima_version}", key=f"motive_rb_{doc_seleccionado}_{item_seleccionado['version']}")

                    if st.button(f"Confirmar y Ejecutar Rollback a la Versión v{item_seleccionado['version']}", type="primary", key=f"btn_confirm_rollback_{doc_seleccionado}_{item_seleccionado['version']}"):
                        if not autor_rb or not autor_rb.strip():
                            st.error(
                                "Error de Auditoría: Debe ingresar el Editor / Técnico responsable de ejecutar el Rollback.")
                        elif not motivo_rb or not motivo_rb.strip():
                            st.error(
                                "Error de Auditoría: Debe ingresar la justificación técnica del Rollback.")
                        else:
                            excel_snap = item_seleccionado.get(
                                "archivo_excel_snapshot")
                            snap_full_path = os.path.join(
                                HISTORY_DIR, doc_seleccionado, excel_snap) if excel_snap else ""
                            if excel_snap and os.path.exists(snap_full_path):
                                shutil.copy2(snap_full_path, os.path.join(
                                    DOCS_DIR, doc_seleccionado))
                                nuevo_md = procesar_excel_limpio(
                                    os.path.join(DOCS_DIR, doc_seleccionado))
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
                            st.toast(
                                f"Documento restaurado a v{item_seleccionado['version']} (Registrado como v{nueva_v})")
                            st.success(
                                f"Rollback completado con éxito. Se generó la versión [Version v{nueva_v}] restaurando la versión [Version v{item_seleccionado['version']}]. Responsable: {autor_rb.strip()}")
                            st.rerun()
                else:
                    st.info(
                        f"La versión v{item_seleccionado['version']} es la versión activa actual. Para ejecutar un Rollback, elija una versión previa en el selector superior.")
    else:
        st.warning(
            "No hay documentos indexados. Cargue un archivo en el panel lateral.")

# ----------------- TAB 4: PLANTILLAS Y RUNBOOKS -----------------
with tab_templates:
    st.subheader("Generador Rápido de Documentación y Runbooks")
    st.caption("Crea y publica procedimientos técnicos estandarizados o define nuevos tipos personalizados en 2 minutos.")

    sac.steps(
        items=[
            sac.StepsItem(title="Paso 1", subtitle="Selección y Metadatos"),
            sac.StepsItem(title="Paso 2", subtitle="Parámetros Técnicos"),
            sac.StepsItem(title="Paso 3", subtitle="Previsualización y Publicación"),
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
            "Tipo de Procedimiento",
            lista_tipos,
            key="select_tipo_procedimiento_gen"
        )

        es_crear_nuevo = tipo_plantilla_sel == "[+ Crear Nuevo Tipo de Procedimiento...]"

        if es_crear_nuevo:
            st.info("[NUEVO TIPO] Defina el nombre y estructura de este nuevo tipo de procedimiento.")
            nuevo_tipo_nombre = st.text_input("Nombre del Nuevo Tipo de Procedimiento (*)", placeholder="Ej: Procedimiento de Auditoría de Accesos y Permisos", key="input_nuevo_tipo_proc")
            guardar_catalogo = st.checkbox("Guardar este nuevo Tipo de Plantilla en el catálogo permanente", value=True)
            tipo_plantilla = nuevo_tipo_nombre.strip() if nuevo_tipo_nombre.strip() else "Procedimiento Personalizado"
        else:
            tipo_plantilla = tipo_plantilla_sel
            guardar_catalogo = False
            nuevo_tipo_nombre = ""

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            autor = st.text_input("Autor / Técnico Responsable (*)", value="Developer / DevOps", key="proc_autor_input")
            nombre_servicio = st.text_input("Servicio o Componente (*)", value="Booking Core Engine", key="proc_srv_input")
        with col_g2:
            nivel_arq = st.selectbox("Nivel de Arquitectura", [
                "L4 - Aplicación y Negocio",
                "L3 - Middleware e Integración",
                "L2 - Virtualización y Cómputo",
                "L1 - Hardware e Infraestructura Base"
            ], key="proc_nivel_input")
            ambiente = st.selectbox("Ambiente Objetivo", ["Producción", "Staging / QA", "Desarrollo", "Datacenter DR", "Todos los Ambientes"], key="proc_amb_input")

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            criticidad = st.selectbox("Criticidad / SLA", ["Crítico 7x24 (P1)", "Alta (P2)", "Media (P3)", "Baja (P4)"], index=2, key="proc_crit_input")
        with col_g4:
            ventana = st.text_input("Ventana de Mantenimiento", value="02:00 a 04:00 AM (Horario no hábil)", key="proc_vent_input")

        servidores = st.text_input("Servidores / Nodos / IPs Involucrados", value="BALANCER001, 10.24.0.125, VM-BOOKING-01", key="proc_srvs_input")

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
            params["criterio"] = st.text_area("Criterio de Activación de Rollback", value="Latencia > 500ms en New Relic por más de 3 min o Error Rate 5xx > 2%")
            params["pasos"] = st.text_area("Pasos de Reversión (Comandos / Acciones)", value="1. Ejecutar pipeline de Rollback en Azure DevOps release-v2.4.1\n2. Revertir cambios de esquema en BD Postgres si aplica\n3. Limpiar caché en Redis Sentinel: redis-cli FLUSHDB")
            params["verif"] = st.text_area("Comandos de Verificación de Salud", value="curl -I https://api.booking.internal/health\nsystemctl status booking-service")
        elif "Paso a Producción" in tipo_plantilla:
            params["version"] = st.text_input("Versión / Tag de Release", value="v2.5.0")
            params["pipeline"] = st.text_input("Pipeline Azure DevOps / Release ID", value="https://dev.azure.com/smucorp/pipelines/142")
            params["variables"] = st.text_area("Variables de Entorno / Configuración", value="REDIS_HOST=10.24.0.126\nJWT_SECRET=[CONFIGURADO EN KEYVAULT]\nLOG_LEVEL=INFO")
            params["smoke"] = st.text_area("Checklist de Validación (Smoke Tests)", value="- [ ] Endpoint /health respondiendo HTTP 200\n- [ ] Transacciones fluyendo en VZOR Suite\n- [ ] Cero alertas críticas en Nagios")
        elif "Postmortem" in tipo_plantilla:
            params["incidente_id"] = st.text_input("ID del Ticket / Incidente", value="INC-88912")
            params["impacto"] = st.text_area("Resumen del Impacto", value="Indisponibilidad del servicio de autorización por 14 minutos. 120 transacciones rechazadas.")
            params["causa"] = st.text_area("Diagnóstico de Causa Raíz (RCA)", value="Agotamiento de pool de conexiones JDBC en WSO2 Enterprise Integrator debido a query no indexada.")
            params["solucion"] = st.text_area("Solución Inmediata Aplicada", value="Reinicio del nodo worker WSO2 y ampliación de maxConnections a 150.")
            params["preventiva"] = st.text_area("Medida Preventiva para Evitar Recurrencia", value="Creación de índice en tabla t_auth_tokens y ajuste de timeout en WSO2.")
        elif "Microservicio" in tipo_plantilla:
            params["endpoint"] = st.text_input("Endpoint Base / Ruta API", value="/api/v1/booking")
            params["auth"] = st.text_input("Método de Autenticación", value="OAuth2 Bearer Token (Redis Sentinel)")
            params["dependencias"] = st.text_area("Dependencias Backend y Nodos", value="* VM: VM-BOOKING-01 (10.24.0.125)\n* DB: Postgres HA (10.24.0.130)\n* Gateway: WSO2 API Manager")
        elif "Parchado" in tipo_plantilla or "Mantenimiento de SO" in tipo_plantilla:
            params["paquetes"] = st.text_area("Alcance y Paquetes a Actualizar", value="Actualización de seguridad mensual del kernel y paquetes críticos de OpenSSL.")
            params["pasos_parchado"] = st.text_area("Pasos de Aplicación de Parches", value="1. Tomar snapshot de VM en VMware vCloud Director\n2. yum update -y / apt-get update && apt-get upgrade -y\n3. Reinicio controlado de nodo secundario\n4. Validación de servicios")
            params["rollback_parchado"] = st.text_area("Plan de Reversión en caso de Fallo", value="Revertir al snapshot de VM en VMware vCloud Director.")
        elif "Certificados" in tipo_plantilla or "SSL" in tipo_plantilla:
            params["dominio"] = st.text_input("Dominio / CN del Certificado", value="*.smucorp.internal")
            params["ruta_cert"] = st.text_input("Ruta de Instalación en el Servidor", value="/etc/ssl/certs/api_smucorp.crt")
            params["comandos_renov"] = st.text_area("Comandos de Generación y Carga", value="openssl req -new -newkey rsa:2048 -nodes -keyout api.key -out api.csr\n# Copiar certificado firmado a /etc/ssl/certs/")
            params["validacion_ssl"] = st.text_area("Comandos de Validación SSL", value="echo | openssl s_client -connect localhost:443 -servername api.smucorp.internal 2>/dev/null | openssl x509 -noout -dates")
        elif "Disaster Recovery" in tipo_plantilla or "DRP" in tipo_plantilla:
            params["rpo_rto"] = st.text_input("Objetivos RPO / RTO", value="RPO: 15 minutos | RTO: 1 hora")
            params["activacion_drp"] = st.text_area("Criterios de Activación del DRP", value="Indisponibilidad total del Datacenter Principal por más de 30 minutos.")
            params["pasos_drp"] = st.text_area("Pasos de Conmutación a Datacenter DR", value="1. Conmutar DNS externo al Datacenter Secundario\n2. Promover réplica de Base de Datos PostgreSQL a Primario\n3. Iniciar workers de WSO2 en sitio secundario")
        elif "Respaldo" in tipo_plantilla or "Base de Datos" in tipo_plantilla:
            params["motor_bd"] = st.text_input("Motor de Base de Datos", value="PostgreSQL 15 HA / Oracle 19c RAC")
            params["comando_backup"] = st.text_area("Comando / Script de Respaldo", value="pg_dump -h 10.24.0.130 -U admin -Fc db_booking > /backups/booking_$(date +%F).dump")
            params["comando_restore"] = st.text_area("Comando / Script de Restauración", value="pg_restore -h 10.24.0.130 -U admin -d db_booking /backups/booking_snapshot.dump")
        elif "Contingencia" in tipo_plantilla or "Failover" in tipo_plantilla:
            params["sintoma"] = st.text_area("Síntoma de Falla / Alerta Disparadora", value="Host ESXi no responde en vCloud o alerta CRITICAL en Nagios por ping timeout.")
            params["pasos"] = st.text_area("Procedimiento de Conmutación (Failover)", value="1. Conmutar tráfico en HAProxy a BALANCER002 (10.24.0.126)\n2. Activar réplica en VMware vCloud Director\n3. Validar resolución DNS interna")
        else:
            params["objetivo"] = st.text_area("Objetivo y Alcance del Procedimiento", value=f"Procedimiento estandarizado para la ejecución segura de {tipo_plantilla} en los componentes de {nombre_servicio}.")
            params["prerequisitos"] = st.text_area("Requisitos Previos y Permisos Necesarios", value="* Acceso SSH con privilegios sudo en los servidores\n* Notificación previa a Mesa de Ayuda / Operaciones 7x24\n* Snapshot o backup preventivo verificado")
            params["pasos_custom"] = st.text_area("Pasos de Ejecución Detallados (Comandos / Acciones)", value="1. Validar estado previo del servicio: systemctl status servicio\n2. Ejecutar script de actualización o mantenimiento\n3. Verificar logs en /var/log/syslog o New Relic")
            params["verificacion_custom"] = st.text_area("Validación y Criterios de Aceptación", value="* Transacciones operativas sin errores 5xx\n* Métricas de CPU y Memoria dentro de umbrales normales (<70%)\n* Nagios check_http reportando estado OK")
            params["rollback_custom"] = st.text_area("Plan de Contingencia / Reversión en caso de Fallo", value="1. Detener ejecución de scripts de inmediato\n2. Restaurar archivos de configuración desde backup local\n3. Reiniciar servicio y notificar al líder técnico")

        doc_generado_md, nombre_archivo_sugerido = generar_doc_plantilla(tipo_plantilla, autor, nombre_servicio, nivel_arq, params)

    with col_t2:
        st.markdown("#### 2. Previsualización en Vivo del Documento")
        nombre_final = st.text_input("Nombre de Archivo Final (.md)", value=nombre_archivo_sugerido, key="input_nombre_archivo_proc_final")

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
                    campos=["objetivo", "prerequisitos", "pasos_custom", "verificacion_custom", "rollback_custom"]
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
            st.success(f"¡Procedimiento guardado e indexado exitosamente como **{nombre_final}** (Versión [Version v1])!")
            st.info("El Chat Copilot, DuckDB y el visualizador Lado a Lado ya pueden consultar y renderizar este nuevo procedimiento.")
            st.rerun()

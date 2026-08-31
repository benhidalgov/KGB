import base64
import os
import re
import streamlit as st
import pandas as pd
from core.auditoria import cargar_hoja_excel_dataframe, guardar_nueva_version, obtener_nombres_hojas_excel
from core.procesador import IMAGE_EXTENSIONS, preparar_markdown_con_imagenes
from core.configuracion import DOCS_DIR

MIME_MAP = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml", ".webp": "image/webp", ".txt": "text/plain", ".csv": "text/csv"
}


def extraer_caption_diagrama(md_content: str, default_name: str) -> str:
    """Extrae el texto del pie de imagen (caption) definido en la ficha Markdown."""
    if md_content:
        m = re.search(r'\*\*Pie de Imagen\s*(?:\(Caption\))?:\*\*\s*(.+)', md_content, re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return f"Diagrama de Arquitectura: {default_name}"


def actualizar_caption_en_markdown(md_content: str, nuevo_caption: str) -> str:
    """Actualiza o inserta el campo de pie de imagen (caption) en el contenido Markdown."""
    cap_str = nuevo_caption.strip()
    if re.search(r'(\*\*Pie de Imagen\s*(?:\(Caption\))?:\*\*\s*).+', md_content, re.IGNORECASE):
        return re.sub(r'(\*\*Pie de Imagen\s*(?:\(Caption\))?:\*\*\s*).+', rf'\g<1>{cap_str}', md_content)
    m_bin = re.search(r'(\* \*\*Archivo Binario:\*\* `[^`]+`\n)', md_content)
    if m_bin:
        return re.sub(r'(\* \*\*Archivo Binario:\*\* `[^`]+`\n)', rf'\g<1>* **Pie de Imagen (Caption):** {cap_str}\n', md_content)
    return f"* **Pie de Imagen (Caption):** {cap_str}\n\n" + md_content


def mostrar_pdf_embebido(pdf_path: str, height: int = 550):
    """Renderiza un visor nativo de PDF embebido mediante un iframe Base64 o boton de descarga para archivos pesados."""
    try:
        size_mb = (os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0) / (1024 * 1024)
        fname = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        if size_mb > 2.5:
            st.markdown(f"""
            <div style="padding: 14px 16px; background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 8px; margin-bottom: 12px;">
                <div style="font-weight: 700; font-size: 0.88rem; color: #6366F1; margin-bottom: 4px;">Documento PDF ({size_mb:.1f} MB)</div>
                <div style="font-size: 0.78rem; opacity: 0.85; margin-bottom: 10px; line-height: 1.4;">Visualice mediante descarga directa o visor del sistema para proteger la memoria del navegador.</div>
            </div>
            """, unsafe_allow_html=True)
            st.download_button(label=f"Descargar PDF Original ({fname})", data=pdf_bytes, file_name=fname, mime="application/pdf", width="stretch", key=f"dl_heavy_pdf_{fname}")
            return

        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}#toolbar=1&navpanes=0" width="100%" height="{height}px" type="application/pdf" style="border:1px solid rgba(128,128,128,0.25); border-radius:6px; background-color:#ffffff;"></iframe>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"No fue posible renderizar el PDF: {str(e)}")


def renderizar_diagrama_limpio(ruta_original: str, doc_name: str, md_content: str, ultima_version: int = 1, ultimo_editor: str = "Técnico Responsable", ultimo_timestamp: str = "N/A", key_suffix: str = ""):
    """Renderiza de forma limpia y exclusiva el diagrama/imagen con su caption y formulario de edicion auditada."""
    fname = os.path.basename(ruta_original)
    size_kb = os.path.getsize(ruta_original) / 1024
    ext = os.path.splitext(ruta_original)[1].lower()
    caption_actual = extraer_caption_diagrama(md_content, os.path.splitext(fname)[0])

    st.markdown(f"""
    <div style="background-color: rgba(128, 128, 128, 0.06); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 6px; padding: 8px 14px; margin-bottom: 12px; font-size: 0.84rem; display: flex; justify-content: space-between; align-items: center;">
        <div><b>Activo Gráfico:</b> <code style="color: #38BDF8;">{fname}</code></div>
        <div><b>Formato:</b> <span class="badge-ok">{ext.upper().replace('.', '')}</span></div>
        <div><b>Tamaño:</b> <code>{size_kb:.1f} KB</code></div>
        <div><b>Versión:</b> <span class="badge-ok">v{ultima_version}</span></div>
        <div><b>Último Editor:</b> <span style="color: #34D399;">{ultimo_editor}</span></div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.image(ruta_original, caption=caption_actual, width="stretch")

    st.markdown("---")
    st.markdown("##### Gestión y Edición del Pie de Imagen (Caption)")
    st.caption("Modifique la descripción técnica del diagrama registrando el responsable de la modificación para trazabilidad.")

    col_e1, col_e2 = st.columns([1.2, 2])
    with col_e1:
        autor_caption = st.text_input("Editor / Técnico Responsable (*)", placeholder="Ej: Juan Pérez / DevOps", key=f"input_author_caption_{doc_name}_{key_suffix}")
        motivo_caption = st.text_input("Motivo de Edición", placeholder="Ej: Actualización de arquitectura de red", key=f"input_motive_caption_{doc_name}_{key_suffix}")
    with col_e2:
        nuevo_caption_input = st.text_area("Descripción Técnica del Diagrama (Pie de Imagen / Caption) (*)", value=caption_actual, height=108, key=f"textarea_caption_{doc_name}_{key_suffix}")

    col_btn_save, col_btn_info = st.columns([2, 3])
    with col_btn_save:
        if st.button(f"Guardar Caption y Publicar Versión v{ultima_version + 1}", type="primary", width="stretch", key=f"btn_save_caption_{doc_name}_{key_suffix}"):
            if not autor_caption or not autor_caption.strip():
                st.error("Error de Auditoría: Debe ingresar el Editor / Técnico Responsable.")
            elif not nuevo_caption_input or not nuevo_caption_input.strip():
                st.error("Error de Validación: El texto del pie de imagen no puede estar vacío.")
            else:
                md_actualizado = actualizar_caption_en_markdown(md_content, nuevo_caption_input.strip())
                doc_path = os.path.join(DOCS_DIR, doc_name)
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(md_actualizado)

                if "doc_store" in st.session_state:
                    st.session_state.doc_store[doc_name] = md_actualizado

                nueva_v = guardar_nueva_version(
                    doc_name=doc_name,
                    nuevo_contenido=md_actualizado,
                    autor=autor_caption.strip(),
                    comentario=motivo_caption.strip() or f"Actualización de pie de imagen: '{nuevo_caption_input.strip()}'",
                    doc_store=st.session_state.get("doc_store")
                )
                st.toast(f"Pie de imagen actualizado (Versión v{nueva_v})")
                st.success(f"¡Versión [Version v{nueva_v}] guardada con éxito! Editor: {autor_caption.strip()}.")
                st.rerun()

    with col_btn_info:
        st.caption(f"*Al guardar, se generará la versión **v{ultima_version + 1}** con registro inmutable en el historial.*")

    st.markdown("---")
    with open(ruta_original, "rb") as f_img:
        bytes_img = f_img.read()
    mime_type = MIME_MAP.get(ext, "image/png")
    st.download_button(label=f"Descargar Imagen Original ({fname})", data=bytes_img, file_name=fname, mime=mime_type, width="stretch", key=f"dl_btn_diag_direct_{fname}_{key_suffix}")

    with st.expander("Ver Especificación Técnica e Indexación (Texto Interno)", expanded=False):
        st.code(md_content, language="markdown")


def renderizar_original_adaptativo(ruta_original: str, doc_name: str, md_content: str = "", key_suffix: str = ""):
    """Renderiza el documento fuente original de forma adaptativa según su tipo de formato binario."""
    if not ruta_original or not os.path.exists(ruta_original):
        st.info("[INFORMACIÓN] El documento no dispone de un archivo binario original adjunto en disco.")
        return

    ext = os.path.splitext(ruta_original)[1].lower()
    fname = os.path.basename(ruta_original)
    size_kb = os.path.getsize(ruta_original) / 1024

    st.markdown(f"""
    <div class="visor-source-meta-bar">
        <div class="visor-source-meta-title"><b>Archivo Fuente:</b> <code>{fname}</code></div>
        <div class="visor-source-meta-tags">
            <span class="badge-tag">{ext.upper().replace('.', '')}</span>
            <span class="badge-tag">{size_kb:.1f} KB</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if ext in IMAGE_EXTENSIONS:
        st.image(ruta_original, caption=extraer_caption_diagrama(md_content, fname), width="stretch")
    elif ext in (".xlsx", ".xls"):
        mtime = os.path.getmtime(ruta_original) if os.path.exists(ruta_original) else 0.0
        sheets = obtener_nombres_hojas_excel(ruta_original, mtime)
        hoja_sel = st.selectbox("Seleccionar Hoja de Trabajo:", sheets, key=f"visor_orig_sheet_{fname}_{key_suffix}")
        df_hoja = cargar_hoja_excel_dataframe(ruta_original, hoja_sel, mtime)
        st.dataframe(df_hoja, width="stretch", height=420)
    elif ext == ".pdf":
        mostrar_pdf_embebido(ruta_original, height=480)
    elif ext in (".docx", ".doc", ".pptx", ".ppt"):
        st.markdown(f"""
        <div class="visor-office-notice-card">
            <div class="visor-office-title">Documento Ofimático: {fname}</div>
            <div class="visor-office-desc">El contenido estructurado y tablas se encuentran normalizados e indexados en la columna izquierda.</div>
        </div>
        """, unsafe_allow_html=True)
    elif ext in (".txt", ".csv", ".json", ".sql", ".py", ".md"):
        try:
            with open(ruta_original, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            st.code(raw_text[:5000] + ("\n... [Truncado]" if len(raw_text) > 5000 else ""), language=ext.replace(".", ""))
        except Exception as e:
            st.error(f"Error al leer archivo: {str(e)}")

    with open(ruta_original, "rb") as f:
        bytes_orig = f.read()
    st.download_button(label=f"Descargar Archivo ({fname})", data=bytes_orig, file_name=fname, mime=MIME_MAP.get(ext, "application/octet-stream"), width="stretch", key=f"dl_btn_orig_{fname}_{key_suffix}")


def renderizar_codigo_seguro(md_content: str):
    """Renderiza código Markdown protegiendo el DOM si el texto es muy extenso (> 50 KB)."""
    if len(md_content) > 50_000:
        st.info(f"[INFO] Documento extenso ({len(md_content)/1024:.1f} KB). Mostrando primeros 50 KB.")
        st.code(md_content[:50_000] + "\n\n... [Truncado en visor de código]", language="markdown")
    else:
        st.code(md_content, language="markdown")


def _render_md_tabs(md_content: str, doc_name: str, ruta_original: str | None):
    tab_rendered, tab_source = st.tabs(["Vista Formateada", "Código Markdown"])
    with tab_rendered:
        with st.container(border=True):
            st.markdown(preparar_markdown_con_imagenes(md_content, doc_name=doc_name, ruta_original=ruta_original), unsafe_allow_html=True)
    with tab_source:
        renderizar_codigo_seguro(md_content)


def renderizar_lado_a_lado(doc_name: str, md_content: str, ruta_original: str | None, ultima_version: int = 1, ultimo_editor: str = "Técnico Responsable", ultimo_timestamp: str = "N/A", key_suffix: str = ""):
    """Gestiona la visualización Lado a Lado de documentos técnicos y diagramas."""
    es_diag = doc_name.startswith("DIAGRAMA__") or (ruta_original and any(ruta_original.lower().endswith(e) for e in IMAGE_EXTENSIONS))
    if es_diag and ruta_original and os.path.exists(ruta_original):
        renderizar_diagrama_limpio(ruta_original, doc_name, md_content, ultima_version, ultimo_editor, ultimo_timestamp, key_suffix)
        return

    col_sel, col_stat = st.columns([2.5, 1.5], vertical_alignment="center")
    with col_sel:
        modo_vista = st.segmented_control("Modo de Visualización", ["[Lado a Lado]", "[Solo Markdown]", "[Solo Formato Original]"], default="[Lado a Lado]", label_visibility="collapsed", key=f"seg_modo_vista_{doc_name}_{key_suffix}") or "[Lado a Lado]"
    with col_stat:
        badge = '<span class="badge-ok">Fuente Disponible</span>' if (ruta_original and os.path.exists(ruta_original)) else '<span class="badge-warn">Nativo Markdown</span>'
        st.markdown(f'<div style="text-align: right; padding-top: 18px;"><b>Estado Fuente:</b> {badge}</div>', unsafe_allow_html=True)

    st.markdown("---")

    if modo_vista == "[Lado a Lado]":
        col_md, col_orig = st.columns(2, gap="medium")
        with col_md:
            st.markdown("##### [Versión Markdown Normalizada]")
            _render_md_tabs(md_content, doc_name, ruta_original)
        with col_orig:
            st.markdown("##### [Documento Fuente Original]")
            with st.container(border=True):
                renderizar_original_adaptativo(ruta_original, doc_name, md_content=md_content, key_suffix=f"side_{key_suffix}")
    elif modo_vista == "[Solo Markdown]":
        _render_md_tabs(md_content, doc_name, ruta_original)
    else:
        with st.container(border=True):
            renderizar_original_adaptativo(ruta_original, doc_name, md_content=md_content, key_suffix=f"full_{key_suffix}")

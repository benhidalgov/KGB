import base64
import json
import mimetypes
import os
import re
import html
import logging
import streamlit as st
import pandas as pd
from core.auditoria import cargar_hoja_excel_dataframe, guardar_nueva_version, obtener_nombres_hojas_excel

logger = logging.getLogger("infra_copilot.visor")
from core.procesador import IMAGE_EXTENSIONS, preparar_markdown_con_imagenes, normalizar_titulo_display, enmascarar_data_uris, restaurar_data_uris
from core.auth import tiene_permiso
from core.configuracion import DOCS_DIR, escribir_atomico

# mimetypes resuelve el MIME en cada plataforma; estos cinco no son fiables sin
# ayuda: OOXML no está en la tabla de stdlib (depende del SO), .webp sólo está
# en la lista no-estándar de stdlib y en Windows con Office el registro del
# sistema pisa .csv con el tipo de Excel. add_type los fija para todos los SO.
for _ext_mime in (
    (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    (".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    (".webp", "image/webp"),
    (".csv", "text/csv"),
):
    mimetypes.add_type(_ext_mime[1], _ext_mime[0])


def mime_de_extension(ext: str, defecto: str = "application/octet-stream") -> str:
    """MIME estándar del archivo; lo que stdlib no conozca cae en `defecto`."""
    return mimetypes.guess_type(f"archivo{ext}")[0] or defecto

# Formatos raster que Pillow puede abrir. Streamlit delega en Pillow para
# incrustar la imagen, asi que la extension no basta: el archivo debe ser una
# imagen real. Un .png renombrado o una ficha Markdown rompian la pagina entera.
EXTENSIONES_IMAGEN_RASTER = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def es_imagen_visualizable(ruta: str | None) -> bool:
    """Indica si el archivo se puede mostrar como imagen en la consola."""
    if not ruta or not os.path.isfile(ruta):
        return False
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".svg":
        # Cabecera: un archivo .svg renombrado tampoco es un SVG.
        try:
            with open(ruta, "rb") as f:
                return b"<svg" in f.read(4096).lower()
        except OSError:
            return False
    if ext not in EXTENSIONES_IMAGEN_RASTER:
        return False
    try:
        from PIL import Image
        with Image.open(ruta) as imagen:
            imagen.verify()
        return True
    except Exception:
        return False


def es_documento_diagrama(doc_name: str, ruta_original: str | None) -> bool:
    """Decide si el documento se abre como diagrama: por nombre o extension, y por contenido real."""
    if not ruta_original or not os.path.exists(ruta_original):
        return False
    ext = os.path.splitext(ruta_original)[1].lower()
    if not (doc_name.startswith("DIAGRAMA__") or ext in IMAGE_EXTENSIONS):
        return False
    return es_imagen_visualizable(ruta_original)


def renderizar_imagen_segura(ruta: str, caption: str) -> bool:
    """Muestra la imagen verificada; si no se puede, avisa y deja la descarga disponible.

    Devuelve True cuando la imagen quedo visible en la pagina.
    """
    fname = os.path.basename(ruta)
    ext = os.path.splitext(ruta)[1].lower()
    etiqueta = ext.upper().replace(".", "") or "desconocido"

    if es_imagen_visualizable(ruta):
        try:
            if ext == ".svg":
                # Pillow no abre SVG: se incrusta como Data URI y lo resuelve el navegador.
                with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                    svg = f.read()
                b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
                st.markdown(
                    f'<div style="text-align:center;"><img src="data:image/svg+xml;base64,{b64}" alt="{html.escape(fname)}" '
                    f'style="max-width:100%;height:auto;border-radius:6px;"/></div>'
                    f'<div style="text-align:center;font-size:0.78rem;color:var(--text-secondary);margin-top:6px;">{html.escape(caption)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.image(ruta, caption=caption, width="stretch")
            return True
        except Exception as e:
            logger.warning(f"[Visor] No se pudo mostrar la imagen {fname}: {e}")

    st.markdown(f"""
    <div class="bento-card" style="padding: 12px 14px; font-size: 0.84rem; line-height: 1.5;">
        <span class="badge-warn">[WARN]</span> No se puede previsualizar <code>{fname}</code> como imagen
        (formato {etiqueta}): el archivo no es una imagen valida o su contenido no coincide con la extension.
        Use el boton de descarga para revisarlo.
    </div>
    """, unsafe_allow_html=True)
    return False


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
        return re.sub(r'(\*\*Pie de Imagen\s*(?:\(Caption\))?:\*\*\s*).+', lambda m: m.group(1) + cap_str, md_content)
    m_bin = re.search(r'(\* \*\*Archivo Binario:\*\* `[^`]+`\n)', md_content)
    if m_bin:
        return re.sub(r'(\* \*\*Archivo Binario:\*\* `[^`]+`\n)', lambda m: m.group(1) + f"* **Pie de Imagen (Caption):** {cap_str}\n", md_content)
    return f"* **Pie de Imagen (Caption):** {cap_str}\n\n" + md_content


def mostrar_pdf_embebido(pdf_path: str, height: int = 550, key_suffix: str = ""):
    """Renderiza un visor nativo de PDF embebido mediante un iframe Base64 o boton de descarga para archivos pesados."""
    try:
        size_mb = (os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0) / (1024 * 1024)
        fname = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        if size_mb > 2.5:
            st.markdown(f"""
            <div class="bento-card" style="margin-bottom: 12px;">
                <div style="font-weight: 600; font-size: 0.88rem; color: var(--text-primary); margin-bottom: 4px;">Documento PDF ({size_mb:.1f} MB)</div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.4;">Descárgalo para verlo sin recargar el navegador.</div>
            </div>
            """, unsafe_allow_html=True)
            st.download_button(label=f"Descargar PDF Original ({fname})", data=pdf_bytes, file_name=fname, mime="application/pdf", width="stretch", key=f"dl_heavy_pdf_{fname}_{key_suffix}")
            return

        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}#toolbar=1&navpanes=0" width="100%" height="{height}px" type="application/pdf" style="border:1px solid var(--border-subtle); border-radius:6px; background-color:var(--bg-surface);"></iframe>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"No se pudo mostrar el PDF: {str(e)}")


@st.cache_data(show_spinner=False)
def cargar_docx_a_html(filepath: str, mtime: float) -> str:
    """Convierte un documento .docx a HTML semántico enriquecido utilizando mammoth."""
    try:
        import mammoth

        def _convertir_imagen(image):
            with image.open() as img_bytes:
                enc = base64.b64encode(img_bytes.read()).decode("ascii")
            return {
                "src": f"data:{image.content_type};base64,{enc}",
                "style": "max-width: 100%; height: auto; border-radius: 6px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08);"
            }

        with open(filepath, "rb") as docx_file:
            result = mammoth.convert_to_html(
                docx_file,
                convert_image=mammoth.images.img_element(_convertir_imagen)
            )
            return result.value or ""
    except Exception as e:
        logger.warning(f"[Visor] Error al convertir {filepath} con mammoth: {e}")
        return ""


@st.cache_data(show_spinner=False)
def cargar_pptx_a_slides(filepath: str, mtime: float) -> list:
    """Extrae diapositivas estructuradas de un archivo .pptx con python-pptx."""
    try:
        from pptx import Presentation
        from pptx.enum.shapes import PP_PLACEHOLDER
        prs = Presentation(filepath)
        slides_data = []
        for idx, slide in enumerate(prs.slides, 1):
            title = ""
            texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    txt = shape.text_frame.text.strip()
                    if not txt:
                        continue
                    # Comparar con `==` contra slide.shapes.title nunca era True:
                    # cada acceso crea un proxy nuevo (identidad, no igualdad).
                    es_titulo = idx == 1 or (
                        shape.is_placeholder
                        and shape.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)
                    )
                    if not title and es_titulo:
                        title = txt
                    else:
                        texts.append(txt)
            slides_data.append({
                "numero": idx,
                "titulo": title or f"Diapositiva {idx}",
                "contenido": texts
            })
        return slides_data
    except Exception as e:
        logger.warning(f"[Visor] Error al leer {filepath} con python-pptx: {e}")
        return []


def renderizar_diagrama_limpio(ruta_original: str, doc_name: str, md_content: str, ultima_version: int = 1, ultimo_editor: str = "Técnico Responsable", ultimo_timestamp: str = "N/A", key_suffix: str = ""):
    """Renderiza de forma limpia y exclusiva el diagrama/imagen con su caption y formulario de edicion auditada."""
    fname = os.path.basename(ruta_original)
    size_kb = os.path.getsize(ruta_original) / 1024
    ext = os.path.splitext(ruta_original)[1].lower()
    caption_actual = extraer_caption_diagrama(md_content, os.path.splitext(fname)[0])

    st.markdown(f"""
    <div class="bento-card" style="padding: 10px 14px; margin-bottom: 12px; font-size: 0.84rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div><b>Archivo:</b> <code style="color: var(--text-primary);">{fname}</code></div>
        <div><b>Formato:</b> <span class="badge-ok">{ext.upper().replace('.', '')}</span></div>
        <div><b>Tamaño:</b> <code>{size_kb:.1f} KB</code></div>
        <div><b>Versión:</b> <span class="badge-ok">v{ultima_version}</span></div>
        <div><b>Último Editor:</b> <span style="color: var(--text-secondary);">{html.escape(str(ultimo_editor))}</span></div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        renderizar_imagen_segura(ruta_original, caption_actual)

    st.markdown("---")
    st.markdown("##### Editar Descripción del Diagrama")
    st.caption("Cambia la descripción del diagrama. Guarda tu nombre para dejar registro.")

    col_e1, col_e2 = st.columns([1.2, 2])
    with col_e1:
        autor_caption = st.text_input("Tu nombre (*)", key=f"input_author_caption_{doc_name}_{key_suffix}")
        motivo_caption = st.text_input("Motivo", key=f"input_motive_caption_{doc_name}_{key_suffix}")
    with col_e2:
        nuevo_caption_input = st.text_area("Descripción del Diagrama (*)", value=caption_actual, height=108, key=f"textarea_caption_{doc_name}_{key_suffix}")

    col_btn_save, col_btn_info = st.columns([2, 3])
    with col_btn_save:
        if st.button(f"Guardar Descripción (v{ultima_version + 1})", type="primary", width="stretch", key=f"btn_save_caption_{doc_name}_{key_suffix}"):
            if not tiene_permiso("puede_editar_docs"):
                st.error("Tu rol no permite editar descripciones.")
            elif not autor_caption or not autor_caption.strip():
                st.error("Escribe tu nombre.")
            elif not nuevo_caption_input or not nuevo_caption_input.strip():
                st.error("La descripción no puede estar vacía.")
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
                st.toast(f"Descripción actualizada (v{nueva_v})")
                st.success(f"Versión v{nueva_v} guardada. Editor: {autor_caption.strip()}.")
                st.rerun()

    with col_btn_info:
        st.caption(f"*Al guardar se creará la versión **v{ultima_version + 1}** y quedará en el historial.*")

    st.markdown("---")
    with open(ruta_original, "rb") as f_img:
        bytes_img = f_img.read()
    mime_type = mime_de_extension(ext, "image/png")
    st.download_button(label=f"Descargar Imagen Original ({fname})", data=bytes_img, file_name=fname, mime=mime_type, width="stretch", key=f"dl_btn_diag_direct_{fname}_{key_suffix}")

    with st.expander("Ver Texto Interno (Markdown)", expanded=False):
        st.code(md_content, language="markdown")


def renderizar_original_adaptativo(ruta_original: str, doc_name: str, md_content: str = "", height: int = 480, key_suffix: str = ""):
    """Renderiza el documento fuente original de forma adaptativa según su tipo de formato binario."""
    if not ruta_original or not os.path.exists(ruta_original):
        st.info("Este documento no tiene un archivo original adjunto.")
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

    if ext in IMAGE_EXTENSIONS or ext in EXTENSIONES_IMAGEN_RASTER:
        renderizar_imagen_segura(ruta_original, extraer_caption_diagrama(md_content, fname))
    elif ext in (".xlsx", ".xls"):
        mtime = os.path.getmtime(ruta_original) if os.path.exists(ruta_original) else 0.0
        sheets = obtener_nombres_hojas_excel(ruta_original, mtime)
        hoja_sel = st.selectbox("Seleccionar Hoja de Trabajo:", sheets, key=f"visor_orig_sheet_{fname}_{key_suffix}")
        df_hoja = cargar_hoja_excel_dataframe(ruta_original, hoja_sel, mtime)
        st.dataframe(df_hoja, width="stretch", height=height)
    elif ext == ".pdf":
        mostrar_pdf_embebido(ruta_original, height=height, key_suffix=key_suffix)
    elif ext in (".docx", ".doc"):
        mtime = os.path.getmtime(ruta_original) if os.path.exists(ruta_original) else 0.0
        html_docx = cargar_docx_a_html(ruta_original, mtime) if ext == ".docx" else ""
        if html_docx:
            st.markdown(
                f'<div class="visor-docx-container" style="max-height: {height}px; overflow-y: auto;">'
                f'{html_docx}'
                f'</div>',
                unsafe_allow_html=True
            )
        elif md_content and md_content.strip():
            with st.container(height=height):
                st.markdown(preparar_markdown_con_imagenes(md_content, ruta_original=ruta_original), unsafe_allow_html=True)
        else:
            st.info(f"No se pudo generar la vista previa del documento {fname}.")
    elif ext in (".pptx", ".ppt"):
        mtime = os.path.getmtime(ruta_original) if os.path.exists(ruta_original) else 0.0
        slides = cargar_pptx_a_slides(ruta_original, mtime) if ext == ".pptx" else []
        if slides:
            with st.container(height=height):
                for s in slides:
                    bullets_html = "".join(f"<li>{t}</li>" for t in s["contenido"]) if s["contenido"] else "<p style='color:var(--text-muted);font-style:italic;'>Sin contenido textual en la diapositiva.</p>"
                    st.markdown(f"""
                    <div class="visor-pptx-slide-card">
                        <div class="visor-pptx-slide-header">
                            <span class="badge-tag">Diapositiva {s['numero']}</span>
                            <span class="visor-pptx-slide-title">{s['titulo']}</span>
                        </div>
                        <div class="visor-pptx-slide-body">
                            <ul style="margin: 8px 0; padding-left: 20px;">
                                {bullets_html}
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        elif md_content and md_content.strip():
            with st.container(height=height):
                st.markdown(preparar_markdown_con_imagenes(md_content, ruta_original=ruta_original), unsafe_allow_html=True)
        else:
            st.info(f"No se pudo generar la vista previa de la presentación {fname}.")
    elif ext in (".txt", ".csv", ".json", ".sql", ".py", ".md"):
        try:
            with open(ruta_original, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            st.code(raw_text[:8000] + ("\n... [Truncado]" if len(raw_text) > 8000 else ""), language=ext.replace(".", ""))
        except Exception as e:
            st.error(f"Error al leer archivo: {str(e)}")

    with open(ruta_original, "rb") as f:
        bytes_orig = f.read()
    st.download_button(label=f"Descargar Archivo ({fname})", data=bytes_orig, file_name=fname, mime=mime_de_extension(ext), width="stretch", key=f"dl_btn_orig_{fname}_{key_suffix}")


def _render_md_tabs(md_content: str, doc_name: str, ruta_original: str | None):
    tab_rendered, tab_source = st.tabs(["Vista Formateada", "Código Markdown"])
    with tab_rendered:
        with st.container(border=True):
            st.markdown(preparar_markdown_con_imagenes(md_content, ruta_original=ruta_original), unsafe_allow_html=True)
    with tab_source:
        # El DOM solo aguanta hasta 50 KB de codigo en un bloque st.code.
        if len(md_content) > 50_000:
            st.info(f"Documento largo ({len(md_content)/1024:.1f} KB). Se muestran los primeros 50 KB.")
            st.code(md_content[:50_000] + "\n\n... [Truncado en visor de codigo]", language="markdown")
        else:
            st.code(md_content, language="markdown")


def renderizar_lado_a_lado(doc_name: str, md_content: str, ruta_original: str | None, ultima_version: int = 1, ultimo_editor: str = "Técnico Responsable", ultimo_timestamp: str = "N/A", key_suffix: str = ""):
    """Gestiona la visualización Lado a Lado de documentos técnicos y diagramas con Modo Enfoque inmersivo."""
    if es_documento_diagrama(doc_name, ruta_original):
        renderizar_diagrama_limpio(ruta_original, doc_name, md_content, ultima_version, ultimo_editor, ultimo_timestamp, key_suffix)
        return

    col_sel, col_stat, col_zen = st.columns([2.5, 1.2, 1.3], vertical_alignment="center")
    with col_sel:
        modo_vista = st.segmented_control(
            "Modo de Visualización",
            ["[Lado a Lado]", "[Solo Markdown]", "[Solo Formato Original]"],
            default="[Lado a Lado]",
            label_visibility="collapsed",
            key=f"seg_modo_vista_{doc_name}_{key_suffix}"
        ) or "[Lado a Lado]"
    with col_stat:
        badge = '<span class="badge-ok" style="font-size:0.72rem;padding:2px 7px;">Fuente Disponible</span>' if (ruta_original and os.path.exists(ruta_original)) else '<span class="badge-warn" style="font-size:0.72rem;padding:2px 7px;">Nativo Markdown</span>'
        st.markdown(f'<div style="text-align:center;font-size:0.78rem;opacity:0.9;"><b>Estado:</b> {badge}</div>', unsafe_allow_html=True)
    with col_zen:
        if st.button("Abrir en Modo Lectura", type="primary", width="stretch", key=f"btn_zen_enter_{doc_name}_{key_suffix}", help="Abre el modo de lectura a pantalla completa."):
            st.session_state["zen_studio_activo"] = True
            st.session_state["zen_doc_sel"] = doc_name
            st.rerun()

    alt_visores = 550
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if modo_vista == "[Lado a Lado]":
        col_md, col_orig = st.columns(2, gap="medium")
        with col_md:
            st.markdown("##### [Texto]")
            _render_md_tabs(md_content, doc_name, ruta_original)
        with col_orig:
            st.markdown("##### [Archivo Original]")
            with st.container(border=True):
                renderizar_original_adaptativo(ruta_original, doc_name, md_content=md_content, height=alt_visores, key_suffix=f"side_{key_suffix}")
    elif modo_vista == "[Solo Markdown]":
        _render_md_tabs(md_content, doc_name, ruta_original)
    else:
        with st.container(border=True):
            renderizar_original_adaptativo(ruta_original, doc_name, md_content=md_content, height=alt_visores, key_suffix=f"full_{key_suffix}")


def extraer_tabla_de_contenidos(md_content: str) -> list[dict]:
    """Analiza el documento Markdown y extrae la jerarquía de títulos (H1-H4)."""
    toc = []
    lineas = md_content.splitlines()
    for idx, linea in enumerate(lineas):
        m = re.match(r'^(#{1,4})\s+(.+)$', linea.strip())
        if m:
            nivel = len(m.group(1))
            titulo = m.group(2).strip()
            titulo_limpio = re.sub(r'[*_`]', '', titulo)
            toc.append({
                "nivel": nivel,
                "titulo": titulo_limpio,
                "linea": idx + 1,
                "id": f"sec_{idx}"
            })
    return toc


def resaltar_termino_en_html(html_o_md: str, termino: str) -> tuple[str, int]:
    """Resalta con etiqueta mark las ocurrencias de una palabra clave."""
    if not termino or not termino.strip():
        return html_o_md, 0
    base, uris = enmascarar_data_uris(html_o_md)
    t_clean = re.escape(termino.strip())
    patron = re.compile(rf'(?i)({t_clean})')
    coincidencias = len(patron.findall(base))
    if coincidencias > 0:
        res = patron.sub(r'<mark style="background-color: var(--pastel-amber-bg); color: var(--pastel-amber-text); padding: 2px 4px; border-radius: 3px; font-weight: 600;">\1</mark>', base)
        return restaurar_data_uris(res, uris), coincidencias
    return html_o_md, 0


# Paletas de lectura del Zen Studio: colores de tema, fuera de la funcion para
# no reconstruirlas en cada render y separar datos de presentacion.
PALETAS_LECTURA = {
    "Sepia": {
        "bg": "#F5EEDC", "fg": "#342A1E", "fg_subtle": "#544635",
        "border": "#DECFA8", "code_bg": "#EADFCA", "card_bg": "#EFE6D2",
    },
    "Grafito": {
        "bg": "#1C1E22", "fg": "#EDEDEC", "fg_subtle": "#A8A7A0",
        "border": "rgba(255, 255, 255, 0.15)", "code_bg": "rgba(255, 255, 255, 0.08)",
        "card_bg": "#24272D",
    },
    "Cálido": {
        "bg": "#FAF7F2", "fg": "#1C1B19", "fg_subtle": "#484540",
        "border": "#E5E0D5", "code_bg": "#EFEBE2", "card_bg": "#F4EFE6",
    },
}

# Ruta y helpers para persistir preferencias del lector zen entre sesiones.
_ZEN_PREFS_PATH = os.path.join(os.path.dirname(DOCS_DIR), "zen_prefs.json")
_ZEN_PREFS_DEFAULT = {"tema": "Cálido", "tam_fuente": "Normal (15px)", "historial": []}


def _cargar_prefs_zen() -> dict:
    """Lee preferencias del lector zen desde data/zen_prefs.json."""
    if os.path.exists(_ZEN_PREFS_PATH):
        try:
            with open(_ZEN_PREFS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return dict(_ZEN_PREFS_DEFAULT)


def _guardar_prefs_zen(prefs: dict) -> None:
    """Guarda preferencias del lector zen de forma atómica."""
    try:
        escribir_atomico(_ZEN_PREFS_PATH, json.dumps(prefs, indent=2, ensure_ascii=False))
    except Exception:
        pass


# CSS del lector zen como plantilla con placeholders: se renderiza una vez por
# tema/tamaño con .format(). Los estilos estaticos viven aqui (fuera de un
# f-string gigante embebido en Python) y los colores provienen de
# PALETAS_LECTURA.
_CSS_ZEN = """
<style>
.zen-reader-canvas {{
    background-color: {bg} !important;
    border: 1px solid {border} !important;
    color: {fg} !important;
    font-size: {font_size} !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}}
.zen-reader-canvas p,
.zen-reader-canvas li,
.zen-reader-canvas div,
.zen-reader-canvas span,
.zen-reader-canvas td,
.zen-reader-canvas th {{
    color: {fg_subtle} !important;
    font-size: {font_size} !important;
    line-height: 1.75 !important;
}}
.zen-reader-canvas h1,
.zen-reader-canvas h2,
.zen-reader-canvas h3,
.zen-reader-canvas h4,
.zen-reader-canvas h5,
.zen-reader-canvas h6,
.zen-reader-canvas strong,
.zen-reader-canvas b {{
    color: {fg} !important;
    font-family: var(--font-serif) !important;
}}
.zen-reader-canvas code,
.zen-reader-canvas pre {{
    background-color: {code_bg} !important;
    color: {fg} !important;
    border: 1px solid {border} !important;
    font-size: 0.88em !important;
}}
.zen-reader-canvas blockquote {{
    border-left: 3px solid {border} !important;
    color: {fg_subtle} !important;
    padding-left: 12px !important;
    margin-left: 0 !important;
}}
.zen-reader-canvas hr {{
    border: none !important;
    border-top: 1px solid {border} !important;
    margin: 20px 0 !important;
}}
.zen-reader-canvas table {{
    border: 1px solid {border} !important;
}}
.zen-toc-card {{
    background-color: {card_bg} !important;
    border: 1px solid {border} !important;
}}
.zen-toc-item {{
    color: {fg_subtle} !important;
}}
</style>
""".strip()


def renderizar_zen_studio(doc_name: str, md_content: str, ruta_original: str | None, u_ver: int = 1, u_edit: str = "Técnico", u_time: str = "N/A", doc_store: dict | None = None):
    """Renderiza el entorno inmersivo Zen Studio con TOC interactivo, buscador interno, personalización de lectura y visor multimodal."""
    # Cargar preferencias persistidas (tema y tamaño de fuente entre sesiones).
    _prefs_zen = _cargar_prefs_zen()
    st.session_state.setdefault("zen_theme_selector", _prefs_zen.get("tema", "Cálido"))
    st.session_state.setdefault("zen_font_size_selector", _prefs_zen.get("tam_fuente", "Normal (15px)"))
    st.html("<style>section[data-testid=\"stSidebar\"], header[data-testid=\"stHeader\"] { display: none !important; } [data-testid=\"stMainBlockContainer\"] { max-width: 98vw !important; padding: 0.6rem 1.4rem !important; } .zen-controles { display: flex; align-items: center; gap: 8px; background: var(--bg-surface-subtle); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 6px 10px; } .zen-controles .stSelectbox > div > div { background-color: var(--bg-surface) !important; border: 1px solid var(--border-medium) !important; border-radius: 4px !important; font-size: 0.82rem !important; } .zen-controles .stSelectbox > div > div:hover { border-color: var(--border-medium) !important; } .zen-controles .stSelectbox svg { fill: var(--text-secondary) !important; } .zen-search-input input { padding: 6px 10px !important; font-size: 0.85rem !important; }</style>")

    col_zt_title, col_zt_search, col_zt_theme, col_zt_exit = st.columns([3.2, 2.4, 2.2, 1.2], vertical_alignment="center")

    with col_zt_title:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;padding-top:4px;">
            <span class="badge-ok" style="font-size:0.7rem;padding:2px 8px;font-weight:600;">[Modo Lectura]</span>
            <span style="font-family:var(--font-serif);font-size:1.2rem;font-weight:600;color:var(--text-primary);">{normalizar_titulo_display(doc_name)}</span>
            <span class="badge-info" style="font-size:0.68rem;padding:2px 6px;font-weight:500;">v{u_ver}</span>
        </div>
        """, unsafe_allow_html=True)

    with col_zt_search:
        col_search_in, col_search_clear = col_zt_search.columns([5, 1])
        with col_search_in:
            zen_search_query = st.text_input("Buscar en documento:", placeholder="Buscar en este documento...", label_visibility="collapsed", key="zen_search_in_doc")
        with col_search_clear:
            if st.button("Limpiar", key="zen_buscar_limpiar", width="stretch", help="Borrar el término de búsqueda y volver al documento completo"):
                st.session_state["zen_search_in_doc"] = ""
                st.rerun()

    with col_zt_theme:
        st.markdown('<div class="zen-controles">', unsafe_allow_html=True)
        col_zt_th1, col_zt_th2 = st.columns(2)
        with col_zt_th1:
            tema_lectura = st.selectbox("Tema", ["Cálido", "Sepia", "Grafito"], label_visibility="collapsed", key="zen_theme_selector")
        with col_zt_th2:
            tam_fuente = st.selectbox("Tamaño", ["Normal (15px)", "Grande (17px)", "Compacto (13px)"], label_visibility="collapsed", key="zen_font_size_selector")
        st.markdown('</div>', unsafe_allow_html=True)
        # Persistir preferencias al cambiar tema o tamaño de fuente.
        _guardar_prefs_zen({"tema": tema_lectura, "tam_fuente": tam_fuente})

    with col_zt_exit:
        if st.button("Salir", type="primary", width="stretch", key="btn_exit_zen_studio", help="Vuelve a la consola de operaciones (tecla Esc)"):
            st.session_state["zen_studio_activo"] = False
            # El router (app.py) decide por nav_seccion_activa; sin esto el
            # siguiente rerun vuelve a entrar en Zen y queda en bucle.
            st.session_state["nav_seccion_activa"] = "Consultas y Búsqueda"
            st.rerun()

    # Botones de atajos de teclado del lector zen: se muestran para que los
    # usuarios los descubran y los usen; pulsar uno equivale a teclear la
    # tecla correspondiente (app.py lee el parámetro zen_nav al rerun).
    cols_atajos = st.columns(6)
    with cols_atajos[0]:
        if st.button("Anterior (k)", key="zen_atajo_prev", width="stretch", help="Documento anterior (tecla k o flecha arriba)"):
            st.query_params["zen_nav"] = "prev"
            st.rerun()
    with cols_atajos[1]:
        if st.button("Siguiente (j)", key="zen_atajo_next", width="stretch", help="Documento siguiente (tecla j o flecha abajo)"):
            st.query_params["zen_nav"] = "next"
            st.rerun()
    with cols_atajos[2]:
        if st.button("Fuente +", key="zen_atajo_font_bigger", width="stretch", help="Tamaño de fuente más grande (tecla + o =)"):
            st.query_params["zen_nav"] = "font_bigger"
            st.rerun()
    with cols_atajos[3]:
        if st.button("Fuente -", key="zen_atajo_font_smaller", width="stretch", help="Tamaño de fuente más pequeño (tecla -)"):
            st.query_params["zen_nav"] = "font_smaller"
            st.rerun()
    with cols_atajos[4]:
        if st.button("Reset (0)", key="zen_atajo_font_reset", width="stretch", help="Restaurar tamaño de fuente por defecto (tecla 0)"):
            st.query_params["zen_nav"] = "font_reset"
            st.rerun()
    with cols_atajos[5]:
        if st.button("Salir (Esc)", key="zen_atajo_exit", width="stretch", help="Volver a la consola de operaciones (tecla Esc)"):
            st.query_params["zen_nav"] = "exit"
            st.rerun()

    # Selector para cambiar de documento sin salir del Modo Lectura.
    if doc_store:
        docs_opciones = sorted(doc_store.keys())
        doc_actual = doc_name
        idx_actual = docs_opciones.index(doc_actual) if doc_actual in docs_opciones else 0
        nuevo_doc = st.selectbox(
            "Cambiar documento:",
            docs_opciones,
            index=idx_actual,
            key="zen_cambiar_documento",
            format_func=normalizar_titulo_display,
        )
        if nuevo_doc != doc_actual:
            st.session_state["zen_doc_sel"] = nuevo_doc
            st.rerun()

    # Historial de documentos leídos (últimos 5, persistido entre sesiones).
    historial_zen = list(_prefs_zen.get("historial", []))
    if doc_name in historial_zen:
        historial_zen.remove(doc_name)
    historial_zen.insert(0, doc_name)
    historial_zen = historial_zen[:5]
    _prefs_zen["historial"] = historial_zen
    _guardar_prefs_zen(_prefs_zen)

    if len(historial_zen) > 1:
        recientes = [d for d in historial_zen if d != doc_name]
        st.markdown("##### Recientes")
        for d in recientes:
            st.markdown(f"- {normalizar_titulo_display(d)}", unsafe_allow_html=False)

    font_size_val = "17px" if "Grande" in tam_fuente else ("13px" if "Compacto" in tam_fuente else "15px")
    p_lec = PALETAS_LECTURA.get(tema_lectura, PALETAS_LECTURA["Cálido"])
    css_zen = _CSS_ZEN.format(bg=p_lec["bg"], fg=p_lec["fg"], fg_subtle=p_lec["fg_subtle"],
                              border=p_lec["border"], code_bg=p_lec["code_bg"],
                              card_bg=p_lec["card_bg"], font_size=font_size_val)
    st.markdown(css_zen, unsafe_allow_html=True)

    # Atajos de teclado del lector zen: j/k documento siguiente/anterior,
    # Esc salir, +/- cambiar tamaño de fuente, 0 restablecer. Modifican
    # los parámetros de URL y la app los procesa en el siguiente rerun.
    st.html("""
    <script>
    (function() {
        var mapa = {
            'j': 'next', 'k': 'prev', 'ArrowDown': 'next', 'ArrowUp': 'prev',
            '+': 'font_bigger', '=': 'font_bigger', '-': 'font_smaller',
            '0': 'font_reset', 'Escape': 'exit'
        };
        document.addEventListener('keydown', function(e) {
            var accion = mapa[e.key];
            if (!accion) return;
            if (e.target.tagName && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
            e.preventDefault();
            var url = new URL(window.location);
            url.searchParams.set('zen_nav', accion);
            window.history.replaceState(null, '', url.pathname + '?' + url.searchParams.toString());
        });
    })();
    </script>
    """, unsafe_allow_javascript=True)

    # Persistencia de posición de scroll por documento (localStorage del navegador).
    _doc_name_js = json.dumps(doc_name)
    st.html("""
    <script>
    (function() {
        var key = "zen_scroll_" + __DOC_NAME__;
        var saved = localStorage.getItem(key);
        if (saved) {
            setTimeout(function() {
                try { window.scrollTo(0, parseInt(saved, 10)); } catch(e) {}
            }, 100);
        }
        var timer;
        window.onscroll = function() {
            clearTimeout(timer);
            timer = setTimeout(function() {
                try { localStorage.setItem(key, window.scrollY.toString()); } catch(e) {}
            }, 200);
        };
        window.addEventListener('beforeunload', function() {
            try { localStorage.setItem(key, window.scrollY.toString()); } catch(e) {}
        });
    })();
    </script>
    """.replace("__DOC_NAME__", _doc_name_js), unsafe_allow_javascript=True)

    col_toc, col_canvas = st.columns([1.1, 3.4], gap="medium")

    with col_toc:
        st.markdown("##### [Índice]")
        toc_items = extraer_tabla_de_contenidos(md_content)
        palabras = len(md_content.split())
        minutos_lectura = max(1, palabras // 200)

        if toc_items:
            with st.container(border=True):
                st.caption(f"**{len(toc_items)} secciones**:")
                opciones_seccion = ["Documento Completo"] + [f"{'—' * (it['nivel'] - 1)} {it['titulo']}" for it in toc_items]
                seccion_sel = st.selectbox("Saltar a Sección:", opciones_seccion, key=f"zen_section_jump_sel_{doc_name}")

                toc_html_list = []
                for it in toc_items:
                    indent = (it['nivel'] - 1) * 10
                    badge_h = f"<span class='badge-tag' style='font-size:0.65rem;margin-right:4px;'>H{it['nivel']}</span>"
                    # El título viene del Markdown crudo del documento: sin escapar,
                    # un encabezado subido inyecta HTML en el índice de todos los roles.
                    toc_html_list.append(f"<div class='zen-toc-item' style='margin-left:{indent}px;'>{badge_h} {html.escape(it['titulo'])}</div>")
                st.markdown(f"<div class='zen-toc-card'>{''.join(toc_html_list)}</div>", unsafe_allow_html=True)
        else:
            st.info("Este documento no tiene secciones.")
            seccion_sel = "Documento Completo"

        st.markdown(f"""
        <div class="bento-card" style="padding:10px 14px;margin-top:10px;font-size:0.8rem;">
            <div style="font-weight:600;color:var(--text-primary);margin-bottom:6px;">Detalles del Documento</div>
            <div style="display:flex;flex-direction:column;gap:4px;color:var(--text-secondary);">
                <div><b>Palabras:</b> {palabras:,}</div>
                <div><b>Lectura:</b> ~{minutos_lectura} min</div>
                <div><b>Editor:</b> {html.escape(str(u_edit))}</div>
                <div><b>Actualizado:</b> {u_time}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if ruta_original and os.path.exists(ruta_original):
            ext_orig = os.path.splitext(ruta_original)[1].lower()
            with open(ruta_original, "rb") as f_dl_zen:
                st.download_button(
                    label=f"Descargar Fuente ({ext_orig.upper().replace('.', '')})",
                    data=f_dl_zen.read(),
                    file_name=os.path.basename(ruta_original),
                    mime=mime_de_extension(ext_orig),
                    width="stretch",
                    key=f"zen_dl_btn_{doc_name}"
                )

    with col_canvas:
        texto_a_mostrar = md_content
        if seccion_sel != "Documento Completo":
            # El TOC limpia énfasis (*_`); comparar los encabezados igualmente limpiados.
            titulo_buscado = seccion_sel.lstrip('— ').strip()
            m_sec = None
            for m_h in re.finditer(r'(?m)^#+\s+(.+)$', md_content):
                if re.sub(r'[*_`]', '', m_h.group(1)).strip() == titulo_buscado:
                    resto = md_content[m_h.end():]
                    sig = re.search(r'(?m)^#+\s+', resto)
                    m_sec = md_content[m_h.start():m_h.end() + (sig.start() if sig else len(resto))]
                    break
            if m_sec:
                texto_a_mostrar = m_sec

        cnt_coincidencias = 0
        if zen_search_query.strip():
            texto_preparado = preparar_markdown_con_imagenes(texto_a_mostrar, ruta_original=ruta_original)
            html_resaltado, cnt_coincidencias = resaltar_termino_en_html(texto_preparado, zen_search_query)
            st.markdown(f"<div style='font-size:0.8rem;margin-bottom:6px;'><span class='badge-ok'>[{cnt_coincidencias} Coincidencias]</span> para '<b>{html.escape(zen_search_query)}</b>'</div>", unsafe_allow_html=True)
        else:
            html_resaltado = preparar_markdown_con_imagenes(texto_a_mostrar, ruta_original=ruta_original)

        tiene_orig = ruta_original and os.path.exists(ruta_original)
        if tiene_orig:
            tab_z_fmt, tab_z_orig, tab_z_side = st.tabs(["Texto", "Original", "Lado a Lado"])
            with tab_z_fmt:
                st.markdown(f"<div class='zen-reader-canvas'>{html_resaltado}</div>", unsafe_allow_html=True)
            with tab_z_orig:
                with st.container(border=True):
                    renderizar_original_adaptativo(ruta_original, doc_name, md_content=md_content, height=750, key_suffix="zen_orig")
            with tab_z_side:
                col_z_s1, col_z_s2 = st.columns(2, gap="medium")
                with col_z_s1:
                    st.markdown(f"<div class='zen-reader-canvas' style='padding:16px;'>{html_resaltado}</div>", unsafe_allow_html=True)
                with col_z_s2:
                    with st.container(border=True):
                        renderizar_original_adaptativo(ruta_original, doc_name, md_content=md_content, height=750, key_suffix="zen_side")
        else:
            st.markdown(f"<div class='zen-reader-canvas'>{html_resaltado}</div>", unsafe_allow_html=True)

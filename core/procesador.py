import hashlib
import os
import re
import glob
from datetime import datetime
import streamlit as st
from excel_cleaner import procesar_excel_limpio
from core.configuracion import DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR, INBOX_DIR

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.svg', '.webp')
OFFICE_EXTENSIONS = ('.docx', '.pdf', '.pptx', '.xlsx', '.xls')
TEXT_EXTENSIONS = ('.md', '.txt', '.csv', '.json', '.sql', '.py')
SUPPORTED_EXTENSIONS = ('.pdf', '.docx', '.xlsx', '.xls', '.pptx', '.txt', '.csv', '.md', '.png', '.jpg', '.jpeg', '.svg', '.webp')


def calcular_sha256(data: bytes) -> str:
    """Calcula el hash criptográfico SHA-256 de un bloque de bytes o archivo."""
    return hashlib.sha256(data).hexdigest()


def leer_texto_resiliente(filepath: str) -> str:
    """Lee un archivo de texto probando secuencialmente UTF-8 con BOM, UTF-8 y Latin-1/CP1252."""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception:
            break
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def sanitizar_nombre_descarga(doc_name: str, version: int, ext_salida: str) -> str:
    """Genera un nombre de archivo normalizado y limpio para descargas sin dobles extensiones ni caracteres invalidos.
    Ejemplo: 'informe.docx', 2, '.md' -> 'informe_v2.md'
    """
    base_name = os.path.splitext(doc_name)[0]
    base_name = re.sub(r'\.(docx|pdf|pptx|xlsx|xls|txt|md|csv|png|jpg|jpeg|svg|webp)$', '', base_name, flags=re.IGNORECASE)
    base_name = re.sub(r'^v\d+[-_]', '', base_name, flags=re.IGNORECASE)
    base_name = re.sub(r'[\\/:*?"<>|]', '_', base_name)
    if not ext_salida.startswith('.'):
        ext_salida = '.' + ext_salida
    return f"{base_name}_v{version}{ext_salida}"


def generar_ficha_diagrama(
    image_filename: str,
    orig_rel_path: str = "",
    sha256_hash: str = "",
    caption: str = "",
    resumen: str = "",
    elementos: str = "",
    texto_ocr: str = "",
    categoria: str = "Topología y Arquitectura"
) -> str:
    """Genera una ficha técnica Markdown estructurada asociada a un diagrama o imagen gráfica."""
    nombre_limpio = os.path.splitext(os.path.basename(image_filename))[0].replace("_", " ").replace("-", " ").title()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_orig = orig_rel_path.replace("\\", "/") if orig_rel_path else f"assets/{image_filename}"
    orig_path_str = clean_orig
    hash_str = sha256_hash if sha256_hash else "N/A"
    caption_txt = caption.strip() if caption.strip() else f"Esquema visual de {nombre_limpio}"

    resumen_txt = resumen.strip() if resumen.strip() else f"Esquema visual correspondiente a {nombre_limpio}. Contiene especificaciones de topología, conectividad o procedimiento operativo."
    elementos_txt = elementos.strip() if elementos.strip() else "- Servidores y Nodos de Cómputo\n- Direccionamiento IP y Enlaces de Red\n- Interfaces de Integración"
    ocr_txt = texto_ocr.strip() if texto_ocr.strip() else f"[Indexación de Diagrama]: {nombre_limpio} (Ubicación: assets/{image_filename})"

    ficha_md = f"""# [FICHA TÉCNICA DE DIAGRAMA] {nombre_limpio}

## 1. Metadatos del Activo Gráfico
* **Archivo Binario:** `assets/{image_filename}`
* **Pie de Imagen (Caption):** {caption_txt}
* **Ruta de Origen:** `{orig_path_str}`
* **Firma SHA-256:** `{hash_str}`
* **Fecha de Ingesta:** `{fecha_hoy}`
* **Categoría:** `{categoria}`

---

## 2. Resumen y Contexto Técnico
{resumen_txt}

---

## 3. Elementos Técnicos Identificados (Indexables)
{elementos_txt}

---

## 4. Texto Extraído y Términos Clave
```text
{ocr_txt}
```
"""
    return ficha_md


def obtener_ruta_original(doc_name: str, md_content: str = "") -> str | None:
    """Localiza la ruta del archivo binario original asociado a un documento Markdown.
    Busca en data/docs/assets/, data/originals/, data/docs/ o analiza metadatos en el Markdown.
    """
    # 1. Si el archivo ya es un binario existente en data/docs/
    path_en_docs = os.path.join(DOCS_DIR, doc_name)
    ext_doc = os.path.splitext(doc_name)[1].lower()
    if ext_doc in OFFICE_EXTENSIONS + IMAGE_EXTENSIONS and os.path.exists(path_en_docs):
        return path_en_docs

    # 2. Si existe un archivo idéntico en data/originals/
    path_en_orig = os.path.join(ORIGINALS_DIR, doc_name)
    if os.path.exists(path_en_orig):
        return path_en_orig

    # 3. Si doc_name es .md, buscar versiones con otras extensiones
    base_name = os.path.splitext(doc_name)[0]
    base_name_clean = re.sub(r'^(DIAGRAMA__|DOC__)', '', base_name, flags=re.IGNORECASE)
    base_name_clean = re.sub(r'\.(png|jpg|jpeg|svg|webp|docx|pdf|xlsx|xls|pptx)$', '', base_name_clean, flags=re.IGNORECASE)

    # 3a. Buscar en assets/ para imágenes
    for ext_img in IMAGE_EXTENSIONS:
        candidatos = [
            os.path.join(ASSETS_DIR, f"{base_name}{ext_img}"),
            os.path.join(ASSETS_DIR, f"{base_name_clean}{ext_img}")
        ]
        for c in candidatos:
            if os.path.exists(c):
                return c

    # 3b. Buscar en data/originals/ con cualquier extensión soportada
    for ext_cand in OFFICE_EXTENSIONS + IMAGE_EXTENSIONS + TEXT_EXTENSIONS:
        candidatos = [
            os.path.join(ORIGINALS_DIR, f"{base_name}{ext_cand}"),
            os.path.join(ORIGINALS_DIR, f"{base_name_clean}{ext_cand}")
        ]
        for c in candidatos:
            if os.path.exists(c):
                return c

    # 3c. Buscar en data/docs/ con cualquier extensión
    for ext_cand in OFFICE_EXTENSIONS + IMAGE_EXTENSIONS:
        candidatos = [
            os.path.join(DOCS_DIR, f"{base_name}{ext_cand}"),
            os.path.join(DOCS_DIR, f"{base_name_clean}{ext_cand}")
        ]
        for c in candidatos:
            if os.path.exists(c):
                return c

    # 4. Extraer desde el contenido Markdown (regex para assets o ubicaciones origen)
    if md_content:
        # Buscar Archivo Binario en metadatos
        m_bin = re.search(r'\*\*Archivo Binario:\*\*\s*`([^`]+)`', md_content)
        if m_bin:
            rel_bin = m_bin.group(1).replace("/", os.sep)
            full_bin = os.path.join(DOCS_DIR, rel_bin) if not os.path.isabs(rel_bin) else rel_bin
            if os.path.exists(full_bin):
                return full_bin

        # Buscar tag de imagen Markdown si existiera: ![...](assets/...)
        m_img = re.search(r'!\[.*?\]\((assets/[^\)]+)\)', md_content)
        if m_img:
            rel_asset = m_img.group(1).replace("/", os.sep)
            full_asset = os.path.join(DOCS_DIR, rel_asset)
            if os.path.exists(full_asset):
                return full_asset

        # Buscar Ubicacion Origen
        m_orig = re.search(r'\*\*Ubicación Origen:\*\*\s*`([^`]+)`', md_content)
        if m_orig:
            orig_str = m_orig.group(1)
            cand_inbox = os.path.join(INBOX_DIR, orig_str)
            cand_orig = os.path.join(ORIGINALS_DIR, orig_str)
            if os.path.exists(cand_inbox):
                return cand_inbox
            if os.path.exists(cand_orig):
                return cand_orig
            if os.path.exists(orig_str):
                return orig_str

    return None


@st.cache_data(show_spinner=False)
def _cargar_documento_individual_cached(filepath: str, mtime: float) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    fname = os.path.basename(filepath)

    if ext in (".xlsx", ".xls"):
        return procesar_excel_limpio(filepath)
    elif ext in IMAGE_EXTENSIONS:
        asset_target = os.path.join(ASSETS_DIR, fname)
        if not os.path.exists(asset_target) and filepath != asset_target:
            import shutil
            shutil.copy2(filepath, asset_target)
        with open(filepath, "rb") as f:
            fhash = calcular_sha256(f.read())
        return generar_ficha_diagrama(image_filename=fname, orig_rel_path=filepath, sha256_hash=fhash)
    elif ext in (".md", ".txt", ".csv", ".json", ".sql", ".py"):
        return leer_texto_resiliente(filepath)
    else:
        try:
            from markitdown import MarkItDown
            md_engine = MarkItDown()
            res = md_engine.convert(filepath)
            return res.text_content
        except Exception:
            return leer_texto_resiliente(filepath)


def cargar_documento_individual(filepath: str) -> str:
    """Convierte un archivo individual al formato Markdown estructurado según su extensión con decodificación resiliente y cache por mtime."""
    mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else 0.0
    return _cargar_documento_individual_cached(filepath, mtime)


def cargar_documentos_locales(doc_store: dict, force: bool = False) -> dict:
    """Carga y sincroniza todos los documentos de data/docs/ en el almacén de memoria."""
    if os.path.exists(DOCS_DIR):
        if force:
            doc_store.clear()

        # 1. Cargar todos los archivos directos de data/docs/
        for doc_file in glob.glob(os.path.join(DOCS_DIR, "*.*")):
            fname = os.path.basename(doc_file)
            if fname not in doc_store:
                try:
                    doc_store[fname] = cargar_documento_individual(doc_file)
                except Exception:
                    pass

        # 2. Cargar imágenes de data/docs/assets/ generando su ficha técnica en memoria si no existe
        if os.path.exists(ASSETS_DIR):
            for asset_file in glob.glob(os.path.join(ASSETS_DIR, "*.*")):
                ext_a = os.path.splitext(asset_file)[1].lower()
                if ext_a in IMAGE_EXTENSIONS:
                    asset_name = os.path.basename(asset_file)
                    base_clean = os.path.splitext(asset_name)[0]
                    ficha_name = f"DIAGRAMA__{base_clean}.md"
                    if ficha_name not in doc_store:
                        try:
                            doc_store[ficha_name] = cargar_documento_individual(asset_file)
                        except Exception:
                            pass

    return doc_store

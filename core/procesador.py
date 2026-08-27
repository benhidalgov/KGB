import hashlib
import os
import re
import glob
import unicodedata
import base64
import zipfile
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


# Mapeo de acrónimos técnicos y marcas conocidas para formateo corporativo
ACRONIMOS_TECNICOS = {
    'cmdb': 'CMDB', 'jwt': 'JWT', 'ip': 'IP', 'san': 'SAN', 'wso2': 'WSO2',
    'hpe': 'HPE', 'ssl': 'SSL', 'tls': 'TLS', 'api': 'API', 'vm': 'VM',
    'drp': 'DRP', 'dns': 'DNS', 'ssh': 'SSH', 'http': 'HTTP', 'https': 'HTTPS',
    'cpu': 'CPU', 'ram': 'RAM', 'so': 'SO', 'cicd': 'CI/CD', 'vlan': 'VLAN',
    'dmz': 'DMZ', 'apm': 'APM', 'nsx': 'NSX', 'sql': 'SQL', 'csv': 'CSV',
    'pdf': 'PDF', 'av': 'AV', 'ha': 'HA', 'dc': 'DC', 'dr': 'DR', 'ad': 'AD',
    'lan': 'LAN', 'wan': 'WAN', 'vpn': 'VPN', 'l1': 'L1', 'l2': 'L2',
    'l3': 'L3', 'l4': 'L4', 'p1': 'P1', 'p2': 'P2', 'p3': 'P3',
    'balancer001': 'BALANCER001', 'purestorage': 'PureStorage',
    'vmware': 'VMware', 'vcloud': 'vCloud', 'redis': 'Redis',
    'nagios': 'Nagios', 'newrelic': 'NewRelic', 'postgresql': 'PostgreSQL',
    'mysql': 'MySQL', 'devops': 'DevOps'
}

CONECTORES_TITULO = {'de', 'del', 'la', 'las', 'el', 'los', 'y', 'en', 'para', 'por', 'con', 'a'}


def normalizar_nombre_archivo(nombre: str) -> str:
    """Normaliza un nombre de archivo a formato snake_case limpio y seguro para el sistema de archivos.
    Elimina acentos, espacios, caracteres conflictivos y dobles extensiones.
    Ejemplo: 'CMDB UNICARD v 1.1.xlsx' -> 'cmdb_unicard_v1_1.xlsx'
    """
    base, ext = os.path.splitext(nombre)
    base = re.sub(r'\.(docx|pdf|pptx|xlsx|xls|txt|md|csv|png|jpg|jpeg|svg|webp)$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'^v\d+[-_]', '', base, flags=re.IGNORECASE)
    base = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode('utf-8')
    base = re.sub(r'(?i)\bv\s*(\d+)[\.\s_-]+(\d+)\b', r'v\1_\2', base)
    base = re.sub(r'[^a-zA-Z0-9_-]', '_', base)
    base = re.sub(r'_+', '_', base).strip('_').lower()
    if not base:
        base = "archivo_sin_nombre"
    return f"{base}{ext.lower()}"


def normalizar_titulo_display(nombre_o_doc: str) -> str:
    """Convierte nombres técnicos de archivo en títulos corporativos limpios y legibles.
    Preserva siglas y marcas registradas de arquitectura (CMDB, SAN, WSO2, etc.).
    Ejemplo: 'almacenamiento_san_purestorage.md' -> 'Almacenamiento SAN PureStorage'
    """
    raw = str(nombre_o_doc).replace('DIAGRAMA__', '').replace('DOC__', '')
    base, _ = os.path.splitext(raw)
    base = re.sub(r'\.(docx|pdf|pptx|xlsx|xls|txt|md|csv|png|jpg|jpeg|svg|webp)$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'^v\d+[-_]', '', base, flags=re.IGNORECASE)
    base = re.sub(r'^\d+(\.\d+)+[-_]?[a-zA-Z0-9]+[-_]', '', base)
    base = re.sub(r'(?i)\bv[_ ]*(\d+)[_ ]+(\d+)\b', r'v\1.\2', base)
    base = re.sub(r'(?i)\bv[_ ]*(\d+)\b', r'v\1', base)
    texto = base.replace('_', ' ').replace('-', ' ')
    texto = re.sub(r'\s+', ' ', texto).strip()

    if not texto:
        return str(nombre_o_doc)

    palabras = texto.split()
    palabras_formateadas = []
    for i, p in enumerate(palabras):
        p_low = p.lower()
        if p_low in ACRONIMOS_TECNICOS:
            palabras_formateadas.append(ACRONIMOS_TECNICOS[p_low])
        elif p_low in CONECTORES_TITULO and i > 0:
            palabras_formateadas.append(p_low)
        elif re.match(r'^v\d+(\.\d+)*$', p_low):
            palabras_formateadas.append(p_low)
        elif p.isupper() and len(p) <= 4:
            palabras_formateadas.append(p)
        else:
            palabras_formateadas.append(p.capitalize())

    return ' '.join(palabras_formateadas)


def sanitizar_nombre_descarga(doc_name: str, version: int, ext_salida: str) -> str:
    """Genera un nombre de archivo normalizado y limpio para descargas sin dobles extensiones ni caracteres invalidos.
    Ejemplo: 'informe.docx', 2, '.md' -> 'informe_v2.md'
    """
    base_limpia = normalizar_nombre_archivo(doc_name)
    base_name = os.path.splitext(base_limpia)[0]
    base_name = re.sub(r'_v\d+$', '', base_name)
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

## 2. Esquema del Diagrama
![{caption_txt}](assets/{image_filename})

---

## 3. Resumen y Contexto Técnico
{resumen_txt}

---

## 4. Elementos Técnicos Identificados (Indexables)
{elementos_txt}

---

## 5. Texto Extraído y Términos Clave
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
            # keep_data_uris=False evita inyectar megabytes de cadenas Base64 en memoria protegiendo el navegador
            res = md_engine.convert(filepath, keep_data_uris=False)
            return res.text_content
        except Exception:
            return leer_texto_resiliente(filepath)


def extraer_imagenes_de_docx(docx_path: str) -> list[str]:
    """Extrae las imágenes binarias de un archivo .docx empaquetado (limitadas en tamaño para no saturar memoria)."""
    imgs = []
    if not (docx_path and os.path.exists(docx_path) and docx_path.lower().endswith(".docx")):
        return imgs
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            media_files = [f for f in z.namelist() if f.startswith("word/media/")]
            def sort_key(name):
                nums = re.findall(r"\d+", os.path.basename(name))
                return int(nums[0]) if nums else 9999
            media_files.sort(key=sort_key)
            for mf in media_files:
                ext = os.path.splitext(mf)[1].lower().replace(".", "")
                if ext in ("png", "jpg", "jpeg", "svg", "webp"):
                    info = z.getinfo(mf)
                    # Omitir imagenes gigantes (>400 KB) para evitar bloqueos del DOM en Streamlit
                    if info.file_size > 400 * 1024:
                        continue
                    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
                    data = z.read(mf)
                    b64 = base64.b64encode(data).decode("utf-8")
                    imgs.append(f"data:image/{mime};base64,{b64}")
    except Exception:
        pass
    return imgs


def resolver_ruta_imagen_a_base64(src_path: str, ruta_original: str | None = None) -> str:
    """Resuelve rutas de imagen locales a Data URI base64 seguro limitando el tamaño a 400 KB para proteger el navegador."""
    if not src_path:
        return ""
    if src_path.startswith("data:image/") and not src_path.endswith("..."):
        return src_path

    clean_src = src_path.strip().replace("/", os.sep).replace("\\", os.sep)
    fname = os.path.basename(clean_src)
    candidatos = [
        src_path,
        os.path.join(DOCS_DIR, clean_src),
        os.path.join(DOCS_DIR, "assets", fname),
        os.path.join(ASSETS_DIR, fname),
        os.path.join(ORIGINALS_DIR, fname),
        os.path.join(DOCS_DIR, fname),
    ]
    if ruta_original and os.path.exists(ruta_original):
        candidatos.append(os.path.join(os.path.dirname(ruta_original), fname))
        candidatos.append(os.path.join(os.path.dirname(ruta_original), clean_src))

    for cand in candidatos:
        if os.path.exists(cand) and os.path.isfile(cand):
            # Proteger rendimiento: si la imagen supera los 400 KB no inyectarla como base64 en el DOM
            if os.path.getsize(cand) > 400 * 1024:
                return ""
            ext = os.path.splitext(cand)[1].lower().replace('.', '')
            mime = 'jpeg' if ext in ('jpg', 'jpeg') else 'svg+xml' if ext == 'svg' else ext
            try:
                with open(cand, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/{mime};base64,{b64}"
            except Exception:
                pass
    return ""


def preparar_markdown_con_imagenes(md_content: str, doc_name: str = "", ruta_original: str | None = None) -> str:
    """Prepara el contenido Markdown para la pestaña de Vista Formateada sin sobrecargar la memoria del navegador.
    Mantiene el texto ágil e inyecta únicamente diagramas o esquemas de tamaño óptimo.
    """
    if not md_content:
        return ""
    res = md_content

    # 1. Reemplazar referencias truncadas de base64 por insignias informativas ligeras
    res = re.sub(
        r'!\[([^\]]*)\]\((?:data:image/[^;]+;base64\.\.\.)\)',
        r'<span class="badge-tag" style="margin: 4px 0; display: inline-block;">[Gráfico / Diagrama en Documento Original]</span>',
        res
    )

    # 2. Si es ficha técnica de diagrama y no posee tag de imagen visible, inyectar el esquema destacado
    tiene_tag_img = bool(re.search(r'!\[.*?\]\(.*?\)|<img\s+[^>]*src=', res))
    if not tiene_tag_img:
        m_bin = re.search(r'\*\*Archivo Binario:\*\*\s*`([^`]+)`', res)
        img_ref = m_bin.group(1) if m_bin else None
        if not img_ref and ruta_original and any(ruta_original.lower().endswith(e) for e in IMAGE_EXTENSIONS):
            img_ref = ruta_original

        if img_ref:
            b64_uri = resolver_ruta_imagen_a_base64(img_ref, ruta_original=ruta_original)
            if b64_uri:
                m_cap = re.search(r'\*\*Pie de Imagen \(Caption\):\*\*\s*(.+)', res)
                caption = m_cap.group(1).strip() if m_cap else 'Esquema visual de arquitectura'
                card_img = f"""
<div style="text-align: center; margin: 16px 0 22px 0; padding: 14px; background: rgba(128,128,128,0.04); border: 1px solid rgba(128,128,128,0.18); border-radius: 8px;">
    <img src="{b64_uri}" alt="{caption}" style="max-width: 100%; max-height: 600px; height: auto; border-radius: 6px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);" />
    <div style="font-size: 0.8rem; font-weight: 500; opacity: 0.75; margin-top: 8px;">{caption}</div>
</div>
"""
                partes = res.split('\n---\n', 1)
                if len(partes) == 2:
                    res = partes[0] + '\n---\n' + card_img + '\n' + partes[1]
                else:
                    res = card_img + '\n' + res

    # 3. Resolver rutas relativas o nombres locales en etiquetas ![alt](src)
    def _sub_md_img(m):
        alt = m.group(1)
        src = m.group(2)
        if src.startswith("data:image/") and not src.endswith("..."):
            return m.group(0)
        b64 = resolver_ruta_imagen_a_base64(src, ruta_original=ruta_original)
        if b64:
            return f"![{alt}]({b64})"
        return m.group(0)

    res = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _sub_md_img, res)

    # 4. Resolver etiquetas HTML <img src="...">
    def _sub_html_img(m):
        full_tag = m.group(0)
        src = m.group(1)
        if src.startswith("data:image/") and not src.endswith("..."):
            return full_tag
        b64 = resolver_ruta_imagen_a_base64(src, ruta_original=ruta_original)
        if b64:
            return full_tag.replace(src, b64)
        return full_tag

    res = re.sub(r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', _sub_html_img, res)

    return res


def cargar_documento_individual(filepath: str) -> str:
    """Convierte un archivo individual al formato Markdown estructurado según su extensión con decodificación resiliente y cache por mtime."""
    mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else 0.0
    return _cargar_documento_individual_cached(filepath, mtime)


def limpiar_cache_documentos():
    """Limpia la caché en memoria de Streamlit para asegurar la recarga fresca de documentos."""
    _cargar_documento_individual_cached.clear()


def cargar_documentos_locales(doc_store: dict, force: bool = False) -> dict:
    """Carga y sincroniza todos los documentos de data/docs/ en el almacén de memoria."""
    if os.path.exists(DOCS_DIR):
        if force:
            _cargar_documento_individual_cached.clear()
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

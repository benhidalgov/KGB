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
SUPPORTED_EXTENSIONS = OFFICE_EXTENSIONS + TEXT_EXTENSIONS + IMAGE_EXTENSIONS

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


def calcular_sha256(data: bytes) -> str:
    """Calcula el hash criptográfico SHA-256 de un bloque de bytes o archivo."""
    return hashlib.sha256(data).hexdigest()


def leer_texto_resiliente(filepath: str) -> str:
    """Lee un archivo de texto probando secuencialmente codificaciones comunes."""
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


def normalizar_nombre_archivo(nombre: str) -> str:
    """Normaliza un nombre de archivo a snake_case seguro para el sistema de archivos."""
    base, ext = os.path.splitext(nombre)
    base = re.sub(r'\.(docx|pdf|pptx|xlsx|xls|txt|md|csv|png|jpg|jpeg|svg|webp)$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'^v\d+[-_]', '', base, flags=re.IGNORECASE)
    base = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode('utf-8')
    base = re.sub(r'(?i)\bv\s*(\d+)[\.\s_-]+(\d+)\b', r'v\1_\2', base)
    base = re.sub(r'[^a-zA-Z0-9_-]', '_', base)
    base = re.sub(r'_+', '_', base).strip('_').lower()
    return f"{base or 'archivo_sin_nombre'}{ext.lower()}"


def normalizar_titulo_display(nombre_o_doc: str) -> str:
    """Convierte nombres técnicos de archivo en títulos corporativos limpios preservando acrónimos."""
    raw = str(nombre_o_doc).replace('DIAGRAMA__', '').replace('DOC__', '')
    base, _ = os.path.splitext(raw)
    base = re.sub(r'\.(docx|pdf|pptx|xlsx|xls|txt|md|csv|png|jpg|jpeg|svg|webp)$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'^v\d+[-_]', '', base, flags=re.IGNORECASE)
    base = re.sub(r'^\d+(\.\d+)+[-_]?[a-zA-Z0-9]+[-_]', '', base)
    base = re.sub(r'(?i)\bv[_ ]*(\d+)[_ ]+(\d+)\b', r'v\1.\2', base)
    base = re.sub(r'(?i)\bv[_ ]*(\d+)\b', r'v\1', base)
    texto = re.sub(r'\s+', ' ', base.replace('_', ' ').replace('-', ' ')).strip()
    if not texto:
        return str(nombre_o_doc)

    palabras = []
    for i, p in enumerate(texto.split()):
        p_low = p.lower()
        if p_low in ACRONIMOS_TECNICOS:
            palabras.append(ACRONIMOS_TECNICOS[p_low])
        elif p_low in CONECTORES_TITULO and i > 0:
            palabras.append(p_low)
        elif re.match(r'^v\d+(\.\d+)*$', p_low) or (p.isupper() and len(p) <= 4):
            palabras.append(p)
        else:
            palabras.append(p.capitalize())
    return ' '.join(palabras)


def sanitizar_nombre_descarga(doc_name: str, version: int, ext_salida: str) -> str:
    """Genera un nombre de archivo limpio para descargas sin dobles extensiones."""
    base = os.path.splitext(normalizar_nombre_archivo(doc_name))[0]
    base = re.sub(r'_v\d+$', '', base)
    ext = ext_salida if ext_salida.startswith('.') else f".{ext_salida}"
    return f"{base}_v{version}{ext}"


def generar_ficha_diagrama(image_filename: str, orig_rel_path: str = "", sha256_hash: str = "", caption: str = "", resumen: str = "", elementos: str = "", texto_ocr: str = "", categoria: str = "Topología y Arquitectura") -> str:
    """Genera una ficha técnica Markdown estructurada asociada a un diagrama o imagen gráfica."""
    nombre_limpio = os.path.splitext(os.path.basename(image_filename))[0].replace("_", " ").replace("-", " ").title()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_orig = orig_rel_path.replace("\\", "/") if orig_rel_path else f"assets/{image_filename}"
    caption_txt = caption.strip() or f"Esquema visual de {nombre_limpio}"
    resumen_txt = resumen.strip() or f"Esquema visual correspondiente a {nombre_limpio}. Contiene especificaciones de topología, conectividad o procedimiento operativo."
    elementos_txt = elementos.strip() or "- Servidores y Nodos de Cómputo\n- Direccionamiento IP y Enlaces de Red\n- Interfaces de Integración"
    ocr_txt = texto_ocr.strip() or f"[Indexación de Diagrama]: {nombre_limpio} (Ubicación: assets/{image_filename})"

    return f"""# [FICHA TÉCNICA DE DIAGRAMA] {nombre_limpio}

## 1. Metadatos del Activo Gráfico
* **Archivo Binario:** `assets/{image_filename}`
* **Pie de Imagen (Caption):** {caption_txt}
* **Ruta de Origen:** `{clean_orig}`
* **Firma SHA-256:** `{sha256_hash or 'N/A'}`
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


def obtener_ruta_original(doc_name: str, md_content: str = "") -> str | None:
    """Localiza la ruta del archivo binario original asociado a un documento Markdown."""
    # 1. Chequeo directo en DOCS_DIR y ORIGINALS_DIR
    for base_dir in (DOCS_DIR, ORIGINALS_DIR):
        p = os.path.join(base_dir, doc_name)
        if os.path.exists(p) and os.path.isfile(p):
            return p

    base = os.path.splitext(doc_name)[0]
    base_clean = re.sub(r'\.(png|jpg|jpeg|svg|webp|docx|pdf|xlsx|xls|pptx)$', '', re.sub(r'^(DIAGRAMA__|DOC__)', '', base, flags=re.IGNORECASE), flags=re.IGNORECASE)

    # 2. Búsqueda por extensión candidata en assets, originals y docs
    rutas_busqueda = [
        (ASSETS_DIR, IMAGE_EXTENSIONS),
        (ORIGINALS_DIR, SUPPORTED_EXTENSIONS),
        (DOCS_DIR, OFFICE_EXTENSIONS + IMAGE_EXTENSIONS),
    ]
    for dir_path, exts in rutas_busqueda:
        for b_name in (base, base_clean):
            for ext in exts:
                cand = os.path.join(dir_path, f"{b_name}{ext}")
                if os.path.exists(cand):
                    return cand

    # 3. Extracción de metadatos desde el Markdown
    if md_content:
        for pattern in (r'\*\*Archivo Binario:\*\*\s*`([^`]+)`', r'!\[.*?\]\((assets/[^\)]+)\)'):
            m = re.search(pattern, md_content)
            if m:
                rel = m.group(1).replace("/", os.sep)
                cand = os.path.join(DOCS_DIR, rel) if not os.path.isabs(rel) else rel
                if os.path.exists(cand):
                    return cand

        m_orig = re.search(r'\*\*Ubicación Origen:\*\*\s*`([^`]+)`', md_content)
        if m_orig:
            orig_s = m_orig.group(1)
            for cand in (os.path.join(INBOX_DIR, orig_s), os.path.join(ORIGINALS_DIR, orig_s), orig_s):
                if os.path.exists(cand):
                    return cand

    return None


@st.cache_data(show_spinner=False)
def _cargar_documento_individual_cached(filepath: str, mtime: float) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    fname = os.path.basename(filepath)

    if ext in (".xlsx", ".xls"):
        return procesar_excel_limpio(filepath)
    if ext in IMAGE_EXTENSIONS:
        target = os.path.join(ASSETS_DIR, fname)
        if not os.path.exists(target) and filepath != target:
            import shutil
            shutil.copy2(filepath, target)
        with open(filepath, "rb") as f:
            fhash = calcular_sha256(f.read())
        return generar_ficha_diagrama(image_filename=fname, orig_rel_path=filepath, sha256_hash=fhash)
    if ext in (".md", ".txt", ".csv", ".json", ".sql", ".py"):
        return leer_texto_resiliente(filepath)

    try:
        from markitdown import MarkItDown
        return MarkItDown().convert(filepath, keep_data_uris=False).text_content or ""
    except Exception:
        return leer_texto_resiliente(filepath)


def extraer_imagenes_de_docx(docx_path: str) -> list[str]:
    """Extrae las imágenes binarias de un archivo .docx empaquetado (limitadas a 400 KB)."""
    imgs = []
    if not (docx_path and os.path.exists(docx_path) and docx_path.lower().endswith(".docx")):
        return imgs
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            media = sorted([f for f in z.namelist() if f.startswith("word/media/")])
            for mf in media:
                ext = os.path.splitext(mf)[1].lower().replace(".", "")
                if ext in ("png", "jpg", "jpeg", "svg", "webp") and z.getinfo(mf).file_size <= 400 * 1024:
                    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
                    b64 = base64.b64encode(z.read(mf)).decode("utf-8")
                    imgs.append(f"data:image/{mime};base64,{b64}")
    except Exception:
        pass
    return imgs


def resolver_ruta_imagen_a_base64(src_path: str, ruta_original: str | None = None) -> str:
    """Resuelve rutas de imagen locales a Data URI base64 seguro limitando a 400 KB."""
    if not src_path or (src_path.startswith("data:image/") and not src_path.endswith("...")):
        return src_path or ""

    clean = src_path.strip().replace("/", os.sep).replace("\\", os.sep)
    fname = os.path.basename(clean)
    candidatos = [src_path, os.path.join(DOCS_DIR, clean), os.path.join(ASSETS_DIR, fname), os.path.join(ORIGINALS_DIR, fname), os.path.join(DOCS_DIR, fname)]
    if ruta_original and os.path.exists(ruta_original):
        candidatos.extend([os.path.join(os.path.dirname(ruta_original), fname), os.path.join(os.path.dirname(ruta_original), clean)])

    for cand in candidatos:
        if os.path.exists(cand) and os.path.isfile(cand) and os.path.getsize(cand) <= 400 * 1024:
            ext = os.path.splitext(cand)[1].lower().replace('.', '')
            mime = 'jpeg' if ext in ('jpg', 'jpeg') else 'svg+xml' if ext == 'svg' else ext
            try:
                with open(cand, "rb") as f:
                    return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"
            except Exception:
                pass
    return ""


def preparar_markdown_con_imagenes(md_content: str, doc_name: str = "", ruta_original: str | None = None) -> str:
    """Prepara el contenido Markdown para la pestaña de Vista Formateada protegiendo el DOM."""
    if not md_content:
        return ""
    res = re.sub(r'!\[([^\]]*)\]\((?:data:image/[^;]+;base64\.\.\.)\)', r'<span class="badge-tag" style="margin: 4px 0; display: inline-block;">[Gráfico / Diagrama en Documento Original]</span>', md_content)

    if not re.search(r'!\[.*?\]\(.*?\)|<img\s+[^>]*src=', res):
        m_bin = re.search(r'\*\*Archivo Binario:\*\*\s*`([^`]+)`', res)
        img_ref = m_bin.group(1) if m_bin else (ruta_original if (ruta_original and any(ruta_original.lower().endswith(e) for e in IMAGE_EXTENSIONS)) else None)
        if img_ref:
            b64 = resolver_ruta_imagen_a_base64(img_ref, ruta_original=ruta_original)
            if b64:
                m_cap = re.search(r'\*\*Pie de Imagen \(Caption\):\*\*\s*(.+)', res)
                caption = m_cap.group(1).strip() if m_cap else 'Esquema visual de arquitectura'
                card = f'\n<div style="text-align:center;margin:16px 0 22px;padding:14px;background:rgba(128,128,128,0.04);border:1px solid rgba(128,128,128,0.18);border-radius:8px;"><img src="{b64}" alt="{caption}" style="max-width:100%;max-height:600px;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,0.12);" /><div style="font-size:0.8rem;font-weight:500;opacity:0.75;margin-top:8px;">{caption}</div></div>\n'
                partes = res.split('\n---\n', 1)
                res = f"{partes[0]}\n---\n{card}\n{partes[1]}" if len(partes) == 2 else f"{card}\n{res}"

    def _sub_img(m):
        alt, src = m.group(1), m.group(2)
        if src.startswith("data:image/") and not src.endswith("..."):
            return m.group(0)
        b64 = resolver_ruta_imagen_a_base64(src, ruta_original=ruta_original)
        return f"![{alt}]({b64})" if b64 else m.group(0)

    res = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _sub_img, res)
    return res


def cargar_documento_individual(filepath: str) -> str:
    """Convierte un archivo individual al formato Markdown estructurado con cache por mtime."""
    mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else 0.0
    return _cargar_documento_individual_cached(filepath, mtime)


def limpiar_cache_documentos():
    """Limpia la caché en memoria de Streamlit para asegurar la recarga fresca de documentos."""
    _cargar_documento_individual_cached.clear()


def cargar_documentos_locales(doc_store: dict, force: bool = False) -> dict:
    """Carga y sincroniza todos los documentos de data/docs/ en el almacén de memoria."""
    if os.path.exists(DOCS_DIR):
        if force:
            limpiar_cache_documentos()
            doc_store.clear()

        for doc_file in glob.glob(os.path.join(DOCS_DIR, "*.*")):
            fname = os.path.basename(doc_file)
            if fname not in doc_store:
                try:
                    doc_store[fname] = cargar_documento_individual(doc_file)
                except Exception:
                    pass

        if os.path.exists(ASSETS_DIR):
            for asset_file in glob.glob(os.path.join(ASSETS_DIR, "*.*")):
                if os.path.splitext(asset_file)[1].lower() in IMAGE_EXTENSIONS:
                    ficha_name = f"DIAGRAMA__{os.path.splitext(os.path.basename(asset_file))[0]}.md"
                    if ficha_name not in doc_store:
                        try:
                            doc_store[ficha_name] = cargar_documento_individual(asset_file)
                        except Exception:
                            pass
    return doc_store

import hashlib
import os
import re
import glob
from excel_cleaner import procesar_excel_limpio
from core.configuracion import DOCS_DIR


def calcular_sha256(data: bytes) -> str:
    """Calcula el hash criptografico SHA-256 de un bloque de bytes o archivo."""
    return hashlib.sha256(data).hexdigest()


def sanitizar_nombre_descarga(doc_name: str, version: int, ext_salida: str) -> str:
    """Genera un nombre de archivo normalizado y limpio para descargas sin dobles extensiones.
    Ejemplo: 'informe.docx', 2, '.md' -> 'informe_v2.md'
    """
    base_name = os.path.splitext(doc_name)[0]
    base_name = re.sub(r'\.(docx|pdf|pptx|xlsx|xls|txt|md|csv)$', '', base_name, flags=re.IGNORECASE)
    base_name = re.sub(r'^v\d+[-_]', '', base_name, flags=re.IGNORECASE)
    if not ext_salida.startswith('.'):
        ext_salida = '.' + ext_salida
    return f"{base_name}_v{version}{ext_salida}"


def cargar_documento_individual(filepath: str) -> str:
    """Convierte un archivo individual al formato Markdown estructurado segun su extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".xlsx", ".xls"):
        return procesar_excel_limpio(filepath)
    elif ext in (".md", ".txt", ".csv"):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        try:
            from markitdown import MarkItDown
            md_engine = MarkItDown()
            res = md_engine.convert(filepath)
            return res.text_content
        except Exception:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()


def cargar_documentos_locales(doc_store: dict, force: bool = False) -> dict:
    """Carga y sincroniza todos los documentos de data/docs/ en el almacén de memoria."""
    if os.path.exists(DOCS_DIR):
        if force:
            doc_store.clear()
        for doc_file in glob.glob(os.path.join(DOCS_DIR, "*.*")):
            fname = os.path.basename(doc_file)
            if fname not in doc_store:
                try:
                    doc_store[fname] = cargar_documento_individual(doc_file)
                except Exception:
                    pass
    return doc_store

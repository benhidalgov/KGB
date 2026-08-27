import os
import glob
import time
import hashlib
import json
import shutil
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from markitdown import MarkItDown
from excel_cleaner import procesar_excel_limpio
from core.configuracion import (
    DOCS_DIR,
    ASSETS_DIR,
    ORIGINALS_DIR,
    INBOX_DIR,
    MANIFEST_PATH,
)
from core.procesador import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    generar_ficha_diagrama,
    normalizar_nombre_archivo,
)

INPUT_DIR = INBOX_DIR
OUTPUT_DIR = DOCS_DIR


def calcular_hash_archivo(filepath: str) -> str:
    """Calcula el hash SHA-256 de un archivo en disco."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def cargar_manifiesto() -> dict:
    """Carga el manifiesto de ingesta inmutable."""
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_manifiesto(manifest: dict):
    """Guarda el estado del manifiesto de ingesta."""
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def procesar_un_archivo(fpath: str, rel_path: str, md_engine: MarkItDown) -> tuple[str, bool, str]:
    """Procesa un archivo individual (documento u activo gráfico) y genera su versión Markdown."""
    fname = os.path.basename(fpath)
    ext = os.path.splitext(fname)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return rel_path, False, f'Extension {ext} no soportada.'

    try:
        # Asegurar copia en data/originals/ con nombre normalizado
        clean_rel = rel_path.replace(os.sep, "__").replace("/", "__")
        orig_target_name = normalizar_nombre_archivo(clean_rel)
        orig_target_path = os.path.join(ORIGINALS_DIR, orig_target_name)
        if not os.path.exists(orig_target_path) or fpath != orig_target_path:
            shutil.copy2(fpath, orig_target_path)

        # 1. Caso de Activos Gráficos / Diagramas
        if ext in IMAGE_EXTENSIONS:
            norm_fname = normalizar_nombre_archivo(fname)
            asset_target = os.path.join(ASSETS_DIR, norm_fname)
            if not os.path.exists(asset_target) or fpath != asset_target:
                shutil.copy2(fpath, asset_target)

            fhash = calcular_hash_archivo(fpath)
            out_name = os.path.splitext(orig_target_name)[0] + '.md'
            out_path = os.path.join(OUTPUT_DIR, out_name)

            md_content = generar_ficha_diagrama(
                image_filename=norm_fname,
                orig_rel_path=rel_path,
                sha256_hash=fhash,
                categoria=os.path.dirname(rel_path) or "General / Raiz"
            )

            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(md_content)

            return rel_path, True, f'Diagrama ingestado y ficha generada en {out_name}'

        # 2. Caso de Libros Excel
        elif ext in ('.xlsx', '.xls'):
            md_content = procesar_excel_limpio(fpath)

        # 3. Caso de Documentos Ofimáticos / PDFs / Markdown
        elif ext in ('.md', '.txt', '.csv'):
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                md_content = f.read()
        else:
            resultado = md_engine.convert(fpath, keep_data_uris=False)
            md_content = resultado.text_content or ""
            if not md_content.strip() and ext == '.pdf':
                md_content = "*Nota: Documento PDF compuesto por páginas escaneadas o imágenes sin capa de texto incrustada. Visualice el archivo original en alta resolución mediante el Visor Lado a Lado.*"

        out_name = os.path.splitext(orig_target_name)[0] + '.md'
        out_path = os.path.join(OUTPUT_DIR, out_name)

        carpeta_origen = os.path.dirname(rel_path) or "Raiz"
        encabezado = f"""# Documento Técnico: {fname}
* **Ubicación Origen:** `{rel_path}`
* **Categoría / Carpeta:** `{carpeta_origen}`
* **Archivo Original:** `data/originals/{orig_target_name}`

---

"""
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(encabezado + md_content)

        return rel_path, True, f'Convertido exitosamente ({len(md_content)} caracteres)'
    except Exception as e:
        return rel_path, False, f'Error al procesar: {str(e)}'


def ejecutar_conversion_masiva(directorio_origen: str = INPUT_DIR, max_workers: int = 4):
    """Ejecuta la ingesta y conversión masiva en paralelo."""
    for d in [directorio_origen, OUTPUT_DIR, ASSETS_DIR, ORIGINALS_DIR]:
        os.makedirs(d, exist_ok=True)

    manifiesto = cargar_manifiesto()
    md_engine = MarkItDown()

    archivos_a_procesar = []
    for root, _, files in os.walk(directorio_origen):
        for f in files:
            # Omitir archivos temporales de bloqueo de Office (~$) y ocultos/sistema
            if f.startswith("~$") or f.startswith(".") or f.lower() in ("thumbs.db", "desktop.ini"):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                fpath = os.path.join(root, f)
                rel_path = os.path.relpath(fpath, directorio_origen)
                fhash = calcular_hash_archivo(fpath)

                # Inmutabilidad por ruta relativa + hash
                if manifiesto.get(rel_path) == fhash:
                    continue
                archivos_a_procesar.append((fpath, rel_path, fhash))

    if not archivos_a_procesar:
        print(f'No hay archivos nuevos o modificados para procesar en "{directorio_origen}".')
        return

    print(
        f'Iniciando conversion masiva de {len(archivos_a_procesar)} archivo(s) desde "{directorio_origen}" con {max_workers} hilos...')
    t_inicio = time.time()

    exitosos = 0
    errores = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {
            executor.submit(procesar_un_archivo, fpath, rel_path, md_engine): (rel_path, fhash)
            for fpath, rel_path, fhash in archivos_a_procesar
        }

        for future in as_completed(futuros):
            rel_path, fhash = futuros[future]
            item_id, ok, mensaje = future.result()
            if ok:
                exitosos += 1
                manifiesto[rel_path] = fhash
                print(f'[OK] {item_id}: {mensaje}')
            else:
                errores += 1
                print(f'[ERROR] {item_id}: {mensaje}')

    guardar_manifiesto(manifiesto)
    t_total = time.time() - t_inicio
    print(
        f'\nProceso completado en {t_total:.2f} segundos. Exitosos: {exitosos}, Errores: {errores}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Procesamiento masivo de documentos e ingesta.")
    parser.add_argument("--origen", "-o", default=INPUT_DIR, help="Carpeta de origen o unidad de red (ej. Z:\\ o data/inbox)")
    parser.add_argument("--workers", "-w", type=int, default=4, help="Cantidad de hilos concurrentes")
    args = parser.parse_args()

    ejecutar_conversion_masiva(directorio_origen=args.origen, max_workers=args.workers)

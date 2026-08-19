import os
import glob
import time
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from markitdown import MarkItDown

INPUT_DIR = os.path.join('data', 'inbox')
OUTPUT_DIR = os.path.join('data', 'docs')
MANIFEST_PATH = os.path.join('data', 'ingestion_manifest.json')

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.xlsx',
                        '.xls', '.pptx', '.txt', '.csv', '.md'}


def calcular_hash_archivo(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def cargar_manifiesto() -> dict:
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_manifiesto(manifest: dict):
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


import argparse
from excel_cleaner import procesar_excel_limpio

def procesar_un_archivo(fpath: str, rel_path: str, md_engine: MarkItDown) -> tuple[str, bool, str]:
    fname = os.path.basename(fpath)
    ext = os.path.splitext(fname)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return rel_path, False, f'Extension {ext} no soportada.'

    try:
        if ext in ('.xlsx', '.xls'):
            md_content = procesar_excel_limpio(fpath)
        else:
            resultado = md_engine.convert(fpath)
            md_content = resultado.text_content


        # Normalizar nombre de salida usando la ruta relativa para evitar colisiones
        # Ej: "Redes/Cisco/manual.docx" -> "Redes__Cisco__manual.md"
        clean_rel = rel_path.replace(os.sep, "__").replace("/", "__")
        out_name = os.path.splitext(clean_rel)[0] + '.md'
        out_path = os.path.join(OUTPUT_DIR, out_name)

        # Agregar encabezado con metadatos del origen
        carpeta_origen = os.path.dirname(rel_path) or "Raiz"
        encabezado = f"""# Documento Técnico: {fname}
* **Ubicación Origen:** `{rel_path}`
* **Categoría / Carpeta:** `{carpeta_origen}`

---

"""
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(encabezado + md_content)

        return rel_path, True, f'Convertido exitosamente ({len(md_content)} caracteres)'
    except Exception as e:
        return rel_path, False, f'Error al procesar: {str(e)}'


def ejecutar_conversion_masiva(directorio_origen: str = INPUT_DIR, max_workers: int = 4):
    if not os.path.exists(directorio_origen):
        os.makedirs(directorio_origen, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    manifiesto = cargar_manifiesto()
    md_engine = MarkItDown()

    archivos_a_procesar = []
    for root, _, files in os.walk(directorio_origen):
        for f in files:
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


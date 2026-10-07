"""Auto-verificacion del visor: nunca debe tratar como imagen un archivo que no lo es.

Cubre el fallo que rompia la pagina completa con un diagrama (una ficha
Markdown pasada a st.image provocaba PIL.UnidentifiedImageError).

Ejecutar:  python tests/check_visor_imagenes.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.procesador as proc
import core.visor as visor
from core.configuracion import APP_DIR

BASE_PRUEBAS = os.path.join(APP_DIR, ".tmp_check_visor")
DOCS = os.path.join(BASE_PRUEBAS, "docs")
ASSETS = os.path.join(BASE_PRUEBAS, "assets")
ORIGINALS = os.path.join(BASE_PRUEBAS, "originals")
SVG_VALIDO = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'


def _preparar() -> str:
    shutil.rmtree(BASE_PRUEBAS, ignore_errors=True)
    for carpeta in (DOCS, ASSETS, ORIGINALS):
        os.makedirs(carpeta, exist_ok=True)

    from PIL import Image
    ruta_png = os.path.join(ASSETS, "diagrama.png")
    Image.new("RGB", (6, 6), (99, 102, 241)).save(ruta_png)

    with open(os.path.join(ASSETS, "roto.png"), "w", encoding="utf-8") as f:
        f.write("esto no es una imagen")
    with open(os.path.join(ASSETS, "vector.svg"), "w", encoding="utf-8") as f:
        f.write(SVG_VALIDO)
    with open(os.path.join(ASSETS, "falso.svg"), "w", encoding="utf-8") as f:
        f.write("no soy un svg")

    with open(os.path.join(DOCS, "DIAGRAMA__diagrama.md"), "w", encoding="utf-8") as f:
        f.write("# Diagrama de prueba\n\n* **Archivo Binario:** `diagrama.png`\n")
    with open(os.path.join(DOCS, "DIAGRAMA__huerfano.md"), "w", encoding="utf-8") as f:
        f.write("# Diagrama sin imagen\n\n* **Archivo Binario:** `no_existe.png`\n")
    with open(os.path.join(DOCS, "notas.md"), "w", encoding="utf-8") as f:
        f.write("# Notas sin archivo binario\n")
    with open(os.path.join(DOCS, "informe.pdf"), "w", encoding="utf-8") as f:
        f.write("%PDF-1.4 simulado")
    with open(os.path.join(DOCS, "datos.csv"), "w", encoding="utf-8") as f:
        f.write("a,b\n1,2\n")
    return ruta_png


def check_deteccion_de_imagenes(ruta_png: str):
    """Solo un archivo cuyo contenido es una imagen real debe considerarse visualizable."""
    assert visor.es_imagen_visualizable(ruta_png), "un PNG real debe ser visualizable"
    assert visor.es_imagen_visualizable(os.path.join(ASSETS, "vector.svg")), "un SVG con contenido svg debe serlo"
    assert not visor.es_imagen_visualizable(os.path.join(ASSETS, "roto.png")), "un .png con texto no es una imagen"
    assert not visor.es_imagen_visualizable(os.path.join(ASSETS, "falso.svg")), "un .svg sin svg no es una imagen"
    assert not visor.es_imagen_visualizable(os.path.join(DOCS, "notas.md")), "un Markdown no es una imagen"
    assert not visor.es_imagen_visualizable(os.path.join(ASSETS, "no_existe.png")), "un archivo ausente no es una imagen"
    assert not visor.es_imagen_visualizable(None)
    print("[OK] deteccion de imagenes")


def check_archivo_original(ruta_png: str):
    """La ficha Markdown no debe devolverse como archivo original (causa del fallo)."""
    originales = (proc.DOCS_DIR, proc.ASSETS_DIR, proc.ORIGINALS_DIR)
    proc.DOCS_DIR, proc.ASSETS_DIR, proc.ORIGINALS_DIR = DOCS, ASSETS, ORIGINALS
    try:
        ruta = proc.obtener_ruta_original("DIAGRAMA__diagrama.md")
        assert ruta == ruta_png, f"esperado el PNG del diagrama, obtenido {ruta}"

        # Sin binario asociado la ficha se muestra a si misma (comportamiento previo).
        assert proc.obtener_ruta_original("notas.md") == os.path.join(DOCS, "notas.md")
        assert proc.obtener_ruta_original("DIAGRAMA__huerfano.md") == os.path.join(DOCS, "DIAGRAMA__huerfano.md")

        # Los binarios y los documentos de texto siguen devolviendose a si mismos.
        assert proc.obtener_ruta_original("informe.pdf") == os.path.join(DOCS, "informe.pdf")
        assert proc.obtener_ruta_original("datos.csv") == os.path.join(DOCS, "datos.csv")
    finally:
        proc.DOCS_DIR, proc.ASSETS_DIR, proc.ORIGINALS_DIR = originales
    print("[OK] resolucion del archivo original")


def check_decision_de_diagrama():
    """El caso exacto del fallo: ficha DIAGRAMA__ cuyo original era la propia ficha."""
    ficha = os.path.join(DOCS, "DIAGRAMA__diagrama.md")
    assert not visor.es_documento_diagrama("DIAGRAMA__diagrama.md", ficha), "una ficha Markdown no es un diagrama mostrable"
    assert not visor.es_documento_diagrama("DIAGRAMA__diagrama.md", None)
    assert not visor.es_documento_diagrama("DIAGRAMA__diagrama.md", os.path.join(ASSETS, "roto.png"))
    assert visor.es_documento_diagrama("DIAGRAMA__diagrama.md", os.path.join(ASSETS, "diagrama.png"))
    assert visor.es_documento_diagrama("DIAGRAMA__diagrama.md", os.path.join(ASSETS, "vector.svg"))
    assert not visor.es_documento_diagrama("notas.md", os.path.join(DOCS, "notas.md"))
    # Diagrama huerfano: su ficha se resuelve a si misma y no debe abrirse como imagen.
    huerfano = proc.obtener_ruta_original("DIAGRAMA__huerfano.md")
    assert not visor.es_documento_diagrama("DIAGRAMA__huerfano.md", huerfano)
    print("[OK] decision de diagrama")


if __name__ == "__main__":
    try:
        ruta_png_prueba = _preparar()
        check_deteccion_de_imagenes(ruta_png_prueba)
        check_archivo_original(ruta_png_prueba)
        check_decision_de_diagrama()
        print("[OK] check_visor_imagenes")
    finally:
        shutil.rmtree(BASE_PRUEBAS, ignore_errors=True)

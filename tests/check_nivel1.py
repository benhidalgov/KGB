"""Auto-verificación de los arreglos de Nivel 1.

Ejecutar:  python tests/check_nivel1.py
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.motor as motor
from core.procesador import leer_entrada_zip_segura


def check_zip_limite():
    """El tope se aplica a los bytes leídos, no al tamaño declarado en el paquete."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pequeno.txt", b"x" * 10)
        z.writestr("grande.txt", b"x" * 100)
    buf.seek(0)

    with zipfile.ZipFile(buf) as z:
        info = {i.filename: i for i in z.infolist()}
        assert leer_entrada_zip_segura(z, info["pequeno.txt"], 50) == b"x" * 10
        assert leer_entrada_zip_segura(z, info["grande.txt"], 50) is None


def check_firma_documental():
    """La firma cambia si cambian los nombres o el tamaño del corpus."""
    base = {"a.md": "hola", "b.md": "mundo"}
    f0 = motor._firma_documental(base)
    assert f0 == motor._firma_documental(dict(base)), "la firma debe ser estable"
    assert f0 != motor._firma_documental({"a.md": "hola", "b.md": "mundo!"}), "debe detectar edicion"
    assert f0 != motor._firma_documental({"a.md": "hola"}), "debe detectar eliminacion"


def check_duckdb_cursores():
    """Cada consulta recibe su propio cursor: DuckDB no comparte conexión entre hilos."""
    c1 = motor._obtener_conexion_duckdb()
    c2 = motor._obtener_conexion_duckdb()
    assert c1 is not c2, "se esperaban cursores independientes"
    assert motor.ejecutar_consulta_sql("SELECT 1 AS ok").iloc[0, 0] == 1


if __name__ == "__main__":
    check_zip_limite()
    check_firma_documental()
    check_duckdb_cursores()
    print("[OK] check_nivel1")

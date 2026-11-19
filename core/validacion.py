"""
Validaciones de entrada centralizadas para la consola.

Agrupa en un solo lugar los controles de seguridad que antes estaban
dispersos por varios modulos: traversal de rutas, nombres de archivo,
consultas SQL de solo lectura y escape de HTML. Cualquier nueva validacion
de entrada debe anadirse aqui en lugar de duplicar logica en cada modulo.
"""
import html
import os
import re
from typing import Iterable


# ---------------------------------------------------------------------------
# Validacion de rutas (prevencion de path traversal)
# ---------------------------------------------------------------------------

def validar_ruta_segura(ruta: str, raices_permitidas: Iterable[str]) -> str | None:
    """Devuelve la ruta real solo si cae dentro de una de las raices permitidas.

    Previene ataques de traversal (../../etc/passwd) al resolver la ruta
    real y comprobar que empieza por alguna de las raices de datos.
    Devuelve None si la ruta no es segura o el archivo no existe.
    """
    if not ruta:
        return None
    raices_reales = [os.path.realpath(r) + os.sep for r in raices_permitidas]
    real = os.path.realpath(ruta)
    if any(real.startswith(r) for r in raices_reales) and os.path.isfile(real):
        return real
    return None


# ---------------------------------------------------------------------------
# Validacion de nombres de archivo
# ---------------------------------------------------------------------------

_NOMBRE_PELIGROSO = re.compile(r"(\.\.|/|\\|\0|:|\*|\?|\"|<|>|\|)")


def nombre_archivo_seguro(nombre: str) -> bool:
    """Indica si un nombre de archivo es seguro (sin traversal ni caracteres prohibidos)."""
    if not nombre or nombre in (".", ".."):
        return False
    if _NOMBRE_PELIGROSO.search(nombre):
        return False
    return True


# ---------------------------------------------------------------------------
# Validacion de consultas SQL de solo lectura
# ---------------------------------------------------------------------------

_PALABRAS_PROHIBIDAS = (
    "insert", "update", "delete", "drop", "create", "alter",
    "copy", "attach", "detach", "call", "install", "load",
    "pragma", "export", "import", "set", "reset",
)

_FUNCIONES_LECTORA_FS = re.compile(
    r"\b(?:read_\w+|glob|parquet_scan|csv_scan|iceberg_scan|delta_scan)\s*\(",
    re.IGNORECASE,
)


def es_consulta_sql_solo_lectura(query_sql: str) -> bool:
    """Valida que una sentencia SQL sea de una sola lectura sin escribir en disco."""
    texto = " ".join(query_sql.strip().split())
    if not texto:
        return False
    cuerpo = texto[:-1].rstrip() if texto.endswith(";") else texto
    if ";" in cuerpo or not cuerpo:
        return False
    partes = cuerpo.split(None, 1)
    if partes[0].lower() not in ("select", "with", "describe", "show", "explain"):
        return False
    if _FUNCIONES_LECTORA_FS.search(cuerpo):
        return False
    sin_literals = re.sub(r"'[^']*'", "''", cuerpo.lower())
    return not re.search(r"\b(?:%s)\b" % "|".join(_PALABRAS_PROHIBIDAS), sin_literals)


# ---------------------------------------------------------------------------
# Escape de HTML para prevenir XSS
# ---------------------------------------------------------------------------

def escapar_html(texto: str) -> str:
    """Escapa texto para insertarlo de forma segura en HTML."""
    return html.escape(str(texto or ""))

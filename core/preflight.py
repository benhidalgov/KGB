"""Chequeos de arranque para produccion.

En produccion la consola no debe iniciar "a medias": si falta una clave maestra,
la clave de la boveda o PostgreSQL, conviene cortar el arranque con un mensaje
visible en vez de dejar un login que no puede funcionar.

En desarrollo devuelve una lista vacia y no toca la base.
"""
import os

from core import configuracion

VARIABLES_OBLIGATORIAS = (
    "ADMIN_PASSWORD",
    "OPERADOR_PASSWORD",
    "AUDITOR_PASSWORD",
    "VAULT_MASTER_KEY",
)


def problemas_de_entorno(es_produccion=None, engine=None) -> list:
    """Motivos por los que no se debe arrancar (vacio en desarrollo).

    `engine` permite inyectar un motor en los tests; si no se pasa, se pide a
    `core.db.obtener_engine`, que devuelve None cuando falta el driver.
    """
    produccion = configuracion.ES_PRODUCCION if es_produccion is None else es_produccion
    if not produccion:
        return []

    faltan = [f"Falta la variable {variable}" for variable in VARIABLES_OBLIGATORIAS
              if not os.environ.get(variable, "").strip()]

    if engine is None:
        from core.db import obtener_engine
        engine = obtener_engine()
    if engine is None:
        faltan.append("PostgreSQL no disponible (driver o DATABASE_URL/DB_*)")
    else:
        try:
            with engine.connect() as conexion:
                conexion.exec_driver_sql("SELECT 1")
        except Exception as e:
            faltan.append(f"PostgreSQL no responde ({type(e).__name__})")
    return faltan

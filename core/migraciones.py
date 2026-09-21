"""
Aplicador de migraciones de esquema para PostgreSQL.

Los cambios de esquema viven en `migrations/*.sql` y se aplican una sola vez,
en orden, registrándose en la tabla `schema_migrations`. Sustituye al mecanismo
`docker-entrypoint-initdb.d`, que solo corre al crear el volumen de datos.
"""
import os
import glob
import logging

from core.configuracion import APP_DIR

logger = logging.getLogger("infra_copilot.migraciones")

MIGRATIONS_DIR = os.path.join(APP_DIR, "migrations")


def aplicar_migraciones(engine) -> list:
    """Aplica las migraciones pendientes. Devuelve la lista de versiones aplicadas."""
    from sqlalchemy import text

    aplicadas = []
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(120) PRIMARY KEY,
                aplicada_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        ya_aplicadas = {fila[0] for fila in conn.execute(text("SELECT version FROM schema_migrations"))}

        for ruta in sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql"))):
            version = os.path.basename(ruta)
            if version in ya_aplicadas:
                continue
            with open(ruta, "r", encoding="utf-8") as f:
                ddl = f.read()
            # exec_driver_sql evita que SQLAlchemy interprete ':' y '::' del SQL.
            conn.exec_driver_sql(ddl)
            conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": version})
            aplicadas.append(version)
            logger.info(f"[MIGRACIONES] Aplicada: {version}")

    return aplicadas

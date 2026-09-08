"""
Adaptador de Base de Datos Relacional (PostgreSQL) y Capa de Persistencia.
Provee conexión con pooling, verificación de salud con fallback automático a archivos locales,
y operaciones transaccionales para RBAC, Auditoría y CMDB.
"""
import os
import time
import logging
from typing import Optional, Dict, Any, List
import pandas as pd

logger = logging.getLogger("infra_copilot.db")

_ENGINE = None
_LAST_CHECK_TIME: float = 0.0
_IS_AVAILABLE: bool = False
_CHECK_INTERVAL: float = 15.0  # Intervalo de re-verificación en segundos


def _obtener_database_url() -> Optional[str]:
    """Obtiene y normaliza la URL de conexión a PostgreSQL desde variables de entorno."""
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    host = os.environ.get("DB_HOST")
    if host:
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "infra_copilot")
        user = os.environ.get("DB_USER", "infra_admin")
        pwd = os.environ.get("DB_PASSWORD", "infra_secure_password_2026")
        return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"

    return None


def obtener_engine():
    """Retorna el motor SQLAlchemy configurado o None si no hay conexión válida."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    url = _obtener_database_url()
    if not url:
        return None

    try:
        from sqlalchemy import create_engine
        _ENGINE = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 3}
        )
        return _ENGINE
    except Exception as e:
        logger.warning(f"[DB] No se pudo inicializar el motor de PostgreSQL: {e}")
        return None


def es_postgres_disponible() -> bool:
    """Verifica si el servidor PostgreSQL está activo y responde con sondeo ligero."""
    global _LAST_CHECK_TIME, _IS_AVAILABLE
    ahora = time.time()
    if ahora - _LAST_CHECK_TIME < _CHECK_INTERVAL:
        return _IS_AVAILABLE

    _LAST_CHECK_TIME = ahora
    engine = obtener_engine()
    if engine is None:
        _IS_AVAILABLE = False
        return False

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _IS_AVAILABLE = True
        return True
    except Exception:
        _IS_AVAILABLE = False
        return False


def ejecutar_consulta_df(query_sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Ejecuta una consulta SQL SELECT contra PostgreSQL y retorna un DataFrame."""
    if not es_postgres_disponible():
        return pd.DataFrame()

    engine = obtener_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            return pd.read_sql_query(text(query_sql), conn, params=params)
    except Exception as e:
        logger.error(f"[DB] Error en consulta SQL: {e}")
        return pd.DataFrame()


def ejecutar_escritura(query_sql: str, params: Optional[Dict[str, Any]] = None) -> bool:
    """Ejecuta una sentencia de escritura (INSERT, UPDATE, DELETE) en PostgreSQL."""
    if not es_postgres_disponible():
        return False

    engine = obtener_engine()
    if engine is None:
        return False

    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text(query_sql), params or {})
        return True
    except Exception as e:
        logger.error(f"[DB] Error en escritura SQL: {e}")
        return False


# -------------------------------------------------------------
# OPERACIONES RBAC / USUARIOS
# -------------------------------------------------------------

def obtener_usuarios_pg() -> Dict[str, Any]:
    """Recupera el catálogo de usuarios desde PostgreSQL."""
    df = ejecutar_consulta_df("SELECT username, nombre, rol, hash_password, activo FROM usuarios WHERE activo = true")
    if df.empty:
        return {}
    usuarios = {}
    for _, row in df.iterrows():
        usuarios[str(row["username"]).strip().lower()] = {
            "nombre": row["nombre"],
            "rol": row["rol"],
            "hash": row["hash_password"],
            "activo": bool(row["activo"])
        }
    return usuarios


def actualizar_ultimo_login_pg(username: str) -> bool:
    """Actualiza la marca temporal del último login del usuario."""
    sql = "UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP WHERE LOWER(username) = LOWER(:u)"
    return ejecutar_escritura(sql, {"u": username})


# -------------------------------------------------------------
# OPERACIONES DE AUDITORÍA
# -------------------------------------------------------------

def insertar_evento_auditoria_pg(
    documento: str,
    accion: str,
    version_ant: int,
    version_nueva: int,
    autor: str,
    motivo: str,
    sha256_hash: str = ""
) -> bool:
    """Inserta un registro formal e inmutable en la tabla registro_auditoria de PostgreSQL."""
    sql = """
        INSERT INTO registro_auditoria 
        (documento, accion, version_anterior, version_nueva, autor, motivo, sha256_integridad)
        VALUES (:doc, :acc, :v_ant, :v_new, :aut, :mot, :sha)
    """
    params = {
        "doc": documento,
        "acc": accion,
        "v_ant": version_ant,
        "v_new": version_nueva,
        "aut": autor,
        "mot": motivo,
        "sha": sha256_hash
    }
    return ejecutar_escritura(sql, params)


def obtener_eventos_auditoria_pg(limite: int = 200) -> List[Dict[str, Any]]:
    """Recupera la lista de eventos de auditoría ordenados cronológicamente inverso."""
    sql = f"""
        SELECT timestamp, documento, accion, version_anterior, version_nueva, autor, motivo, sha256_integridad
        FROM registro_auditoria
        ORDER BY timestamp DESC
        LIMIT {limite}
    """
    df = ejecutar_consulta_df(sql)
    if df.empty:
        return []

    eventos = []
    for _, row in df.iterrows():
        ts_str = str(row["timestamp"])
        try:
            if hasattr(row["timestamp"], "strftime"):
                ts_str = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        v_ant_num = int(row["version_anterior"] or 0)
        v_new_num = int(row["version_nueva"] or 1)
        eventos.append({
            "timestamp": ts_str,
            "documento": row["documento"],
            "accion": row["accion"],
            "version_anterior": f"v{v_ant_num}" if v_ant_num > 0 else "-",
            "version_nueva": f"v{v_new_num}",
            "editor_responsable": str(row["autor"] or "Desconocido").strip(),
            "motivo_justificacion": str(row["motivo"] or "Sin justificación").strip(),
            "sha256": str(row["sha256_integridad"] or "").strip()
        })
    return eventos


# -------------------------------------------------------------
# OPERACIONES DE CMDB / MANTENIMIENTOS
# -------------------------------------------------------------

def obtener_mantenimientos_pg_df() -> pd.DataFrame:
    """Obtiene el conjunto completo de mantenimientos e inventario de servidores desde PostgreSQL."""
    sql = """
        SELECT servidor_id, numero_serie, ip, vcloud_vm, nivel_arquitectura, componente, 
               fecha, tipo_mantenimiento, tecnico, descripcion, estado, nagios_check
        FROM mantenimientos
        ORDER BY fecha DESC, servidor_id ASC
    """
    return ejecutar_consulta_df(sql)

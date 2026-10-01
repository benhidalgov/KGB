import os

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Cargar automáticamente variables de entorno desde .env si existe (desarrollo local)
_env_path = os.path.join(APP_DIR, ".env")
if os.path.exists(_env_path):
    try:
        import dotenv
        dotenv.load_dotenv(_env_path, override=False)
    except Exception:
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line or _line.startswith("#") or "=" not in _line:
                        continue
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip("'\"")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
        except Exception:
            pass

# Modo de despliegue: en producción (Docker) se exige configuración segura
# explícita y se desactivan los respaldos silenciosos a archivos locales.
ES_PRODUCCION = os.environ.get("PRODUCCION", "").strip().lower() in ("1", "true", "yes", "si", "sí")

# Rutas principales de datos y recursos
DATA_DIR = os.path.join(APP_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "mantenimientos.csv")
DOCS_DIR = os.path.join(DATA_DIR, "docs")
ASSETS_DIR = os.path.join(DATA_DIR, "docs", "assets")
ORIGINALS_DIR = os.path.join(DATA_DIR, "originals")
INBOX_DIR = os.path.join(DATA_DIR, "inbox")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
AUDIT_LOG_PATH = os.path.join(DATA_DIR, "audit_log.json")
MANIFEST_PATH = os.path.join(DATA_DIR, "ingestion_manifest.json")
VAULT_FILE_PATH = os.path.join(DATA_DIR, ".vault.enc")
VAULT_KEY_PATH = os.path.join(DATA_DIR, ".vault.key")
CATEGORIAS_PATH = os.path.join(DATA_DIR, "categorias.json")
PLANTILLAS_CUSTOM_PATH = os.path.join(DATA_DIR, "plantillas_custom.json")
USERS_PATH = os.path.join(DATA_DIR, "users.json")

# Límites de ingesta: protegen contra paquetes ZIP y archivos desproporcionados
# que agotarían la memoria del contenedor.
MAX_SUBIDA_BYTES = 100 * 1024 * 1024   # por archivo cargado
MAX_ENTRADA_BYTES = 25 * 1024 * 1024   # por entrada descomprimida de un ZIP
MAX_LOTE_BYTES = 250 * 1024 * 1024     # total descomprimido por ZIP

# Archivo de estilos CSS
ESTILOS_CSS_PATH = os.path.join(APP_DIR, "core", "estilos.css")

# Asegurar la existencia de directorios base
for directory in [DATA_DIR, DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR, INBOX_DIR, HISTORY_DIR]:
    os.makedirs(directory, exist_ok=True)


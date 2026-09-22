import os

# Modo de despliegue: en producción (Docker) se exige configuración segura
# explícita y se desactivan los respaldos silenciosos a archivos locales.
ES_PRODUCCION = os.environ.get("PRODUCCION", "").strip().lower() in ("1", "true", "yes", "si", "sí")

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

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


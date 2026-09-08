import os
import sys

# Determinación de directorios base (Entorno congelado .exe vs Desarrollo)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', APP_DIR)
    try:
        os.chdir(APP_DIR)
    except Exception:
        pass
else:
    APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    BUNDLE_DIR = APP_DIR

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

# Archivo de estilos CSS
_css_bundle = os.path.join(BUNDLE_DIR, "core", "estilos.css")
_css_app = os.path.join(APP_DIR, "core", "estilos.css")
ESTILOS_CSS_PATH = _css_bundle if os.path.exists(_css_bundle) else _css_app

# Asegurar la existencia de directorios base
for directory in [DATA_DIR, DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR, INBOX_DIR, HISTORY_DIR]:
    os.makedirs(directory, exist_ok=True)


import os

# Rutas principales de datos y recursos
CSV_PATH = os.path.join("data", "mantenimientos.csv")
DOCS_DIR = os.path.join("data", "docs")
ASSETS_DIR = os.path.join("data", "docs", "assets")
ORIGINALS_DIR = os.path.join("data", "originals")
INBOX_DIR = os.path.join("data", "inbox")
HISTORY_DIR = os.path.join("data", "history")
AUDIT_LOG_PATH = os.path.join("data", "audit_log.json")
MANIFEST_PATH = os.path.join("data", "ingestion_manifest.json")
ESTILOS_CSS_PATH = os.path.join("core", "estilos.css")

# Asegurar la existencia de directorios base
for directory in [DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR, INBOX_DIR, HISTORY_DIR]:
    os.makedirs(directory, exist_ok=True)

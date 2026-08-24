# Copilot de Infraestructura y Operaciones

Plataforma corporativa de asistencia técnica y gestión documental para infraestructura, inventario CMDB en memoria (DuckDB), visualización adaptativa lado a lado, control de versiones inmutable y generación de procedimientos operativos.

---

## 1. Capacidades Principales

* **Motor Dual de Búsqueda:** Consultas exactas por IP, host o serie sobre CMDB con DuckDB, y búsqueda full-text con MarkItDown en manuales y diagramas.
* **Visor Lado a Lado:** Inspección sincronizada entre Markdown normalizado y el archivo original (PDF embebido, Excel interactivo, diagramas en alta resolución o Word).
* **Control de Versiones y Auditoría:** Historial inmutable en `data/history/` (`v1`, `v2`...), comparador visual *Diff*, Rollback protegido y registro central en `data/audit_log.json`.
* **Generador de Runbooks:** Creación rápida de procedimientos estandarizados (Rollback, Despliegue, Postmortem P1, Failover) y definición de plantillas personalizadas.
* **Ingesta Masiva Recursiva:** Procesamiento multihilo (`batch_ingest.py`) con firmas SHA-256 y soporte para carpetas compartidas de red (`Z:\` o rutas UNC).
* **Diseño Theme-Safe (Obsidian & Indigo):** Interfaz adaptativa 100% legible en Tema Claro y Oscuro, sin emojis y con terminología técnica formal.

---

## 2. Estructura del Proyecto

```text
C:\Prototipo\
├── app.py                             # Aplicación principal Streamlit (Navbar flotante y 4 Pestañas)
├── batch_ingest.py                    # Ingesta masiva multihilo con caché SHA-256
├── excel_cleaner.py                   # Extractor y normalizador de libros Excel
├── run_app.bat / run_app.ps1          # Lanzadores de ejecución en Windows
├── requirements.txt                   # Dependencias Python
├── README.md                          # Manual de uso y puesta en marcha
├── ARQUITECTURA_COPILOT_INFRAESTRUCTURA.md # Especificación técnica y arquitectura
├── HOJA_DE_RUTA_DIAGRAMAS_E_INGESTA.md     # Roadmap de desarrollo
├── GEMINI.md                          # Reglas y directrices de desarrollo
├── core/                              # Módulos centrales (Lógica, CSS, Motor, Auditoría, Visor, Manual)
└── data/                              # Repositorio de datos (CMDB, docs, history, originals, auditoría)
```

---

## 3. Instalación y Puesta en Marcha

```cmd
# 1. Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar la plataforma (o doble clic en run_app.bat)
streamlit run app.py
```
*Acceso local:* `http://localhost:8501`

---

## 4. Guía Rápida por Módulo

* **Navbar Superior:** Título corporativo, estado `● ONLINE`, selector de vista (`[Consola]` | `[Manual de Uso]`) y contadores en tiempo real de Documentos y CMDB.
* **Panel Lateral (Sidebar):** Carga de archivos arrastrando y soltando, filtros por tipo y acciones rápidas (`Reindexar`, `Limpiar Chat`).
* **Pestaña 1 (Consultas y Búsqueda):** Barra de búsqueda superior con chips de acceso rápido (`BALANCER001`, `JWT`, `10.24.0.125`), tarjetas con bordes temáticos y fragmentos resaltados.
* **Pestaña 2 (Historial de Mantenimientos):** Tabla interactiva con filtros por Nivel (L1-L4), Estado y Técnico, más consola SQL DuckDB en vivo.
* **Pestaña 3 (Documentación Técnica y Versionado):** Visor Lado a Lado (Markdown vs Original), editor en cuadrícula para Excel, editor de texto, comparador Diff, descarga de snapshots y botón de Rollback protegido.
* **Pestaña 4 (Plantillas y Runbooks):** Asistente de 3 pasos con formularios dinámicos para redactar, previsualizar y publicar procedimientos en la base de conocimiento (`v1`).
* **Ingesta Masiva por Lote:** `python batch_ingest.py --origen Z:\RutaRed --workers 8`.

---

## 5. Matriz de Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Interfaz Web** | Streamlit + Antd Components | Dashboard corporativo y componentes interactivos |
| **Motor SQL** | DuckDB + Pandas | Consultas en memoria sobre inventarios y mantenimientos |
| **Conversión Documental** | Microsoft MarkItDown + OpenPyXL | Extracción de texto estructurado de PDFs, Word y Excel |
| **Auditoría e Integridad** | Python `hashlib` (SHA-256) + `difflib` | Versionado inmutable, Diff y bitácora de auditoría |
| **Diagramas** | Mermaid.js | Topologías e infraestructura en 4 niveles (L1-L4) |

---

## 6. Resolución de Problemas (Troubleshooting)

* **Archivos externos no visibles:** Clic en `[Reindexar]` en el Sidebar o ejecutar `python batch_ingest.py`.
* **Error de permisos al guardar (PermissionError):** Cerrar el archivo si está abierto en Excel/Word/Acrobat en Windows.
* **Excel multihoja complejo:** Normalizar ejecutando `python excel_cleaner.py "archivo.xlsx"`.
* **Servicio 7x24 en Windows Server:** Instalar con NSSM (`nssm install CopilotInfra "C:\Prototipo\.venv\Scripts\streamlit.exe" "run C:\Prototipo\app.py --server.port 8501"`) o mediante el Programador de Tareas.
* **Respaldo de auditoría y versiones (PowerShell):**
  ```powershell
  Compress-Archive -Path C:\Prototipo\data\* -DestinationPath C:\Backups\Copilot_Data_$(Get-Date -Format "yyyyMMdd").zip
  ```

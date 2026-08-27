# Copilot de Infraestructura y Operaciones

Plataforma corporativa de asistencia técnica, gestión documental de infraestructura, inventario CMDB en memoria (DuckDB), inferencia generativa con Google Gemini RAG, bóveda de seguridad cifrada (AES-256), telemetría de sistemas SAP y control de versiones inmutable.

---

## 1. Capacidades Principales

* **Motor Dual e Inteligencia Generativa (Gemini RAG):** Asistencia técnica en lenguaje natural mediante el SDK oficial `google-genai` (`gemini-3.6-flash`) con inyección de contexto (*Retrieval-Augmented Generation*). Directriz estricta de cero alucinaciones y fallback transparente al motor local autónomo (DuckDB + MarkItDown) si no hay API Key o falla la conexión externa.
* **Caché en Memoria y Alto Rendimiento:** Almacén de respuestas frecuentes en memoria RAM (`Query Response Cache`) que reduce la latencia en consultas repetidas de 13.4 segundos a **0.79 milisegundos**. Búsqueda documental con pre-normalización léxica en memoria y DuckDB en RAM con cero I/O de disco.
* **Bóveda de Seguridad Local (Vault AES-256):** Custodia de credenciales y API Keys (`GEMINI_API_KEY`, `SAP_ENDPOINT`, `SAP_CLIENT_ID`, etc.) mediante cifrado simétrico Fernet. Jerarquía de resolución en cascada (OS Environment -> Bóveda Cifrada -> Streamlit Secrets), limpieza automática de inputs al guardar, cegado total de vista previa y supresión de botones reveladores en la interfaz.
* **Integración y Telemetría SAP (API):** Consola dedicada para el monitoreo del landscape SAP S/4HANA 2022, bases de datos SAP HANA 2.0 (HSR en alta disponibilidad), servidores de aplicación NetWeaver (ASCS/PAS/AAS), Web Dispatcher y sincronización automatizada con la CMDB local.
* **Visor Lado a Lado con Imágenes Activas:** Inspección sincronizada entre Markdown normalizado y el archivo original (PDF embebido, Excel interactivo, diagramas en alta resolución o Word). La **Vista Formateada** renderiza esquemas y todas las imágenes embebidas de documentos Word (.docx) mediante Data URIs base64.
* **Control de Versiones y Auditoría:** Historial inmutable en `data/history/` (`v1`, `v2`...), comparador visual *Diff*, Rollback protegido y registro central de auditoría en `data/audit_log.json`.
* **Generador de Runbooks y Procedimientos:** Asistente de redacción para contingencias, rollbacks, mantenimientos preventivos y definición de plantillas personalizadas indexadas de inmediato en la base de conocimiento.
* **Ingesta Masiva Recursiva:** Procesamiento multihilo (`batch_ingest.py`) con firmas de integridad SHA-256 y soporte para carpetas compartidas de red (`Z:\` o rutas UNC).
* **Diseño Corporativo Theme-Safe (Obsidian & Indigo):** Interfaz adaptativa 100% legible en Tema Claro y Oscuro, estrictamente libre de emojis y con terminología técnica formal de ingeniería.

---

## 2. Estructura del Proyecto

```text
C:\Prototipo\
├── app.py                             # Aplicación principal Streamlit (Navbar flotante y 5 Pestañas)
├── batch_ingest.py                    # Ingesta masiva multihilo con caché SHA-256
├── excel_cleaner.py                   # Extractor y normalizador de libros Excel
├── run_app.bat / run_app.ps1          # Lanzadores de ejecución en Windows
├── requirements.txt                   # Dependencias Python
├── README.md                          # Manual de uso y puesta en marcha
├── ARQUITECTURA_COPILOT_INFRAESTRUCTURA.md # Especificación técnica y arquitectura
├── HOJA_DE_RUTA_DIAGRAMAS_E_INGESTA.md     # Roadmap de desarrollo
├── GEMINI.md                          # Reglas y directrices de desarrollo
├── core/                              # Módulos centrales de la plataforma
│   ├── __init__.py                    # Exportación de paquetes
│   ├── auditoria.py                   # Control de versiones, Diff y bitácora inmutable
│   ├── configuracion.py               # Rutas base y definición de directorios
│   ├── conector_sap.py                # Conector, telemetría y topología Mermaid SAP
│   ├── estilos.py / estilos.css       # Reglas visuales corporativas y seguridad CSS
│   ├── manual.py                      # Manual de uso interactivo en consola
│   ├── motor.py                       # Motor de consultas, DuckDB en RAM, Gemini RAG y cachés
│   ├── plantillas.py                  # Generador de procedimientos y runbooks
│   ├── procesador.py                  # MarkItDown, extracción de medios y sanitización
│   ├── topologia.py                   # Diagramas arquitectónicos Mermaid (L1-L4)
│   ├── vault.py                       # Bóveda de credenciales con cifrado AES-256
│   └── visor.py                       # Visor Lado a Lado y renderizador nativo
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

# 3. Iniciar la plataforma (o ejecutar run_app.bat)
streamlit run app.py
```
*Acceso local:* `http://localhost:8501`

---

## 4. Guía por Pestaña de la Consola

* **Navbar Superior:** Marca corporativa, estado de servicio `● ONLINE`, selector de vista (`[Consola]` | `[Manual de Uso]`) y contadores de base documental.
* **Panel Lateral (Sidebar):** Ingesta de archivos con detección automática de tipo, explorador con filtro por categoría, acción de consola (`>_ Reindexar`), **Bóveda de Credenciales `[VAULT]`** con inputs protegidos y pie de sesión corporativo.
* **Pestaña 1 (Consultas y Búsqueda):** Consultas técnicas en lenguaje natural potenciadas por **Google Gemini RAG** (`gemini-3.6-flash`) con aceleración por **Query Response Cache** en RAM (latencia < 1 ms en consultas repetidas), botón **`>_ Limpiar Chat`** en cabecera de resultados y fallback automático al motor local autónomo (DuckDB + MarkItDown).
* **Pestaña 2 (Historial de Mantenimientos):** Tabla interactiva de servidores con filtros por Nivel de Arquitectura (L1-L4), Estado y Técnico, más consola SQL DuckDB en memoria RAM sobre `mantenimientos.csv`.
* **Pestaña 3 (Documentación Técnica y Versionado):** Visor Lado a Lado (Markdown vs Original), renderizado de diagramas, imágenes DOCX en la **Vista Formateada**, editor en cuadrícula para libros Excel, editor de texto, comparador Diff, descarga de snapshots y Rollback protegido.
* **Pestaña 4 (Plantillas y Runbooks):** Asistente paso a paso para la redacción, validación y publicación formal de procedimientos operativos (`v1`).
* **Pestaña 5 (Integración SAP - API):** Monitoreo del landscape SAP, verificación de endpoints y latencia en milisegundos, visualizador de topología Mermaid para HANA HSR y NetWeaver, visor de payload JSON REST/OData y botón de sincronización directa hacia la CMDB local.

---

## 5. Matriz de Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Interfaz Web** | Streamlit + Antd Components | Consola corporativa, navegación por pestañas y componentes interactivos |
| **Motor de Inteligencia (IA)** | Google GenAI SDK (`google-genai`) | Inferencia generativa RAG con `gemini-3.6-flash` fundamentada en evidencia CMDB |
| **Aceleración de Consultas** | LRU Query Cache + Pre-normalización | Caché en RAM para respuestas instantáneas (< 1 ms) y búsqueda léxica sub-milisegundo |
| **Bóveda de Credenciales** | Python `cryptography` (Fernet / AES-256) | Custodia cifrada local de API Keys y tokens con jerarquía en cascada |
| **Integración ERP / Core** | Conector REST / OData SAP | Telemetría e inventario de SAP S/4HANA y bases de datos SAP HANA HSR |
| **Motor SQL en Memoria** | DuckDB + Pandas | Consultas ultrarrápidas en RAM con Zero Disk I/O sobre mantenimientos e inventario |
| **Conversión Documental** | Microsoft MarkItDown + OpenPyXL | Extracción estructurada de texto de PDFs, Word y Excel con `keep_data_uris=True` |
| **Procesador de Medios** | Python `base64` + `zipfile` | Inyección de Data URIs para imágenes y extracción de gráficos en documentos Word |
| **Auditoría e Integridad** | Python `hashlib` (SHA-256) + `difflib` | Versionado inmutable, Diff y bitácora de auditoría en `audit_log.json` |
| **Diagramas de Topología** | Mermaid.js | Visualización interactiva de arquitectura en 4 niveles y landscapes SAP |
| **Caché y Rendimiento** | `@st.cache_data` + `functools.lru_cache` | Aceleración de I/O en documentos, hojas Excel, CSS y metadatos |

---

## 6. Resolución de Problemas (Troubleshooting)

* **Activar Google Gemini:** Abrir la sección **Bóveda de Credenciales `[VAULT]`** en la barra lateral, seleccionar `GEMINI_API_KEY`, ingresar la clave y guardar. La consulta responderá automáticamente vía RAG.
* **Archivos externos no visibles:** Clic en `>_ Reindexar` en el panel lateral o ejecutar `python batch_ingest.py`.
* **Caché de consultas desactualizada tras editar archivos:** Al hacer clic en `>_ Reindexar`, el sistema purga automáticamente la caché de respuestas en memoria.
* **Error de permisos al guardar (PermissionError):** Asegurar que el archivo no se encuentre abierto en Excel, Word o Adobe Acrobat en Windows.
* **Excel multihoja complejo:** Normalizar ejecutando `python excel_cleaner.py "archivo.xlsx"`.
* **Despliegue como Servicio 7x24 en Windows Server:** Instalar con NSSM (`nssm install CopilotInfra "C:\Prototipo\.venv\Scripts\streamlit.exe" "run C:\Prototipo\app.py --server.port 8501"`) o mediante el Programador de Tareas.
* **Respaldo de auditoría y versiones (PowerShell):**
  ```powershell
  Compress-Archive -Path C:\Prototipo\data\* -DestinationPath C:\Backups\Copilot_Data_$(Get-Date -Format "yyyyMMdd").zip
  ```

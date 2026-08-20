# Copilot de Infraestructura y Operaciones (AIOps)

Asistente inteligente corporativo y motor de búsqueda dual diseñado para la gestión de infraestructura, análisis de mantenimientos en tiempo real, consulta de CMDBs, edición versionada y recuperación de procedimientos técnicos operativos.

---

## 1. Características Principales

* **Motor de Búsqueda Dual:**
  * **Analítico / Estructurado (DuckDB):** Consultas ultra-rápidas en memoria sobre el inventario y mantenimientos (`data/mantenimientos.csv`) por número de serie, IP, servidor, técnico o componente.
  * **Documental / No Estructurado (MarkItDown + Extracción de Hojas Excel):** Búsqueda contextual y por palabras clave en manuales operativos, contingencias, CMDBs, reportes postmortem y guías técnicas.
* **Modos de Operación:**
  * **Modo Local Autónomo (Por defecto):** No requiere conexión a internet ni llaves de API. Genera fichas técnicas formateadas y extractos documentales al instante con DuckDB y motor de texto.
  * **Integración con Google Gemini (Opcional):** Compatible con el SDK oficial `google-genai` para síntesis avanzada, diagnóstico de infraestructura y correlación de contexto RAG mediante API Key.
* **Visor y Editor de Cuadrícula Interactiva para Excel:**
  * **Visualización en Cuadrícula (`st.dataframe`):** Renderizado de hojas de cálculo con celdas, bordes, ordenamiento de columnas y buscador integrado.
  * **Edición Celda a Celda en Vivo (`st.data_editor`):** Modificación directa de valores, agregado e inserción dinámica de filas directamente en el libro `.xlsx`.
* **Control de Versiones y Auditoría Estricta:**
  * **Snapshots Inmutables (`data/history/`):** Respaldo automático de copias históricas de cada versión (`v1`, `v2`, etc.) tanto para documentos Markdown como para libros Excel.
  * **Validación Obligatoria de Editor y Motivo:** Exigencia estricta de identificación del técnico y justificación técnica para cualquier guardado o reversión.
  * **Comparador Visual de Cambios (Diff Viewer):** Comparación línea a línea entre dos versiones históricas con sintaxis unificada `diff`.
  * **Rollback Seguro:** Restauración con un clic a cualquier punto histórico con registro de auditoría.
  * **Registro Central de Auditoría (`data/audit_log.json`):** Trazabilidad global de todas las operaciones realizadas en la plataforma.
* **Pipeline de Ingesta Masiva Multihilo (`batch_ingest.py`):**
  * Conversión automática por lotes con control de inmutabilidad y firmas criptográficas **SHA-256** en `data/ingestion_manifest.json`.
* **Mapeo Topológico y Arquitectura en 4 Niveles:**
  * Visualización jerárquica (L1: Hardware, L2: Virtualización, L3: Middleware, L4: Aplicaciones) y correlación con la capa de Observabilidad (*Nagios, New Relic, VZOR, PRTG*) y CI/CD (*GitLab, Jenkins*).
* **Generador Integrado de Plantillas y Runbooks:**
  * Creación y publicación rápida de procedimientos técnicos estandarizados (Rollbacks, Despliegues, Postmortems P1, Fichas de Microservicios y Failover) con inicialización automática de versión `v1`.

---

## 2. Estructura del Proyecto

```text
C:\Prototipo\
│
├── app.py                             # Aplicación principal interactiva (Streamlit)
├── batch_ingest.py                    # Worker de ingesta masiva multihilo con caché SHA-256
├── excel_cleaner.py                   # Motor de extracción y limpieza de CMDBs y libros Excel
├── requirements.txt                   # Dependencias del entorno virtual de Python
├── run_app.bat                        # Acceso directo para iniciar la app en Windows (CMD)
├── run_app.ps1                        # Script de inicio para PowerShell
├── README.md                          # Manual de uso e instrucciones del sistema
├── ARQUITECTURA_COPILOT_INFRAESTRUCTURA.md # Especificación técnica y arquitectura detallada
├── HOJA_DE_RUTA_DIAGRAMAS_E_INGESTA.md     # Roadmap de diagramas, OCR y sincronización de red
├── GEMINI.md                          # Reglas y directrices de desarrollo para el asistente
│
└── data/
    ├── inbox/                         # Carpeta para colocar archivos a procesar en lote
    ├── docs/                          # Repositorio de documentación técnica indexada
    ├── history/                       # Snapshots inmutables y metadatos de versiones históricas
    ├── audit_log.json                 # Log centralizado de auditoría y trazabilidad
    ├── mantenimientos.csv             # Base de datos estructurada de inventario y mantenimientos
    └── ingestion_manifest.json        # Manifiesto con firmas SHA-256 de archivos procesados
```

---

## 3. Instalación y Puesta en Marcha

### 3.1 Requisitos Previos
* Python 3.10 o superior instalado en el sistema.

### 3.2 Configuración del Entorno Virtual
```cmd
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# En CMD:
.venv\Scripts\activate
# En PowerShell:
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 3.3 Iniciar la Aplicación
* **Opción Rápida (Recomendada):** Doble clic en `run_app.bat` (o ejecutar `.\run_app.ps1`).
* **Vía Terminal:**
  ```cmd
  .venv\Scripts\streamlit run app.py
  ```

La interfaz web se abrirá automáticamente en `http://localhost:8501`.

---

## 4. Guía de Módulos y Pestañas

### 4.1 Barra Lateral (Sidebar)
* **Carga Rápida de Archivos:** Soporte multiarchivo con indexación automática (`.xlsx`, `.docx`, `.pdf`, `.md`, etc.).
* **Base Indexada con Filtros:** Contadores categorizados por tipo y buscador de archivos en tiempo real.
* **Acciones Rápidas:** Botones para reindexar la base documental y limpiar la conversación.
* **Estado del Sistema:** Monitoreo en vivo de conexiones a DuckDB SQL y motor MarkItDown.

---

### 4.2 Pestañas Principales

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  [1] Consultar dudas  │  [2] Historial Mantenimientos  │  [3] Preview de arquitecturas │
│  [4] Documentación Técnica  │  [5] Plantillas de documentación                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Pestaña 1: Consultar dudas (Buscar por palabras)
* Motor conversacional de búsqueda en lenguaje natural y extracción técnica.
* Consultas por Servidor (`BALANCER001`), Número de Serie (`SN-8842-A`), Dirección IP (`10.24.0.125`), Técnico o Procedimiento.

#### Pestaña 2: Historial de Mantenimientos
* Motor analítico sobre `data/mantenimientos.csv` impulsado por **DuckDB**.
* Filtros por Nivel de Arquitectura, Estado Operativo y Técnico.
* Consola SQL integrada para sentencias analíticas personalizadas.

#### Pestaña 3: Preview de arquitecturas
* Diagrama topológico interactivo en **Mermaid.js** con dependencias entre Hardware (L1), Virtualización (L2), Middleware (L3), Aplicaciones (L4), Observabilidad y CI/CD.

#### Pestaña 4: Documentación Técnica y Versionado
* **Subpestaña 1 (Visualización):** Visor con soporte de cuadrícula interactiva para Excel y visor formateado para Markdown.
* **Subpestaña 2 (Editar Documento):**
  * Para Excel: Editor en vivo celda a celda (`st.data_editor`) por hoja con validación obligatoria de Editor y Motivo.
  * Para Markdown: Editor de texto en vivo con control de versiones.
* **Subpestaña 3 (Historial de Versiones):**
  * Tabla cronológica de auditoría (Versión, Fecha, Editor, Motivo, Tamaño).
  * Comparador visual de diferencias (Diff Viewer) entre cualquier par de versiones.
  * Inspección de snapshots históricos.
  * Botón de Rollback seguro con justificación técnica obligatoria.

#### Pestaña 5: Plantillas de documentación
* Generador rápido de Runbooks estandarizados (Rollback, Despliegue CI/CD, Postmortem P1, Ficha de Microservicio, Contingencia y Failover) con registro automático de versión `v1`.

---

## 5. Tecnologías y Librerías

| Componente | Tecnología / Librería | Función Principal |
| :--- | :--- | :--- |
| **Framework de Interfaz** | [Streamlit](https://streamlit.io/) | Dashboard interactivo, visualización y edición en cuadrícula |
| **Motor SQL Analítico** | [DuckDB](https://duckdb.org/) | Consultas tabulares ultrarrápidas en memoria sobre CSV |
| **Motor de IA / LLM** | [Google GenAI SDK](https://github.com/google-gemini/deprecations) (`google-genai`) | Integración oficial con modelos Google Gemini |
| **Conversión Documental** | [Microsoft MarkItDown](https://github.com/microsoft/markitdown) | Conversión universal de Word, PDF, PowerPoint y texto |
| **Procesador de CMDBs/Excel** | [OpenPyXL](https://openpyxl.readthedocs.io/) / `excel_cleaner.py` | Extracción estructurada y edición de libros multihoja |
| **Manipulación de Datos** | [Pandas](https://pandas.pydata.org/) | Gestión de DataFrames, transformaciones y exportaciones |
| **Comparación de Versiones** | Python `difflib` | Generación de diferencias unificadas (*Diff*) |
| **Diagramas Topológicos** | [Mermaid.js](https://mermaid.js.org/) | Renderizado de diagramas de arquitectura y flujos de datos |

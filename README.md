# Copilot de Infraestructura y Operaciones (AIOps)

Asistente inteligente corporativo y motor de búsqueda dual diseñado para la gestión de infraestructura, análisis de mantenimientos en tiempo real, consulta de CMDBs, inspección visual de diagramas y topologías, edición versionada y recuperación de procedimientos técnicos operativos.

---

## 1. Visión General y Capacidades Principales

* **Motor de Búsqueda Dual:**
  * **Analítico / Estructurado (DuckDB):** Consultas ultrarrápidas en memoria sobre el inventario y mantenimientos (`data/mantenimientos.csv`) por número de serie (`SN-8842-A`), dirección IP (`10.24.0.125`), servidor (`BALANCER001`), técnico o componente.
  * **Documental / No Estructurado (MarkItDown + Extracción Multihoja):** Búsqueda contextual y por palabras clave en manuales operativos, contingencias, CMDBs, reportes postmortem y guías técnicas.

* **Visor Comparativo Lado a Lado (Side-by-Side):**
  * **Columna Izquierda:** Representación Markdown normalizada, indexable y estructurada.
  * **Columna Derecha (Adaptativa según formato):**
    * **Diagramas e Imágenes (`.png`, `.jpg`, `.svg`, `.webp`):** Renderizado visual en alta resolución con gestión auditada de **Pie de Imagen (*Caption*)**.
    * **Libros Excel (`.xlsx`, `.xls`):** Cuadrícula interactiva con selector dinámico de hojas de cálculo.
    * **Documentos PDF (`.pdf`):** Visor PDF nativo embebido en iframe Base64 seguro.
    * **Documentos Ofimáticos Word / PPTX (`.docx`, `.pptx`):** Tarjeta de propiedades y botón de descarga directa del binario original.
    * **Texto y Código (`.txt`, `.csv`, `.sql`, `.py`):** Visor con resaltado de sintaxis.

* **Gestión Organizada de Activos y Documentos Fuente:**
  * `data/docs/assets/`: Repositorio centralizado para imágenes y diagramas de topología.
  * `data/originals/`: Resguardo inmutable de copias binarias de archivos originales subidos o procesados.
  * Generación automática de fichas Markdown estandarizadas para activos gráficos con firmas criptográficas **SHA-256**.

* **Control de Versiones y Auditoría Estricta:**
  * **Snapshots Inmutables (`data/history/`):** Respaldo automático de copias históricas de cada versión (`v1`, `v2`, etc.).
  * **Trazabilidad Obligatoria:** Exigencia estricta de identificación del técnico/editor y justificación técnica para cualquier guardado, modificación de caption o reversión.
  * **Comparador Visual de Cambios (Diff Viewer):** Comparación línea a línea con sintaxis unificada `diff`.
  * **Rollback Seguro:** Restauración con un clic a cualquier versión histórica previa con registro de auditoría.
  * **Registro Central de Auditoría (`data/audit_log.json`):** Trazabilidad global de todas las operaciones realizadas en la plataforma.

* **Generador Ampliado de Documentación y Runbooks:**
  * **Creación de Nuevos Tipos de Procedimientos:** Capacidad de definir nuevos tipos de procedimientos personalizados con persistencia permanente en `data/plantillas_custom.json`.
  * **Catálogo Oficial:** Plantillas estándar para Rollback, Despliegue CI/CD, Postmortem P1, Microservicios, Contingencia/Failover, Parchado de SO, Renovación de Certificados SSL/TLS, Disaster Recovery (DRP) y Respaldo de BD.
  * **Gobernanza Operativa:** Campos para Ambiente Objetivo, Criticidad / SLA, Ventana de Mantenimiento y Servidores Afectados.

* **Pipeline de Ingesta Masiva Multihilo (`batch_ingest.py`):**
  * Conversión paralela multihilo con soporte para unidades de red compartidas (`Z:\` o rutas UNC) y control de inmutabilidad mediante manifiesto SHA-256 (`data/ingestion_manifest.json`).

* **Compatibilidad de Tema (Theme-Safe):**
  * Diseño visual adaptativo 100% compatible con Tema Claro (*Light*) y Tema Oscuro (*Dark*).

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
├── GEMINI.md                          # Reglas y directrices de desarrollo corporativas
│
├── core/                              # Módulos centrales de lógica de negocio
│   ├── __init__.py                    # Exportaciones del paquete core
│   ├── auditoria.py                   # Versionado, snapshots inmutables, Diff y auditoría
│   ├── configuracion.py               # Rutas globales y aseguramiento de directorios
│   ├── estilos.py                     # Cargador dinámico de reglas visuales CSS
│   ├── estilos.css                    # Hoja de estilos CSS corporativa (Theme-Safe)
│   ├── motor.py                       # Motor analítico DuckDB, búsqueda y Copilot
│   ├── procesador.py                  # Ingesta, lectura multiformato y fichas de diagramas
│   ├── plantillas.py                  # Catálogo oficial y gestor de plantillas personalizadas
│   ├── topologia.py                   # Diagrama Mermaid y especificación de capas
│   └── visor.py                       # Visor Lado a Lado (Side-by-Side) y renderizado adaptativo
│
└── data/
    ├── inbox/                         # Carpeta de entrada para procesamiento por lotes
    ├── docs/                          # Repositorio de documentación técnica indexada (.md)
    │   └── assets/                    # Repositorio central de imágenes y diagramas gráficos
    ├── originals/                     # Copias binarias inmutables de archivos originales
    ├── history/                       # Snapshots inmutables y metadatos de versiones históricas
    ├── audit_log.json                 # Log centralizado de auditoría y trazabilidad
    ├── plantillas_custom.json         # Registro persistente de tipos de plantillas creadas
    ├── mantenimientos.csv             # Base de datos estructurada de inventario y mantenimientos
    └── ingestion_manifest.json        # Manifiesto con firmas SHA-256 de archivos procesados
```

---

## 3. Instalación y Puesta en Marcha

### 3.1 Requisitos Previos
* Python 3.10 o superior instalado en el sistema operativo Windows / Linux.

### 3.2 Configuración del Entorno Virtual
```cmd
# 1. Crear el entorno virtual
python -m venv .venv

# 2. Activar el entorno virtual
# En Windows CMD:
.venv\Scripts\activate
# En Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# 3. Instalar las dependencias del proyecto
pip install -r requirements.txt
```

### 3.3 Iniciar la Aplicación
* **Opción Rápida (Recomendada en Windows):** Doble clic en `run_app.bat` (o ejecutar `.\run_app.ps1`).
* **Vía Terminal:**
  ```cmd
  .venv\Scripts\streamlit run app.py
  ```

El dashboard se abrirá automáticamente en el navegador en `http://localhost:8501`.

---

## 4. Manual de Uso por Módulo

### 4.1 Panel Lateral (Sidebar)
1. **Subida de Archivos:**
   * Arrastre uno o varios archivos (`.pdf`, `.docx`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.md`, `.pptx`, `.png`, `.jpg`, `.svg`).
   * El sistema detecta el tipo de archivo, guarda una copia binaria en `data/originals/`, almacena las imágenes en `data/docs/assets/`, genera la ficha Markdown normalizada en `data/docs/` y registra la versión inicial `v1`.
2. **Filtros de Base Documental:**
   * Permite filtrar la lista de documentos cargados por categoría (*Todos, Diagramas / Imágenes, Excel, Documentos Word/PDF, Markdown / Texto*).
3. **Acciones Rápidas:**
   * `Reindexar`: Recarga en memoria todos los documentos de `data/docs/` y activos de `data/docs/assets/`.
   * `Limpiar Chat`: Reinicia el historial de la conversación actual.

---

### 4.2 Pestaña 1: Consultar dudas (Buscar por palabras)
* **Función:** Asistente conversacional de operaciones con búsqueda híbrida.
* **Modo de Uso:**
  1. Ingrese una consulta técnica en el campo de texto inferior (ej. *"¿Cuál es la IP y estado de BALANCER001?"*, *"Procedimiento de contingencia WSO2"* o *"SN-8842-A"*).
  2. El asistente correlaciona DuckDB y los documentos indexados, respondiendo con tablas de atributos, fragmentos de procedimientos y enlaces a diagramas.

---

### 4.3 Pestaña 2: Historial de Mantenimientos
* **Función:** Motor analítico SQL sobre el inventario y mantenimientos de servidores.
* **Modo de Uso:**
  1. Utilice los filtros superiores para acotar por **Nivel de Arquitectura** (L1 a L4), **Estado Operativo** (Operativo, En Revisión, Crítico) o **Técnico**.
  2. Despliegue el panel **"Ejecutar Consulta SQL Personalizada"** para ejecutar sentencias SQL directas en DuckDB (ej. `SELECT tecnico, count(*) FROM read_csv_auto('data/mantenimientos.csv') GROUP BY tecnico`).

---

### 4.4 Pestaña 3: Documentación Técnica y Versionado
* **Función:** Repositorio central de manuales, diagramas de topología, CMDBs, edición en vivo y auditoría.
* **Modo de Uso:**

#### A. Visualización Lado a Lado (Side-by-Side)
* **Para Diagramas e Imágenes:** Muestra la imagen en resolución completa con su **Pie de Imagen (*Caption*)** activo, formulario de edición auditada del caption y botón de descarga de la imagen original.
* **Para Documentos (PDF, Word, Excel, Markdown):**
  * Alterne entre los modos **[Lado a Lado]**, **[Solo Markdown]** y **[Solo Formato Original]**.
  * En modo Lado a Lado, compare la versión Markdown indexada frente al PDF embebido, la cuadrícula multihoja de Excel o el archivo original.

#### B. Edición de Documentos
* **Libros Excel:** Edite valores celda a celda directamente en la cuadrícula (`st.data_editor`), agregue filas y guarde la nueva versión.
* **Diagramas:** Actualice el pie descriptivo (*Caption*), editor responsable y motivo.
* **Documentos Markdown:** Modifique procedimientos o parámetros técnicos en el editor de texto.
* *Nota:* Para guardar cualquier versión es obligatorio ingresar el **Editor / Técnico Responsable** y el **Motivo del Cambio**.

#### C. Historial de Versiones y Rollback
1. **Tabla Cronológica:** Visualice todas las versiones registradas con fecha, autor, motivo y tamaño.
2. **Comparador Diff:** Seleccione dos versiones cualesquiera para inspeccionar las diferencias línea por línea con resaltado de sintaxis.
3. **Descarga de Históricos:** Descargue el snapshot inmutable de cualquier versión histórica previa en formato `.xlsx` o `.md`.
4. **Ejecución de Rollback:** Seleccione una versión previa, ingrese el Técnico responsable y la justificación técnica, y confirme la restauración para volver a ese estado operativo.

---

### 4.5 Pestaña 4: Plantillas de Documentación y Runbooks
* **Función:** Generador de procedimientos técnicos estandarizados y creador de nuevos tipos de plantillas.
* **Modo de Uso:**
  1. En **Tipo de Procedimiento**, seleccione una plantilla oficial (Rollback, Despliegue, Postmortem P1, Microservicio, Contingencia, Parchado, Certificados SSL, DRP, Backup BD) o elija `[+ Crear Nuevo Tipo de Procedimiento...]`.
  2. Si crea un tipo nuevo, defina el nombre y marque la opción para guardarlo en el catálogo permanente (`data/plantillas_custom.json`).
  3. Complete los metadatos de gobernanza (Autor, Servicio, Nivel, Ambiente Objetivo, Criticidad, Ventana y Servidores Involucrados).
  4. Complete los pasos técnicos específicos en los campos dinámicos.
  5. Revise la previsualización en vivo en la columna derecha y haga clic en **Guardar y Publicar en Base de Conocimiento**. El documento quedará inmediatamente indexado como `v1`.

---

### 4.6 Ingesta Masiva por Lote (`batch_ingest.py`)
Para procesar cientos de documentos o sincronizar con una carpeta de red compartida (`Z:\`):

```cmd
# Ingesta estándar desde data/inbox/
python batch_ingest.py

# Ingesta desde una unidad de red compartida o ruta personalizada con 8 hilos
python batch_ingest.py --origen Z:\Infraestructura\Documentos --workers 8
```

El script procesa recursivamente todos los archivos soportados, preserva binarios en `data/originals/`, copia imágenes a `data/docs/assets/`, genera fichas `.md` en `data/docs/` y registra las firmas en `data/ingestion_manifest.json`.

---

## 5. Matriz de Tecnologías y Dependencias

| Componente | Tecnología / Librería | Propósito en el Sistema |
| :--- | :--- | :--- |
| **Framework de Aplicación** | [Streamlit](https://streamlit.io/) | Dashboard interactivo web, visualizadores y edición en cuadrícula |
| **Motor SQL Analítico** | [DuckDB](https://duckdb.org/) | Consultas tabulares ultrarrápidas en memoria sobre archivos CSV |
| **Motor de Extracción Universal** | [Microsoft MarkItDown](https://github.com/microsoft/markitdown) | Conversión de documentos Word, PDF, PowerPoint y texto |
| **Procesador de CMDBs y Excel** | [OpenPyXL](https://openpyxl.readthedocs.io/) / `excel_cleaner.py` | Extracción estructurada y edición de libros multihoja |
| **Manipulación de Datos** | [Pandas](https://pandas.pydata.org/) | Gestión de DataFrames, transformaciones y exportaciones |
| **Comparador de Versiones** | Python `difflib` | Generación de diferencias unificadas (*Diff*) |
| **Auditoría e Inmutabilidad** | Python `hashlib` (SHA-256) | Firmas criptográficas y verificación de integridad de archivos |
| **Diagramas y Topologías** | [Mermaid.js](https://mermaid.js.org/) | Renderizado de diagramas de arquitectura y mapas de dependencias |
| **Integración con IA (Opcional)** | Google GenAI SDK (`google-genai`) | Conexión con modelos Gemini mediante inyección RAG |

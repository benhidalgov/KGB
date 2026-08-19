# Copilot de Infraestructura y Operaciones (AIOps)

Asistente inteligente corporativo y motor de búsqueda dual diseñado para la gestión de infraestructura, análisis de mantenimientos en tiempo real y recuperación de procedimientos técnicos operativos.

---

## 🌟 Características Principales

* **Motor de Búsqueda Dual:**
  * **Analítico / Estructurado (DuckDB):** Consultas ultra-rápidas en memoria sobre el inventario y mantenimientos (`data/mantenimientos.csv`) por número de serie, IP, servidor, técnico o componente.
  * **Documental / No Estructurado (MarkItDown):** Búsqueda contextual y por palabras clave en manuales operativos, contingencias, reportes postmortem y guías técnicas.
* **Modos de Operación:**
  * **Modo Local Autónomo (Por defecto):** No requiere conexión a internet ni llaves de API. Genera fichas técnicas formateadas y extractos documentales al instante.
  * **Modo Asistido por LLM (Opcional):** Permite ingresar una API Key de OpenAI (`gpt-4o-mini`) para sintetizar respuestas complejas y correlacionar ambas fuentes de datos.
* **Pipeline de Ingesta Masiva Multihilo:**
  * Conversión automática de documentos (`.pdf`, `.docx`, `.xlsx`, `.pptx`, `.md`, `.txt`) a Markdown optimizado.
  * Control de inmutabilidad y caché basado en firmas criptográficas **SHA-256** para evitar reprocesamiento redundante.
* **Mapeo de Arquitectura en 4 Niveles:**
  * Visualización topológica jerárquica (L1: Hardware, L2: Virtualización, L3: Middleware, L4: Aplicaciones) y correlación con la capa de Observabilidad (*Nagios, New Relic, VZOR, PRTG*).

---

## 📁 Estructura del Proyecto

```text
C:\Prototipo\
│
├── app.py                     # Aplicación principal (Streamlit)
├── batch_ingest.py            # Script de procesamiento e ingesta masiva
├── requirements.txt           # Dependencias de Python
├── run_app.bat                # Acceso directo para iniciar la app en Windows
├── run_app.ps1                # Script de inicio para PowerShell
├── README.md                  # Manual de uso e instrucciones del sistema
├── ARQUITECTURA_COPILOT_INFRAESTRUCTURA.md # Especificación técnica detallada
│
└── data/
    ├── inbox/                 # [ENTRADA] Carpeta para colocar archivos a procesar en lote
    ├── docs/                  # [SALIDA/DOCS] Documentación técnica en formato Markdown
    ├── mantenimientos.csv     # Base de datos de inventario y mantenimientos
    └── ingestion_manifest.json# Manifiesto con firmas SHA-256 de archivos procesados
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Requisitos Previos
* Python 3.10 o superior instalado.

### 2. Configuración del Entorno Virtual (Primera vez)
Si necesitas configurar el entorno desde cero:

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

### 3. Iniciar la Aplicación

Puedes iniciar la aplicación de dos formas:

* **Opción rápida:** Doble clic en `run_app.bat` (o ejecuta `.\run_app.ps1`).
* **Vía terminal:**
  ```cmd
  .venv\Scripts\streamlit run app.py
  ```

La interfaz web se abrirá automáticamente en tu navegador (por defecto en `http://localhost:8501`).

---

## 📖 Guía de Uso

### 1. Ingesta Masiva de Documentos (`batch_ingest.py`)

Para procesar múltiples documentos técnicos a la vez:

1. Coloca tus archivos originales (`.docx`, `.pdf`, `.xlsx`, `.pptx`, `.txt`, `.md`) en la carpeta:
   📂 `data/inbox/`
2. Ejecuta el script de ingesta:
   ```cmd
   .venv\Scripts\python.exe batch_ingest.py
   ```
3. El script:
   * Verificará qué archivos son nuevos o han cambiado mediante **SHA-256**.
   * Los convertirá a Markdown en `data/docs/`.
   * Actualizará el registro en `data/ingestion_manifest.json`.

---

### 2. Uso de la Interfaz Web (Streamlit)

La aplicación cuenta con 4 pestañas principales:

#### 💬 Pestaña 1: Chat Copilot
* Permite hacer preguntas en lenguaje natural sobre la infraestructura.
* **Ejemplos de búsqueda:**
  * Por Servidor o VM: `BALANCER001`, `VM-BOOKING-01`
  * Por Número de Serie: `SN-8842-A`, `HPE-BL-9921`
  * Por Dirección IP: `10.24.0.125`, `10.20.1.50`
  * Por Técnico: `Carlos Mendoza`, `Sofia Morales`
  * Por Procedimiento: `rollback booking`, `contingencia wso2`, `politicas de backup`
* **Configuración de IA (Opcional):** En la barra lateral izquierda puedes ingresar tu **OpenAI API Key** si deseas respuestas generadas por `gpt-4o-mini`. Si no la ingresas, el sistema responde de forma instantánea y local mediante DuckDB y extracción de documentos.

#### 📊 Pestaña 2: Analítica DuckDB
* Tabla dinámica para consultar y filtrar los registros de mantenimiento.
* Filtros interactivos por **Nivel de Arquitectura**, **Estado Operativo** y **Técnico**.
* Consola SQL integrada para ejecutar consultas SQL personalizadas directamente sobre el CSV.

#### 🗺️ Pestaña 3: Arquitectura 4 Niveles
* Diagrama topológico interactivo que ilustra las relaciones de dependencia entre:
  * **L4:** Aplicaciones (Booking Core, CI/CD).
  * **L3:** Middleware (WSO2, Redis).
  * **L2:** Virtualización (VMware vCloud Director).
  * **L1:** Hardware base (HPE Blade, Pure Storage SAN).
  * **Capa de Observabilidad:** Nagios Core, New Relic, VZOR Suite y PRTG.

#### 📚 Pestaña 4: Documentación Técnica
* Visor y lector integrado de todos los manuales y documentos técnicos indexados en el sistema.

---

## 🛠️ Tecnologías Utilizadas

* **Framework Web:** [Streamlit](https://streamlit.io/)
* **Motor SQL en Memoria:** [DuckDB](https://duckdb.org/)
* **Conversión Documental:** [Microsoft MarkItDown](https://github.com/microsoft/markitdown)
* **Manipulación de Datos:** [Pandas](https://pandas.pydata.org/)
* **IA / LLM (Opcional):** [OpenAI API](https://platform.openai.com/)

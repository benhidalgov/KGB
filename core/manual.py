"""
Módulo de documentación interactiva y Manual de Usuario del Copilot de Infraestructura y AIOps.
"""
import streamlit as st
import streamlit_antd_components as sac


def renderizar_manual_usuario():
    """Renderiza el manual interactivo de operaciones y guía de arquitectura del sistema."""
    st.markdown('<p class="main-title">Manual de Operaciones y Guía del Sistema</p>', unsafe_allow_html=True)
    st.caption("Guía técnica detallada sobre las capacidades, módulos, motores de búsqueda y directrices operativas de la plataforma.")

    tab_m1, tab_m2, tab_m3, tab_m4, tab_m5, tab_m6 = st.tabs([
        "1. Visión General",
        "2. Motor de Búsqueda y Score",
        "3. Visor Lado a Lado",
        "4. Versionado y Rollback",
        "5. Plantillas y Runbooks",
        "6. Ingesta Masiva (CLI)"
    ])

    # ----------------- SECCIÓN 1: VISIÓN GENERAL -----------------
    with tab_m1:
        st.subheader("1. Arquitectura y Capacidades de la Plataforma")

        st.markdown("""
El **Copilot de Infraestructura y Operaciones (AIOps)** es un sistema unificado para la gestión de activos técnicos, diagnóstico de incidentes, consulta analítica de inventarios y mantenimiento de documentación operativa.

---

### Módulos Principales del Sistema:
1. **Motor de Búsqueda Dual:**
   * **Motor Analítico DuckDB:** Consultas SQL ultrarrápidas en memoria sobre el inventario (`data/mantenimientos.csv`).
   * **Motor Documental Full-Text:** Búsqueda normalizada por palabras clave, siglas y frases sobre manuales y procedimientos (`data/docs/`).
2. **Visor Comparativo Lado a Lado (Side-by-Side):**
   * Visualización simultánea de la representación Markdown indexable frente al archivo fuente original (PDF embebido, Excel interactivo, diagramas e imágenes en alta resolución).
3. **Auditoría e Inmutabilidad:**
   * Control estricto de versiones con snapshots inmutables (`data/history/`), registro cronológico de autor y justificación técnica en `data/audit_log.json`.
4. **Generador de Procedimientos y Runbooks:**
   * Asistente estructurado para crear procedimientos técnicos estandarizados y definir nuevos tipos personalizados con almacenamiento persistente.
5. **Worker de Ingesta Masiva (`batch_ingest.py`):**
   * Procesamiento multihilo por lotes con cálculo de firmas criptográficas **SHA-256**.
        """)

    # ----------------- SECCIÓN 2: MOTOR DE BÚSQUEDA Y SCORE -----------------
    with tab_m2:
        st.subheader("2. Motor de Búsqueda y Algoritmo de Relevancia (Score)")

        st.markdown("""
El motor de búsqueda correlaciona la base de datos estructurada con el repositorio documental técnico.

---

### ¿Cómo buscar información?
* **Por Servidor o Identificador:** Ingrese `BALANCER001`, `DB-POSTGRES-01`, `VM-BOOKING-01`.
* **Por Número de Serie:** Ingrese `SN-8842-A`, `SN-9912-B`.
* **Por Dirección IP:** Ingrese `10.24.0.125`, `10.24.0.126`, `10.24.0.130`.
* **Por Tecnologías o Conceptos:** Ingrese `JWT`, `WSO2`, `Redis`, `Rollback`, `Failover`, `SSL`.

---

### Algoritmo de Cálculo del Score (Puntuación de Relevancia):
El sistema asigna una puntuación numérica a cada documento para clasificar los resultados de mayor a menor relevancia:

| Criterio Evaluado | Puntos Asignados | Explicación |
| :--- | :--- | :--- |
| **Frase Exacta en Contenido** | **+30 pts** | La consulta aparece textual y completa dentro del documento. |
| **Coincidencia en Nombre de Archivo** | **+20 pts** | Algún término de la consulta coincide con el nombre del documento. |
| **Frecuencia de Términos (Densidad)** | **+2 pts por aparición** | Mayor repetición de las palabras clave dentro del cuerpo del texto. |

* **Alta Relevancia (`>= 20 pts`):** Coincidencia directa en títulos o párrafos clave.
* **Media Relevancia (`< 20 pts`):** Coincidencia contextual o mención secundaria.
        """)

    # ----------------- SECCIÓN 3: VISOR LADO A LADO -----------------
    with tab_m3:
        st.subheader("3. Visor Lado a Lado (Side-by-Side) y Renderizado Adaptativo")

        st.markdown("""
El **Visor Lado a Lado** permite verificar y comparar la versión procesada que utiliza el motor de búsqueda frente al documento binario original cargado por el equipo.

---

### Comportamiento según el Formato del Archivo:

1. **Diagramas e Imágenes (`.png`, `.jpg`, `.svg`, `.webp`):**
   * Se muestra la imagen en resolución completa.
   * Cuenta con un apartado de **Pie de Imagen (*Caption*)** editable, donde se requiere obligatoriamente registrar el Editor Responsable y el Motivo del Cambio antes de guardar una nueva versión.
   * Incluye botón para descargar la imagen original.

2. **Libros de Cálculo Excel (`.xlsx`, `.xls`):**
   * La columna derecha despliega una **cuadrícula interactiva** (`st.dataframe`) con selector de hojas de trabajo (*Sheet Selector*).
   * La columna izquierda muestra la normalización en tablas Markdown.

3. **Documentos PDF (`.pdf`):**
   * Renderizado nativo embebido en la página mediante un `iframe` seguro en Base64.
   * Permite lectura, zoom, impresión y búsqueda nativa dentro del PDF.

4. **Documentos Ofimáticos Word / PowerPoint (`.docx`, `.pptx`):**
   * Despliega una tarjeta de especificación técnica y botón de descarga directa del binario original resguardado en `data/originals/`.
        """)

    # ----------------- SECCIÓN 4: VERSIONADO Y AUDITORÍA -----------------
    with tab_m4:
        st.subheader("4. Control de Versiones, Diff y Rollback con Auditoría")

        st.markdown("""
Toda modificación realizada sobre un documento técnico, libro Excel o diagrama genera una nueva versión inmutable con trazabilidad total.

---

### Reglas de Auditoría Obligatoria:
1. **Identificación Obligatoria:** Todo guardado o reversión exige ingresar el **Editor / Técnico Responsable (*)** y el **Motivo del Cambio (*)**.
2. **Inmutabilidad (`data/history/`):** El estado anterior se almacena en una copia histórica inalterable (`v1`, `v2`, etc.).
3. **Registro Central (`data/audit_log.json`):** Cada evento registra marca temporal ISO, autor, motivo, diferencias y versión resultante.

---

### Comparador de Versiones (Diff Viewer):
* En la subpestaña **Historial de Versiones**, seleccione dos versiones cualesquiera para inspeccionar la comparación línea por línea con sintaxis unificada `diff`.

---

### Procedimiento de Rollback Seguro:
1. En la subpestaña **Historial de Versiones**, seleccione la versión previa a la que desea retornar.
2. Ingrese su nombre/rol en *Editor que ejecuta el Rollback* y la justificación técnica.
3. Haga clic en **Confirmar y Ejecutar Rollback**. El sistema restaurará el archivo y generará una nueva versión incremental registrando el evento de restauración.
        """)

    # ----------------- SECCIÓN 5: PLANTILLAS Y RUNBOOKS -----------------
    with tab_m5:
        st.subheader("5. Generador de Plantillas y Runbooks Estandarizados")

        st.markdown("""
El generador permite publicar procedimientos técnicos homologados con gobernanza operativa en menos de 2 minutos.

---

### Catálogo de Plantillas Oficiales:
* **Procedimiento de Rollback de Emergencia:** Criterios de activación, comandos de reversión y verificación post-rollback.
* **Paso a Producción / Despliegue CI/CD:** Variables de entorno, secrets en KeyVault y smoke tests.
* **Reporte Postmortem / Incidente P1 (RCA):** Resumen de impacto, diagnóstico de causa raíz y medidas preventivas.
* **Ficha Técnica de Microservicio / API:** Endpoints base, autenticación, dependencias y telemetría APM/Nagios.
* **Guía de Contingencia y Failover Operativo:** Síntomas de falla, conmutación HAProxy y validación DNS.
* **Procedimiento de Parchado y Mantenimiento de SO:** Alcance de parches, pasos de aplicación y plan de reversión.
* **Renovación de Certificados SSL/TLS:** Comandos OpenSSL, instalación y validación de vigencia.
* **Plan de Recuperación ante Desastres (DRP):** Objetivos RPO/RTO y conmutación a Datacenter DR.
* **Plan de Respaldo y Restauración de Base de Datos:** Scripts de backup y restore.

---

### Definición de Tipos Personalizados:
* Al seleccionar `[+ Crear Nuevo Tipo de Procedimiento...]`, puede definir un nuevo tipo operativo y marcar la opción para guardarlo permanentemente en el catálogo (`data/plantillas_custom.json`).
        """)

    # ----------------- SECCIÓN 6: INGESTA MASIVA CLI -----------------
    with tab_m6:
        st.subheader("6. Worker de Ingesta Masiva Multihilo (`batch_ingest.py`)")

        st.markdown(r"""
Para procesar volúmenes masivos de documentos o sincronizar periódicamente con repositorios compartidos de red:

---

### Ejecución por Línea de Comandos:

```cmd
# 1. Ingesta estándar desde la carpeta data/inbox/
python batch_ingest.py

# 2. Ingesta desde una unidad de red compartida (Z:\) o carpeta externa con 8 hilos
python batch_ingest.py --origen Z:\Infraestructura\Manuales --workers 8
```

---

### Proceso Interno de Ingesta:
1. **Detección Recursiva:** Escanea subcarpetas buscando archivos `.pdf`, `.docx`, `.xlsx`, `.png`, `.jpg`, etc.
2. **Firma Criptográfica SHA-256:** Compara el hash contra `data/ingestion_manifest.json` para omitir archivos sin cambios.
3. **Resguardo de Binarios:** Copia los archivos originales a `data/originals/` y las imágenes a `data/docs/assets/`.
4. **Normalización:** Genera las fichas Markdown en `data/docs/` listas para indexación inmediata.
        """)

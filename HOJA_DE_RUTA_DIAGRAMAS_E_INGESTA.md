# Hoja de Ruta: Procesamiento de Diagramas, Ingesta y Evolución del Sistema

Este documento contiene el registro de avances completados y la planificación técnica para la evolución del **Copilot de Infraestructura y Operaciones**.

---

## 1. Registro de Hitos y Funcionalidades Completadas

- [x] **Paso 1: Ingesta Recursiva y Rutas de Red** *(COMPLETADO)*
  - Soporte de subcarpetas y árboles de directorios profundos sin colisiones de nombres (`Carpeta__Subcarpeta__archivo.md`).
  - Inyección de metadatos de origen en el encabezado de cada documento indexado.
  - Parámetro CLI `--origen` para apuntar a carpetas locales o unidades de red compartidas (`Z:\` o rutas UNC).

- [x] **Paso 2: Ingesta de Diagramas, Assets y Visor Lado a Lado (*Side-by-Side*)** *(COMPLETADO)*
  - Soporte de extensiones `.png`, `.jpg`, `.jpeg`, `.webp`, `.svg` en `batch_ingest.py` y subida web.
  - Almacenamiento organizado de activos gráficos en `data/docs/assets/` y resguardo inmutable de archivos binarios originales en `data/originals/`.
  - Generación de fichas técnicas Markdown asociadas con firmas criptográficas **SHA-256**.
  - Visor Lado a Lado con renderizado adaptativo (Imágenes nativas en alta resolución, PDFs embebidos en iframe Base64, libros Excel interactivos con selector de hojas y documentos Word/PPTX).
  - Gestión de **Pie de Imagen (*Caption*)** con trazabilidad obligatoria de Editor y Motivo del Cambio.

- [x] **Paso 3: Consola de Búsqueda Superior (*Search On-Top*), Resaltado Visual y Algoritmo de Score** *(COMPLETADO)*
  - Reubicación de la barra de búsqueda en la parte superior (*Always On-Top*) con orden cronológico descendente (los resultados más nuevos aparecen inmediatamente arriba).
  - Algoritmo de puntuación de relevancia (**Score**): +30 pts por frase exacta, +20 pts por coincidencia en título, +2 pts por densidad de términos.
  - Normalización de acentos/tildes y soporte para siglas técnicas cortas (>= 2 caracteres: `JWT`, `IP`, `SSL`, `TLS`, `DNS`, `VM`, `DB`, `L1`-`L4`).
  - Resaltado visual automático de términos coincidentes (*Keyword Highlighting*) y tarjetas estructuradas (*Result Cards*).
  - Chips de consultas rápidas en la cabecera (`[BALANCER001]`, `[Autenticación JWT]`, `[10.24.0.125]`, `[Failover Redis]`, `[SN-8842-A]`).

- [x] **Paso 4: Generador de Procedimientos Ampliado y Plantillas Dinámicas** *(COMPLETADO)*
  - Catálogo oficial ampliado: Rollback, Despliegue CI/CD, Postmortem P1, Microservicios, Contingencia/Failover, Parchado de SO, Renovación de Certificados SSL/TLS, Disaster Recovery (DRP) y Respaldo de BD.
  - Capacidad de definir **Nuevos Tipos de Procedimientos Personalizados** con persistencia en `data/plantillas_custom.json`.
  - Barra guiada de pasos **`sac.steps`** (Paso 1: Metadatos ──► Paso 2: Parámetros ──► Paso 3: Publicación).

- [x] **Paso 5: Manual Interactivo de Operaciones y Navegación Centralizada** *(COMPLETADO)*
  - Módulo interactivo [`core/manual.py`](file:///C:/prototipo/core/manual.py) integrado con selector `[Consola]` | `[Manual de Uso]`.
  - Redacción práctica, directa y accesible sin perder el rigor técnico y respetando la regla de cero emojis.

- [x] **Paso 6: Control de Versiones Incremental, Rollback y Registro de Auditoría Global** *(COMPLETADO)*
  - Sistema de snapshots inmutables en `data/history/<doc_name>/` (`v1.md`, `v2.md`, metadata JSON y copias originales de Excel).
  - Tabla de historial de revisiones con timestamp, editor responsable y motivo del cambio.
  - Descarga en un clic de versiones previas tanto en formato Markdown como en libros Excel originales `.xlsx`.
  - Mecanismo de **Rollback seguro** con validación obligatoria de editor y justificación técnica registrada en `data/audit_log.json`.
  - Comparador Diff lado a lado y visor de auditoría global integrados en expanders limpios.

- [x] **Paso 7: Navbar Superior Flotante con Relieve, Paleta Obsidian & Indigo y Estandarización Visual** *(COMPLETADO)*
  - **Navbar Hero Card:** Contenedor superior flotante con gradiente Índigo translúcido, borde brillante y sombra de elevación moderna.
  - Indicador de estado en tiempo real `● ONLINE` en Verde Menta Nórdico junto al Brand corporativo.
  - **KPI Stat Chips:** Micro-tarjetas ampliadas de alta legibilidad para conteo en vivo de `Documentos` e `Inventario CMDB`.
  - **Pestañas Dinámicas:** Estandarización de títulos con contadores automáticos (`Consultas y Búsqueda`, `Historial de Mantenimientos (10)`, `Documentación Técnica (23)`, `Plantillas y Runbooks`).
  - **Paleta Obsidian & Indigo (Theme-Safe):** Acentos en Índigo (`#6366F1`), estados operativos `[OK]` (`#10B981`), `[WARN]` (`#D97706`), `[CRIT]` (`#E11D48`) y bordes laterales de 3.5px en tarjetas de búsqueda.
  - **Gobernanza:** Prohibición estricta de la palabra "AIOps" y política de cero emojis en todo el proyecto.

- [x] **Paso 8: Normalizador Integral de Nombres y Estandarización de Archivos** *(COMPLETADO)*
  - Sanitización automática de nombres de archivo a `snake_case` seguro en disco (`normalizar_nombre_archivo`), eliminando acentos, caracteres conflictivos y dobles extensiones.
  - Formateo corporativo en interfaz (`normalizar_titulo_display`) respetando acrónimos técnicos (`CMDB`, `SAN`, `WSO2`, `JWT`, `IP`, `HPE`, `PureStorage`, `VMware`, etc.).
  - Integración transversal en panel lateral de carga, ingesta masiva (`batch_ingest.py`), explorador documental, selector de documentos (`format_func`) y tarjetas de búsqueda.

- [x] **Paso 9: Renderizado de Imágenes en Vista Formateada y Extracción de Medios DOCX** *(COMPLETADO)*
  - Activación de `keep_data_uris=True` en Microsoft MarkItDown para preservar imágenes completas de documentos Word (.docx).
  - Normalizador de medios Markdown (`preparar_markdown_con_imagenes`) que resuelve rutas locales relativas a Data URIs base64.
  - Motor de auto-recuperación (`extraer_imagenes_de_docx`) para reconstruir imágenes en caliente desde el contenedor ZIP de Word.
  - Inyección de esquemas gráficos centrados con caption en fichas de diagramas (`DIAGRAMA__*.md`).
  - Separación entre visualización enriquecida (`unsafe_allow_html=True`) en **Vista Formateada** y código Markdown limpio en **Código Markdown**.

- [x] **Paso 10: Optimización de Rendimiento, Caché Multinivel e Integridad de Sesión** *(COMPLETADO)*
  - Supresión de reloads superfluos de módulos que ralentizaban la interacción en cada ciclo de Streamlit.
  - Caché `@st.cache_data` indexada por `mtime` en `_cargar_documento_individual_cached`, reduciendo el parsing inicial de 3.28s a 0.0025s.
  - Carga condicional en `st.session_state` para evitar lecturas de disco innecesarias.
  - Caché LRU para auditoría, metadata y fechas de carga de documentos.
  - Caché de hojas de cálculo Excel (`cargar_hoja_excel_dataframe` y `obtener_nombres_hojas_excel`).
  - Claves dinámicas versionadas (`quick_pills_version`) para evitar `StreamlitAPIException`.

- [x] **Paso 11: Bóveda de Seguridad Local Cifrada (AES-256 / Fernet)** *(COMPLETADO)*
  - Custodia simétrica en `core/vault.py` con almacenamiento inmutable en `data/vault.enc`.
  - Derivación criptográfica PBKDF2HMAC con SHA-256 y 100,000 iteraciones.
  - Jerarquía de resolución en cascada (OS Environ -> Bóveda Cifrada -> Streamlit Secrets).
  - Cegado total de credenciales y supresión de botones reveladores en la interfaz CSS.
  - Limpieza automática de inputs de clave tras guardar o revocar.

- [x] **Paso 12: Motor Dual con Inferencia Google Gemini RAG (`gemini-3.6-flash`)** *(COMPLETADO)*
  - Integración nativa del SDK oficial `google-genai` respetando la directriz de ingeniería principal.
  - Ensamblador contextual RAG inyectando registros DuckDB y fragmentos documentales normalizados.
  - Conmutación transparente y resiliente a motor local autónomo ante falta de API Key o fallos de red.
  - Trazabilidad explícita de modelo y fuentes de evidencia en cada respuesta técnica.

- [x] **Paso 13: Consola de Telemetría e Integración SAP S/4HANA (API)** *(COMPLETADO)*
  - Pestaña dedicada con monitoreo de endpoints REST/OData para instancias ASCS, PAS, AAS y Web Dispatcher.
  - Diagrama dinámico Mermaid de topología de base de datos SAP HANA 2.0 con HSR en tiempo real.
  - Visor interactivo de payload JSON para auditoría de interfaces.
  - Botón de sincronización bidireccional automática hacia la CMDB local DuckDB.

- [x] **Paso 14: Aceleración de Rendimiento, Query Response Cache en RAM y Pre-Cálculo Documental** *(COMPLETADO)*
  - Implementación de `_QUERY_RESPONSE_CACHE` (LRU) en `core/motor.py`, reduciendo la latencia en consultas repetidas de 13,405 ms a **0.79 ms** en RAM.
  - Pre-normalización de textos en memoria (`_DOC_STORE_NORM_CACHE`) para acelerar búsquedas léxicas a sub-milisegundo (0.01 ms).
  - Conexión persistente DuckDB en RAM (`_obtener_conexion_duckdb`) con Zero Disk I/O.
  - Reubicación ergonómica del botón `>_ Limpiar Chat` en la cabecera de resultados y purga de secciones superfluas en el sidebar.

- [x] **Paso 15: Arquitectura de Búsqueda Dual en Consola (DuckDB < 2 ms + Gemini RAG)** *(COMPLETADO)*
  - Separación de la Pestaña 1 en dos subpestañas dedicadas con roles perfectamente diferenciados.
  - Subpestaña 1 `Búsqueda Textual (DuckDB & Docs)`: Consultas indexadas instantáneas (< 2 ms) en memoria RAM, cuadrícula estructurada de servidores en CMDB, extractos documentales con `<mark>` y botón puente hacia el Copilot.
  - Subpestaña 2 `Copilot de Infraestructura (Gemini RAG)`: Razonamiento técnico con Gemini 2.5 Flash, diagnósticos RCA, runbooks asistidos y bitácora de diálogo.

- [x] **Paso 16: Control de Acceso y Autenticación Corporativa Basada en Roles (RBAC)** *(COMPLETADO)*
  - Compuerta de autenticación perimetral (`core/auth.py`) con pantalla de login empresarial Obsidian & Indigo.
  - Bloqueo total de la ejecución (`st.stop()`) ante usuarios no autenticados para proteger la privacidad de la CMDB y la cuota de la API Key.
  - Roles granulares (`Administrador`, `Operador`, `Auditor`), contraseñas con PBKDF2-HMAC-SHA256, soporte de variables maestras vía `st.secrets` y bitácora de inicios de sesión en `audit_log.json`.
  - Tarjeta de usuario activo en el sidebar con botón `>_ Cerrar Sesión` y restricción de la Bóveda `[VAULT]` exclusiva para administradores.

- [x] **Paso 17: Ingesta Batch Web con Soporte Nativo de Paquetes ZIP** *(COMPLETADO)*
  - Cargador web ampliado en el panel lateral que acepta selección masiva de archivos y paquetes comprimidos `.zip`.
  - Descompresión en memoria (`io.BytesIO` y `zipfile`), sanitización de nombres, preservación de binarios en `data/originals/`, generación de versión inmutable `v1` e indexación en caliente en `doc_store` y DuckDB.

- [x] **Paso 18: Blindaje de Rendimiento y Prevención de Bloqueos en Visores** *(COMPLETADO)*
  - Configuración de MarkItDown con `keep_data_uris=False` para evitar inyecciones masivas de Base64 (reducción de 4 MB a 23 KB en documentos Word densos).
  - Visor de código fuente limitado a 50 KB para salvaguardar el hilo JavaScript (Prism.js), editor textarea truncado a 100 KB, umbral de 2.5 MB para PDFs embebidos (con tarjeta de descarga directa) y comparador Diff limitado a 400 líneas.
  - Rutina de auto-saneamiento en caliente en `app.py` ante residuos binarios obsoletos en memoria de sesión.

- [x] **Paso 19: Desacoplamiento de Arquitectura y Despliegue en Streamlit Cloud (Python 3.12 LTS)** *(COMPLETADO)*
  - Saneamiento de `core/__init__.py` eliminando dependencias circulares cruzadas en el paquete raíz para compatibilidad absoluta en entornos Linux/Cloud.
  - Archivo `.python-version` fijando Python 3.12 LTS oficial, evitando builds automáticos inestables de Python 3.14.
  - Integración transparente con `st.secrets` para inyección segura de `GEMINI_API_KEY` y `ADMIN_PASSWORD`.

---

## 2. Próximos Pasos y Roadmap de Desarrollo

### Paso 20: Extracción de Contenido Gráfico (OCR y Visión Multimodal con IA)
**Objetivo:** Hacer que los diagramas sean buscables por el Copilot mediante su contenido textual interno (nombres de servidores, puertos, flujos, direcciones IP dentro de la imagen).

1. **Estrategia A — OCR Local (Offline / Sin costo de API):**
   * Integración de `easyocr` o `pytesseract` para extraer cajas de texto y etiquetas de topología.
2. **Estrategia B — Visión Multimodal con Google GenAI SDK (`gemini-2.5-flash`):**
   * Análisis automático de la arquitectura visual para generar un resumen técnico estructurado:
     * *Propósito de la topología.*
     * *Componentes e interfaces involucradas.*
     * *Puntos de contingencia y failover.*
3. **Indexación:**
   * Inyectar automáticamente el texto y resumen extraído dentro de la ficha Markdown del diagrama para su recuperación en búsquedas.

---

### Paso 16: Galería Multimedia y Visor de Topologías Interactivo
**Objetivo:** Ofrecer una experiencia visual inmersiva para navegar mapas de infraestructura y diagramas de procesos.

1. **Galería Visual de Diagramas:**
   * Cuadrícula con miniaturas (*thumbnails*), zoom interactivo en modal y filtros por dominio (Redes, Middleware, Bases de Datos).
2. **Editor Topológico Mermaid Avanzado:**
   * Exportación de diagramas a formatos vectoriales `.svg` y sincronización bidireccional entre el código Mermaid y el inventario DuckDB.

---

### Paso 17: Demonio de Sincronización Automática con Carpetas de Red
**Objetivo:** Mantener el Copilot sincronizado automáticamente con repositorios corporativos compartidos (`Z:\` o rutas UNC) en segundo plano.

1. **Tarea Programada / Background Watcher:**
   * Script demonio que detecta nuevos archivos depositados en carpetas de red, ejecuta la ingesta incremental multihilo y notifica en el log de auditoría.
2. **Reportes de Ingesta:**
   * Resumen automático de archivos nuevos, modificados e ignorados con sus firmas SHA-256.

---

## 3. Matriz de Tecnologías Planificadas

| Componente | Librería / Herramienta | Propósito |
| :--- | :--- | :--- |
| **Componentes de UI** | `streamlit-antd-components` | Segmented controls, chips de categorías y barras de progreso por pasos |
| **OCR Local** | `easyocr` / `pytesseract` | Extracción de texto en diagramas de red sin conexión |
| **Visión Multimodal** | `google-genai` (Gemini Vision) | Interpretación semántica de diagramas de arquitectura |
| **Topologías** | `Mermaid.js` | Diagramas interactivos y mapas jerárquicos L1-L4 |
| **Automatización** | Windows Task Scheduler / Python `watchdog` | Sincronización desasistida en segundo plano |

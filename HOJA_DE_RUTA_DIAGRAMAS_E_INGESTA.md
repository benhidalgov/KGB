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

---

## 2. Próximos Pasos y Roadmap de Desarrollo

### Paso 8: Extracción de Contenido Gráfico (OCR y Visión Multimodal con IA)
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

### Paso 9: Galería Multimedia y Visor de Topologías Interactivo
**Objetivo:** Ofrecer una experiencia visual inmersiva para navegar mapas de infraestructura y diagramas de procesos.

1. **Galería Visual de Diagramas:**
   * Cuadrícula con miniaturas (*thumbnails*), zoom interactivo en modal y filtros por dominio (Redes, Middleware, Bases de Datos).
2. **Editor Topológico Mermaid Avanzado:**
   * Exportación de diagramas a formatos vectoriales `.svg` y sincronización bidireccional entre el código Mermaid y el inventario DuckDB.

---

### Paso 10: Demonio de Sincronización Automática con Carpetas de Red
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

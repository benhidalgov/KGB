# Hoja de Ruta: Procesamiento de Diagramas, Imágenes y Unidades de Red

Este documento contiene la planificación detallada y paso a paso para la integración de diagramas de procesos, imágenes de arquitectura y unidades de red compartidas (`Z:\`) en el **Copilot de Infraestructura y AIOps**.

---

## 1. Estado de Avance

- [x] **Paso 1: Ingesta Recursiva y Rutas de Red** *(COMPLETADO)*
  - Soporte de subcarpetas y árboles de directorios profundos sin colisiones (`Carpeta__Subcarpeta__archivo.md`).
  - Metadatos de origen integrados en el encabezado de cada documento.
  - Parámetro CLI `--origen` para apuntar a carpetas locales o unidades de red (`Z:\` o `\\SMUCORPSP02\Infraestructura`).

---

## 2. Pasos Restantes

### Paso 2: Registro e Ingesta de Imágenes y Diagramas
**Objetivo:** Permitir que `batch_ingest.py` reconozca archivos gráficos, los almacene de forma organizada y cree fichas Markdown vinculadas.

1. **Soporte de Extensiones:**
   * Agregar `.png`, `.jpg`, `.jpeg`, `.webp`, `.svg` a `SUPPORTED_EXTENSIONS`.
2. **Organización de Assets:**
   * Al procesar una imagen, copiarla a una subcarpeta dedicada: `data/docs/assets/`.
3. **Generación de Ficha Markdown:**
   * Crear un archivo `.md` homónimo que contenga:
     * Metadatos (nombre, carpeta de origen, tamaño, fecha).
     * Enlace de renderizado de imagen para Markdown: `![Diagrama](assets/nombre_imagen.png)`.
     * Sección reservada para el texto extraído / descripción técnica.

---

### Paso 3: Extracción de Contenido (OCR y Descripción con Visión IA)
**Objetivo:** Hacer que los diagramas sean buscables por el Copilot mediante su contenido interno (IPs, nombres de servidores, flujos).

1. **Estrategia A — OCR Local (Sin costo / Offline):**
   * Usar librerías como `easyocr` o `pytesseract` para extraer texto de cuadros, etiquetas, puertos y servidores dentro de la imagen.
2. **Estrategia B — Visión con IA (Multimodal):**
   * Enviar la imagen a un modelo de visión (`gpt-4o-mini` o modelo local como `llava` / `qwen2-vl` vía Ollama).
   * Generar una explicación técnica estructurada del flujo:
     * *Propósito del proceso o topología.*
     * *Componentes e interfaces involucradas.*
     * *Puntos de decisión y contingencias.*
3. **Indexación:**
   * Inyectar el texto extraído y la descripción directamente en la ficha `.md` del diagrama para que DuckDB y el motor documental puedan encontrarlo.

---

### Paso 4: Visualización Multimedia en la Interfaz Web (`app.py`)
**Objetivo:** Permitir al usuario ver y explorar los diagramas directamente en la aplicación.

1. **Renderizado en el Chat Copilot:**
   * Cuando el usuario consulte por un proceso o arquitectura (ej. *"Muéstrame el diagrama de contingencia de WSO2"*), el asistente responderá con la explicación técnica y **la imagen embebida en el mensaje**.
2. **Pestaña Galería de Diagramas y Procesos:**
   * Agregar una nueva pestaña en Streamlit para navegar visualmente por todos los diagramas indexados.
   * Filtros por categoría/subcarpeta (ej. Redes, Servidores, Middleware).
   * Vista previa ampliada y botón para abrir la imagen original en alta resolución.

---

### Paso 5: Sincronización Automática con Unidades de Red (Servicio Programado)
**Objetivo:** Mantener el repositorio siempre actualizado sin intervención manual cada vez que un ingeniero guarde un nuevo archivo en el servidor de archivos.

1. **Script de Tarea Programada (Windows Task Scheduler / Cron):**
   * Ejecución cada 30 o 60 minutos: `python batch_ingest.py --origen Z:\Infraestructura\Docs`.
2. **Alertamiento de Ingesta:**
   * Resumen automático en el log y notificación de nuevos documentos agregados al Copilot.mágenes procesadas y tiempo transcurrido.

---

## [TECNOLOGÍAS Y DEPENDENCIAS] Tecnologías y Dependencias Necesarias para los Siguientes Pasos

| Componente | Librería / Herramienta | Propósito |
| :--- | :--- | :--- |
| **Copia y Manejo de Assets** | `shutil` (Nativo de Python) | Mover y versionar imágenes en `data/docs/assets/` |
| **OCR Local** | `easyocr` o `pytesseract` | Extraer texto de imágenes sin conexión |
| **Visión IA (Opcional)** | `openai` (Vision API) o `ollama` | Describir flujos y diagramas complejos con IA |
| **Visualización Web** | `streamlit` (`st.image`) | Renderizar diagramas en chat y galería |

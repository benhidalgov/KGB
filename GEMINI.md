# Directrices y Reglas del Proyecto: Copilot de Infraestructura y Operaciones

## 1. Regla Estricta: Prohibicion Total de Emojis
* **Sin Emojis en Codigo e Interfaz:** Queda estrictamente prohibido el uso de emojis (iconos visuales Unicode) en cualquier componente de la interfaz de Streamlit, botones, titulos, pestanas, modales, toasts, mensajes de error o descripciones.
* **Sin Emojis en Respuestas y Mensajes:** Las respuestas del asistente hacia el usuario y en la documentacion tecnica deben ser 100% sobrias, formales y corporativas, sin incluir emojis.
* **Estilo Visual Corporativo:** Utilizar etiquetas de texto estructuradas y badges limpios en su lugar (ejemplos: `[OK]`, `[WARN]`, `[CRIT]`, `[Version v1]`, `[Documento]`, `[Excel]`, etc.).

---

## 2. Regla Estricta: Prohibicion Total de la Palabra "AIOps"
* **Sin 'AIOps' en Codigo, Interfaz ni Documentacion:** Queda estrictamente prohibido el uso del termino "AIOps" (o "aiops") en cualquier parte de la interfaz de usuario, botones, titulos, componentes, insignias, respuestas del asistente, documentacion o codigo.
* **Terminologia Corporativa Alternativa:** Utilizar en su lugar terminos formales como "Operaciones", "Infraestructura", "Copilot de Infraestructura", "Consola de Operaciones" o "Gestion Documental".

---

## 3. Buenas Practicas de Codigo y Arquitectura
* **Inmutabilidad y Versionado:** Cualquier modificacion de documentos o CMDBs debe respetar el esquema de versionado incremental (`data/history/`) con registro de autor, timestamp y motivo del cambio.
* **Auditoria Obligatoria:** Toda edicion y operacion de Rollback debe registrar obligatoriamente el Editor Responsable y la Justificacion Tecnica en `data/audit_log.json`.
* **Compatibilidad de Tema (Theme-Safe):** La interfaz de Streamlit debe ser completamente legible tanto en Tema Claro (*Light*) como en Tema Oscuro (*Dark*).
* **Integracion con Gemini:** Cuando se conecte el motor de IA, utilizar el SDK oficial `google-genai` respetando la inyeccion de contexto RAG y el manejo seguro de API Keys.

---

## 4. Guia Estandar de Badges y Tokens Visuales (Obsidian & Indigo)

Para preservar la coherencia y el acabado de ingenieria, utilizar exclusivamente la paleta y badges estandarizados:

| Badge / Elemento | Clase CSS | Color Hex / Tono | Significado / Uso |
| :--- | :--- | :--- | :--- |
| `[OK]` / `[OPERATIVO]` | `.badge-ok` | `#10B981` (Verde Menta) | Estado saludable, conexion activa, validacion exitosa |
| `[WARN]` / `[ALERTA]` | `.badge-warn` | `#D97706` (Naranja Ocre) | Servidor en revision, sin coincidencia exacta, advertencia |
| `[CRIT]` / `[INCIDENTE]` | `.badge-crit` | `#E11D48` (Carmesí) | Servidor critico, falla de servicio, lineas eliminadas en Diff |
| `[INFO]` / `[CONSOLA]` | `.badge-info` | `#6366F1` (Índigo) | Componentes de arquitectura, origen CMDB, metadata tecnica |
| `[DOC]` / `[EXCEL]` | `.badge-tag` | `rgba(128,128,128,...)` | Tipo de archivo, formato, nivel de arquitectura (L1-L4) |
| `● ONLINE` | `.badge-pulse-online` | `#10B981` (Pulso animado) | Indicador de disponibilidad del servicio en Navbar |

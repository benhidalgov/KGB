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

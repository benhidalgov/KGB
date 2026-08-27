# Copilot de Infraestructura y Operaciones

Plataforma corporativa de asistencia técnica, gestión documental de infraestructura, inventario CMDB en memoria (DuckDB), inferencia generativa con Google Gemini RAG, autenticación y control de acceso basado en roles (RBAC), bóveda de seguridad cifrada (AES-256), telemetría de sistemas SAP y control de versiones inmutable.

---

## 1. Capacidades Principales

* **Control de Acceso y Autenticación Corporativa (RBAC):** Compuerta de acceso perimetral (`core/auth.py`) que bloquea la ejecución de la consola ante usuarios no autenticados. Control de roles granular (`Administrador`, `Operador`, `Auditor`), contraseñas protegidas con **PBKDF2-HMAC-SHA256**, soporte de variables maestras vía `st.secrets` y bitácora inmutable de inicios de sesión.
* **Búsqueda Dual en Consola:**
  * **Subpestaña 1: Búsqueda Textual (DuckDB & Docs):** Recuperación indexada ultrarrápida en memoria RAM (**latencia < 2 ms**, Zero API calls) sobre la CMDB y los 30 documentos técnicos, con resaltado de términos (`<mark>`) y botón puente hacia el Copilot.
  * **Subpestaña 2: Copilot de Infraestructura (Gemini RAG):** Asistencia técnica en lenguaje natural con el SDK oficial `google-genai` (`gemini-2.5-flash`), inyección de contexto RAG estricta, *Fast-Fail* y fallback autónomo al motor local si no hay conexión externa.
* **Caché en Memoria y Alto Rendimiento:** Almacén de respuestas frecuentes en memoria RAM (`Query Response Cache`) que entrega consultas resueltas en **0.79 milisegundos**. Pre-normalización léxica en memoria y DuckDB en RAM con cero I/O de disco.
* **Ingesta Batch y Soporte para Paquetes ZIP:** El panel lateral soporta selección múltiple de archivos y arrastrar paquetes comprimidos **`.zip`**. La aplicación descomprime en memoria (`io.BytesIO`), normaliza nombres, sanitiza formatos, genera versiones `v1` e indexa todo en tiempo real.
* **Bóveda de Seguridad Local (Vault AES-256):** Custodia de credenciales y API Keys (`GEMINI_API_KEY`, `SAP_ENDPOINT`, `SAP_CLIENT_ID`, etc.) mediante cifrado simétrico Fernet. Jerarquía en cascada (OS Environment -> Streamlit Secrets -> Bóveda Cifrada), con acceso exclusivo restringido al rol de Administrador.
* **Blindaje de Rendimiento y Prevención de Bloqueos:**
  * Conversión documental con `keep_data_uris=False` para evitar inyección masiva de Base64 en el DOM.
  * Visores protegidos: visor de código truncado a 50 KB para salvaguardar el hilo JavaScript, textarea limitada a 100 KB, umbral de 2.5 MB para PDFs embebidos (con tarjeta de descarga directa para archivos grandes) y diff HTML limitado a 400 líneas.
  * Auto-saneamiento en caliente de la sesión ante residuos de caché obsoletos.
* **Integración y Telemetría SAP (API):** Consola dedicada para el monitoreo del landscape SAP S/4HANA 2022, bases de datos SAP HANA 2.0 (HSR en alta disponibilidad), servidores NetWeaver (ASCS/PAS/AAS) y sincronización automatizada con la CMDB local.
* **Visor Lado a Lado con Imágenes Activas:** Inspección sincronizada entre Markdown normalizado y el archivo original (PDF embebido, Excel interactivo, diagramas en alta resolución o Word).
* **Control de Versiones y Auditoría:** Historial inmutable en `data/history/` (`v1`, `v2`...), comparador visual *Diff*, Rollback protegido y registro central de auditoría en `data/audit_log.json`.
* **Diseño Corporativo Theme-Safe (Obsidian & Indigo):** Interfaz adaptativa 100% legible en Tema Claro y Oscuro, estrictamente libre de emojis y con terminología técnica formal de ingeniería.

---

## 2. Estructura del Proyecto

```text
C:\Prototipo\
├── app.py                             # Aplicación principal Streamlit (Navbar, Login y 5 Pestañas)
├── batch_ingest.py                    # Ingesta masiva multihilo con caché SHA-256
├── excel_cleaner.py                   # Extractor y normalizador de libros Excel
├── run_app.bat / run_app.ps1          # Lanzadores de ejecución en Windows
├── requirements.txt                   # Dependencias Python
├── .python-version                    # Fijación de runtime oficial (Python 3.12 LTS)
├── README.md                          # Manual de uso y puesta en marcha
├── ARQUITECTURA_COPILOT_INFRAESTRUCTURA.md # Especificación técnica y arquitectura
├── HOJA_DE_RUTA_DIAGRAMAS_E_INGESTA.md     # Roadmap de desarrollo
├── GEMINI.md                          # Reglas y directrices mandatorias de desarrollo
├── core/                              # Módulos centrales de la plataforma
│   ├── __init__.py                    # Inicializador de paquete desacoplado
│   ├── auth.py                        # Sistema de autenticación RBAC y sesiones
│   ├── auditoria.py                   # Control de versiones, Diff y bitácora inmutable
│   ├── configuracion.py               # Rutas base y definición de directorios
│   ├── conector_sap.py                # Conector, telemetría y topología Mermaid SAP
│   ├── estilos.py / estilos.css       # Reglas visuales corporativas y seguridad CSS
│   ├── manual.py                      # Manual de uso interactivo en consola
│   ├── motor.py                       # Motor de consultas, DuckDB en RAM, Gemini RAG y cachés
│   ├── plantillas.py                  # Generador de procedimientos y runbooks
│   ├── procesador.py                  # Normalización documental, extracción limpia y sanitización
│   ├── topologia.py                   # Diagramas arquitectónicos Mermaid (L1-L4)
│   ├── vault.py                       # Bóveda de credenciales con cifrado AES-256
│   └── visor.py                       # Visor Lado a Lado y renderizador protegido
└── data/                              # Repositorio de datos (CMDB, docs, history, originals, auditoría)
```

---

## 3. Instalación y Puesta en Marcha

### Ejecución en Entorno Local (Windows / Linux / macOS)

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

### Cuentas Iniciales Preconfiguradas

| Usuario | Rol Asignado | Contraseña Inicial | Nivel de Acceso |
| :--- | :--- | :--- | :--- |
| `admin` | Administrador | `admin2026` | Acceso total (Bóveda `[VAULT]`, Ingesta Batch, Edición, Rollback) |
| `operador` | Operador | `operador2026` | Consultas Copilot, Búsqueda DuckDB, Visor Lado a Lado e Ingesta |
| `auditor` | Auditor | `auditor2026` | Solo lectura (Búsqueda DuckDB y Visor Documental) |

---

## 4. Despliegue en la Nube (Streamlit Community Cloud)

1. Suba el repositorio a su cuenta de **GitHub** (privado o público).
2. Conecte el repositorio en [share.streamlit.io](https://share.streamlit.io/).
3. El archivo [`.python-version`](file:///C:/Prototipo/.python-version) garantiza el despliegue automático en **Python 3.12**.
4. En el panel de **App Settings -> Secrets**, configure las credenciales sin exponerlas en la interfaz:
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   ADMIN_PASSWORD = "MiContrasenaMaestra2026"
   ```
5. Presione **Deploy**. La aplicación arrancará protegida detrás del formulario de inicio de sesión corporativo.

---

## 5. Guía por Pestaña de la Consola

* **Pantalla de Login:** Acceso corporativo con validación criptográfica PBKDF2. Bloquea la carga de la aplicación y CMDB a usuarios no autorizados.
* **Navbar Superior:** Marca corporativa, usuario activo (`@admin [Administrador]`), estado `● ONLINE`, selector de vista (`[Consola]` | `[Manual de Uso]`) y contadores documentales.
* **Panel Lateral (Sidebar):** Tarjeta de sesión activa con botón **`>_ Cerrar Sesión`**, cargador de archivos individuales o paquetes **`[ZIP BATCH]`**, explorador de documentos filtrable, botón **`>_ Reindexar`** y **Bóveda de Credenciales `[VAULT]`** (exclusiva para administradores).
* **Pestaña 1 (Consultas y Búsqueda):**
  * *Subpestaña 1.1 (Búsqueda Textual):* Búsqueda en milisegundos (< 2 ms) en memoria RAM sobre DuckDB y documentación, con chips rápidos (`BALANCER001`, `10.24.0.125`, `JWT`, `Failover Redis`), visualización de servidores y fragmentos coincidentes, más botón puente para analizar con el Copilot.
  * *Subpestaña 1.2 (Copilot de Infraestructura):* Diálogo analítico con Gemini 2.5 Flash RAG, aceleración por memoria caché, diagnósticos de causa raíz y botón **`>_ Limpiar Chat`**.
* **Pestaña 2 (Historial de Mantenimientos):** Tabla interactiva de servidores con filtros por Nivel de Arquitectura (L1-L4), Estado y Técnico, más consola SQL DuckDB en memoria RAM sobre `mantenimientos.csv`.
* **Pestaña 3 (Documentación Técnica y Versionado):** Visor Lado a Lado protegido (Markdown vs Original), renderizado de diagramas, editor de libros Excel, editor de texto seguro, comparador Diff (límite 400 líneas) y Rollback auditado.
* **Pestaña 4 (Plantillas y Runbooks):** Asistente paso a paso para la redacción, validación y publicación formal de procedimientos operativos (`v1`).
* **Pestaña 5 (Integración SAP - API):** Monitoreo del landscape SAP, verificación de endpoints y latencia en milisegundos, visualizador de topología Mermaid para HANA HSR y NetWeaver, visor de payload JSON REST/OData y botón de sincronización hacia la CMDB local.

---

## 6. Matriz de Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Control de Acceso (RBAC)** | Python `hashlib` (PBKDF2-HMAC-SHA256) | Autenticación perimetral, gestión de sesiones y permisos por rol |
| **Interfaz Web** | Streamlit + Antd Components | Consola corporativa, navegación por pestañas y componentes interactivos |
| **Motor de Inteligencia (IA)** | Google GenAI SDK (`google-genai`) | Inferencia generativa RAG con `gemini-2.5-flash` fundamentada en evidencia CMDB |
| **Aceleración de Consultas** | LRU Query Cache + Pre-normalización | Caché en RAM para respuestas instantáneas (< 1 ms) y búsqueda léxica sub-milisegundo |
| **Bóveda de Credenciales** | Python `cryptography` (Fernet / AES-256) | Custodia cifrada local de API Keys y tokens con jerarquía en cascada |
| **Integración ERP / Core** | Conector REST / OData SAP | Telemetría e inventario de SAP S/4HANA y bases de datos SAP HANA HSR |
| **Motor SQL en Memoria** | DuckDB + Pandas | Consultas ultrarrápidas en RAM con Zero Disk I/O sobre mantenimientos e inventario |
| **Conversión Documental** | Microsoft MarkItDown + OpenPyXL | Extracción estructurada sin base64 masivo para protección de memoria en navegador |
| **Ingesta Batch ZIP** | Python `zipfile` + `io.BytesIO` | Descompresión e ingesta masiva en memoria de paquetes `.zip` directamente desde la web |
| **Auditoría e Integridad** | Python `hashlib` (SHA-256) + `difflib` | Versionado inmutable, Diff y bitácora de auditoría en `audit_log.json` |
| **Diagramas de Topología** | Mermaid.js | Visualización interactiva de arquitectura en 4 niveles y landscapes SAP |

---

## 7. Resolución de Problemas (Troubleshooting)

* **Olvido de contraseña de administrador:** En Streamlit Cloud, configure `ADMIN_PASSWORD = "nueva_clave"` en **App Settings -> Secrets**; el sistema la adoptará inmediatamente. En local, borre `data/users.json` para restablecer las claves iniciales de fábrica.
* **Activar Google Gemini:** Configurar `GEMINI_API_KEY` en los Secrets de Streamlit Cloud o en la sección **Bóveda de Credenciales `[VAULT]`** del panel lateral como administrador.
* **Archivos externos no visibles:** Clic en `>_ Reindexar` en el panel lateral o ejecutar `python batch_ingest.py`.
* **Caché de consultas desactualizada tras editar archivos:** Al hacer clic en `>_ Reindexar`, el sistema purga automáticamente la caché de respuestas y la caché documental en memoria.
* **Subida de lotes grandes:** Comprimir los documentos en un archivo `.zip` y arrastrarlo al cargador del panel lateral para ingesta paralela automática.

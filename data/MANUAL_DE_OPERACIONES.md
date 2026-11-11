# Manual Técnico y Guía de Operación Detallada

---

## Módulo 1

<div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[Módulo 1 de 8]</span>
                <span class="badge-tag">Seguridad y Bóveda</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Módulo 1: Control de Acceso (RBAC), Sesiones y Bóveda Cifrada (AES-256)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Arquitectura de autenticación perimetral, almacenamiento seguro de contraseñas y custodia de credenciales.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Autenticación Perimetral (`core/auth.py`):** Bloquea la carga del DOM, la CMDB y los documentos a usuarios no autenticados. Valida credenciales contra `data/users.json` aplicando **PBKDF2-HMAC-SHA256** con salt estático y 100,000 iteraciones de hash.
        * **Bloqueo por Intentos Fallidos:** 5 intentos fallidos dentro de la ventana de bloqueo impiden el acceso a la combinación **usuario + origen (IP)**, de modo que quien fuerza desde una IP no deja fuera al usuario legítimo que entra desde otra. El login distingue los dos casos: dice **`Cuenta bloqueada por intentos fallidos...`** cuando el candado está activo y **`Usuario o contraseña incorrectos.`** cuando sólo fallaron las credenciales.
        * **Matriz de Permisos RBAC:** cada pantalla evalúa sus permisos (`puede_ver_vault`, `puede_editar_vault`, `puede_ingestar_archivos`, `puede_editar_docs`, `puede_rollback`, `puede_ejecutar_sql`, `puede_ver_auditoria`) y los controles sin permiso **no se renderizan**; donde el aviso informativo corresponde (editor, ingesta, bóveda) se muestra un mensaje que explica qué permiso falta.
          * **`Administrador`:** Control total. Puede ver y modificar la Bóveda `[VAULT]`, subir archivos ZIP, editar documentos, ejecutar *Rollbacks* y consultar el Registro de Actividad.
          * **`Operador`:** Técnico de operaciones. Puede realizar búsquedas, dialogar con el Asistente, usar el Visor, cargar archivos y editar documentos (sin bóveda, sin *Rollback* y sin Registro de Actividad).
          * **`Auditor`:** Cumplimiento normativo. Consulta inventario, documentos, historial y bitácora `data/audit_log.json`, pero no ingesta, ni edición, ni *Rollback*.
        * **Bóveda de Secretos (`core/vault.py`):** Custodia claves sensibles (`GEMINI_API_KEY`, etc.) mediante cifrado simétrico **Fernet (AES-256-CBC)** en `data/.vault.enc`. Utiliza una jerarquía en cascada: Variables de Entorno del Sistema Operativo -> Secrets de Streamlit Cloud -> Bóveda Local Cifrada. Las claves y sus vistas previas se escapan con `html.escape` antes de inyectarse en el HTML del panel.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Iniciar Sesión:**
           * Ingrese su usuario (`admin`, `operador` o `auditor`) y la contraseña correspondiente en el formulario de acceso.
           * El sistema genera la sesión en `st.session_state` y registra un evento `LOGIN_EXITOSO` en `data/audit_log.json`.
           * Si la cuenta quedó bloqueada por intentos fallidos, el formulario lo indica con **`Cuenta bloqueada por intentos fallidos. Espera unos minutos y vuelve a intentar.`**; esperar la ventana de bloqueo y reintentar.
        2. **Verificar su Perfil:**
           * En el panel lateral izquierdo, observe la tarjeta superior **`Sesión Activa`**, que muestra su nombre, rol y nombre de usuario.
        3. **Configurar o Modificar Claves en la Bóveda (Solo Administrador):**
           * En el panel lateral, despliegue la sección **`Bóveda de Credenciales [VAULT]`**.
           * En el desplegable, seleccione la clave a configurar (por ejemplo, `GEMINI_API_KEY`).
           * Escriba el valor de la clave en el campo de texto y presione **`Guardar`**. El nombre y el valor son obligatorios: en blanco se rechaza con `Escribe un nombre y un valor.`
           * El sistema cifra el valor en memoria y lo guarda en `data/.vault.enc` registrando la auditoría. Sin `puede_editar_vault` (Operador o Auditor) los botones responden **`Tu rol no permite administrar credenciales.`**
           * Para borrar una clave, selecciónela y presione **`Revocar`**.
        4. **Cerrar Sesión:**
           * Haga clic en el botón **`Salir`** en la barra lateral. La sesión se purga y el evento `LOGOUT` queda registrado.

---

## Módulo 2

<div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[Módulo 2 de 8]</span>
                <span class="badge-tag">Motor en RAM</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Módulo 2: Búsqueda Textual Instantánea y Algoritmo de Scoring</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Recuperación en memoria RAM (< 2 ms) sobre DuckDB y 30 documentos técnicos con cálculo determinista de relevancia.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **DuckDB en RAM (`core/motor.py`):** Ejecuta consultas SQL vectorizadas en memoria sobre el inventario `data/mantenimientos.csv`. Al buscar un término, filtra simultáneamente por hostname, IP, capa arquitectónica, sistema operativo y técnico responsable sin tocar el disco.
        * **Motor de Búsqueda Léxica Documental:** Escanea el diccionario `st.session_state.doc_store` (30 documentos técnicos en memoria) aplicando normalización léxica (conversión a minúsculas, remoción de acentos Unicode y división en tokens).
        * **Algoritmo de Puntuación (*Scoring* de Relevancia):**
          * **`+30 puntos`:** Coincidencia exacta de la frase en el cuerpo del documento.
          * **`+20 puntos`:** Coincidencia del término en el nombre de archivo o título normalizado.
          * **`+2 puntos`:** Por cada repetición del término dentro de los párrafos.
        * **Resaltado Dinámico:** Extrae una ventana de contexto de +-120 caracteres alrededor del término coincidente y lo envuelve en `<mark style="background-color:#fef08a;color:#713f12;">` para visibilidad inmediata.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. Vaya a la pestaña **`Consultas y Búsqueda`** -> subpestaña **`Búsqueda Textual (DuckDB & Docs)`**.
        2. Escriba el término en la barra de búsqueda superior:
           * Hostname de servidor: `BALANCER001`, `VM-BOOKING-01`.
           * Dirección IP: `10.24.0.125`, `10.24.0.10`.
           * Protocolo o Componente: `JWT`, `SSL`, `Redis`, `WSO2`, `PostgreSQL`.
           * Número de Serie: `SN-8842-A`.
        3. Presione `Enter` o haga clic en **`Buscar en CMDB y Documentos`**.
        4. **Interpretación de Resultados:**
           * **Panel Superior (Servidores CMDB):** Muestra la cuadrícula de servidores con su IP, Nivel arquitectónico (`L1` Hardware físico, `L2` Virtualización, `L3` Middleware, `L4` Aplicaciones), Estado operativo (`[OPERATIVO]`, `[ALERTA]`, `[CRÍTICO]`) y Técnico Responsable.
           * **Panel Inferior (Documentos Técnicos):** Tarjetas con el Score de relevancia, fragmentos de texto con términos resaltados y el botón **`Analizar con Asistente`** para transferir el contexto a la IA.

---

## Módulo 3

<div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[Módulo 3 de 8]</span>
                <span class="badge-tag">IA Generativa RAG</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Módulo 3: Asistente Técnico Generativo (Google Gemini 2.5 Flash RAG)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Inferencia generativa fundamentada en evidencia documental con salvaguardas de cero alucinaciones y fallback local.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Pipeline RAG (*Retrieval-Augmented Generation*):**
          1. Recibe la consulta en lenguaje natural del operador.
          2. Recupera automáticamente los servidores relevantes de DuckDB y los fragmentos más puntuados de la base documental.
          3. Construye un prompt enriquecido inyectando el contexto técnico real.
          4. Invoca el SDK oficial `google-genai` apuntando al modelo **`gemini-2.5-flash`** (o `gemini-flash-latest`) con temperatura baja (`0.2`) para máxima precisión técnica.
        * **Directivas Estrictas del Sistema:**
          * **Zero Hallucinations:** El modelo tiene instrucción explícita de responder únicamente sobre la evidencia provista en el contexto. Si un dato no está en los documentos, indica con claridad que no existe registro documentado.
          * **Estilo Corporativo:** Respuestas sobrias, técnicas y formales sin emojis ni términos informales. Salida estructurada con tablas Markdown y comandos de terminal.
        * **Mecanismo de Resiliencia (*Fast-Fail & Fallback Local*):** Si la API de Google no responde (código 403, 429, 503 o falta de internet), el sistema conmuta automáticamente al **Motor Local Autónomo**, entregando una síntesis determinista con los datos de DuckDB y los documentos sin interrumpir el servicio.
        * **Caché LRU de Respuestas:** Almacena respuestas previas en RAM, entregando consultas repetidas en **0.79 milisegundos**.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. Ingrese a la subpestaña **`Asistente Técnico (Gemini RAG)`**.
        2. Escriba su consulta en lenguaje natural en el campo de texto. Ejemplos de uso operativo:
           * *"¿Cómo realizo el procedimiento de failover de Redis según los manuales de contingencia?"*
           * *"Indícame la IP, capa y técnico responsable del servidor BALANCER001."*
           * *"¿Qué servidores de nivel L3 están en estado crítico y qué servicios afectan?"*
        3. Presione el botón **`Consultar Asistente`**.
        4. Revise la respuesta generada con pasos secuenciales, comandos de terminal y referencias documentales.
        5. Para iniciar una nueva consulta limpia, presione **`Limpiar Chat`**.

---

## Módulo 4

<div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[Módulo 4 de 8]</span>
                <span class="badge-tag">Telemetría y SQL</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Módulo 4: Historial de Mantenimientos y Consola SQL en Memoria</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Tablero interactivo de activos por capas arquitectónicas y motor de consultas analíticas SQL embebido.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Tablero de Inventario CMDB:** Lee `data/mantenimientos.csv` con caché de tiempo de modificación (`mtime`). Permite filtrar dinámicamente por Nivel de Arquitectura (`L1 Hardware`, `L2 Virtualización`, `L3 Middleware`, `L4 Aplicaciones`), Estado (`Operativo`, `En Revisión`, `Falla Crítica`) y Técnico.
        * **Consola SQL Embebida (DuckDB):** Permite a los ingenieros ejecutar consultas SQL completas en memoria RAM sobre la tabla virtual `mantenimientos` (`SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `COUNT`) sin necesidad de clientes externos como DBeaver ni bases de datos relacionales instaladas.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. Vaya a la pestaña **`Historial de Mantenimientos`**.
        2. **Filtrado Visual:**
           * Use los selectores superiores para aislar servidores por capa (ej: `L2 (Virtualización)`), estado o técnico asignado.
           * La tabla interactiva se actualiza al instante permitiendo ordenar columnas y redimensionar anchos.
        3. **Ejecución de Consultas SQL:**
           * Despliegue la sección **`Ejecutar Consulta SQL en Memoria (DuckDB)`**.
           * Escriba su sentencia SQL en el editor. Ejemplos prácticos:
             ```sql
             -- Servidores con alertas activas agrupados por capa
             SELECT nivel_arquitectura, COUNT(*) AS total_con_alerta
             FROM mantenimientos
             WHERE estado != 'Operativo'
             GROUP BY nivel_arquitectura;

             -- Buscar máquinas administradas por un técnico
             SELECT servidor_id, ip, sistema_operativo, estado
             FROM mantenimientos
             WHERE tecnico_asignado ILIKE '%Carlos%'
             ORDER BY ip;
             ```
           * Presione **`Ejecutar SQL`** para visualizar la cuadrícula de datos resultante.

---

## Módulo 5

<div class="search-result-card" style="border-left: 4px solid #D97706; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-warn">[Módulo 5 de 8]</span>
                <span class="badge-tag">Visor Multimodal</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #D97706;">Módulo 5: Visor Lado a Lado y Renderizado Adaptativo de Documentos</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Inspección sincronizada entre la versión Markdown indexada y el archivo binario fuente original.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Arquitectura de Doble Columna (`core/visor.py`):**
          * **Columna Izquierda (Markdown Normalizado):** Presenta el texto estructurado extraído por MarkItDown con renderizado HTML sanitizado (`preparar_markdown_con_imagenes`).
          * **Columna Derecha (Renderizador Adaptativo Binario):** Identifica la extensión del archivo original en `data/originals/` y aplica el componente nativo adecuado:
            * **PDF:** Iframe Base64 con controles nativos de zoom e impresión (con control de memoria que ofrece descarga directa si el archivo supera 2.5 MB).
            * **Excel (`.xlsx`, `.xls`):** Cuadrícula interactiva con selector dinámico de hojas de cálculo (`openpyxl`).
            * **Diagramas (`.png`, `.jpg`, `.svg`):** Visor de imagen en alta resolución con pie de imagen (*Caption*) indexable.
            * **Word / PPTX (`.docx`, `.pptx`):** Ficha técnica descriptiva con botón de descarga del binario original.
        * **Ficha y Bitácora por Documento:** La cabecera de la ficha (categorías, último editor, fecha) escapa sus valores con `html.escape` antes de inyectarlos en el HTML. Debajo del *Diff* aparece el expander **`Registro de Actividad`**, reservado a los roles con permiso `puede_ver_auditoria` (Administrador y Auditor): el Operador simplemente no lo ve.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. Ingrese a la pestaña **`Documentación Técnica`**.
        2. Seleccione el tipo de documento en el filtro `Tipo` y elija el archivo en el selector `Seleccione Documento`.
        3. En la subpestaña **`Visualización Lado a Lado`**, utilice el control superior para cambiar el modo de vista:
           * **`[Lado a Lado]`:** Muestra el Markdown a la izquierda y el archivo original a la derecha.
           * **`[Solo Markdown]`:** Oculta el archivo original para concentrarse en el texto limpio.
           * **`[Solo Formato Original]`:** Muestra exclusivamente el visor PDF o la tabla Excel a todo el ancho.
        4. En libros Excel: Utilice el selector `Seleccionar Hoja de Trabajo`w
         para alternar entre hojas del libro de cálculo.
        5. Botón de Descarga: Al pie de la columna izquierda o derecha, pulse **`Descargar Versión Activa v{N}`** para obtener una copia local en `.md`, `.xlsx` o `.pdf`.
        6. **Registro de Actividad (Administrador y Auditor):** dentro del documento, despliegue **`Registro de Actividad`** para ver la bitácora con timestamp, documento, acción, versiones, editor y motivo, con la casilla **`Filtrar solo este documento`** activada por defecto.

---

## Módulo 6

<div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[Módulo 6 de 8]</span>
                <span class="badge-tag">Lectura Inmersiva</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Módulo 6: Modo Lectura con Buscador Interno</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Entorno inmersivo de pantalla completa para navegación fluida en manuales técnicos de gran volumen.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Aislamiento de Interfaz (`renderizar_zen_studio`):** Inyecta CSS dinámico que oculta el sidebar y los encabezados globales, expandiendo el lienzo de lectura al **98% del ancho útil de la pantalla**.
        * **Extractor de Tabla de Contenidos (TOC):** Analiza el Markdown mediante expresiones regulares extrayendo los encabezados `H1` a `H4` y generando un árbol de navegación con indentación jerárquica.
        * **Buscador In-Document:** Resalta en tiempo real las coincidencias de una palabra dentro del texto usando `<mark>` y reporta el contador exacto de hallazgos.
        * **Motor de Temas y Tipografía:** Permite alternar la paleta de colores del lienzo (`Obsidian` oscuro, `Sepia` cálido, `Papel` blanco) y el tamaño tipográfico (`13px`, `15px`, `17px`) con interlineado optimizado (`line-height: 1.75`).
        * **Métricas Automáticas:** Calcula el volumen de palabras y el tiempo estimado de lectura aplicando el estándar de **200 palabras por minuto (WPM)**.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Entrar al Modo lectura:**
           * En la pestaña `Documentación Técnica`, presione el botón azul **`Abrir en Modo lectura`** (o elija `Modo lectura` en la barra superior).
        2. **Navegar por Secciones:**
           * En el panel lateral izquierdo, use el selector **`Saltar a Sección:`** para aislar un procedimiento específico (ej: *"Procedimiento de Failover"* o *"Parámetros de Red"*), o elija *"Documento Completo"*.
        3. **Buscar Palabras Clave en el Documento:**
           * En la barra superior, escriba un término en **`Buscar en doc:`** (ej: `failover`, `puerto`, `root`). Todas las coincidencias se resaltarán en amarillo de inmediato.
        4. **Personalizar Lectura:**
           * Alterne el tema en el selector `Tema` (`Obsidian`, `Sepia`, `Papel`) y el tamaño en `Tamaño` (`Compacto`, `Normal`, `Grande`).
        5. **Subpestañas Multimodales:**
           * Alterne entre `Lector Markdown`, `Documento Original` (PDF o Excel a 750px de altura) y `Lado a Lado (50/50)`.
        6. **Salir:** Presione el botón **`Salir`** en la esquina superior derecha para retornar a la consola estándar.

---

## Módulo 7

<div class="search-result-card" style="border-left: 4px solid #6A397B; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-crit">[Módulo 7 de 8]</span>
                <span class="badge-tag">Control de Versiones</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6A397B;">Módulo 7: Edición Colaborativa, Comparador Diff y Rollback Seguro</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Versionado incremental inmutable, cálculo de firmas SHA-256 y reversión auditada de cambios fallidos.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Inmutabilidad Documental (`core/auditoria.py`):** Los documentos nunca se sobreescriben a ciegas. Cualquier modificación genera una versión nueva incremental (`v1`, `v2`, `v3`...) almacenando un snapshot exacto en `data/history/{doc_name}/` junto con su firma criptográfica **SHA-256**.
        * **Campos Obligatorios de Auditoría:** El sistema rechaza cualquier guardado que no incluya el **Editor Responsable** y el **Motivo del Cambio**.
        * **Comparador de Diferencias (*Diff* Visual):** Compara dos versiones mediante `difflib.unified_diff`, generando una vista visual con resaltado verde para líneas añadidas y ciruela para líneas eliminadas (con límite de 400 líneas para salvaguardar el navegador).
        * **Operación de Rollback:** Restaura un snapshot histórico anterior, crea una versión nueva que registra la reversión y almacena el evento en `data/audit_log.json`. El bloque **`Volver a la Versión v{N}`** sólo se renderiza con el permiso `puede_rollback` (Administrador); si un rol sin permiso llegara a forzar el clic, responde **`Tu rol no permite ejecutar rollbacks.`**
        * **Permisos de Edición:** Sin `puede_editar_docs` la subpestaña **`Editar Documento`** muestra **`Tu rol no permite editar documentos.`** y no renderiza ni el área de texto ni el botón de guardar. La inicialización automática de la versión `v1` sólo escribe para quien tiene ese permiso: para el Auditor el historial queda en solo lectura al consultar un documento por primera vez.
        * **Datos de Usuario Seguros:** el editor, los autores y las categorías se escapan con `html.escape` antes de inyectarse en el HTML de la ficha y los resultados.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Editar un Documento de Texto / Markdown:** (Requiere permiso de edición: Administrador u Operador; el Auditor ve el aviso de permiso en lugar del editor.)
           * Vaya a `Documentación Técnica` -> subpestaña **`Editar Documento`**.
           * Modifique el texto en el área de edición.
           * Ingrese su nombre en **Editor (*)** y la justificación técnica en **Motivo (*)**.
           * Presione **`Guardar Versión v{N+1}`**.
        2. **Editar una Hoja de Cálculo Excel:**
           * Seleccione la hoja en el desplegable.
           * Modifique celdas o agregue filas directamente en la tabla interactiva `st.data_editor`.
           * Ingrese Editor y Motivo y presione **`Guardar Versión v{N+1}`**.
        3. **Consultar el Historial de Revisiones:**
           * Abra la subpestaña **`Historial de Versiones`** para ver la tabla de auditoría con versión, fecha/hora, editor, motivo y firma SHA-256.
        4. **Ejecutar un Rollback (Reversión):** (Sólo Administrador; los demás roles no ven este bloque.)
           * En el selector de versiones, elija la versión histórica a restaurar (ej: `v1`).
           * Revise el comparador *Diff* para comprobar qué líneas cambiaron.
           * Ingrese el nombre del técnico y el motivo de la reversión en los campos inferiores.
           * Presione **`Confirmar y Ejecutar Rollback a Versión v{N}`**. El documento anterior queda restaurado inmediatamente.

---

## Módulo 8

<div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[Módulo 8 de 8]</span>
                <span class="badge-tag">Ingesta y Plantillas</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Módulo 8: Ingesta Masiva de Archivos ZIP y Generación de Runbooks</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Carga batch con descompresión en memoria RAM y redacción formal de procedimientos operativos estandarizados.
            </div>
        </div>

#### 1. ¿Qué hace este componente internamente?
        * **Pipeline de Ingesta ZIP (`core/procesador.py`):**
          * Descomprime paquetes comprimidos `.zip` en memoria (`io.BytesIO`) sin crear archivos temporales inseguros en disco.
          * Normaliza nombres de archivo (remoción de tildes y caracteres incompatibles).
          * Extrae texto estructurado mediante MarkItDown sin inyectar Base64 masivo en el DOM (`keep_data_uris=False`).
          * Guarda el binario en `data/originals/`, genera la versión Markdown en `data/docs/` y crea el snapshot inicial `v1`.
        * **Categoría Automática desde el ZIP:** el nombre del paquete comprimido (sin `.zip`, en su forma original) se usa como categoría de sus entradas; si no existe, la crea y la estandariza (p. ej. `Carpeta_prueba.zip` -> `Carpeta Prueba`, conservando siglas como `SAN` o `API`). Se suma a la categoría elegida en el formulario, si la hubo.
        * **Filtro de Extensiones en el Servidor:** sólo se aceptan `.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.md`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.svg`, `.webp` y `.zip`; el resto se omite con el aviso **`Se omitió '...': extensión no soportada.`** Sin permiso `puede_ingestar_archivos` (Auditor) el cargador no se renderiza y el panel sólo muestra **`Tu rol no permite subir archivos.`**
        * **Generador de Runbooks (`core/plantillas.py`):**
          * Asistente estructurado para redacción formal de 8 tipos de procedimientos operativos estándar (SOPs).
          * Soporte para crear nuevos tipos de procedimientos guardados en `data/plantillas_custom.json`.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Ingestar Archivos o Lotes ZIP (Panel Lateral):**
           * En el panel lateral, arrastre un archivo suelto (`.pdf`, `.docx`, `.xlsx`, `.md`, `.png`) o un archivo comprimido **`.zip`** al cargador.
           * **Categoría:** con archivos sueltos es obligatorio elegir una categoría existente o escribir una nueva antes de confirmar. Un lote **sólo de ZIP** no lo exige: cada paquete aporta su propia categoría, derivada del nombre del ZIP.
           * El motor procesa todos los archivos del paquete y muestra notificaciones toast con el recuento de archivos indexados y las categorías usadas.
        2. **Crear un Runbook o Procedimiento Operativo:** (Requiere permiso de edición: los botones **`[+ Usar]`** y **`Guardar Documento`** responden **`Tu rol no permite editar documentos.`** sin `puede_editar_docs`.)
           * Vaya a la pestaña **`Plantillas y Runbooks`**.
           * Seleccione el tipo de procedimiento:
             * *Rollback de Emergencia*
             * *Paso a Producción*
             * *Postmortem de Incidente P1*
             * *Ficha Técnica de API REST / SOAP*
             * *Plan de Contingencia y DRP*
             * *Parchado de Sistema Operativo*
             * *Renovación de Certificados SSL/TLS*
             * *Respaldo y Restauración de Base de Datos*
             * *`[+ Crear Nuevo Tipo de Procedimiento...]`*
           * Complete los campos guiados: Nombre del servicio, responsable, criticidad, ventana de mantenimiento, pasos secuenciales y comandos de terminal.
           * Revise la vista previa generada en tiempo real en la columna derecha.
           * Presione **`Guardar Documento`**. El runbook queda guardado en `data/docs/` como `v1` y disponible para búsquedas.
        3. **Sincronización:** Si agrega documentos directamente en el servidor o terminal, pulse el botón **`Recargar Documentos`** en el panel lateral para refrescar la memoria caché.

"""
Módulo de documentación interactiva y Manual Detallado de Arquitectura y Operación Paso a Paso.
"""
import streamlit as st


def activar_manual_en_inicio():
    """Abre el manual completo como primera vista tras el login."""
    st.session_state["top_navbar_view_selector"] = "Manual de Uso"
    st.session_state["manual_lanzamiento"] = True
    st.session_state["manual_paso_actual"] = 1


def ir_a_consola_desde_manual():
    """Cierra el onboarding de inicio y pide entrar a la consola en el siguiente rerun."""
    st.session_state["manual_lanzamiento"] = False
    st.session_state["_ir_consola"] = True


def renderizar_manual_lanzamiento():
    """Guía de inicio rápido en la pantalla de login antes de autenticar."""
    st.markdown("""
    <div class="search-result-card" style="border-left: 3.5px solid #6366F1; margin-bottom: 12px;">
        <div class="search-header-row">
            <div>
                <span class="badge-info">[GUÍA DETALLADA]</span>
                <span class="search-doc-title" style="margin-left: 8px;">Manual Completo de Operación del Sistema</span>
            </div>
            <span class="badge-tag">Arquitectura y Uso</span>
        </div>
        <div style="font-size: 0.86rem; line-height: 1.55; opacity: 0.92; margin-top: 4px;">
            Consola centralizada de inventario CMDB (DuckDB en RAM), RAG con Gemini 2.5 Flash, control de versiones inmutable (SHA-256) y visor multimodal Zen Studio.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ##### 1. Cómo iniciar sesión y seleccionar rol
    Elija una de las cuentas configuradas en la matriz de acceso:
    * **`admin`** / `admin2026` (Acceso total: Bóveda `[VAULT]`, Ingesta, Edición y Rollback auditado).
    * **`operador`** / `operador2026` (Operación: Búsqueda DuckDB, Asistente RAG, Visor Lado a Lado y Edición).
    * **`auditor`** / `auditor2026` (Cumplimiento: Solo lectura de CMDB, documentos y bitácora SHA-256).

    ##### 2. Qué hacer una vez autenticado
    1. Se desplegará el **Manual Detallado en 8 Módulos** con el funcionamiento interno y paso a paso exacto.
    2. Presione **`>_ Ir a la Consola`** para comenzar a operar o consulte el manual en cualquier momento.
    3. Puede abrir el manual en una pestaña independiente del navegador con el botón inferior.
    """)

    st.markdown("""
    <div style="margin-top: 10px; margin-bottom: 8px;">
        <a href="?view=manual" target="_blank" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; font-weight:600; font-size:0.82rem; color:#6366F1; border:1px solid rgba(99,102,241,0.3); padding:6px 14px; border-radius:6px; background:rgba(99,102,241,0.06);">>_ Abrir Manual Completo en Nueva Pestaña ↗</a>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Términos de Prueba Inmediata en Consola", expanded=False):
        st.markdown("""
        * **Buscar Balanceador:** `BALANCER001`
        * **Buscar por Dirección IP:** `10.24.0.125`
        * **Buscar Seguridad / Tokens:** `JWT`
        * **Consultar Contingencia:** `Failover Redis`
        * **Buscar por Serial Físico:** `SN-8842-A`
        """)


def renderizar_manual_usuario():
    """Renderiza el manual exhaustivo y detallado estructurado en 8 módulos técnicos y operativos."""
    es_inicio = bool(st.session_state.get("manual_lanzamiento"))

    st.markdown('<p class="main-title" style="margin-bottom:2px;">Manual Técnico y Guía de Operación Detallada</p>', unsafe_allow_html=True)

    if es_inicio:
        st.caption("Guía exhaustiva del sistema. Revise los módulos paso a paso o ingrese directamente a la consola.")
        col_cta, col_hint = st.columns([1.2, 2.8], gap="small", vertical_alignment="center")
        with col_cta:
            if st.button(">_ Ir a la Consola", type="primary", width="stretch", key="btn_manual_ir_consola"):
                ir_a_consola_desde_manual()
                st.rerun()
        with col_hint:
            st.caption("Puede alternar en cualquier momento entre Consola | Zen Studio | Manual de Uso desde la barra superior.")
        st.markdown("---")
    else:
        st.caption("Especificación técnica de cada componente y procedimiento operativo paso a paso.")

    if "manual_paso_actual" not in st.session_state:
        st.session_state["manual_paso_actual"] = 1

    modulos_titulos = [
        "1. Autenticación y Bóveda [VAULT]",
        "2. Búsqueda DuckDB y Scoring",
        "3. Asistente RAG (Gemini 2.5)",
        "4. Inventario y Consola SQL",
        "5. Visor Lado a Lado",
        "6. Lector Zen Studio (TOC)",
        "7. Edición, Diff y Rollback",
        "8. Ingesta ZIP y Runbooks"
    ]

    def al_cambiar_stepper():
        val = st.session_state.get("stepper_manual_selector")
        if val in modulos_titulos:
            st.session_state["manual_paso_actual"] = modulos_titulos.index(val) + 1

    def navegar_modulo(nuevo_num: int):
        if 1 <= nuevo_num <= len(modulos_titulos):
            st.session_state["manual_paso_actual"] = nuevo_num
            st.session_state["stepper_manual_selector"] = modulos_titulos[nuevo_num - 1]

    paso_num = st.session_state["manual_paso_actual"]
    if "stepper_manual_selector" not in st.session_state or st.session_state["stepper_manual_selector"] not in modulos_titulos:
        st.session_state["stepper_manual_selector"] = modulos_titulos[paso_num - 1]

    st.segmented_control(
        "Módulos del Sistema",
        modulos_titulos,
        label_visibility="collapsed",
        key="stepper_manual_selector",
        on_change=al_cambiar_stepper
    )

    paso_num = st.session_state["manual_paso_actual"]

    # Barra superior de navegación rápida y progreso
    col_t_prev, col_t_prog, col_t_next = st.columns([1.2, 2.0, 1.4], vertical_alignment="center")
    with col_t_prev:
        if paso_num > 1:
            st.button(f"< Módulo {paso_num - 1}", width="stretch", key=f"btn_top_prev_{paso_num}", on_click=navegar_modulo, args=(paso_num - 1,))
    with col_t_prog:
        st.progress(paso_num / len(modulos_titulos), text=f"Progreso: Módulo {paso_num} de {len(modulos_titulos)}")
    with col_t_next:
        if paso_num < 8:
            st.button(f"Siguiente: Módulo {paso_num + 1} >", type="primary", width="stretch", key=f"btn_top_next_{paso_num}", on_click=navegar_modulo, args=(paso_num + 1,))
        else:
            if st.button(">_ ¡Entrar a la Consola!", type="primary", width="stretch", key=f"btn_top_finish_{paso_num}"):
                ir_a_consola_desde_manual()
                st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # MÓDULO 1: AUTENTICACIÓN, ROLES Y BÓVEDA
    # =========================================================================
    if paso_num == 1:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[MÓDULO 1 DE 8]</span>
                <span class="badge-tag">Seguridad y Bóveda</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Módulo 1: Control de Acceso (RBAC), Sesiones y Bóveda Cifrada (AES-256)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Arquitectura de autenticación perimetral, almacenamiento seguro de contraseñas y custodia de credenciales.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. ¿Qué hace este componente internamente?
        * **Autenticación Perimetral (`core/auth.py`):** Bloquea la carga del DOM, la CMDB y los documentos a usuarios no autenticados. Valida credenciales contra `data/users.json` aplicando **PBKDF2-HMAC-SHA256** con salt estático y 100,000 iteraciones de hash.
        * **Matriz de Permisos RBAC:**
          * **`Administrador`:** Control total. Puede ver y modificar la Bóveda `[VAULT]`, subir archivos ZIP, editar documentos y ejecutar *Rollbacks*.
          * **`Operador`:** Técnico de operaciones. Puede realizar búsquedas, dialogar con el Asistente, usar el Visor, cargar archivos y editar (sin permisos de Rollback destructivo ni acceso a secretos).
          * **`Auditor`:** Cumplimiento normativo. Modo de solo lectura (`read-only`) para verificar inventario, documentos y la bitácora `data/audit_log.json`.
        * **Bóveda de Secretos (`core/vault.py`):** Custodia claves sensibles (`GEMINI_API_KEY`, etc.) mediante cifrado simétrico **Fernet (AES-256-CBC)** en `data/.vault.enc`. Utiliza una jerarquía en cascada: Variables de Entorno del Sistema Operativo -> Secrets de Streamlit Cloud -> Bóveda Local Cifrada.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Iniciar Sesión:**
           * Ingrese su usuario (`admin`, `operador` o `auditor`) y la contraseña correspondiente en el formulario de acceso.
           * El sistema genera la sesión en `st.session_state` y registra un evento `LOGIN_EXITOSO` en `data/audit_log.json`.
        2. **Verificar su Perfil:**
           * En el panel lateral izquierdo, observe la tarjeta superior **`Sesión Activa`**, que muestra su nombre, rol y nombre de usuario.
        3. **Configurar o Modificar Claves en la Bóveda (Solo Administrador):**
           * En el panel lateral, despliegue la sección **`Bóveda de Credenciales [VAULT]`**.
           * En el desplegable, seleccione la clave a configurar (por ejemplo, `GEMINI_API_KEY`).
           * Escriba el valor de la clave en el campo de texto y presione **`>_ Guardar`**.
           * El sistema cifra el valor en memoria y lo guarda en `data/.vault.enc` registrando la auditoría.
           * Para borrar una clave, selecciónela y presione **`>_ Revocar`**.
        4. **Cerrar Sesión:**
           * Haga clic en el botón **`>_ Cerrar Sesión`** en la barra lateral. La sesión se purga y el evento `LOGOUT` queda registrado.
        """)

    # =========================================================================
    # MÓDULO 2: BÚSQUEDA DUCKDB Y SCORING
    # =========================================================================
    elif paso_num == 2:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[MÓDULO 2 DE 8]</span>
                <span class="badge-tag">Motor en RAM</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Módulo 2: Búsqueda Textual Instantánea y Algoritmo de Scoring</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Recuperación en memoria RAM (< 2 ms) sobre DuckDB y 30 documentos técnicos con cálculo determinista de relevancia.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
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
        3. Presione `Enter` o haga clic en **`>_ Buscar en CMDB y Documentos`**.
        4. **Interpretación de Resultados:**
           * **Panel Superior (Servidores CMDB):** Muestra la cuadrícula de servidores con su IP, Nivel arquitectónico (`L1` Hardware físico, `L2` Virtualización, `L3` Middleware, `L4` Aplicaciones), Estado operativo (`[OPERATIVO]`, `[ALERTA]`, `[CRÍTICO]`) y Técnico Responsable.
           * **Panel Inferior (Documentos Técnicos):** Tarjetas con el Score de relevancia, fragmentos de texto con términos resaltados y el botón **`>_ Analizar con Asistente`** para transferir el contexto a la IA.
        """)

    # =========================================================================
    # MÓDULO 3: ASISTENTE TÉCNICO (GEMINI 2.5 FLASH RAG)
    # =========================================================================
    elif paso_num == 3:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[MÓDULO 3 DE 8]</span>
                <span class="badge-tag">IA Generativa RAG</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Módulo 3: Asistente Técnico Generativo (Google Gemini 2.5 Flash RAG)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Inferencia generativa fundamentada en evidencia documental con salvaguardas de cero alucinaciones y fallback local.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
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
        3. Presione el botón **`>_ Consultar Asistente`**.
        4. Revise la respuesta generada con pasos secuenciales, comandos de terminal y referencias documentales.
        5. Para iniciar una nueva consulta limpia, presione **`>_ Limpiar Chat`**.
        """)

    # =========================================================================
    # MÓDULO 4: INVENTARIO Y CONSOLA SQL DUCKDB
    # =========================================================================
    elif paso_num == 4:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[MÓDULO 4 DE 8]</span>
                <span class="badge-tag">Telemetría y SQL</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Módulo 4: Historial de Mantenimientos y Consola SQL en Memoria</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Tablero interactivo de activos por capas arquitectónicas y motor de consultas analíticas SQL embebido.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
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
           * Despliegue la sección **`>_ Ejecutar Consulta SQL en Memoria (DuckDB)`**.
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
           * Presione **`>_ Ejecutar SQL`** para visualizar la cuadrícula de datos resultante.
        """)

    # =========================================================================
    # MÓDULO 5: VISOR LADO A LADO
    # =========================================================================
    elif paso_num == 5:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #D97706; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-warn">[MÓDULO 5 DE 8]</span>
                <span class="badge-tag">Visor Multimodal</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #D97706;">Módulo 5: Visor Lado a Lado y Renderizado Adaptativo de Documentos</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Inspección sincronizada entre la versión Markdown indexada y el archivo binario fuente original.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. ¿Qué hace este componente internamente?
        * **Arquitectura de Doble Columna (`core/visor.py`):**
          * **Columna Izquierda (Markdown Normalizado):** Presenta el texto estructurado extraído por MarkItDown con renderizado HTML sanitizado (`preparar_markdown_con_imagenes`).
          * **Columna Derecha (Renderizador Adaptativo Binario):** Identifica la extensión del archivo original en `data/originals/` y aplica el componente nativo adecuado:
            * **PDF:** Iframe Base64 con controles nativos de zoom e impresión (con control de memoria que ofrece descarga directa si el archivo supera 2.5 MB).
            * **Excel (`.xlsx`, `.xls`):** Cuadrícula interactiva con selector dinámico de hojas de cálculo (`openpyxl`).
            * **Diagramas (`.png`, `.jpg`, `.svg`):** Visor de imagen en alta resolución con pie de imagen (*Caption*) indexable.
            * **Word / PPTX (`.docx`, `.pptx`):** Ficha técnica descriptiva con botón de descarga del binario original.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. Ingrese a la pestaña **`Documentación Técnica`**.
        2. Seleccione el tipo de documento en el filtro `Tipo` y elija el archivo en el selector `Seleccione Documento`.
        3. En la subpestaña **`Visualización Lado a Lado`**, utilice el control superior para cambiar el modo de vista:
           * **`[Lado a Lado]`:** Muestra el Markdown a la izquierda y el archivo original a la derecha.
           * **`[Solo Markdown]`:** Oculta el archivo original para concentrarse en el texto limpio.
           * **`[Solo Formato Original]`:** Muestra exclusivamente el visor PDF o la tabla Excel a todo el ancho.
        4. En libros Excel: Utilice el selector `Seleccionar Hoja de Trabajo` para alternar entre hojas del libro de cálculo.
        5. Botón de Descarga: Al pie de la columna izquierda o derecha, pulse **`Descargar Versión Activa v{N}`** para obtener una copia local en `.md`, `.xlsx` o `.pdf`.
        """)

    # =========================================================================
    # MÓDULO 6: LECTOR ZEN STUDIO (TOC)
    # =========================================================================
    elif paso_num == 6:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[MÓDULO 6 DE 8]</span>
                <span class="badge-tag">Lectura Inmersiva</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Módulo 6: Lector Zen Studio con Índice Interactivo (TOC) y Buscador Interno</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Entorno inmersivo de pantalla completa para navegación fluida en manuales técnicos de gran volumen.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. ¿Qué hace este componente internamente?
        * **Aislamiento de Interfaz (`renderizar_zen_studio`):** Inyecta CSS dinámico que oculta el sidebar y los encabezados globales, expandiendo el lienzo de lectura al **98% del ancho útil de la pantalla**.
        * **Extractor de Tabla de Contenidos (TOC):** Analiza el Markdown mediante expresiones regulares extrayendo los encabezados `H1` a `H4` y generando un árbol de navegación con indentación jerárquica.
        * **Buscador In-Document:** Resalta en tiempo real las coincidencias de una palabra dentro del texto usando `<mark>` y reporta el contador exacto de hallazgos.
        * **Motor de Temas y Tipografía:** Permite alternar la paleta de colores del lienzo (`Obsidian` oscuro, `Sepia` cálido, `Papel` blanco) y el tamaño tipográfico (`13px`, `15px`, `17px`) con interlineado optimizado (`line-height: 1.75`).
        * **Métricas Automáticas:** Calcula el volumen de palabras y el tiempo estimado de lectura aplicando el estándar de **200 palabras por minuto (WPM)**.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Entrar a Zen Studio:**
           * En la pestaña `Documentación Técnica`, presione el botón azul **`>_ Abrir en Zen Studio`** (o elija `Zen Studio` en la barra superior).
        2. **Navegar por Secciones:**
           * En el panel lateral izquierdo, use el selector **`Saltar a Sección:`** para aislar un procedimiento específico (ej: *"Procedimiento de Failover"* o *"Parámetros de Red"*), o elija *"Documento Completo"*.
        3. **Buscar Palabras Clave en el Documento:**
           * En la barra superior, escriba un término en **`Buscar en doc:`** (ej: `failover`, `puerto`, `root`). Todas las coincidencias se resaltarán en amarillo de inmediato.
        4. **Personalizar Lectura:**
           * Alterne el tema en el selector `Tema` (`Obsidian`, `Sepia`, `Papel`) y el tamaño en `Tamaño` (`Compacto`, `Normal`, `Grande`).
        5. **Subpestañas Multimodales:**
           * Alterne entre `Lector Markdown`, `Documento Original` (PDF o Excel a 750px de altura) y `Lado a Lado (50/50)`.
        6. **Salir:** Presione el botón **`>_ Salir`** en la esquina superior derecha para retornar a la consola estándar.
        """)

    # =========================================================================
    # MÓDULO 7: EDICIÓN, DIFF Y ROLLBACK
    # =========================================================================
    elif paso_num == 7:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6A397B; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-crit">[MÓDULO 7 DE 8]</span>
                <span class="badge-tag">Control de Versiones</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6A397B;">Módulo 7: Edición Colaborativa, Comparador Diff y Rollback Seguro</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Versionado incremental inmutable, cálculo de firmas SHA-256 y reversión auditada de cambios fallidos.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. ¿Qué hace este componente internamente?
        * **Inmutabilidad Documental (`core/auditoria.py`):** Los documentos nunca se sobreescriben a ciegas. Cualquier modificación genera una versión nueva incremental (`v1`, `v2`, `v3`...) almacenando un snapshot exacto en `data/history/{doc_name}/` junto con su firma criptográfica **SHA-256**.
        * **Campos Obligatorios de Auditoría:** El sistema rechaza cualquier guardado que no incluya el **Editor Responsable** y el **Motivo del Cambio**.
        * **Comparador de Diferencias (*Diff* Visual):** Compara dos versiones mediante `difflib.unified_diff`, generando una vista visual con resaltado verde para líneas añadidas y ciruela para líneas eliminadas (con límite de 400 líneas para salvaguardar el navegador).
        * **Operación de Rollback:** Restaura un snapshot histórico anterior, crea una versión nueva que registra la reversión y almacena el evento en `data/audit_log.json`.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Editar un Documento de Texto / Markdown:**
           * Vaya a `Documentación Técnica` -> subpestaña **`Editar Documento`**.
           * Modifique el texto en el área de edición.
           * Ingrese su nombre en **Editor (*)** y la justificación técnica en **Motivo (*)**.
           * Presione **`Guardar y Publicar Versión v{N+1}`**.
        2. **Editar una Hoja de Cálculo Excel:**
           * Seleccione la hoja en el desplegable.
           * Modifique celdas o agregue filas directamente en la tabla interactiva `st.data_editor`.
           * Ingrese Editor y Motivo y presione **`Guardar y Publicar Versión v{N+1}`**.
        3. **Consultar el Historial de Revisiones:**
           * Abra la subpestaña **`Historial de Versiones`** para ver la tabla de auditoría con versión, fecha/hora, editor, motivo y firma SHA-256.
        4. **Ejecutar un Rollback (Reversión):**
           * En el selector de versiones, elija la versión histórica a restaurar (ej: `v1`).
           * Revise el comparador *Diff* para comprobar qué líneas cambiaron.
           * Ingrese el nombre del técnico y el motivo de la reversión en los campos inferiores.
           * Presione **`Confirmar y Ejecutar Rollback a Versión v{N}`**. El documento anterior queda restaurado inmediatamente.
        """)

    # =========================================================================
    # MÓDULO 8: INGESTA BATCH ZIP Y RUNBOOKS
    # =========================================================================
    elif paso_num == 8:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[MÓDULO 8 DE 8]</span>
                <span class="badge-tag">Ingesta y Plantillas</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Módulo 8: Ingesta Masiva de Archivos ZIP y Generación de Runbooks</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Carga batch con descompresión en memoria RAM y redacción formal de procedimientos operativos estandarizados.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. ¿Qué hace este componente internamente?
        * **Pipeline de Ingesta ZIP (`core/procesador.py`):**
          * Descomprime paquetes comprimidos `.zip` en memoria (`io.BytesIO`) sin crear archivos temporales inseguros en disco.
          * Normaliza nombres de archivo (remoción de tildes y caracteres incompatibles).
          * Extrae texto estructurado mediante MarkItDown sin inyectar Base64 masivo en el DOM (`keep_data_uris=False`).
          * Guarda el binario en `data/originals/`, genera la versión Markdown en `data/docs/` y crea el snapshot inicial `v1`.
        * **Generador de Runbooks (`core/plantillas.py`):**
          * Asistente estructurado para redacción formal de 8 tipos de procedimientos operativos estándar (SOPs).
          * Soporte para crear nuevos tipos de procedimientos guardados en `data/plantillas_custom.json`.

        ---

        #### 2. ¿Cómo se utiliza paso a paso?
        1. **Ingestar Archivos o Lotes ZIP (Panel Lateral):**
           * En el panel lateral, arrastre un archivo suelto (`.pdf`, `.docx`, `.xlsx`, `.md`, `.png`) o un archivo comprimido **`.zip`** al cargador.
           * El motor procesa todos los archivos del paquete y muestra notificaciones toast con el recuento de archivos indexados.
        2. **Crear un Runbook o Procedimiento Operativo:**
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
           * Presione **`Guardar y Publicar en Base de Conocimiento`**. El runbook queda guardado en `data/docs/` como `v1` y disponible para búsquedas.
        3. **Sincronización:** Si agrega documentos directamente en el servidor o terminal, pulse el botón **`>_ Reindexar`** en el panel lateral para refrescar la memoria caché.
        """)

    # =========================================================================
    # BARRA DE NAVEGACIÓN INFERIOR DEL STEPPER
    # =========================================================================
    st.markdown("---")
    col_prev, col_center_info, col_next = st.columns([1.2, 2.0, 1.4], vertical_alignment="center")

    with col_prev:
        if paso_num > 1:
            st.button(f"< Módulo {paso_num - 1}", width="stretch", key=f"btn_bot_prev_{paso_num}", on_click=navegar_modulo, args=(paso_num - 1,))

    with col_center_info:
        st.markdown(f"<div style='text-align: center; font-size: 0.82rem; opacity: 0.8;'>Módulo <b>{paso_num}</b> de <b>8</b> completado</div>", unsafe_allow_html=True)

    with col_next:
        if paso_num < 8:
            st.button(f"Siguiente: Módulo {paso_num + 1} >", type="primary", width="stretch", key=f"btn_bot_next_{paso_num}", on_click=navegar_modulo, args=(paso_num + 1,))
        else:
            if st.button(">_ ¡Entrar a la Consola!", type="primary", width="stretch", key=f"btn_bot_finish_{paso_num}"):
                ir_a_consola_desde_manual()
                st.rerun()

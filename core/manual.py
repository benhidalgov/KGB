"""
Módulo de documentación interactiva y Guía Práctica Paso a Paso de la Consola de Infraestructura y Operaciones.
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
    """Manual de inicio rápido en 3 pasos visible en la pantalla de login antes de autenticar."""
    st.markdown("""
    <div class="search-result-card" style="border-left: 3.5px solid #6366F1; margin-bottom: 12px;">
        <div class="search-header-row">
            <div>
                <span class="badge-info">[GUÍA RÁPIDA]</span>
                <span class="search-doc-title" style="margin-left: 8px;">Inicio de Operaciones en 3 Pasos</span>
            </div>
            <span class="badge-tag">Paso a Paso</span>
        </div>
        <div style="font-size: 0.86rem; line-height: 1.55; opacity: 0.92; margin-top: 4px;">
            Plataforma centralizada para inventario CMDB, base documental versionada y asistencia técnica con RAG.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ##### Paso 1: Seleccionar Perfil de Acceso
    Elija una de las cuentas preconfiguradas según su rol operativo:
    * **`admin`** (`admin2026`): Acceso total a Bóveda `[VAULT]`, Ingesta, Edición y Rollback auditado.
    * **`operador`** (`operador2026`): Consultas RAG, Búsqueda DuckDB, Visor de Documentos e Ingesta.
    * **`auditor`** (`auditor2026`): Modo de solo lectura para inspección técnica y bitácora.

    ##### Paso 2: Autenticación y Flujo Guiado
    1. Ingrese el usuario y la contraseña en el formulario a la izquierda.
    2. Al autenticarse, se desplegará automáticamente el **Manual Paso a Paso** con los 6 flujos clave.
    3. Puede cambiar en cualquier momento entre el **Manual**, la **Consola** o el **Zen Studio** desde la barra superior.

    ##### Paso 3: Consultas y Operación en Consola
    * **Búsqueda instantánea (< 2 ms):** Escriba un hostname (`BALANCER001`), IP (`10.24.0.125`) o serial (`SN-8842-A`).
    * **Diagnóstico Asistido:** Pregunte en lenguaje natural sobre contingencias, arquitectura o procedimientos.
    """)

    with st.expander("Términos y Atajos Recomendados", expanded=False):
        st.markdown("""
        * **Balanceador de Carga:** `BALANCER001`
        * **Seguridad y Tokens:** `JWT`
        * **Dirección IP Crítica:** `10.24.0.125`
        * **Procedimiento de Contingencia:** `Failover Redis`
        * **Número de Serie Físico:** `SN-8842-A`
        """)


def renderizar_manual_usuario():
    """Renderiza el manual interactivo paso a paso estructurado como flujo guiado de 6 etapas."""
    es_inicio = bool(st.session_state.get("manual_lanzamiento"))

    st.markdown('<p class="main-title">Manual de Operaciones: Flujo Guiado Paso a Paso</p>', unsafe_allow_html=True)
    if es_inicio:
        st.caption("Guía de bienvenida interactiva. Complete los pasos secuenciales o ingrese directamente a la consola.")
        col_cta, col_hint = st.columns([1.2, 2.8], gap="small", vertical_alignment="center")
        with col_cta:
            if st.button(">_ Ir a la Consola", type="primary", width="stretch", key="btn_manual_ir_consola"):
                ir_a_consola_desde_manual()
                st.rerun()
        with col_hint:
            st.caption("También puede alternar la vista en la barra superior: Consola | Zen Studio | Manual de Uso.")
        st.markdown("---")
    else:
        st.caption("Guía operativa interactiva. Seleccione un paso para revisar el procedimiento detallado.")

    # Inicialización del paso activo
    if "manual_paso_actual" not in st.session_state:
        st.session_state["manual_paso_actual"] = 1

    pasos_titulos = [
        "1. Acceso y Roles (RBAC)",
        "2. Búsqueda en CMDB (< 2 ms)",
        "3. Asistente Técnico (RAG)",
        "4. Visor Lado a Lado y Zen",
        "5. Edición y Rollback Seguro",
        "6. Ingesta Batch y Runbooks"
    ]

    # Stepper interactivo en barra segmentada
    paso_idx_prev = st.session_state["manual_paso_actual"] - 1
    paso_sel_str = st.segmented_control(
        "Navegación de Pasos",
        pasos_titulos,
        default=pasos_titulos[paso_idx_prev] if 0 <= paso_idx_prev < len(pasos_titulos) else pasos_titulos[0],
        label_visibility="collapsed",
        key="stepper_manual_selector"
    ) or pasos_titulos[0]

    # Sincronizar índice según la selección del usuario
    try:
        paso_num = pasos_titulos.index(paso_sel_str) + 1
    except ValueError:
        paso_num = 1
    st.session_state["manual_paso_actual"] = paso_num

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # PASO 1: ACCESO Y ROLES (RBAC)
    # =========================================================================
    if paso_num == 1:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[PASO 1 DE 6]</span>
                <span class="badge-tag">Seguridad y Permisos</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Paso 1: Identificación y Niveles de Acceso (RBAC)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Comprenda el modelo de permisos corporativo y cómo verificar los privilegios de su sesión activa.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. Objetivo del Paso
        Verificar la identidad del operador y reconocer el alcance de acciones autorizadas para su perfil de usuario.

        ---

        #### 2. Instrucciones Paso a Paso
        1. **Revise la tarjeta de Sesión Activa:** En el panel lateral izquierdo, observe el recuadro superior donde figura su nombre de usuario, nombre corporativo y badge de rol (`Administrador`, `Operador` o `Auditor`).
        2. **Identifique los permisos de su perfil:**
           * **`Administrador`:** Acceso total a la Bóveda de Credenciales `[VAULT]`, carga masiva de archivos ZIP, edición en caliente de documentos y ejecución de *Rollbacks*.
           * **`Operador`:** Consultas con el Asistente Técnico, búsquedas instantáneas en DuckDB, visor multimodal, carga de archivos y edición estándar (sin reversiones destructivas ni acceso a secretos).
           * **`Auditor`:** Inspección en modo solo lectura de documentos, tablas de servidores y verificación de firmas SHA-256 en la bitácora.
        3. **Configuración de Bóveda (Solo Administradores):** En la sección `Bóveda de Credenciales [VAULT]` del panel lateral, configure la variable `GEMINI_API_KEY` para habilitar el motor generativo en la nube.
        4. **Cierre de Turno:** Al finalizar sus tareas operativas, pulse el botón **`>_ Cerrar Sesión`** para registrar el evento en auditoría y revocar la sesión.

        ---

        #### 3. Resultado Esperado en Pantalla
        * El Navbar superior mostrará el indicador de estado **`● ONLINE`** y el contador de documentos activos.
        * Las pestañas operativas quedarán habilitadas de acuerdo con la matriz de permisos de su perfil.
        """)

    # =========================================================================
    # PASO 2: BÚSQUEDA EN CMDB DUCKDB
    # =========================================================================
    elif paso_num == 2:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[PASO 2 DE 6]</span>
                <span class="badge-tag">Rendimiento en RAM</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Paso 2: Búsqueda Rápida en CMDB y Documentación (< 2 ms)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Localice servidores, IPs, números de serie y fragmentos documentales con latencia sub-milisegundo.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. Objetivo del Paso
        Aprender a consultar el inventario de infraestructura y los manuales técnicos sin consumir cuota de API externa.

        ---

        #### 2. Instrucciones Paso a Paso
        1. Ingrese a la pestaña **`Consultas y Búsqueda`** -> subpestaña **`Búsqueda Textual (DuckDB & Docs)`**.
        2. En la barra de búsqueda superior, escriba un término concreto. Ejemplos de prueba:
           * Hostname exacto: `BALANCER001`
           * Dirección IP: `10.24.0.125`
           * Estándar o protocolo: `JWT` o `SSL`
           * Procedimiento: `Failover Redis`
        3. Presione `Enter` o haga clic en **`>_ Buscar en CMDB y Documentos`**.
        4. Analice los dos paneles de respuesta generados en memoria RAM:
           * **Cuadrícula de Servidores CMDB:** Muestra hostname, IP, nivel de arquitectura (`L1` a `L4`), estado operativo (`[OPERATIVO]`, `[ALERTA]`, `[CRÍTICO]`) y técnico responsable.
           * **Extractos Documentales con Score:** Presenta los párrafos exactos donde aparece el término con resaltado amarillo `<mark>`.
        5. **Escalar al Asistente:** Si detecta un servidor con alarma o requiere un análisis más profundo, pulse el botón **`>_ Analizar con Asistente`** para transferir la consulta a la IA generativa.

        ---

        #### 3. Cómo se calcula el Score de Relevancia
        | Criterio de Coincidencia | Puntos Asignados |
        | :--- | :--- |
        | **Frase exacta coincidente en el texto** | **+30 puntos** (Máxima certeza) |
        | **Término presente en el nombre del archivo** | **+20 puntos** |
        | **Frecuencia del término en párrafos** | **+2 puntos** por cada repetición |
        """)

    # =========================================================================
    # PASO 3: ASISTENTE TÉCNICO (GEMINI RAG)
    # =========================================================================
    elif paso_num == 3:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[PASO 3 DE 6]</span>
                <span class="badge-tag">Inferencia Generativa</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Paso 3: Diagnóstico y Asistencia Técnica con Gemini RAG</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Obtenga explicaciones técnicas, análisis de causa raíz y comandos asistidos fundamentados en la evidencia.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. Objetivo del Paso
        Formular preguntas en lenguaje natural para recibir diagnósticos técnicos basados exclusivamente en la CMDB y los manuales corporativos (*Zero Hallucinations*).

        ---

        #### 2. Instrucciones Paso a Paso
        1. Vaya a la subpestaña **`Asistente Técnico (Gemini RAG)`** dentro de la pestaña de búsqueda.
        2. Escriba su consulta técnica en el campo de texto. Ejemplos recomendados:
           * *"¿Cuál es el procedimiento detallado de failover para el clúster de Redis?"*
           * *"Indícame la IP, capa arquitectónica y técnico a cargo de BALANCER001."*
           * *"¿Qué servidores de nivel L3 se encuentran en estado de alerta o revisión?"*
        3. Presione el botón **`>_ Consultar Asistente`**.
        4. El motor inyectará el contexto recuperado de DuckDB y los documentos locales hacia el modelo **`gemini-2.5-flash`**, entregando:
           * Diagnóstico formal sin informalidades ni emojis.
           * Tablas Markdown y bloques de comandos de terminal listos para ejecutar.
           * Identificación explícita de los documentos y servidores usados como evidencia.
        5. **Mecanismo de Resiliencia (Fallback Local):** Si la clave de Gemini no está configurada o hay una interrupción externa, el sistema conmuta automáticamente al **Motor Local Autónomo** para responder con datos deterministas sin interrumpir la operación.
        6. **Limpieza de Sesión:** Use el botón **`>_ Limpiar Chat`** para reiniciar la bitácora de diálogo.
        """)

    # =========================================================================
    # PASO 4: VISOR LADO A LADO Y ZEN STUDIO
    # =========================================================================
    elif paso_num == 4:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #D97706; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-warn">[PASO 4 DE 6]</span>
                <span class="badge-tag">Experiencia de Lectura</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #D97706;">Paso 4: Exploración de Documentación y Lector Zen Studio</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Inspeccione documentos en dos columnas paralelas o ingrese a pantalla completa con índice interactivo.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. Objetivo del Paso
        Comparar el texto indexado contra el archivo binario original y utilizar el entorno inmersivo para manuales extensos.

        ---

        #### 2. Instrucciones Paso a Paso
        1. Diríjase a la pestaña **`Documentación Técnica`**.
        2. Utilice los filtros superiores para seleccionar el tipo de activo (*Diagramas, Excel, PDFs, Markdown*) y elija un archivo del catálogo.
        3. **Visor Lado a Lado Estándar:**
           * **Columna Izquierda:** Texto estructurado en Markdown limpio procesado por el motor.
           * **Columna Derecha:** Archivo fuente original (PDF interactivo, cuadrícula Excel con cambio de hojas, diagrama en alta resolución o visor de código).
        4. **Entrar al Lector Zen Studio:**
           * Haga clic en el botón **`>_ Abrir en Zen Studio`** en la cabecera del documento (o elija `Zen Studio` en la barra de navegación superior).
        5. **Herramientas de Zen Studio:**
           * **Índice Interactivo (TOC):** Salte directamente a encabezados `H1`-`H4` desde el panel lateral izquierdo.
           * **Buscador Interno:** Escriba un término en la cabecera Zen para resaltarlo en amarillo `<mark>` a lo largo de todo el texto.
           * **Selector de Temas:** Alterne entre los temas `Obsidian`, `Sepia` y `Papel` según la iluminación de su entorno.
           * **Métricas de Lectura:** Verifique el total de palabras y el tiempo estimado de lectura en minutos.
        6. **Salir:** Presione el botón **`>_ Salir`** para volver a la consola normal.
        """)

    # =========================================================================
    # PASO 5: EDICIÓN Y ROLLBACK SEGURO
    # =========================================================================
    elif paso_num == 5:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6A397B; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-crit">[PASO 5 DE 6]</span>
                <span class="badge-tag">Auditoría e Inmutabilidad</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6A397B;">Paso 5: Edición Colaborativa, Versionado y Rollback Seguro</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Actualice fichas técnicas y libros Excel con registro obligatorio de auditoría y respaldo inmutable.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. Objetivo del Paso
        Modificar información técnica con trazabilidad estricta y aprender a revertir cambios fallidos sin riesgo de pérdida de datos.

        ---

        #### 2. Instrucciones Paso a Paso
        1. En la pestaña **`Documentación Técnica`**, seleccione el archivo deseado y abra la subpestaña **`Editar Documento`**.
        2. **Edición según formato:**
           * **Si es Excel:** Modifique los datos directamente en la tabla interactiva (`st.data_editor`).
           * **Si es Markdown / Texto:** Edite el contenido en el área de texto protegida.
           * **Si es un Diagrama:** Modifique la descripción técnica (*Caption*) en su formulario dedicado.
        3. **Registro Obligatorio de Auditoría:** Ingrese su nombre en **Editor / Responsable** y detalle el **Motivo del Cambio** (ej: *"Actualización de IP de réplica en cluster PostgreSQL"*).
        4. Haga clic en **`Guardar y Publicar Versión v{N+1}`**. El sistema genera un snapshot inmutable en `data/history/` y calcula la firma SHA-256.
        5. **Cómo Ejecutar un Rollback (Reversión):**
           * Abra la subpestaña **`Historial de Versiones`**.
           * Seleccione la versión previa que desea restaurar (ej: `v1`).
           * Revise el comparador visual de diferencias (*Diff*).
           * Ingrese la justificación técnica del rollback y presione **`Confirmar y Ejecutar Rollback`**.
           * El sistema restaurará el archivo anterior, creando una nueva versión y registrando el evento en `data/audit_log.json`.
        """)

    # =========================================================================
    # PASO 6: INGESTA BATCH Y RUNBOOKS
    # =========================================================================
    elif paso_num == 6:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[PASO 6 DE 6]</span>
                <span class="badge-tag">Operaciones Avanzadas</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Paso 6: Ingesta Masiva de Archivos y Generación de Runbooks</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Incorpore lotes de documentos comprimidos y estandarice procedimientos operativos formales.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### 1. Objetivo del Paso
        Cargar paquetes masivos de documentación y redactar procedimientos de emergencia listos para producción.

        ---

        #### 2. Instrucciones Paso a Paso
        1. **Ingesta de Paquetes ZIP (Panel Lateral):**
           * Arrastre archivos individuales o un archivo **`.zip`** completo hacia el cargador de archivos en la barra lateral.
           * El motor descomprime el lote en memoria (`io.BytesIO`), extrae el texto, sanitiza formatos, genera copias `v1` e indexa todos los archivos en tiempo real sin reiniciar el servidor.
        2. **Generación de Runbooks y Procedimientos:**
           * Abra la pestaña **`Plantillas y Runbooks`**.
           * Seleccione una plantilla prediseñada:
             * *Rollback de Emergencia*
             * *Paso a Producción*
             * *Postmortem de Incidente P1*
             * *Ficha Técnica de API REST / SOAP*
             * *Plan de Contingencia y DRP*
             * *Parchado de Sistema Operativo*
             * *Renovación de Certificados SSL/TLS*
             * *Respaldo y Restauración de Base de Datos*
           * Complete los campos guiados (Servicio, Criticidad, Ventana de Horario, Pasos Secuenciales, Comandos).
           * Compruebe la vista previa generada a la derecha y pulse **`Publicar Procedimiento en data/docs/`**.
        3. **Sincronización:** Pulse **`>_ Reindexar`** en el panel lateral para refrescar la memoria caché si agregó documentos externos por terminal.
        """)

    # =========================================================================
    # BARRA DE NAVEGACIÓN INFERIOR DEL STEPPER
    # =========================================================================
    st.markdown("---")
    col_prev, col_center_info, col_next = st.columns([1.2, 2.0, 1.4], vertical_alignment="center")

    with col_prev:
        if paso_num > 1:
            if st.button(f"< Paso {paso_num - 1}", width="stretch", key="btn_manual_prev_step"):
                st.session_state["manual_paso_actual"] = paso_num - 1
                st.rerun()

    with col_center_info:
        st.markdown(f"<div style='text-align: center; font-size: 0.82rem; opacity: 0.8;'>Paso <b>{paso_num}</b> de <b>6</b> completado</div>", unsafe_allow_html=True)

    with col_next:
        if paso_num < 6:
            if st.button(f"Siguiente: Paso {paso_num + 1} >", type="primary", width="stretch", key="btn_manual_next_step"):
                st.session_state["manual_paso_actual"] = paso_num + 1
                st.rerun()
        else:
            if st.button(">_ ¡Entrar a la Consola!", type="primary", width="stretch", key="btn_manual_finish"):
                ir_a_consola_desde_manual()
                st.rerun()

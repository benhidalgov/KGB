"""
Módulo de documentación interactiva y Guía Práctica de Uso Paso a Paso de la Consola de Infraestructura y Operaciones.
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
    """Guía de inicio rápido paso a paso en la pantalla de login antes de autenticar."""
    st.markdown("""
    <div class="search-result-card" style="border-left: 3.5px solid #6366F1; margin-bottom: 12px;">
        <div class="search-header-row">
            <div>
                <span class="badge-info">[GUÍA DE USO]</span>
                <span class="search-doc-title" style="margin-left: 8px;">Cómo utilizar la consola paso a paso</span>
            </div>
            <span class="badge-tag">Flujo Operativo</span>
        </div>
        <div style="font-size: 0.86rem; line-height: 1.55; opacity: 0.92; margin-top: 4px;">
            Aprenda el flujo completo de trabajo: desde la recepción de una alerta hasta el diagnóstico, consulta técnica y resolución documentada.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ##### 1. Cómo iniciar sesión
    1. Seleccione una cuenta en la tabla de abajo según su rol:
       * **`admin`** / `admin2026` (Control total, bóveda de claves, ingesta y reversiones).
       * **`operador`** / `operador2026` (Búsquedas, asistente generativo, visor y edición).
       * **`auditor`** / `auditor2026` (Inspección en solo lectura y bitácora).
    2. Escriba usuario y contraseña en el formulario y presione **Iniciar Sesión**.

    ##### 2. Qué hacer una vez dentro
    1. Se abrirá la **Guía Práctica Paso a Paso** con el recorrido operativo en 6 etapas.
    2. Revise el flujo o presione **`>_ Ir a la Consola`** para comenzar a operar.
    3. Para probar el sistema de inmediato, busque `BALANCER001`, `10.24.0.125` o `Failover Redis`.
    """)

    st.markdown("""
    <div style="margin-top: 10px; margin-bottom: 8px;">
        <a href="?view=manual" target="_blank" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; font-weight:600; font-size:0.82rem; color:#6366F1; border:1px solid rgba(99,102,241,0.3); padding:6px 14px; border-radius:6px; background:rgba(99,102,241,0.06);">>_ Abrir Manual en Nueva Pestaña ↗</a>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Atajos y Casos de Prueba Listos", expanded=False):
        st.markdown("""
        * **Buscar Balanceador:** `BALANCER001`
        * **Buscar por Dirección IP:** `10.24.0.125`
        * **Buscar Seguridad / Tokens:** `JWT`
        * **Consultar Contingencia:** `Failover Redis`
        * **Buscar por Serial Físico:** `SN-8842-A`
        """)


def renderizar_manual_usuario():
    """Renderiza la guía práctica de uso paso a paso estructurada en 6 etapas secuenciales del trabajo diario."""
    es_inicio = bool(st.session_state.get("manual_lanzamiento"))

    col_head_title, col_head_link = st.columns([3.2, 1.3], vertical_alignment="center")
    with col_head_title:
        st.markdown('<p class="main-title" style="margin-bottom:2px;">Guía Práctica: Cómo usar el sistema paso a paso</p>', unsafe_allow_html=True)
    with col_head_link:
        st.markdown('<div style="text-align:right;"><a href="?view=manual" target="_blank" style="text-decoration:none; font-size:0.78rem; font-weight:600; color:#6366F1; border:1px solid rgba(99,102,241,0.3); padding:4px 10px; border-radius:6px; background:rgba(99,102,241,0.06); display:inline-flex; align-items:center; gap:4px;">Abrir en Nueva Pestaña ↗</a></div>', unsafe_allow_html=True)

    if es_inicio:
        st.caption("Flujo de inducción operativa. Siga los pasos secuenciales o pulse el botón para ir a la consola.")
        col_cta, col_hint = st.columns([1.2, 2.8], gap="small", vertical_alignment="center")
        with col_cta:
            if st.button(">_ Ir a la Consola", type="primary", width="stretch", key="btn_manual_ir_consola"):
                ir_a_consola_desde_manual()
                st.rerun()
        with col_hint:
            st.caption("Puede alternar en cualquier momento entre Consola | Zen Studio | Manual de Uso desde la barra superior.")
        st.markdown("---")
    else:
        st.caption("Recorrido práctico del trabajo diario en la consola. Seleccione una etapa para ver cómo se ejecuta.")

    if "manual_paso_actual" not in st.session_state:
        st.session_state["manual_paso_actual"] = 1

    etapas_titulos = [
        "Paso 1: Iniciar Turno y Verificar Estado",
        "Paso 2: Buscar Servidores ante una Alerta",
        "Paso 3: Pedir Diagnóstico al Asistente",
        "Paso 4: Consultar Manuales en Zen Studio",
        "Paso 5: Registrar Cambios con Auditoría",
        "Paso 6: Crear Runbooks e Ingestar Lotes"
    ]

    paso_idx_prev = st.session_state["manual_paso_actual"] - 1
    paso_sel_str = st.segmented_control(
        "Etapas de Operación",
        etapas_titulos,
        default=etapas_titulos[paso_idx_prev] if 0 <= paso_idx_prev < len(etapas_titulos) else etapas_titulos[0],
        label_visibility="collapsed",
        key="stepper_manual_selector"
    ) or etapas_titulos[0]

    try:
        paso_num = etapas_titulos.index(paso_sel_str) + 1
    except ValueError:
        paso_num = 1
    st.session_state["manual_paso_actual"] = paso_num

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # PASO 1: INICIAR TURNO Y VERIFICAR ESTADO
    # =========================================================================
    if paso_num == 1:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[PASO 1 DE 6]</span>
                <span class="badge-tag">Inicio de Turno</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Paso 1: Iniciar Turno y Verificar el Entorno Operativo</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Compruebe la disponibilidad de los servicios, su rol activo y el estado de la base documental antes de operar.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### ¿Qué se hace en este paso?
        Al comenzar su guardia o turno operativo, valide que la consola está lista para responder consultas y reconozca sus permisos.

        ---

        #### Cómo se hace paso a paso:
        1. **Mire la Barra Superior (Navbar):**
           * Compruebe que el indicador marque **`● ONLINE`** (verde con pulso activo).
           * Verifique el contador de documentos activos en la esquina derecha (debe indicar 30 documentos cargados).
        2. **Revise el Panel Lateral (Sidebar):**
           * En la tarjeta superior **`Sesión Activa`**, valide su nombre de usuario y su rol (`Administrador`, `Operador` o `Auditor`).
           * Despliegue la sección **`Explorador Documental`** para ver el catálogo de diagramas, libros Excel y manuales Word/PDF.
        3. **Verificación de Claves (Solo Administradores):**
           * En la sección **`Bóveda de Credenciales [VAULT]`**, verifique que `GEMINI_API_KEY` figure como `[CONFIGURADO]`. Si no lo está, ingrese la clave y pulse **`>_ Guardar`**.

        ---

        #### Resultado en pantalla:
        * La consola se encuentra lista y conectada en memoria RAM para procesar búsquedas en menos de 2 milisegundos.
        """)

    # =========================================================================
    # PASO 2: BUSCAR SERVIDORES ANTE UNA ALERTA
    # =========================================================================
    elif paso_num == 2:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[PASO 2 DE 6]</span>
                <span class="badge-tag">Atención de Incidentes</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Paso 2: Buscar Servidores o IPs ante una Alerta (< 2 ms)</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Localice de inmediato el servidor afectado, su técnico asignado y los manuales de contingencia relacionados.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### ¿Qué se hace en este paso?
        Llega una notificación de monitoreo (Nagios/PRTG) indicando lentitud o corte en un servicio. Debe ubicar la máquina en la CMDB en milisegundos.

        ---

        #### Cómo se hace paso a paso:
        1. Vaya a la primera pestaña: **`Consultas y Búsqueda`** -> subpestaña **`Búsqueda Textual (DuckDB & Docs)`**.
        2. Escriba el dato que le entregó la alerta en la barra de búsqueda:
           * Por Hostname: `BALANCER001`
           * Por Dirección IP: `10.24.0.125`
           * Por Número de Serie: `SN-8842-A`
           * Por Servicio o Tecnología: `Redis`, `JWT`, `PostgreSQL`
        3. Presione `Enter` o haga clic en **`>_ Buscar en CMDB y Documentos`**.
        4. **Revise la Tabla de Servidores (Panel Superior):**
           * Identifique la IP, Nivel arquitectónico (`L1 Hardware`, `L2 Virtualización`, `L3 Middleware`, `L4 Aplicaciones`), Estado (`[OPERATIVO]`, `[ALERTA]`, `[CRÍTICO]`) y Técnico Responsable.
        5. **Revise los Extractos Documentales (Panel Inferior):**
           * Lea los párrafos exactos de manuales donde se menciona el servidor con los términos destacados en amarillo `<mark>`.
        6. **Escalamiento Rápido:** Pulse el botón **`>_ Analizar con Asistente`** situado en la tarjeta del servidor para trasladar la consulta al módulo de IA.

        ---

        #### Ejemplo de resultado:
        | Servidor | Dirección IP | Capa | Estado | Técnico |
        | :--- | :--- | :--- | :--- | :--- |
        | `BALANCER001` | `10.24.0.125` | `L2 (Virtualización)` | `[ALERTA]` | Carlos DevOps |
        """)

    # =========================================================================
    # PASO 3: PEDIR DIAGNÓSTICO AL ASISTENTE
    # =========================================================================
    elif paso_num == 3:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6366F1; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-info">[PASO 3 DE 6]</span>
                <span class="badge-tag">Diagnóstico Asistido</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6366F1;">Paso 3: Pedir Diagnóstico y Comandos al Asistente Técnico</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Consulte en lenguaje natural cómo resolver el problema basándose en la documentación oficial de la empresa.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### ¿Qué se hace en este paso?
        No recuerda la secuencia exacta de comandos para conmutar un nodo o reiniciar un clúster. El Asistente redacta la guía paso a paso basada en los manuales de la empresa.

        ---

        #### Cómo se hace paso a paso:
        1. Abra la subpestaña **`Asistente Técnico (Gemini RAG)`**.
        2. Formule su pregunta técnica en lenguaje natural. Ejemplos de uso diario:
           * *"¿Cómo realizo el failover manual del clúster Redis según los manuales de contingencia?"*
           * *"Indícame los pasos para reiniciar de forma segura el balanceador BALANCER001 sin botar sesiones."*
           * *"¿Cuáles son los servidores de base de datos en estado crítico y quién los administra?"*
        3. Presione el botón **`>_ Consultar Asistente`**.
        4. El motor recupera la evidencia documental y genera una respuesta formal con:
           * Diagnóstico estructurado y orden cronológico de ejecución.
           * Bloques de comandos de terminal listos para copiar.
           * Referencias a los documentos exactos utilizados como evidencia.
        5. **Si no hay conexión a internet o falta la API Key:** La consola activa automáticamente el **Motor Local Autónomo** para responder con los datos duros de la CMDB sin caídas de servicio.

        ---

        #### Para reiniciar la conversación:
        * Pulse el botón **`>_ Limpiar Chat`** para borrar el historial de preguntas y comenzar un nuevo caso de diagnóstico.
        """)

    # =========================================================================
    # PASO 4: CONSULTAR MANUALES EN ZEN STUDIO
    # =========================================================================
    elif paso_num == 4:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #D97706; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-warn">[PASO 4 DE 6]</span>
                <span class="badge-tag">Inspección de Documentos</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #D97706;">Paso 4: Consultar Manuales y Planos en Zen Studio</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Lea manuales de 50+ páginas, hojas Excel o diagramas de red en pantalla completa sin distracciones.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### ¿Qué se hace en este paso?
        Necesita verificar el diagrama de arquitectura o el documento PDF oficial antes de ejecutar un cambio en producción.

        ---

        #### Cómo se hace paso a paso:
        1. Vaya a la pestaña **`Documentación Técnica`**.
        2. Seleccione el documento en el catálogo desplegable (ej: `CMDB UNICARD v 1.1.xlsx` o `DIAGRAMA__Arquitectura_Red.png`).
        3. **Visor Lado a Lado (Comparativa):**
           * A la izquierda verá el texto Markdown normalizado.
           * A la derecha verá el archivo original: PDF interactivo para hacer zoom, Excel con selector de hojas o imagen en alta resolución.
        4. **Lector Inmersivo Zen Studio:**
           * Presione el botón azul **`>_ Abrir en Zen Studio`** (o elija `Zen Studio` en la barra superior).
           * La pantalla ocultará todos los menús laterales para dejar el 100% del espacio al documento.
        5. **Herramientas en Zen Studio:**
           * **Índice (TOC):** En el panel izquierdo, haga clic en cualquier título `H1-H4` para saltar directo a esa sección.
           * **Buscador en documento:** Escriba `failover` o `puerto 8080` en la cabecera para resaltar todas las apariciones en amarillo.
           * **Temas de lectura:** Alterne entre `Obsidian` (oscuro), `Sepia` (cálido) y `Papel` (blanco).
        6. Presione **`>_ Salir`** en la esquina superior para volver a la consola operativa.
        """)

    # =========================================================================
    # PASO 5: REGISTRAR CAMBIOS CON AUDITORÍA
    # =========================================================================
    elif paso_num == 5:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #6A397B; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-crit">[PASO 5 DE 6]</span>
                <span class="badge-tag">Versionado y Rollback</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #6A397B;">Paso 5: Registrar Cambios con Auditoría y Rollback Seguro</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Actualice fichas técnicas y libros Excel con registro de autor y capacidad de revertir errores en un clic.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### ¿Qué se hace en este paso?
        Modificó la IP de contingencia de un servidor o actualizó un libro Excel y debe guardar el cambio sin riesgo de sobreescribir a ciegas.

        ---

        #### Cómo se hace paso a paso:
        1. En **`Documentación Técnica`**, abra la subpestaña **`Editar Documento`**.
        2. **Realice la modificación:**
           * Si es Excel: Cambie el valor directamente en la celda de la tabla interactiva (`st.data_editor`).
           * Si es Markdown / Texto: Modifique las líneas en el editor de texto.
           * Si es un Diagrama: Edite la descripción técnica (*Caption*).
        3. **Complete los Campos Obligatorios de Auditoría:**
           * Ingrese su nombre en **Editor (*)** (ej: `Carlos DevOps`).
           * Ingrese la justificación en **Motivo (*)** (ej: `Actualización de IP de réplica tras mantenimiento`).
        4. Presione **`Guardar y Publicar Versión v{N+1}`**. El sistema genera una versión inmutable con copia de respaldo en `data/history/`.
        5. **¿Cómo hacer Rollback si el cambio fue erróneo?**
           * Vaya a la subpestaña **`Historial de Versiones`**.
           * Seleccione la versión anterior en el desplegable (ej: `v1`).
           * Revise el comparador visual de diferencias (*Diff*).
           * Ingrese el motivo del rollback y presione **`Confirmar y Ejecutar Rollback`**. El sistema restaurará la versión anterior de inmediato.
        """)

    # =========================================================================
    # PASO 6: CREAR RUNBOOKS E INGESTAR LOTES
    # =========================================================================
    elif paso_num == 6:
        st.markdown("""
        <div class="search-result-card" style="border-left: 4px solid #10B981; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge-ok">[PASO 6 DE 6]</span>
                <span class="badge-tag">Estandarización e Ingesta</span>
            </div>
            <h3 style="margin-top: 8px; margin-bottom: 4px; color: #10B981;">Paso 6: Crear Runbooks Oficiales e Ingestar Paquetes ZIP</h3>
            <div style="font-size: 0.88rem; opacity: 0.85;">
                Estandarice los procedimientos operativos del equipo y cargue paquetes masivos de archivos en segundos.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### ¿Qué se hace en este paso?
        Redacta el informe postmortem del incidente o sube un paquete ZIP con nuevos manuales técnicos para que todo el equipo pueda buscarlos.

        ---

        #### Cómo se hace paso a paso:
        1. **Crear un Runbook Formal:**
           * Abra la pestaña **`Plantillas y Runbooks`**.
           * Seleccione el tipo de procedimiento: *Postmortem P1, Rollback de Emergencia, Paso a Producción, DRP, Parchado SO, Certificados SSL*.
           * Complete el formulario guiado (Nombre del servicio, criticidad, ventana de mantenimiento, pasos secuenciales).
           * Revise la vista previa generada en tiempo real a la derecha.
           * Presione **`Publicar Procedimiento en data/docs/`**. El runbook queda indexado como `v1` y disponible de inmediato para búsquedas.
        2. **Cargar Lotes de Archivos (Paquetes ZIP):**
           * En el panel lateral, arrastre un archivo comprimido **`.zip`** (o archivos sueltos `.pdf`, `.docx`, `.xlsx`, `.png`) al cargador.
           * El motor descomprime en memoria, sanitiza nombres, genera versiones `v1` e indexa todo en tiempo real.
        3. **Sincronización Final:**
           * Si agregó archivos por terminal en `data/docs/`, pulse el botón **`>_ Reindexar`** en el panel lateral para refrescar la memoria caché de consultas.

        ---

        #### ¡Listo! Ya conoce el ciclo operativo completo.
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

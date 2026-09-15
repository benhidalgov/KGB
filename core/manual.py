"""
Módulo de documentación interactiva y Manual Detallado de Arquitectura y Operación Paso a Paso.
"""
from pathlib import Path
import re
import streamlit as st


@st.cache_data
def obtener_modulos_manual() -> dict[int, str]:
    """Carga dinámicamente los 8 módulos técnicos desde data/MANUAL_DE_OPERACIONES.md."""
    ruta_manual = Path(__file__).resolve().parent.parent / "data" / "MANUAL_DE_OPERACIONES.md"
    if not ruta_manual.exists():
        return {}
    contenido = ruta_manual.read_text(encoding="utf-8")
    partes = re.split(r"(?m)^## Módulo\s+(\d+)", contenido)
    return {
        int(partes[i]): re.sub(r"\n+---\s*$", "", partes[i + 1]).strip()
        for i in range(1, len(partes), 2)
    }


def activar_manual_en_inicio():
    """Abre el manual completo como primera vista tras el login."""
    st.session_state["top_navbar_view_selector"] = "Manual de Uso"
    st.session_state["manual_lanzamiento"] = True
    st.session_state["manual_paso_actual"] = 1


def ir_a_consola_desde_manual():
    """Cierra el onboarding de inicio o la vista standalone y redirige a la consola."""
    st.session_state["manual_lanzamiento"] = False
    st.session_state["_ir_consola"] = True
    st.session_state["top_navbar_view_selector"] = "Consola"
    try:
        if hasattr(st, "query_params"):
            for p in ["view", "manual"]:
                if p in st.query_params:
                    del st.query_params[p]
            st.query_params.clear()
    except Exception:
        pass


def renderizar_boton_entrar_consola(key_prefix: str, paso_num: int, label: str = ">_ ¡Entrar a la Consola!"):
    """Renderiza el botón de acceso a la consola compatible con vistas standalone y estándar."""
    es_standalone = bool(
        hasattr(st, "query_params") and (st.query_params.get("view") == "manual" or st.query_params.get("manual") == "1")
    )
    if es_standalone:
        st.markdown(
            f'<a href="./" target="_self" style="display:flex;justify-content:center;align-items:center;width:100%;height:38px;background:#6366F1;color:#ffffff;font-weight:600;font-size:0.875rem;border-radius:8px;text-decoration:none;border:none;box-shadow:0 1px 2px rgba(0,0,0,0.2);cursor:pointer;">{label}</a>',
            unsafe_allow_html=True
        )
    else:
        if st.button(label, type="primary", width="stretch", key=f"{key_prefix}_{paso_num}", on_click=ir_a_consola_desde_manual):
            ir_a_consola_desde_manual()
            st.rerun()


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
    Utilice las credenciales corporativas asignadas por el administrador de infraestructura:
    * **`admin`** (Administrador): Acceso total, Bóveda `[VAULT]`, Ingesta, Edición y Rollback auditado.
    * **`operador`** (Operador): Búsqueda DuckDB, Asistente RAG, Visor Lado a Lado y Edición.
    * **`auditor`** (Auditor): Solo lectura de CMDB, documentos y bitácora SHA-256.

    Las contraseñas se configuran mediante variables de entorno (`ADMIN_PASSWORD`, `OPERADOR_PASSWORD`, `AUDITOR_PASSWORD`). Consulte al responsable del despliegue si desconoce sus credenciales.

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
            renderizar_boton_entrar_consola("btn_manual_ir_consola", 0, label=">_ Ir a la Consola")
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
            renderizar_boton_entrar_consola("btn_top_finish", paso_num)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    modulos = obtener_modulos_manual()
    contenido_modulo = modulos.get(paso_num, "Contenido no disponible para este módulo.")
    st.markdown(contenido_modulo, unsafe_allow_html=True)

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
            renderizar_boton_entrar_consola("btn_bot_finish", paso_num)

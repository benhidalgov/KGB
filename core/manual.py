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


def ir_a_consola_desde_manual():
    """Cierra el onboarding de inicio o la vista standalone y redirige a la consola."""
    st.session_state["manual_lanzamiento"] = False
    st.session_state["_ir_consola"] = True
    try:
        if hasattr(st, "query_params"):
            for p in ["view", "manual"]:
                if p in st.query_params:
                    del st.query_params[p]
            st.query_params.clear()
    except Exception:
        pass


def renderizar_boton_entrar_consola(key_prefix: str, paso_num: int, label: str = "Ir a la Consola"):
    """Renderiza el botón de acceso a la consola compatible con vistas standalone y estándar."""
    es_standalone = bool(
        hasattr(st, "query_params") and (st.query_params.get("view") == "manual" or st.query_params.get("manual") == "1")
    )
    if es_standalone:
        st.markdown(
            f'<a href="./" target="_self" style="display:flex;justify-content:center;align-items:center;width:100%;height:38px;background:var(--btn-primary-bg);color:var(--btn-primary-text);font-family:var(--font-sans);font-weight:500;font-size:0.875rem;border-radius:6px;text-decoration:none;border:none;cursor:pointer;">{label}</a>',
            unsafe_allow_html=True
        )
    else:
        if st.button(label, type="primary", width="stretch", key=f"{key_prefix}_{paso_num}", on_click=ir_a_consola_desde_manual):
            ir_a_consola_desde_manual()
            st.rerun()


def _cb_autocompletar_cuenta_manual(usuario: str):
    """Callback seguro previo a la instanciación de widgets para autocompletar credenciales."""
    st.session_state["login_username_val"] = usuario
    st.session_state["login_password_val"] = st.session_state.get(f"_pwd_{usuario}", f"{usuario}2026")


def renderizar_manual_lanzamiento():
    """Guía de inicio rápido en la pantalla de login antes de autenticar."""
    st.markdown("""
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-subtle); padding-bottom:10px; margin-bottom:12px;">
        <div style="display:flex; align-items:center; gap:8px;">
            <span class="badge-info">[Guía rápida]</span>
            <span style="font-family:var(--font-serif); font-size:1.15rem; font-weight:500; color:var(--text-primary); margin-left:4px;">Uso de la Consola</span>
        </div>
        <span class="badge-tag">Primeros pasos</span>
    </div>
    <div style="font-size: 0.86rem; line-height: 1.55; color: var(--text-secondary); margin-bottom: 14px;">
        Busca, consulta y gestiona documentos técnicos e inventario en un entorno unificado.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ##### 1. Cuentas y perfiles disponibles
    Utiliza cualquiera de las credenciales autorizadas (puedes seleccionarlas con un clic a la izquierda):
    * **`admin`** (Administrador): gestión integral de infraestructura, bóveda de secretos y auditoría.
    * **`operador`** (Operador): búsqueda técnica, asistente con IA y edición documental.
    * **`auditor`** (Auditor): inspección de registros y modo lectura de CMDB.

    ##### 2. Primeros pasos
    1. Inicia sesión con tus credenciales de rol.
    2. Explora el manual interactivo de 8 módulos técnicos.
    3. Pulsa **`Ir a la Consola`** para acceder de inmediato al entorno.
    """)

    st.markdown("""
    <div style="margin-top: 16px; margin-bottom: 4px;">
        <a href="?view=manual" target="_blank" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; font-weight:500; font-size:0.82rem; color:var(--text-primary); border:1px solid var(--border-medium); padding:7px 16px; border-radius:6px; background-color:var(--bg-surface);">Abrir Manual en Pestaña Independiente</a>
    </div>
    """, unsafe_allow_html=True)


def renderizar_manual_usuario():
    """Renderiza el manual exhaustivo y detallado estructurado en 8 módulos técnicos y operativos."""
    es_inicio = bool(st.session_state.get("manual_lanzamiento"))

    st.markdown('<p class="main-title" style="margin-bottom:2px;">Manual de Uso</p>', unsafe_allow_html=True)

    if es_inicio:
        st.caption("Guía del sistema. Revisa los pasos o entra directo a la consola.")
        col_cta, col_hint = st.columns([1.2, 2.8], gap="small", vertical_alignment="center")
        with col_cta:
            renderizar_boton_entrar_consola("btn_manual_ir_consola", 0, label="Ir a la Consola")
        with col_hint:
            st.caption("Puedes cambiar entre Consola, el modo lectura y este manual desde la barra superior.")
        st.markdown("---")
    else:
        st.caption("Explicación de cada parte y cómo usarla.")

    if "manual_paso_actual" not in st.session_state:
        st.session_state["manual_paso_actual"] = 1

    modulos_titulos = [
        "1. Acceso y Bóveda",
        "2. Búsqueda",
        "3. Asistente",
        "4. Inventario y SQL",
        "5. Visor de Documentos",
        "6. Modo Lectura",
        "7. Editar y Versionar",
        "8. Subir Archivos y Runbooks"
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

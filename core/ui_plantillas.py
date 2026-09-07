"""
Módulo desacoplado de renderizado para la Pestaña de Generador de Runbooks y Plantillas Técnicas.
Permite configurar parámetros técnicos con esquemas dinámicos, previsualizar en vivo
y publicar procedimientos con control de versiones y categorización obligatoria.
"""
import os
import importlib
import streamlit as st
import streamlit_antd_components as sac

try:
    _mod_plant = importlib.import_module("core.plantillas")
    if not hasattr(_mod_plant, "obtener_esquema_campos"):
        importlib.reload(_mod_plant)
except Exception:
    pass

from core.plantillas import (
    generar_doc_plantilla,
    obtener_todos_los_tipos_plantillas,
    guardar_plantilla_personalizada,
    obtener_esquema_campos,
    PLANTILLAS_BASE_RESERVADAS,
)
from core.tags import (
    obtener_categorias_disponibles,
    asignar_tags_documento,
)
from core.auditoria import inicializar_version_inicial_si_no_existe
from core.motor import limpiar_cache_consultas
from core.configuracion import DOCS_DIR


def renderizar_pestana_plantillas(doc_store: dict):
    """Renderiza el generador guiado de procedimientos técnicos y runbooks."""
    st.subheader("Generador Rápido de Documentación y Runbooks")
    st.caption("Crea y publica procedimientos técnicos estandarizados o define nuevos tipos personalizados en 2 minutos.")

    st.markdown("""
    <div style="background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.22);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.83rem;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span class="badge-info" style="font-size:0.68rem;padding:2px 6px;">[MÓDULO]</span>
            <b style="color:#6366F1;font-size:0.9rem;">Generador Estandarizado de Procedimientos y Runbooks</b>
        </div>
        <div style="opacity:0.9;line-height:1.45;margin-bottom:6px;">
            <b>¿Qué hace?</b> Estandariza la redacción técnica de procedimientos operativos (Rollback, Paso a Producción, Postmortem, DRP, SSL) publicándolos directamente en la base documental indexada en Version v1.
        </div>
        <div style="opacity:0.82;line-height:1.4;font-size:0.8rem;">
            <b>¿Cómo se usa?</b> En el panel izquierdo seleccione el tipo de procedimiento y complete los parámetros técnicos requeridos; en el panel derecho previsualice el Markdown generado, asigne categoría obligatoria y presione <code>Guardar y Publicar</code>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    sac.steps(items=[
        sac.StepsItem(title="Paso 1", subtitle="Selección y Metadatos"),
        sac.StepsItem(title="Paso 2", subtitle="Parámetros Técnicos"),
        sac.StepsItem(title="Paso 3", subtitle="Previsualización y Publicación")
    ], size="sm", return_index=False)
    st.markdown("---")

    col_t1, col_t2 = st.columns([1, 1], gap="large")
    with col_t1:
        st.markdown("#### 1. Configuración del Procedimiento")
        tipo_sel = st.selectbox("Plantilla / Tipo de Procedimiento", obtener_todos_los_tipos_plantillas(), key="select_tipo_procedimiento_gen")
        es_nuevo_t = "[+ Crear" in tipo_sel

        if es_nuevo_t:
            nuevo_t_nom = st.text_input("Nombre de la Plantilla (*)", placeholder="Ej: Auditoría de Accesos", key="input_nuevo_tipo_proc")
            guardar_cat = st.checkbox("Guardar en catálogo permanente", value=True)
            tipo_plantilla = nuevo_t_nom.strip() or "Procedimiento Personalizado"
        else:
            tipo_plantilla = tipo_sel.replace("[Plantilla]", "").replace("[Personalizado]", "").strip()
            guardar_cat, nuevo_t_nom = False, ""

        with st.expander("Explorar catálogo de plantillas base reservadas (Opcional)", expanded=False):
            col_rs, col_rb = st.columns([3, 1])
            with col_rs:
                base_act = st.selectbox("Seleccionar plantilla base a activar:", PLANTILLAS_BASE_RESERVADAS, key="sel_plantilla_base_res")
            with col_rb:
                st.write("")
                st.write("")
                if st.button("[+ Activar]", key="btn_activar_plantilla_base", width="stretch"):
                    guardar_plantilla_personalizada(base_act, f"Plantilla activada: {base_act}", ["criterio", "pasos", "verif"])
                    st.toast(f"[OK] Plantilla '{base_act}' activada")
                    st.rerun()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            autor = st.text_input("Autor (*)", value="Developer / DevOps", key="proc_autor_input")
            nombre_srv = st.text_input("Servicio (*)", value="Booking Core Engine", key="proc_srv_input")
        with col_g2:
            nivel_arq = st.selectbox("Nivel", ["L4 - Aplicación y Negocio", "L3 - Middleware e Integración", "L2 - Virtualización y Cómputo", "L1 - Hardware e Infraestructura Base"], key="proc_nivel_input")
            ambiente = st.selectbox("Ambiente", ["Producción", "Staging / QA", "Desarrollo", "Datacenter DR", "Todos los Ambientes"], key="proc_amb_input")

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            criticidad = st.selectbox("Criticidad / SLA", ["Crítico 7x24 (P1)", "Alta (P2)", "Media (P3)", "Baja (P4)"], index=2, key="proc_crit_input")
        with col_g4:
            ventana = st.text_input("Ventana", value="02:00 a 04:00 AM (Horario no hábil)", key="proc_vent_input")

        servidores = st.text_input("Servidores / VMs / IPs", value="BALANCER001, 10.24.0.125, VM-BOOKING-01", key="proc_srvs_input")

        st.markdown("---")
        st.markdown("##### Parámetros Específicos del Procedimiento")
        params = {"ambiente": ambiente, "criticidad": criticidad, "ventana": ventana, "servidores": servidores}

        # Generación de campos específicos mediante esquema dinámico
        for f_key, f_lbl, f_def, f_tipo in obtener_esquema_campos(tipo_plantilla):
            val_def = f_def.replace("{servicio}", nombre_srv).replace("{tipo_plantilla}", tipo_plantilla)
            if f_tipo == "area":
                params[f_key] = st.text_area(f_lbl, value=val_def, key=f"fld_param_{f_key}")
            else:
                params[f_key] = st.text_input(f_lbl, value=val_def, key=f"fld_param_{f_key}")

        doc_gen_md, fname_sug = generar_doc_plantilla(tipo_plantilla, autor, nombre_srv, nivel_arq, params)

    with col_t2:
        st.markdown("#### 2. Previsualización en Vivo")
        nom_f = st.text_input("Nombre de Archivo Final (.md)", value=fname_sug, key="input_nombre_archivo_proc_final")

        cats_disp_rb = obtener_categorias_disponibles()
        col_rb_c1, col_rb_c2 = st.columns([1.5, 1.5])
        with col_rb_c1:
            cat_rb_exist = st.selectbox("Categoría Existente (*):", ["(Crear Nueva)"] + cats_disp_rb, key="sb_cat_proc_exist") if cats_disp_rb else "(Crear Nueva)"
        with col_rb_c2:
            cat_rb_nueva = st.text_input("Nueva Categoría (*):" if cat_rb_exist == "(Crear Nueva)" else "O escribir otra categoría:", placeholder="ej: Procedimientos, Runbooks, DRP...", key="input_cat_proc_nueva")

        with st.container(border=True):
            st.markdown(doc_gen_md)

        st.divider()
        if st.button("Guardar y Publicar en Base de Conocimiento", type="primary", width="stretch", key="btn_guardar_doc_plantilla_final"):
            cat_final_rb = cat_rb_nueva.strip() if cat_rb_nueva.strip() else (cat_rb_exist if cat_rb_exist != "(Crear Nueva)" else "")
            if not cat_final_rb:
                st.warning("[REQUERIDO] Debe asignar una categoría existente o escribir una nueva para publicar el procedimiento.")
            else:
                if not nom_f.endswith(".md"):
                    nom_f += ".md"
                if es_nuevo_t and guardar_cat and nuevo_t_nom.strip():
                    guardar_plantilla_personalizada(nuevo_t_nom.strip(), f"Plantilla personalizada {nuevo_t_nom.strip()}", ["objetivo", "prerequisitos", "pasos_custom", "verificacion_custom", "rollback_custom"])

                ruta_dest = os.path.join(DOCS_DIR, nom_f)
                os.makedirs(DOCS_DIR, exist_ok=True)
                with open(ruta_dest, "w", encoding="utf-8") as f_out:
                    f_out.write(doc_gen_md)

                doc_store[nom_f] = doc_gen_md
                asignar_tags_documento(nom_f, [cat_final_rb], autor=autor)
                inicializar_version_inicial_si_no_existe(nom_f, doc_gen_md, autor=autor, comentario=f"Creación mediante plantilla: {tipo_plantilla}")
                limpiar_cache_consultas()
                st.toast(f"Procedimiento guardado como {nom_f} bajo categoría [{cat_final_rb}]")
                st.success(f"¡Procedimiento guardado e indexado como **{nom_f}** [Version v1]!")
                st.rerun()

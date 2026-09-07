"""
Módulo desacoplado de renderizado para el Panel Lateral (Sidebar).
Gestiona la navegación central por módulos de la aplicación, información de sesión,
ingesta documental con categorización obligatoria y bóveda de credenciales.
"""
import os
import io
import zipfile
import importlib
import streamlit as st

try:
    _mod_proc = importlib.import_module("core.procesador")
    if not hasattr(_mod_proc, "procesar_e_ingestar_binario"):
        importlib.reload(_mod_proc)
except Exception:
    pass

from core.procesador import (
    SUPPORTED_EXTENSIONS,
    normalizar_nombre_archivo,
    limpiar_cache_documentos,
    cargar_documentos_locales,
    procesar_e_ingestar_binario,
)
from core.tags import (
    obtener_categorias_disponibles,
    asignar_tags_documento,
)
from core.motor import limpiar_cache_consultas
from core.auth import cerrar_sesion, tiene_permiso
from core.vault import (
    listar_secretos_disponibles,
    guardar_secreto,
    eliminar_secreto,
)


def renderizar_sidebar(user_act: dict, doc_store: dict, total_srvs: int = 0) -> str:
    """Renderiza el panel lateral: navegación principal por módulos, usuario, ingesta y bóveda."""
    with st.sidebar:
        # 1. Cabecera de Marca y Estado
        st.markdown('''
        <div style="display:flex; justify-content:space-between; align-items:center; padding:2px 0 8px 0; border-bottom:1px solid rgba(128,128,128,0.18); margin-bottom:8px;">
            <div style="font-size:0.88rem; font-weight:700; color:#6366F1; letter-spacing:0.4px;">
                <span class="badge-tag" style="font-size:0.65rem; padding:1px 5px; margin-right:4px;">[CLI]</span> Consola Operativa
            </div>
            <span class="badge-pulse-online" style="font-size:0.62rem; padding:2px 6px;"><span class="pulse-dot"></span>ONLINE</span>
        </div>
        ''', unsafe_allow_html=True)

        # 2. Información de Sesión y Logout
        col_u_info, col_u_out = st.columns([2.5, 1.5], vertical_alignment="center")
        with col_u_info:
            st.markdown(f"""
            <div style="font-size:0.86rem;font-weight:600;line-height:1.2;">{user_act.get('nombre', user_act.get('username'))}</div>
            <div style="font-size:0.68rem;opacity:0.75;margin-top:2px;"><span class="badge-ok" style="font-size:0.6rem;padding:1px 4px;">{user_act.get('rol', 'Usuario')}</span> <span style="font-family:monospace;opacity:0.6;">@{user_act.get('username')}</span></div>
            """, unsafe_allow_html=True)
        with col_u_out:
            if st.button(">_ Salir", width="stretch", key="btn_logout_sidebar", help="Cerrar sesión"):
                cerrar_sesion()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # 3. Navegación Principal (Módulos de Trabajo)
        st.markdown('<div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; opacity:0.65; margin-bottom:6px;">Navegación / Módulos</div>', unsafe_allow_html=True)

        cant_docs = len(doc_store)
        opciones_nav = [
            "Consultas y Búsqueda",
            f"Historial CMDB ({total_srvs})",
            f"Documentación Técnica ({cant_docs})",
            "Plantillas y Runbooks",
            "Zen Studio (Modo Lectura)",
        ]

        if st.session_state.pop("_ir_consola", False):
            st.session_state["nav_seccion_activa"] = opciones_nav[0]

        seccion_sel = st.radio(
            "Navegación Principal",
            options=opciones_nav,
            key="nav_seccion_activa",
            label_visibility="collapsed"
        )

        st.markdown('<div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; opacity:0.65; margin:14px 0 6px 0;">Herramientas del Sistema</div>', unsafe_allow_html=True)

        # 4. Ingesta de Archivos
        st.session_state.setdefault("uploader_key_ver", 0)
        with st.expander("Ingesta de Archivos (Batch & Lotes)", expanded=False):
            st.markdown('<div class="sidebar-format-tags" style="margin-bottom:8px;"><span class="sidebar-format-tag">[ZIP]</span><span class="sidebar-format-tag">[PDF]</span><span class="sidebar-format-tag">[DOCX]</span><span class="sidebar-format-tag">[XLSX]</span><span class="sidebar-format-tag">[DIAGRAMAS]</span><span class="sidebar-format-tag">[MD]</span></div>', unsafe_allow_html=True)
            uploaded_files = st.file_uploader(
                "Arrastra archivos o paquetes ZIP en lote:",
                type=["pdf", "docx", "xlsx", "xls", "csv", "txt", "md", "pptx", "png", "jpg", "jpeg", "svg", "webp", "zip"],
                accept_multiple_files=True,
                label_visibility="collapsed",
                key=f"uploader_files_{st.session_state.uploader_key_ver}"
            )
            if uploaded_files:
                st.markdown(f"""
                <div style="background:rgba(99,102,241,0.07);border:1px solid #6366F1;border-radius:6px;padding:8px 10px;margin:8px 0 6px 0;font-size:0.8rem;">
                    <span class="badge-info">[CATEGORIZACIÓN OBLIGATORIA]</span>
                    <div style="margin-top:4px;opacity:0.9;">Documentos a subir: <b>{len(uploaded_files)} archivo(s)</b>.</div>
                </div>
                """, unsafe_allow_html=True)

                cats_disp = obtener_categorias_disponibles()
                cat_seleccionadas = []

                if not cats_disp:
                    st.caption("No existen categorías registradas en el catálogo. Ingrese la categoría para clasificar el/los documento(s):")
                    nueva_cat_input = st.text_input("Nueva Categoría (*):", placeholder="ej: Redes, Base de Datos, Servidores, Contingencias...", key=f"sb_nueva_cat_ini_{st.session_state.uploader_key_ver}")
                    if nueva_cat_input.strip():
                        cat_seleccionadas = [nueva_cat_input.strip()]
                else:
                    modo_cat = st.radio("Clasificación:", ["Usar Existente", "Crear Nueva"], horizontal=True, key=f"sb_radio_modo_cat_{st.session_state.uploader_key_ver}")
                    if modo_cat == "Usar Existente":
                        cat_seleccionadas = st.multiselect("Categoría(s) Existente(s) (*):", options=cats_disp, key=f"sb_ms_cat_exist_{st.session_state.uploader_key_ver}")
                    else:
                        nueva_cat_input = st.text_input("Nombre de Nueva Categoría (*):", placeholder="ej: Almacenamiento SAN, VPN, Seguridad...", key=f"sb_nueva_cat_input_{st.session_state.uploader_key_ver}")
                        if nueva_cat_input.strip():
                            cat_seleccionadas = [nueva_cat_input.strip()]

                col_conf_up, col_canc_up = st.columns([2.4, 1.1])
                with col_conf_up:
                    btn_confirmar_subida = st.button(">_ Confirmar e Ingestar", type="primary", width="stretch", key="btn_confirmar_ingesta_tags")
                with col_canc_up:
                    if st.button("Cancelar", width="stretch", key="btn_cancelar_ingesta"):
                        st.session_state["uploader_key_ver"] += 1
                        st.rerun()

                if btn_confirmar_subida:
                    if not cat_seleccionadas:
                        st.warning("[REQUERIDO] Debe seleccionar al menos una categoría existente o crear una nueva para continuar.")
                    else:
                        autor_act = f"{user_act.get('username', 'Técnico')} ({user_act.get('rol', 'Operador')})"
                        proc_cnt, new_cnt, upd_cnt = 0, 0, 0
                        for uf in uploaded_files:
                            c_name = normalizar_nombre_archivo(uf.name)
                            ext_u = os.path.splitext(c_name)[1].lower()
                            buf = uf.getbuffer().tobytes()

                            if ext_u == ".zip":
                                try:
                                    with zipfile.ZipFile(io.BytesIO(buf)) as z:
                                        zip_cnt = 0
                                        for zi in [i for i in z.infolist() if not i.is_dir()]:
                                            in_fn = os.path.basename(zi.filename)
                                            if not in_fn or in_fn.startswith(".") or "__MACOSX" in zi.filename:
                                                continue
                                            in_cl = normalizar_nombre_archivo(in_fn)
                                            if os.path.splitext(in_cl)[1].lower() in SUPPORTED_EXTENSIONS:
                                                st_res, _ = procesar_e_ingestar_binario(
                                                    in_cl, z.read(zi), doc_store,
                                                    autor=autor_act, origen_detalle=f"Lote ZIP: {c_name}",
                                                    tags=cat_seleccionadas
                                                )
                                                zip_cnt += 1
                                                proc_cnt += 1
                                                if st_res == "nuevo":
                                                    new_cnt += 1
                                                elif st_res == "actualizado":
                                                    upd_cnt += 1
                                        st.toast(f"[OK] ZIP '{c_name}': {zip_cnt} archivos indexados.")
                                except Exception as e_z:
                                    st.error(f"[ERROR] Error al procesar ZIP '{c_name}': {str(e_z)}")
                            else:
                                st_res, msg = procesar_e_ingestar_binario(
                                    c_name, buf, doc_store,
                                    autor=autor_act, origen_detalle="Carga en panel lateral",
                                    tags=cat_seleccionadas
                                )
                                proc_cnt += 1
                                if st_res == "nuevo":
                                    new_cnt += 1
                                    st.toast(f"[OK] {msg}")
                                elif st_res == "actualizado":
                                    upd_cnt += 1
                                    st.toast(f"[OK] {msg}")
                                elif st_res == "sin_cambios":
                                    asignar_tags_documento(c_name, cat_seleccionadas, autor=autor_act)
                                    st.toast(f"[INFO] Tags actualizados: {c_name}")

                        limpiar_cache_consultas()
                        st.session_state["uploader_key_ver"] += 1
                        st.toast(f"[OK] {proc_cnt} archivo(s) clasificados bajo: {', '.join(cat_seleccionadas)}")
                        st.rerun()
        # 5. Herramientas del Sistema y Bóveda
        with st.expander("Herramientas del Sistema y Bóveda", expanded=False):
            if st.button(">_ Reindexar Base Documental", help="Recarga todos los documentos desde data/docs/", width="stretch", key="btn_sidebar_reindexar"):
                limpiar_cache_documentos()
                cargar_documentos_locales(doc_store, force=True)
                limpiar_cache_consultas()
                st.toast("[OK] Base documental reindexada con éxito")
                st.rerun()

            if tiene_permiso("puede_ver_vault"):
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                st.markdown("<b style='font-size:0.78rem;'>Bóveda de Credenciales [AES-256]:</b>", unsafe_allow_html=True)
                sec_list = listar_secretos_disponibles()
                cfg_cnt = sum(1 for s in sec_list if s["estado"] == "[CONFIGURADO]")
                st.markdown(f"<div style='font-size:0.72rem;margin-bottom:8px;opacity:0.8;'>Estado: <b>{cfg_cnt} configurada(s)</b>.</div>", unsafe_allow_html=True)
                for s in sec_list:
                    badge_s = '<span class="badge-ok" style="font-size:0.62rem;padding:1px 4px;">[CONFIGURADO]</span>' if s["estado"] == "[CONFIGURADO]" else '<span class="badge-tag" style="font-size:0.62rem;padding:1px 4px;">[NO CONFIGURADO]</span>'
                    prev_s = f"({s['vista_previa']})" if s['vista_previa'] != '-' else ""
                    st.markdown(f"<div style='font-size:0.72rem;padding:3px 0;display:flex;justify-content:space-between;align-items:center;'><span style='font-family:monospace;font-weight:600;'>{s['clave']}</span>{badge_s}</div><div style='font-size:0.64rem;opacity:0.6;margin-bottom:4px;'>Origen: {s['origen']} {prev_s}</div>", unsafe_allow_html=True)

                st.markdown("<b style='font-size:0.75rem;'>Guardar o Actualizar Clave:</b>", unsafe_allow_html=True)
                sel_k = st.selectbox("Seleccionar Llave:", [s["clave"] for s in sec_list] + ["OTRA_CLAVE_PERSONALIZADA"], key="sb_vault_sel_key", label_visibility="collapsed")
                k_final = st.text_input("Nombre de la Clave:", value="", placeholder="EJ: MI_API_KEY", key="sb_vault_custom_key") if sel_k == "OTRA_CLAVE_PERSONALIZADA" else sel_k
                if "vault_input_version" not in st.session_state:
                    st.session_state.vault_input_version = 0

                v_val = st.text_input("Valor Seguro:", type="password", placeholder="Pegue la clave secreta...", key=f"sb_vault_val_{st.session_state.vault_input_version}")
                col_vs, col_vd = st.columns([2, 1])
                with col_vs:
                    if st.button("Guardar Llave", width="stretch", type="primary", key="sb_btn_guardar_key"):
                        if k_final and v_val:
                            if guardar_secreto(k_final.strip().upper(), v_val.strip()):
                                st.toast(f"[OK] Clave '{k_final.strip().upper()}' almacenada con cifrado AES-256")
                                st.session_state.vault_input_version += 1
                                st.rerun()
                        else:
                            st.error("Indique nombre y valor.")
                with col_vd:
                    if st.button("Eliminar", width="stretch", key="sb_btn_eliminar_key", help="Elimina la clave de la bóveda"):
                        if k_final and k_final != "OTRA_CLAVE_PERSONALIZADA":
                            if eliminar_secreto(k_final.strip().upper()):
                                st.toast(f"[INFO] Clave '{k_final.strip().upper()}' eliminada de la bóveda")
                                st.rerun()

        return seccion_sel

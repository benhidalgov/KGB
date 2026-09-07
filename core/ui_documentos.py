"""
Módulo desacoplado de renderizado para la Pestaña de Gestión Documental y Diagramas.
Encapsula el visor interactivo (Side-by-Side, auditoría, diff y rollback), el editor activo (Excel/Markdown)
y la consola de clasificación taxonómica masiva en lote.
"""
import os
import shutil
import time
import datetime
import pandas as pd
import streamlit as st

from core.visor import renderizar_lado_a_lado
from core.procesador import (
    IMAGE_EXTENSIONS,
    normalizar_titulo_display,
    sanitizar_nombre_descarga,
    obtener_ruta_original,
    limpiar_cache_documentos,
)
from core.tags import (
    obtener_categorias_disponibles,
    obtener_tags_documento,
    asignar_tags_documento,
    obtener_documentos_sin_categoria,
    sugerir_categoria_documento,
    asignar_tags_en_lote,
)
from core.auditoria import (
    inicializar_version_inicial_si_no_existe,
    guardar_nueva_version,
    guardar_nueva_version_excel,
    obtener_contenido_version,
    obtener_bytes_snapshot,
    cargar_hoja_excel_dataframe,
    obtener_nombres_hojas_excel,
    generar_diff_texto,
    obtener_todos_los_eventos_auditoria,
    obtener_fecha_carga_documento,
)
from core.motor import limpiar_cache_consultas
from core.configuracion import DOCS_DIR, HISTORY_DIR
from excel_cleaner import procesar_excel_limpio


def renderizar_pestana_documentacion(doc_store: dict):
    """Renderiza la pestaña completa de Documentación Técnica estructurada en 3 subpestañas."""
    st.subheader("Repositorio de Documentación Técnica y Diagramas")
    st.caption("Visor interactivo Lado a Lado, control de cambios, editor de contenido y gestión taxonómica.")

    if not doc_store:
        st.warning("No hay documentos indexados en el repositorio.")
        return

    todos_docs = sorted(list(doc_store.keys()))
    docs_pendientes = obtener_documentos_sin_categoria(todos_docs)
    cats_disp_t3 = obtener_categorias_disponibles()

    lbl_lote = f"Clasificación en Lote ({len(docs_pendientes)} pendientes)" if docs_pendientes else "Clasificación en Lote"
    subtab_visor, subtab_editor, subtab_lote = st.tabs([
        "Visor y Explorador Documental",
        "Editar Documento Activo",
        lbl_lote
    ])

    # -------------------------------------------------------------
    # SUBPESTAÑA 1: VISOR Y EXPLORADOR DOCUMENTAL
    # -------------------------------------------------------------
    with subtab_visor:
        mapa_fechas = {d: obtener_fecha_carga_documento(d) for d in doc_store.keys()}
        fechas_v = [f for f in mapa_fechas.values() if f]
        min_doc_d = min(fechas_v) if fechas_v else datetime.date.today()
        max_doc_d = max(fechas_v) if fechas_v else datetime.date.today()

        opts_cat_t3 = ["Todas"]
        if docs_pendientes:
            opts_cat_t3.append(f"[Sin Categoría] ({len(docs_pendientes)})")
        opts_cat_t3.extend(cats_disp_t3)

        col_t4_t, col_t4_c, col_t4_d, col_t4_s = st.columns([1.1, 1.0, 1.1, 1.8], gap="small")
        with col_t4_t:
            filtro_t4 = st.selectbox(
                "Tipo",
                ["Todos", "Diagramas e Imágenes (.png, .jpg, .svg)", "Excel (.xlsx, .xls)", "Documentos (.docx, .pdf, .pptx)", "Markdown / Texto (.md, .txt)"],
                key="tab4_type_selector"
            )
        with col_t4_c:
            filtro_cat_t3 = st.selectbox("Categoría:", opts_cat_t3, key="tab4_cat_selector")
        with col_t4_d:
            rango_fecha_doc = st.date_input(
                "Fecha:",
                value=(min_doc_d, max_doc_d),
                min_value=min_doc_d,
                max_value=max_doc_d,
                key="tab4_date_range_selector"
            )

        docs_disp = []
        for d in sorted(doc_store.keys()):
            ext_d = os.path.splitext(d)[1].lower()
            is_diag = d.startswith("DIAGRAMA__") or ext_d in IMAGE_EXTENSIONS
            if filtro_t4.startswith("Diagramas") and not is_diag:
                continue
            if filtro_t4.startswith("Excel") and ext_d not in ('.xlsx', '.xls'):
                continue
            if filtro_t4.startswith("Documentos") and ext_d not in ('.docx', '.pdf', '.pptx', '.doc'):
                continue
            if filtro_t4.startswith("Markdown") and (is_diag or ext_d not in ('.md', '.txt', '.csv')):
                continue
            if filtro_cat_t3.startswith("[Sin Categoría]"):
                if obtener_tags_documento(d):
                    continue
            elif filtro_cat_t3 != "Todas":
                tags_d_t3 = obtener_tags_documento(d)
                if filtro_cat_t3 not in tags_d_t3:
                    continue
            f_d = mapa_fechas.get(d)
            if f_d and isinstance(rango_fecha_doc, (tuple, list)) and len(rango_fecha_doc) == 2 and not (rango_fecha_doc[0] <= f_d <= rango_fecha_doc[1]):
                continue
            docs_disp.append(d)

        with col_t4_s:
            doc_sel = st.selectbox(
                f"Seleccione Documento ({len(docs_disp)} disponibles)",
                docs_disp,
                format_func=normalizar_titulo_display,
                key="tab4_doc_selector"
            ) if docs_disp else None

        if doc_sel:
            doc_cont = doc_store.get(doc_sel, "")
            historial = inicializar_version_inicial_si_no_existe(doc_sel, doc_cont)
            u_ver = len(historial)
            u_edit = historial[-1]["autor"] if historial else "Desconocido"
            u_time = historial[-1]["timestamp"] if historial else "N/A"
            f_carga = historial[0]["timestamp"].split()[0] if (historial and " " in historial[0]["timestamp"]) else "N/A"
            ruta_orig = obtener_ruta_original(doc_sel, doc_cont)
            tags_doc = obtener_tags_documento(doc_sel)
            tags_badges = " ".join([f'<span class="badge-info" style="font-size:0.75rem;padding:1px 6px;">[{t}]</span>' for t in tags_doc]) if tags_doc else '<span class="badge-warn" style="font-size:0.75rem;padding:1px 6px;">[Sin Categoría]</span>'

            col_meta_t3, col_zen_t3 = st.columns([3.8, 1.2], vertical_alignment="center")
            with col_meta_t3:
                st.markdown(f"""
                <div style="background-color:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2);border-radius:6px;padding:8px 14px;font-size:0.85rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <div><b>Documento:</b> <span style="color:#6366F1;font-weight:600;">{normalizar_titulo_display(doc_sel)}</span> <span style="font-family:monospace;opacity:0.65;font-size:0.8rem;">({doc_sel})</span></div>
                    <div><b>Categoría:</b> {tags_badges}</div>
                    <div><b>Versión:</b> <span class="badge-ok">v{u_ver}</span></div>
                    <div><b>Fecha Carga:</b> <span class="badge-tag">[{f_carga}]</span></div>
                    <div><b>Último Editor:</b> <span style="color:#10B981;font-weight:500;">{u_edit}</span></div>
                    <div><b>Actualizado:</b> <span style="opacity:0.75;">{u_time}</span></div>
                </div>""", unsafe_allow_html=True)
            with col_zen_t3:
                if st.button(">_ Abrir en Zen Studio", type="primary", width="stretch", key=f"btn_tab3_zen_top_{doc_sel}", help="Abre el entorno inmersivo Zen Studio a pantalla completa con índice interactivo."):
                    st.session_state["zen_studio_activo"] = True
                    st.session_state["zen_doc_sel"] = doc_sel
                    st.rerun()

            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            renderizar_lado_a_lado(doc_sel, doc_cont, ruta_orig, u_ver, u_edit, u_time, key_suffix="tab3_view")
            st.markdown("---")
            col_dla, col_dli = st.columns([1.5, 2.5])
            with col_dla:
                es_x = doc_sel.lower().endswith(('.xlsx', '.xls')) and os.path.exists(os.path.join(DOCS_DIR, doc_sel))
                if es_x:
                    with open(os.path.join(DOCS_DIR, doc_sel), "rb") as fx:
                        st.download_button(label=f"Descargar Versión Activa v{u_ver} (.xlsx)", data=fx.read(), file_name=sanitizar_nombre_descarga(doc_sel, u_ver, ".xlsx"), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key=f"dl_act_x_{doc_sel}")
                else:
                    st.download_button(label=f"Descargar Versión Activa v{u_ver} (.md)", data=doc_cont.encode("utf-8"), file_name=sanitizar_nombre_descarga(doc_sel, u_ver, ".md"), mime="text/markdown", width="stretch", key=f"dl_act_m_{doc_sel}")
            with col_dli:
                st.caption(f"Descarga la versión activa actual (**v{u_ver}**).")

            with st.expander(f"Historial de Revisiones y Control de Cambios ({u_ver} versiones)", expanded=False):
                df_h = pd.DataFrame(historial)
                cols_h = [c for c in ["version", "timestamp", "autor", "comentario", "caracteres", "sha256"] if c in df_h.columns]
                df_h = df_h[cols_h].rename(columns={"version": "Versión", "timestamp": "Fecha y Hora", "autor": "Editor / Responsable", "comentario": "Motivo del Cambio", "caracteres": "Caracteres", "sha256": "Firma SHA-256"})
                st.dataframe(df_h, width="stretch", hide_index=True)

                st.markdown("---")
                opts_ver = {f"v{i['version']} - {i['timestamp']} ({i['autor']}): {i['comentario']}": i for i in reversed(historial)}
                v_sel_lbl = st.selectbox("Seleccione versión para inspeccionar / descargar:", list(opts_ver.keys()), key=f"select_hist_ver_{doc_sel}")
                it_sel = opts_ver[v_sel_lbl]
                c_snap = obtener_contenido_version(doc_sel, it_sel["archivo_snapshot"])
                ex_snap = it_sel.get("archivo_excel_snapshot")

                col_hv1, col_hv2 = st.columns(2)
                with col_hv1:
                    if ex_snap:
                        b_xl = obtener_bytes_snapshot(doc_sel, ex_snap)
                        if b_xl:
                            st.download_button(f"Descargar v{it_sel['version']} (.xlsx)", b_xl, sanitizar_nombre_descarga(doc_sel, it_sel['version'], ".xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key=f"btn_dl_x_h_{doc_sel}_{it_sel['version']}")
                    else:
                        st.download_button(f"Descargar v{it_sel['version']} (.md)", c_snap.encode("utf-8"), sanitizar_nombre_descarga(doc_sel, it_sel['version'], ".md"), "text/markdown", width="stretch", key=f"btn_dl_m_h_{doc_sel}_{it_sel['version']}")
                with col_hv2:
                    st.caption(f"Snapshot generado el **{it_sel['timestamp']}** por **{it_sel['autor']}**.")

                if it_sel["version"] != u_ver:
                    st.markdown("---")
                    st.markdown(f"##### Revertir Documento a la Versión v{it_sel['version']} (Rollback)")
                    col_ra, col_rm = st.columns([1, 2])
                    with col_ra:
                        aut_rb = st.text_input("Técnico que ejecuta Rollback (*)", key=f"author_rb_{doc_sel}_{it_sel['version']}")
                    with col_rm:
                        mot_rb = st.text_input("Justificación del Rollback (*)", key=f"motive_rb_{doc_sel}_{it_sel['version']}")
                    if st.button(f"Confirmar Rollback a Versión v{it_sel['version']}", type="primary", key=f"btn_rb_{doc_sel}_{it_sel['version']}"):
                        if not aut_rb.strip() or not mot_rb.strip():
                            st.error("Error de Auditoría: Editor y Justificación son obligatorios.")
                        else:
                            if ex_snap and os.path.exists(os.path.join(HISTORY_DIR, doc_sel, ex_snap)):
                                shutil.copy2(os.path.join(HISTORY_DIR, doc_sel, ex_snap), os.path.join(DOCS_DIR, doc_sel))
                                nuevo_m = procesar_excel_limpio(os.path.join(DOCS_DIR, doc_sel))
                            else:
                                nuevo_m = c_snap
                            nv = guardar_nueva_version(doc_sel, nuevo_m, aut_rb.strip(), f"[Rollback a v{it_sel['version']}] {mot_rb.strip()}", doc_store)
                            st.toast(f"Restaurado a v{it_sel['version']} (v{nv})")
                            st.rerun()

                if len(historial) >= 2:
                    with st.expander("Comparar diferencias de texto entre dos versiones (Diff)", expanded=False):
                        c_d1, c_d2 = st.columns(2)
                        n_vers = [f"v{i['version']} - {i['timestamp']} ({i['autor']})" for i in historial]
                        map_v = {n_vers[idx]: historial[idx] for idx in range(len(historial))}
                        with c_d1:
                            v_base = st.selectbox("Versión Base:", n_vers, index=0, key=f"diff_base_{doc_sel}")
                        with c_d2:
                            v_comp = st.selectbox("Versión Comparada:", n_vers, index=len(n_vers)-1, key=f"diff_comp_{doc_sel}")
                        st.code(generar_diff_texto(obtener_contenido_version(doc_sel, map_v[v_base]["archivo_snapshot"]), obtener_contenido_version(doc_sel, map_v[v_comp]["archivo_snapshot"]), v_base, v_comp), language="diff")

                with st.expander("Registro Central de Auditoría Global (Audit Log)", expanded=False):
                    evs = obtener_todos_los_eventos_auditoria()
                    if evs:
                        df_aud = pd.DataFrame(evs)
                        df_aud_disp = df_aud[df_aud["documento"] == doc_sel] if st.checkbox("Filtrar solo este documento", value=True, key=f"chk_aud_{doc_sel}") else df_aud
                        st.dataframe(df_aud_disp.rename(columns={"timestamp": "Timestamp", "documento": "Documento", "accion": "Acción", "version_anterior": "Versión Ant.", "version_nueva": "Versión Nueva", "editor_responsable": "Editor", "motivo_justificacion": "Motivo"}), width="stretch", hide_index=True)

    # -------------------------------------------------------------
    # SUBPESTAÑA 2: EDITAR DOCUMENTO ACTIVO
    # -------------------------------------------------------------
    with subtab_editor:
        doc_act_edit = st.session_state.get("tab4_doc_selector") or (docs_disp[0] if docs_disp else None)
        if not doc_act_edit:
            st.info("Seleccione un documento en la pestaña 'Visor y Explorador Documental' para editar.")
        else:
            doc_cont_e = doc_store.get(doc_act_edit, "")
            historial_e = inicializar_version_inicial_si_no_existe(doc_act_edit, doc_cont_e)
            u_ver_e = len(historial_e)

            st.markdown(f"""
            <div style="background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.2);border-radius:6px;padding:8px 14px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
                <div><b>Documento Activo:</b> <span style="color:#6366F1;font-weight:600;">{normalizar_titulo_display(doc_act_edit)}</span> <span style="font-family:monospace;opacity:0.65;font-size:0.8rem;">({doc_act_edit})</span></div>
                <div><span class="badge-ok">Versión Activa: v{u_ver_e}</span></div>
            </div>
            """, unsafe_allow_html=True)

            es_x = doc_act_edit.lower().endswith(('.xlsx', '.xls')) and os.path.exists(os.path.join(DOCS_DIR, doc_act_edit))
            if es_x:
                p_xl = os.path.join(DOCS_DIR, doc_act_edit)
                mt_xl = os.path.getmtime(p_xl) if os.path.exists(p_xl) else 0.0
                sheets_e = obtener_nombres_hojas_excel(p_xl, mt_xl)
                col_es1, col_es2 = st.columns([1.5, 2.5])
                with col_es1:
                    hoja_e = st.selectbox("Seleccionar Hoja:", sheets_e or ["Hoja1"], key=f"edit_sheet_sel_{doc_act_edit}")
                with col_es2:
                    col_ae1, col_ae2 = st.columns(2)
                    with col_ae1:
                        aut_e = st.text_input("Editor (*)", placeholder="Juan Pérez", key=f"author_input_grid_{doc_act_edit}")
                    with col_ae2:
                        mot_e = st.text_input("Motivo (*)", placeholder="Actualización de IP", key=f"motive_input_grid_{doc_act_edit}")

                tags_actuales_xl = obtener_tags_documento(doc_act_edit)
                cats_disp_xl = obtener_categorias_disponibles()
                col_tx1, col_tx2 = st.columns(2)
                with col_tx1:
                    tags_xl_sel = st.multiselect("Categorías Asignadas:", options=sorted(list(set(cats_disp_xl + tags_actuales_xl))), default=tags_actuales_xl, key=f"ms_tags_edit_xl_{doc_act_edit}")
                with col_tx2:
                    nueva_cat_xl = st.text_input("Agregar Nueva Categoría:", placeholder="ej: CMDB, Inventario...", key=f"input_new_cat_edit_xl_{doc_act_edit}")

                df_e = cargar_hoja_excel_dataframe(p_xl, hoja_e, mt_xl)
                df_mod = st.data_editor(df_e, width="stretch", num_rows="dynamic", height=450, key=f"grid_editor_{doc_act_edit}_{hoja_e}")
                if st.button(f"Guardar y Publicar Versión v{u_ver_e + 1}", type="primary", key=f"btn_save_grid_{doc_act_edit}"):
                    if not aut_e or not aut_e.strip() or not mot_e or not mot_e.strip():
                        st.error("Error de Auditoría: Editor y Motivo son obligatorios.")
                    else:
                        nv = guardar_nueva_version_excel(doc_act_edit, hoja_e, df_mod, aut_e.strip(), mot_e.strip(), doc_store)
                        tags_finales_xl = list(tags_xl_sel)
                        if nueva_cat_xl.strip():
                            tags_finales_xl.append(nueva_cat_xl.strip())
                        if tags_finales_xl:
                            asignar_tags_documento(doc_act_edit, tags_finales_xl, autor=aut_e.strip())
                            limpiar_cache_consultas()
                        st.toast(f"Versión v{nv} guardada exitosamente")
                        st.rerun()
            else:
                col_e1, col_e2 = st.columns([1, 2])
                with col_e1:
                    aut_e = st.text_input("Editor (*)", placeholder="Juan Pérez", key=f"author_input_{doc_act_edit}")
                with col_e2:
                    mot_e = st.text_input("Motivo (*)", placeholder="Actualización técnica", key=f"motive_input_{doc_act_edit}")

                tags_actuales_doc = obtener_tags_documento(doc_act_edit)
                cats_disp_e = obtener_categorias_disponibles()
                col_te1, col_te2 = st.columns(2)
                with col_te1:
                    tags_e_sel = st.multiselect("Categorías Asignadas:", options=sorted(list(set(cats_disp_e + tags_actuales_doc))), default=tags_actuales_doc, key=f"ms_tags_edit_{doc_act_edit}")
                with col_te2:
                    nueva_cat_e = st.text_input("Agregar Nueva Categoría:", placeholder="ej: Contingencias, Networking...", key=f"input_new_cat_edit_{doc_act_edit}")

                val_txt = doc_cont_e[:100_000] if len(doc_cont_e) > 100_000 else doc_cont_e
                txt_edit = st.text_area("Contenido (Markdown)", value=val_txt, height=450, key=f"textarea_edit_{doc_act_edit}")
                if st.button(f"Guardar y Publicar Versión v{u_ver_e + 1}", type="primary", key=f"btn_save_{doc_act_edit}"):
                    if not aut_e or not aut_e.strip() or not mot_e or not mot_e.strip():
                        st.error("Error de Auditoría: Editor y Motivo son obligatorios.")
                    else:
                        nv = guardar_nueva_version(doc_act_edit, txt_edit, aut_e.strip(), mot_e.strip(), doc_store)
                        tags_finales = list(tags_e_sel)
                        if nueva_cat_e.strip():
                            tags_finales.append(nueva_cat_e.strip())
                        if tags_finales:
                            asignar_tags_documento(doc_act_edit, tags_finales, autor=aut_e.strip())
                            limpiar_cache_consultas()
                        if nv == u_ver_e:
                            st.toast(f"[OK] Categorías actualizadas para {doc_act_edit}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.toast(f"[OK] Versión v{nv} publicada con éxito")
                            st.rerun()

    # -------------------------------------------------------------
    # SUBPESTAÑA 3: CLASIFICACIÓN EN LOTE
    # -------------------------------------------------------------
    with subtab_lote:
        st.markdown("#### Clasificación de Documentos en Lote")
        st.caption("Asignación masiva de categorías y aplicación de sugerencias heurísticas a la base documental.")

        if docs_pendientes:
            st.warning(f"[PENDIENTE] Se detectaron {len(docs_pendientes)} documentos sin categoría asignada en el repositorio.")
        else:
            st.success(f"[OK] Todos los documentos ({len(todos_docs)}) cuentan con al menos una categoría asignada.")

        col_bl_f, col_bl_s = st.columns([2.2, 1.8], vertical_alignment="bottom")
        with col_bl_f:
            filtro_lote = st.radio(
                "Alcance de clasificación:",
                options=[f"Solo pendientes ({len(docs_pendientes)})", f"Todos los documentos ({len(todos_docs)})"],
                index=0 if docs_pendientes else 1,
                horizontal=True,
                key="radio_batch_scope"
            )
        with col_bl_s:
            col_bs1, col_bs2 = st.columns(2)
            with col_bs1:
                if st.button("[Marcar Todos]", width="stretch", key="btn_batch_sel_all"):
                    st.session_state["batch_select_default"] = True
                    st.session_state["batch_tagger_ver"] = st.session_state.get("batch_tagger_ver", 0) + 1
                    st.rerun()
            with col_bs2:
                if st.button("[Deseleccionar Todos]", width="stretch", key="btn_batch_desel_all"):
                    st.session_state["batch_select_default"] = False
                    st.session_state["batch_tagger_ver"] = st.session_state.get("batch_tagger_ver", 0) + 1
                    st.rerun()

        docs_a_gestionar = docs_pendientes if filtro_lote.startswith("Solo pendientes") else todos_docs

        if docs_a_gestionar:
            default_sel = st.session_state.get("batch_select_default", False)
            filas_lote = []
            for d in docs_a_gestionar:
                tags_actuales = obtener_tags_documento(d)
                sug = sugerir_categoria_documento(d, doc_store.get(d, "")[:1500])
                filas_lote.append({
                    "Seleccionar": bool(default_sel),
                    "Documento": normalizar_titulo_display(d),
                    "Sugerencia Heurística": sug,
                    "Categoría Actual": ", ".join(tags_actuales) if tags_actuales else "[Sin Categoría]",
                    "Archivo": d
                })
            df_lote_base = pd.DataFrame(filas_lote)

            tagger_ver = st.session_state.get("batch_tagger_ver", 0)
            df_lote_edit = st.data_editor(
                df_lote_base,
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False),
                    "Documento": st.column_config.TextColumn("Documento", disabled=True),
                    "Sugerencia Heurística": st.column_config.TextColumn("Sugerencia Heurística", disabled=True),
                    "Categoría Actual": st.column_config.TextColumn("Categoría Actual", disabled=True),
                    "Archivo": st.column_config.TextColumn("Archivo", disabled=True),
                },
                hide_index=True,
                height=320,
                width="stretch",
                key=f"editor_batch_tagger_{tagger_ver}_{filtro_lote}"
            )

            col_ba1, col_ba2, col_ba3 = st.columns([2.0, 1.5, 1.5], vertical_alignment="bottom")
            with col_ba1:
                opts_dest = ["[SUGERENCIA] Usar categoría sugerida de cada archivo"]
                if cats_disp_t3:
                    opts_dest.extend(cats_disp_t3)
                opts_dest.append("[NUEVA] Crear una nueva categoría...")
                cat_dest_sel = st.selectbox("Categoría Destino para seleccionados:", opts_dest, key="batch_cat_dest_sel")

            with col_ba2:
                nueva_cat_batch = ""
                if cat_dest_sel.startswith("[NUEVA]"):
                    nueva_cat_batch = st.text_input("Nombre de nueva categoría (*):", placeholder="ej: Seguridad Perimetral", key="batch_new_cat_input")
                else:
                    st.caption("Los documentos seleccionados recibirán la categoría seleccionada.")

            with col_ba3:
                cant_marcados = len(df_lote_edit[df_lote_edit["Seleccionar"] == True]) if "Seleccionar" in df_lote_edit.columns else 0
                btn_label = f"[APLICAR] Clasificar Seleccionados ({cant_marcados})" if cant_marcados > 0 else "[APLICAR] Clasificar Seleccionados"
                if st.button(btn_label, type="primary", width="stretch", key="btn_apply_batch_tags"):
                    df_sel = df_lote_edit[df_lote_edit["Seleccionar"] == True]
                    if df_sel.empty:
                        st.warning("[ALERTA] Debe marcar al menos un documento en la columna 'Seleccionar'.")
                    else:
                        doc_tags_map = {}
                        if cat_dest_sel.startswith("[SUGERENCIA]"):
                            for _, row in df_sel.iterrows():
                                doc_tags_map[row["Archivo"]] = [row["Sugerencia Heurística"]]
                        elif cat_dest_sel.startswith("[NUEVA]"):
                            if not nueva_cat_batch.strip():
                                st.error("[ERROR] Debe indicar el nombre de la nueva categoría.")
                                st.stop()
                            for _, row in df_sel.iterrows():
                                doc_tags_map[row["Archivo"]] = [nueva_cat_batch.strip()]
                        else:
                            for _, row in df_sel.iterrows():
                                doc_tags_map[row["Archivo"]] = [cat_dest_sel]

                        if doc_tags_map:
                            n_act = asignar_tags_en_lote(doc_tags_map, autor="Operaciones")
                            limpiar_cache_consultas()
                            limpiar_cache_documentos()
                            st.session_state["batch_select_default"] = False
                            st.toast(f"[OK] Se categorizaron {n_act} documentos exitosamente.")
                            st.success(f"[OK] Clasificación completada: {n_act} documentos actualizados.")
                            time.sleep(0.8)
                            st.rerun()
        else:
            st.info("[INFO] No hay documentos en el alcance seleccionado.")

"""
Módulo desacoplado de renderizado para Consultas y Búsqueda.
Provee búsqueda textual ultrarrápida en memoria RAM (< 2 ms) sobre DuckDB y documentos técnicos,
además del Asistente Técnico con inyección contextual RAG (Gemini).
"""
import time
import html
import pandas as pd
import streamlit as st

from core.motor import (
    buscar_servidores_duckdb,
    buscar_en_documentos,
    extraer_fragmento_relevante,
    resaltar_terminos_en_html,
    generar_respuesta_asistente,
)


def renderizar_modulo_consultas(doc_store: dict):
    """Renderiza el módulo de búsqueda y asistente de IA."""
    subtab_duckdb, subtab_asistente = st.tabs([
        "Búsqueda Textual (DuckDB & Docs)",
        "Asistente Técnico (Gemini RAG)"
    ])

    # 1. Búsqueda Textual en CMDB y Documentos
    with subtab_duckdb:
        st.markdown("""
        <div style="background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.22);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.83rem;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <span class="badge-info" style="font-size:0.68rem;padding:2px 6px;">[MOTOR DUCKDB]</span>
                <b style="color:#6366F1;font-size:0.9rem;">Búsqueda Textual Instantánea en RAM (DuckDB &amp; Documentación)</b>
            </div>
            <div style="opacity:0.9;line-height:1.45;margin-bottom:6px;">
                <b>¿Qué hace?</b> Localización determinística de alta velocidad (&lt; 2 ms) para coincidencias exactas o parciales de IPs, hostnames, números de serie en la CMDB y fragmentos en la documentación técnica.
            </div>
            <div style="opacity:0.82;line-height:1.4;font-size:0.8rem;">
                <b>¿Cómo se usa?</b> Ingrese una IP (ej: <code>10.24.0.125</code>), servidor (ej: <code>BALANCER001</code>) o término técnico y presione <code>Buscar</code>. Si requiere correlación asistida por IA sobre los resultados, utilice el botón <code>&gt;_ Analizar con Asistente</code>.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form(key="form_duckdb_search", clear_on_submit=False):
            col_din, col_dbtn = st.columns([5, 1])
            with col_din:
                query_duckdb_in = st.text_input(
                    "Término:",
                    value=st.session_state.get("duckdb_active_term", ""),
                    placeholder="IP (10.24.0.125), servidor (BALANCER001), serie (SN-8842-A) o palabra clave...",
                    label_visibility="collapsed"
                )
            with col_dbtn:
                sub_duckdb = st.form_submit_button("Buscar", type="primary", width="stretch")

        active_duck_term = query_duckdb_in.strip() if sub_duckdb and query_duckdb_in.strip() else st.session_state.get("duckdb_active_term", "")
        st.session_state["duckdb_active_term"] = active_duck_term

        if not active_duck_term:
            st.markdown("""
            <div class="empty-state-container">
                <div class="empty-state-console-icon">&gt;_ Buscador :1</div>
                <div class="empty-state-title">Motor de Búsqueda Textual en RAM</div>
                <div class="empty-state-subtitle">Búsqueda ultrarrápida indexada directamente sobre los documentos técnicos locales.</div>
            </div>""", unsafe_allow_html=True)
        else:
            t0_d = time.perf_counter()
            df_srv_found = buscar_servidores_duckdb(active_duck_term)
            doc_matches_found = buscar_en_documentos(active_duck_term, doc_store)
            t_ms = (time.perf_counter() - t0_d) * 1000

            st.markdown(f"""
            <div style="background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.2);border-radius:6px;padding:8px 14px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div><b>Término:</b> <code>{active_duck_term}</code></div>
                <div><b>Servidores CMDB:</b> <span class="badge-ok">{len(df_srv_found)}</span></div>
                <div><b>Documentos:</b> <span class="badge-info">{len(doc_matches_found)}</span></div>
                <div><b>Tiempo:</b> <span class="badge-tag">{t_ms:.2f} ms [RAM]</span></div>
            </div>""", unsafe_allow_html=True)

            st.markdown(f"##### Servidores Coincidentes en CMDB ({len(df_srv_found)})")
            if not df_srv_found.empty:
                cols_s = [c for c in ["servidor_id", "ip", "numero_serie", "vcloud_vm", "nivel_arquitectura", "componente", "estado", "nagios_check"] if c in df_srv_found.columns]
                st.dataframe(
                    df_srv_found[cols_s].rename(columns={
                        "servidor_id": "Servidor",
                        "ip": "IP",
                        "numero_serie": "N° Serie",
                        "vcloud_vm": "VM vCloud",
                        "nivel_arquitectura": "Capa",
                        "componente": "Componente",
                        "estado": "Estado",
                        "nagios_check": "Nagios / Chequeo"
                    }),
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info(f"No se registraron servidores para '{active_duck_term}' en la CMDB.")

            st.markdown(f"##### Documentación Técnica Coincidente ({len(doc_matches_found)})")
            if doc_matches_found:
                for doc_n, cont, sc in doc_matches_found[:5]:
                    snip = resaltar_terminos_en_html(html.escape(extraer_fragmento_relevante(cont, active_duck_term, max_chars=350)), active_duck_term)
                    st.markdown(f"""
                    <div class="search-result-card" style="margin-bottom:10px;padding:12px 14px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><div><b>Documento:</b> <code>{doc_n}</code></div><span class="badge-info">{sc} pts</span></div>
                        <div style="font-size:0.83rem;line-height:1.5;opacity:0.9;background:rgba(128,128,128,0.05);padding:8px 10px;border-radius:4px;border-left:3px solid #6366F1;">{snip}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info(f"No se encontraron coincidencias en la documentación para '{active_duck_term}'.")

            st.markdown("---")
            col_bt, col_bb = st.columns([3.5, 1.5], vertical_alignment="center")
            with col_bt:
                st.caption("¿Deseas un análisis técnico y diagnóstico asistido con IA?")
            with col_bb:
                if st.button(">_ Analizar con Asistente", width="stretch", type="primary", key="btn_bridge_to_asistente"):
                    with st.spinner("Generando análisis..."):
                        resp_c = generar_respuesta_asistente(active_duck_term, doc_store)
                        st.session_state.historial_busquedas.insert(0, {
                            "query": active_duck_term,
                            "response": resp_c,
                            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                        })
                    st.rerun()

    # 2. Asistente Técnico Especializado RAG
    with subtab_asistente:
        st.markdown("""
        <div style="background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.22);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.83rem;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <span class="badge-ok" style="font-size:0.68rem;padding:2px 6px;">[IA / VECTORIAL]</span>
                <b style="color:#6366F1;font-size:0.9rem;">Asistente Técnico con Recuperación Contextual y Vectorial (Gemini RAG)</b>
            </div>
            <div style="opacity:0.9;line-height:1.45;margin-bottom:6px;">
                <b>¿Qué hace?</b> Motor de inteligencia artificial que recupera contextualmente la CMDB y los documentos técnicos mediante análisis semántico/vectorial para resolver dudas operativas, diagnosticar incidencias y correlacionar dependencias de servicios.
            </div>
            <div style="opacity:0.82;line-height:1.4;font-size:0.8rem;">
                <b>¿Cómo se usa?</b> Escriba su consulta técnica en lenguaje natural (ej: <i>"Explícame el procedimiento de failover de Redis y sus dependencias"</i>) y presione <code>Consultar Asistente</code> para generar una respuesta fundamentada en la evidencia.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form(key="top_asistente_form", clear_on_submit=True):
            col_cin, col_cbtn = st.columns([5, 1])
            with col_cin:
                query_asistente_in = st.text_input(
                    "Consulta:",
                    placeholder="Ej: Explícame el procedimiento de failover de Redis y sus dependencias...",
                    label_visibility="collapsed"
                )
            with col_cbtn:
                sub_asistente = st.form_submit_button("Consultar Asistente", type="primary", width="stretch")

        query_c_exec = query_asistente_in.strip() if sub_asistente and query_asistente_in.strip() else None
        if query_c_exec:
            with st.spinner("Analizando infraestructura..."):
                resp = generar_respuesta_asistente(query_c_exec, doc_store)
                st.session_state.historial_busquedas.insert(0, {
                    "query": query_c_exec,
                    "response": resp,
                    "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                })
            st.rerun()

        st.markdown("---")
        if not st.session_state.historial_busquedas:
            st.markdown("""
            <div class="empty-state-container">
                <div class="empty-state-console-icon">&gt;_ infra::rag_engine</div>
                <div class="empty-state-title">Asistente de Infraestructura y Operaciones</div>
                <div class="empty-state-subtitle">Realiza preguntas analíticas y operativas fundamentadas estrictamente en la evidencia técnica.</div>
            </div>""", unsafe_allow_html=True)
        else:
            col_rt, col_rb = st.columns([4, 1])
            with col_rt:
                st.markdown(f"<div style='font-size:0.95rem;font-weight:600;'>Historial de Consultas ({len(st.session_state.historial_busquedas)}):</div>", unsafe_allow_html=True)
            with col_rb:
                if st.button(">_ Limpiar Chat", width="stretch", key="btn_clear_search_history"):
                    st.session_state.historial_busquedas = []
                    st.session_state.messages = []
                    st.toast("[INFO] Historial reiniciado")
                    st.rerun()

            for idx, it in enumerate(st.session_state.historial_busquedas):
                badge_o = '<span class="badge-ok">[ÚLTIMA CONSULTA]</span>' if idx == 0 else f'<span class="badge-tag">[{it["timestamp"]}]</span>'
                st.markdown(f'<div style="margin-top:12px;margin-bottom:4px;font-size:0.9rem;">{badge_o} <span style="font-weight:600;margin-left:6px;">Consulta:</span> <code>{it["query"]}</code></div>', unsafe_allow_html=True)
                st.markdown(it["response"], unsafe_allow_html=True)

"""
Módulo desacoplado de renderizado para el Inventario CMDB e Historial de Mantenimientos.
Ofrece consultas SQL sobre DuckDB en memoria, filtrado multidimensional y métricas clave (KPIs).
"""
import os
import datetime
import duckdb
import pandas as pd
import streamlit as st

from core.configuracion import CSV_PATH
from core.motor import ejecutar_consulta_sql


def _render_kpi_grid(total_reg: int, cnt_op: int, cnt_rev: int, cnt_crit: int, tec_activo: str, pct_op: float, pct_crit: float):
    """Renderiza la cuadrícula de métricas operativas clave (KPIs) del parque de servidores."""
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card"><span class="kpi-label">Total Servidores</span><span class="kpi-value-primary">{total_reg}</span><span class="kpi-caption">Registros CMDB</span></div>
        <div class="kpi-card"><span class="kpi-label">Operativos</span><span class="kpi-value-ok">{cnt_op}</span><span class="kpi-caption">{pct_op}% del parque</span></div>
        <div class="kpi-card"><span class="kpi-label">En Revisión</span><span class="kpi-value-warn">{cnt_rev}</span><span class="kpi-caption">Atención requerida</span></div>
        <div class="kpi-card"><span class="kpi-label">Críticos</span><span class="kpi-value-crit">{cnt_crit}</span><span class="kpi-caption">{pct_crit}% del parque</span></div>
        <div class="kpi-card"><span class="kpi-label">Técnico Principal</span><span class="kpi-value-neutral" style="font-size:1.05rem;padding-top:4px;">{tec_activo}</span><span class="kpi-caption">Mayor asignación</span></div>
    </div>
    """, unsafe_allow_html=True)


def renderizar_modulo_mantenimientos(df_mantenimientos_cache: pd.DataFrame):
    """Renderiza el módulo analítico y de mantenimiento de infraestructura."""
    st.subheader("Motor SQL DuckDB - Historial de Mantenimientos e Inventario")
    st.caption("Consultas analíticas estructuradas con filtrado multidimensional por fecha, nivel, estado y técnico.")

    min_date, max_date = datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)
    if not df_mantenimientos_cache.empty and 'fecha' in df_mantenimientos_cache.columns:
        try:
            fechas_dt = pd.to_datetime(df_mantenimientos_cache['fecha'], errors='coerce')
            if pd.notnull(fechas_dt.min()):
                min_date = fechas_dt.min().date()
            if pd.notnull(fechas_dt.max()):
                max_date = fechas_dt.max().date()
        except Exception:
            pass

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.1, 1.2, 1.5], gap="small")
    with col_f1:
        filtro_nivel = st.selectbox("Nivel de Arquitectura", ["Todos", "L1 - Hardware", "L2 - Virtualización", "L3 - Middleware", "L4 - Aplicación"])
    with col_f2:
        filtro_estado = st.selectbox("Estado Operativo", ["Todos", "Operativo", "En Revision", "Critico"])
    with col_f3:
        filtro_tec = st.text_input("Filtrar por Técnico", placeholder="Nombre del técnico...")
    with col_f4:
        rango_fechas = st.date_input("Rango de Fechas:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="filtro_rango_fechas_mantenimientos")

    if not os.path.exists(CSV_PATH):
        st.warning("[WARN] El archivo data/mantenimientos.csv no existe en el entorno actual.")
    else:
        conds = ["1=1"]
        if filtro_nivel != "Todos":
            conds.append(f"nivel_arquitectura = '{filtro_nivel}'")
        if filtro_estado != "Todos":
            conds.append(f"estado = '{filtro_estado}'")
        if filtro_tec.strip():
            conds.append(f"LOWER(tecnico) LIKE LOWER('%{filtro_tec.strip()}%')")
        if isinstance(rango_fechas, (tuple, list)) and len(rango_fechas) == 2:
            conds.append(f"fecha >= '{rango_fechas[0].strftime('%Y-%m-%d')}' AND fecha <= '{rango_fechas[1].strftime('%Y-%m-%d')}'")
        elif isinstance(rango_fechas, datetime.date):
            conds.append(f"fecha = '{rango_fechas.strftime('%Y-%m-%d')}'")

        try:
            df_filtrado = duckdb.sql(f"SELECT * FROM read_csv_auto('{CSV_PATH}') WHERE {' AND '.join(conds)} ORDER BY fecha DESC").df()
        except Exception as e_sql:
            st.error(f"[CRIT] Error al ejecutar consulta SQL: {e_sql}")
            df_filtrado = pd.DataFrame()

        total_reg = len(df_filtrado)
        cnt_op = int((df_filtrado['estado'] == 'Operativo').sum()) if 'estado' in df_filtrado.columns else 0
        cnt_rev = int((df_filtrado['estado'] == 'En Revision').sum()) if 'estado' in df_filtrado.columns else 0
        cnt_crit = int((df_filtrado['estado'] == 'Critico').sum()) if 'estado' in df_filtrado.columns else 0
        tec_activo = df_filtrado['tecnico'].value_counts().idxmax() if ('tecnico' in df_filtrado.columns and total_reg > 0) else "N/D"
        pct_op = round(cnt_op / total_reg * 100, 1) if total_reg > 0 else 0
        pct_crit = round(cnt_crit / total_reg * 100, 1) if total_reg > 0 else 0

        _render_kpi_grid(total_reg, cnt_op, cnt_rev, cnt_crit, tec_activo, pct_op, pct_crit)
        st.markdown(f"<div style='font-size:0.85rem;margin-bottom:8px;font-weight:500;'><span class='badge-info'>{total_reg} registros coincidentes</span></div>", unsafe_allow_html=True)
        st.dataframe(df_filtrado, width="stretch", hide_index=True)

    with st.expander("Ejecutar Consulta SQL Personalizada"):
        custom_sql = st.text_area("Sentencia SQL", value=f"SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM read_csv_auto('{CSV_PATH}') GROUP BY nivel_arquitectura")
        if st.button("Ejecutar") and os.path.exists(CSV_PATH):
            st.dataframe(ejecutar_consulta_sql(custom_sql), width="stretch")

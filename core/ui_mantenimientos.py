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


def renderizar_modulo_mantenimientos(df_mantenimientos_cache: pd.DataFrame):
    """Renderiza el módulo analítico y de mantenimiento de infraestructura."""
    st.subheader("Historial de Mantenimientos e Inventario")
    st.caption("Filtra por fecha, nivel, estado y técnico, o escribe tu propia consulta SQL.")

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
        filtro_nivel = st.selectbox("Nivel", ["Todos", "L1 - Hardware", "L2 - Virtualización", "L3 - Middleware", "L4 - Aplicación"])
    with col_f2:
        filtro_estado = st.selectbox("Estado", ["Todos", "Operativo", "En Revision", "Critico"])
    with col_f3:
        filtro_tec = st.text_input("Técnico")
    with col_f4:
        rango_fechas = st.date_input("Rango de Fechas:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="filtro_rango_fechas_mantenimientos")

    if not os.path.exists(CSV_PATH):
        st.warning("No se encontró data/mantenimientos.csv.")
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
            st.error(f"Error al ejecutar la consulta: {e_sql}")
            df_filtrado = pd.DataFrame()

        total_reg = len(df_filtrado)
        st.markdown(f"<div style='font-size:0.85rem;margin-bottom:8px;font-weight:500;'><span class='badge-info'>{total_reg} registros encontrados</span></div>", unsafe_allow_html=True)
        st.dataframe(df_filtrado, width="stretch", hide_index=True)

    with st.expander("Escribir Consulta SQL"):
        custom_sql = st.text_area("Consulta SQL", value=f"SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM read_csv_auto('{CSV_PATH}') GROUP BY nivel_arquitectura")
        if st.button("Ejecutar") and os.path.exists(CSV_PATH):
            st.dataframe(ejecutar_consulta_sql(custom_sql), width="stretch")

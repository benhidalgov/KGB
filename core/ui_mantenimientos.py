"""
Módulo desacoplado de renderizado para el Inventario CMDB e Historial de Mantenimientos.
Ofrece consultas SQL sobre DuckDB en memoria, filtrado multidimensional y métricas clave (KPIs).
"""
import os
import datetime
import pandas as pd
import streamlit as st

from core.configuracion import CSV_PATH, ES_PRODUCCION
from core.motor import ejecutar_consulta_sql, _es_sql_solo_lectura
from core.auth import tiene_permiso


def renderizar_modulo_mantenimientos(df_mantenimientos_cache: pd.DataFrame):
    """Renderiza el módulo analítico y de mantenimiento de infraestructura."""
    st.subheader("Historial de Mantenimientos e Inventario")
    st.caption("Filtra por fecha, nivel, estado y técnico" + ("" if ES_PRODUCCION else ", o escribe tu propia consulta SQL de solo lectura."))

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

    df_filtrado = df_mantenimientos_cache
    if not df_filtrado.empty:
        if filtro_nivel != "Todos" and "nivel_arquitectura" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["nivel_arquitectura"] == filtro_nivel]
        if filtro_estado != "Todos" and "estado" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]
        if filtro_tec.strip() and "tecnico" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado["tecnico"].astype(str).str.contains(filtro_tec.strip(), case=False, na=False, regex=False)
            ]
        # st.date_input en modo rango devuelve (d,) mientras queda un solo extremo.
        if isinstance(rango_fechas, (tuple, list)) and len(rango_fechas) == 1:
            rango_fechas = (rango_fechas[0], rango_fechas[0])
        if "fecha" in df_filtrado.columns and isinstance(rango_fechas, (tuple, list)) and len(rango_fechas) == 2:
            fechas_serie = pd.to_datetime(df_filtrado["fecha"], errors="coerce")
            inicio = pd.Timestamp(rango_fechas[0])
            fin = pd.Timestamp(rango_fechas[1])
            df_filtrado = df_filtrado[(fechas_serie >= inicio) & (fechas_serie <= fin)]

    if df_mantenimientos_cache.empty and not os.path.exists(CSV_PATH):
        st.warning("No se encontró data/mantenimientos.csv.")

    total_reg = len(df_filtrado)
    st.markdown(f"<div style='font-size:0.85rem;margin-bottom:8px;font-weight:500;'><span class='badge-info'>{total_reg} registros encontrados</span></div>", unsafe_allow_html=True)
    st.dataframe(df_filtrado, width="stretch", hide_index=True)

    if not ES_PRODUCCION and tiene_permiso("puede_ejecutar_sql"):
        with st.expander("Escribir Consulta SQL (solo lectura)"):
            custom_sql = st.text_area(
                "Consulta SQL",
                value="SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM mantenimientos GROUP BY nivel_arquitectura",
            )
            if st.button("Ejecutar"):
                st.dataframe(ejecutar_consulta_sql(custom_sql), width="stretch")

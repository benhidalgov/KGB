from excel_cleaner import procesar_excel_limpio
import glob
import os

import duckdb
import pandas as pd
import streamlit as st

# Configuracion inicial de Streamlit
st.set_page_config(
    page_title="Copilot de Infraestructura y AIOps",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos visuales profesionales y completamente responsivos
st.markdown("""
<style>
    /* Tipografía y Títulos Responsivos con clamp() */
    .main-title {
        font-size: clamp(1.4rem, 2.5vw, 2.2rem);
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 2px;
        line-height: 1.2;
    }
    .sub-title {
        font-size: clamp(0.85rem, 1.2vw, 1rem);
        color: #475569;
        margin-bottom: 15px;
        line-height: 1.4;
    }

    /* Badges de Estado */
    .badge-ok { background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .badge-warn { background-color: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .badge-crit { background-color: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }

    /* Tablas Responsivas con Desplazamiento Horizontal Suave */
    .stMarkdown table {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        border-collapse: collapse !important;
        margin: 12px 0 !important;
        -webkit-overflow-scrolling: touch;
        border-radius: 6px;
    }
    .stMarkdown th, .stMarkdown td {
        padding: 7px 12px !important;
        border: 1px solid #CBD5E1 !important;
        font-size: 0.85rem !important;
    }
    .stMarkdown th {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
        font-weight: 600 !important;
        position: sticky;
        top: 0;
    }
    .stMarkdown tr:nth-child(even) {
        background-color: #F8FAFC !important;
    }
    .stMarkdown tr:hover {
        background-color: #F1F5F9 !important;
        transition: background-color 0.15s ease;
    }

    /* Scrollbars Modernas y Discretas */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #F1F5F9;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb {
        background: #94A3B8;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #64748B;
    }

    /* Tarjetas y Contenedores Fluidos */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
        border-radius: 8px;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"]:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    /* Reglas Responsivas para Pantallas Medianas y Pequeñas */
    @media (max-width: 992px) {
        .main-title { font-size: 1.5rem !important; }
        .sub-title { font-size: 0.85rem !important; }
    }
    @media (max-width: 768px) {
        .main-title { font-size: 1.3rem !important; }
        .sub-title { font-size: 0.8rem !important; }
        div[data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; margin-bottom: 8px; }
    }

    /* Botones fluidos con animación */
    .stButton button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# Rutas de datos
CSV_PATH = os.path.join("data", "mantenimientos.csv")
DOCS_DIR = os.path.join("data", "docs")

# Inicializacion de estado de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "**Sistema Bisqueda de documentacion por palabras clabes.**\n\n"
                "Capacidades activas:\n"
                "- Consulta analitica de inventario y mantenimientos por numero de serie, servidor o tecnico .\n"
                "- Recuperacion de procedimientos tecnicos, contingencias y despliegues (Usando MarkItDown).\n"
                
            )
        }
    ]

if "doc_store" not in st.session_state:
    st.session_state.doc_store = {}


# Carga de documentos locales


def cargar_documentos_locales():
    if os.path.exists(DOCS_DIR):
        for doc_file in glob.glob(os.path.join(DOCS_DIR, "*.*")):
            fname = os.path.basename(doc_file)
            ext = os.path.splitext(fname)[1].lower()
            if fname not in st.session_state.doc_store:
                try:
                    if ext in (".xlsx", ".xls"):
                        st.session_state.doc_store[fname] = procesar_excel_limpio(
                            doc_file)
                    elif ext in (".md", ".txt", ".csv"):
                        with open(doc_file, "r", encoding="utf-8", errors="ignore") as f:
                            st.session_state.doc_store[fname] = f.read()
                    elif ext in (".docx", ".pdf", ".pptx"):
                        from markitdown import MarkItDown
                        md_engine = MarkItDown()
                        res = md_engine.convert(doc_file)
                        st.session_state.doc_store[fname] = res.text_content
                except Exception:
                    pass


cargar_documentos_locales()

# Funciones de consulta DuckDB


def ejecutar_consulta_sql(query_sql: str) -> pd.DataFrame:
    try:
        con = duckdb.connect(database=':memory:')
        con.execute(
            f"CREATE TABLE mantenimientos AS SELECT * FROM read_csv_auto('{CSV_PATH}')")
        df = con.execute(query_sql).df()
        con.close()
        return df
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})


def buscar_servidores_duckdb(termino: str) -> pd.DataFrame:
    termino_sanitizado = termino.strip().replace("'", "")
    query_sql = f"""
        SELECT
            servidor_id,
            numero_serie,
            ip,
            vcloud_vm,
            nivel_arquitectura,
            componente,
            fecha,
            tipo_mantenimiento,
            tecnico,
            descripcion,
            estado,
            nagios_check
        FROM read_csv_auto('{CSV_PATH}')
        WHERE LOWER(servidor_id) LIKE LOWER('%{termino_sanitizado}%')
           OR LOWER(numero_serie) LIKE LOWER('%{termino_sanitizado}%')
           OR LOWER(ip) LIKE LOWER('%{termino_sanitizado}%')
           OR LOWER(tecnico) LIKE LOWER('%{termino_sanitizado}%')
           OR LOWER(descripcion) LIKE LOWER('%{termino_sanitizado}%')
           OR LOWER(componente) LIKE LOWER('%{termino_sanitizado}%')
           OR LOWER(vcloud_vm) LIKE LOWER('%{termino_sanitizado}%')
        ORDER BY fecha DESC
    """
    try:
        return duckdb.sql(query_sql).df()
    except Exception:
        return pd.DataFrame()

# Busqueda en base documental


def buscar_en_documentos(query: str):
    resultados = []
    tokens = [t.lower() for t in query.split() if len(t) > 3]
    for doc_name, content in st.session_state.doc_store.items():
        score = sum(content.lower().count(token) for token in tokens)
        if score > 0 or any(token in doc_name.lower() for token in tokens):
            resultados.append((doc_name, content, score))
    resultados.sort(key=lambda x: x[2], reverse=True)
    return resultados

# Motor de generacion de respuestas


def generar_respuesta_asistente(prompt_usuario: str):
    df_srv = buscar_servidores_duckdb(prompt_usuario)
    doc_matches = buscar_en_documentos(prompt_usuario)

    # Modo Local Autonomo (DuckDB + Base Documental)
    if not df_srv.empty:
        total_coincidencias = len(df_srv)
        row = df_srv.iloc[0]
        estado_label = f"[{row['estado'].upper()}]"

        tabla_md = f"""
### Registro de Infraestructura Encontrado ({total_coincidencias} resultado(s))

| Atributo | Detalle |
| :--- | :--- |
| **Servidor** | {row['servidor_id']} |
| **Numero de Serie** | {row['numero_serie']} |
| **IP / VM vCloud** | {row['ip']} ({row['vcloud_vm']}) |
| **Nivel de Arquitectura** | {row['nivel_arquitectura']} |
| **Componente** | {row['componente']} |
| **Fecha de Registro** | {row['fecha']} |
| **Tipo de Intervencion** | {row['tipo_mantenimiento']} |
| **Tecnico Responsable** | {row['tecnico']} |
| **Estado Operativo** | {estado_label} |
| **Chequeo de Monitoreo** | {row['nagios_check']} |

**Descripcion Tecnica:**
{row['descripcion']}

*Origen de datos: DuckDB Engine (data/mantenimientos.csv)*
"""
        if total_coincidencias > 1:
            tabla_md += f"\n\n*Nota: Existen {total_coincidencias - 1} registro(s) adicionales. Se puede consultar el desglose completo en la seccion Analitica DuckDB.*"

        return tabla_md

    elif doc_matches:
        doc_name, content, _ = doc_matches[0]
        return f"""
### Informacion Recuperada de Documentacion: {doc_name}

{content[:1400]}...

---
*Origen de datos: Base documental indexada*
"""

    else:
        return (
            f"No se encontraron registros de inventario ni procedimientos tecnicos para el termino: **{prompt_usuario}**.\n\n"
            "Verifique la referencia por numero de serie, identificador de servidor, direccion IP o manual tecnico."
        )


# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("### Panel de Control")
    st.caption("Documentacion de Infraestructura")

    st.divider()
    st.markdown("#### Ingesta de Documentos")
    uploaded_file = st.file_uploader(
        "Cargar archivo tecnico",
        type=["pdf", "docx", "xlsx", "csv", "txt", "md"],
        help="Procesamiento e indexacion automatica en memoria."
    )

    if uploaded_file:
        save_path = os.path.join(DOCS_DIR, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        try:
            if ext in (".xlsx", ".xls"):
                st.session_state.doc_store[uploaded_file.name] = procesar_excel_limpio(
                    save_path)
                st.success(
                    f"Hoja de cálculo procesada e indexada limpiamente: {uploaded_file.name}")
            else:
                from markitdown import MarkItDown
                md_engine = MarkItDown()
                res = md_engine.convert(save_path)
                st.session_state.doc_store[uploaded_file.name] = res.text_content
                st.success(
                    f"Archivo indexado correctamente: {uploaded_file.name}")
        except Exception:
            with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
                st.session_state.doc_store[uploaded_file.name] = f.read()
            st.info(f"Archivo cargado en modo texto: {uploaded_file.name}")


# ================= ENCABEZADO =================
col_title, col_stat = st.columns([3, 1])
with col_title:
    st.markdown('<p class="main-title">Copilot de Infraestructura y Operaciones</p>',
                unsafe_allow_html=True)

with col_stat:
    total_srvs = 0
    if os.path.exists(CSV_PATH):
        try:
            df_tot = pd.read_csv(CSV_PATH)
            total_srvs = len(df_tot)
        except Exception:
            pass
    st.metric("Documentos cargados",
              f"{total_srvs} Documentos")

# ================= SECCIONES =================
tab_chat, tab_analytics, tab_arch, tab_docs, tab_templates = st.tabs([
    "Chat Copilot",
    "Analitica DuckDB",
    "Preview 4 Niveles",
    "Documentacion Tecnica",
    "Plantillas & Runbooks"
])

# ----------------- TAB 1: CHAT -----------------
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ingrese su consulta tecnica..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Procesando consulta..."):
                respuesta = generar_respuesta_asistente(prompt)
                st.markdown(respuesta)
                st.session_state.messages.append(
                    {"role": "assistant", "content": respuesta})

# ----------------- TAB 2: ANALITICA DUCKDB -----------------
with tab_analytics:
    st.subheader("Motor SQL DuckDB - Historial de Mantenimientos e Inventario")
    st.caption(
        "Consultas analiticas estructuradas con filtrado de alto rendimiento.")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_nivel = st.selectbox("Nivel de Arquitectura", [
                                    "Todos", "L1 - Hardware", "L2 - Virtualización", "L3 - Middleware", "L4 - Aplicación"])
    with col_f2:
        filtro_estado = st.selectbox(
            "Estado Operativo", ["Todos", "Operativo", "En Revision", "Critico"])
    with col_f3:
        filtro_tec = st.text_input("Filtrar por Tecnico")

    condiciones = ["1=1"]
    if filtro_nivel != "Todos":
        condiciones.append(f"nivel_arquitectura = '{filtro_nivel}'")
    if filtro_estado != "Todos":
        condiciones.append(f"estado = '{filtro_estado}'")
    if filtro_tec.strip():
        condiciones.append(
            f"LOWER(tecnico) LIKE LOWER('%{filtro_tec.strip()}%')")

    sql_query = f"SELECT * FROM read_csv_auto('{CSV_PATH}') WHERE {' AND '.join(condiciones)} ORDER BY fecha DESC"
    df_filtrado = duckdb.sql(sql_query).df()

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    with st.expander("Ejecutar Consulta SQL Personalizada"):
        custom_sql = st.text_area(
            "Sentencia SQL", value=f"SELECT nivel_arquitectura, count(*) as total_mantenimientos FROM read_csv_auto('{CSV_PATH}') GROUP BY nivel_arquitectura")
        if st.button("Ejecutar"):
            df_custom = ejecutar_consulta_sql(custom_sql)
            st.dataframe(df_custom, use_container_width=True)

# ----------------- TAB 3: PREVIEW 4 NIVELES -----------------
with tab_arch:
    st.subheader("Preview Topológico y Arquitectura en 4 Niveles")
    st.caption("Mapeo visual jerárquico de la infraestructura y dependencias entre capas.")

    # --- DIAGRAMA MERMAID ---
    st.markdown("#### 1. Diagrama Topológico de Dependencias")
    st.markdown("""
```mermaid
graph TD
    subgraph DevOps ["Capa DevOps y Despliegues (CI/CD)"]
        GitLab["GitLab (Control de Versiones y SCM)"]
        Jenkins["Jenkins (PRODJENK001/002 - Despliegues)"]
        PasosProd["Pasos a Producción Unicard (Procedimientos)"]
        GitLab --> Jenkins
        PasosProd -. Rige a .-> Jenkins
    end

    subgraph L4 ["Nivel 4: Aplicaciones y Negocio de Producción"]
        CreditMaker["CREDITMAKER (Evaluación y Venta de Créditos)"]
        Engage["ENGAGE (Sitio y Call Centers 10.24.0.12)"]
        BookingApp["Booking Core Engine (Motor de Negocio)"]
    end

    subgraph L3 ["Nivel 3: Middleware e Integración"]
        WSO2["WSO2 Suite (API Manager, EI, Identity Server)"]
        Balancer["HAProxy (BALANCER001/002 - 10.24.0.125/126)"]
        Redis["Redis Sentinel (Caché de Tokens)"]
    end

    subgraph L2 ["Nivel 2: Virtualización y Cómputo"]
        VCloud["VMware vCloud (vDCs, ESXi Clusters Microsoft/Linux)"]
    end

    subgraph L1 ["Nivel 1: Infraestructura Base / Hardware"]
        HPE["Blades HPE Synergy / ProLiant DL385 G7 / DL360"]
        SAN["SAN Pure Storage FlashArray (Fibre Channel)"]
    end

    subgraph Obs ["Capa Transversal de Observabilidad"]
        PRTG["PRTG Network Monitor (Sensores CPU/RAM/Disco/SLA)"]
        NAG["Nagios Core (Host Checks, Pings, SNMP)"]
        NR["New Relic (APM y Latencia de Microservicios)"]
    end

    %% Relaciones
    Jenkins -. Despliega en .-> L4
    Jenkins -. Despliega en .-> WSO2
    CreditMaker --> Balancer
    Engage --> Balancer
    BookingApp --> Balancer
    Balancer --> WSO2
    WSO2 --> Redis
    WSO2 --> VCloud
    VCloud --> HPE
    VCloud --> SAN

    PRTG -. Monitorea .-> WSO2
    PRTG -. Monitorea .-> VCloud
    NAG -. Monitorea .-> VCloud
    NAG -. Monitorea .-> HPE
    NR -. Monitorea .-> L4
```
""")

    st.divider()
    st.markdown("#### 2. Especificación por Capa de Infraestructura")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info("**L1: Hardware Base**\n\n- HPE ProLiant DL385/DL360\n- Pure Storage SAN FlashArray\n- Redes Fibre Channel 16Gbps\n- Fuentes Redundantes 7x24")
    with c2:
        st.info("**L2: Virtualización**\n\n- VMware vCloud Director\n- Clusters ESXi Intesis & Lidice\n- Redes SDN NSX-T\n- Datastores VMFS")
    with c3:
        st.info("**L3: Middleware**\n\n- WSO2 API Manager 2.5.0\n- WSO2 Enterprise Integrator 6.2\n- HAProxy (BALANCER001/002)\n- Redis Sentinel Cluster")
    with c4:
        st.info("**L4: Aplicaciones**\n\n- CREDITMAKER (Créditos)\n- ENGAGE (Call Center)\n- Jenkins / GitLab CI/CD\n- Booking Core Engine")


# ----------------- TAB 4: DOCUMENTOS -----------------
with tab_docs:
    st.subheader("Repositorio de Documentacion Tecnica Indexada")
    st.caption(
        "Manuales de contingencia, procedimientos de recuperacion, guias tecnicas y CMDBs.")

    if st.session_state.doc_store:
        col_doc_sel, col_info = st.columns([3, 1])
        with col_doc_sel:
            doc_seleccionado = st.selectbox(
                "Seleccionar Documento Activo", list(st.session_state.doc_store.keys()))
        with col_info:
            if doc_seleccionado:
                doc_text = st.session_state.doc_store[doc_seleccionado]
                st.caption(f"**Tamano:** {len(doc_text):,} caracteres")

        if doc_seleccionado:
            doc_content = st.session_state.doc_store[doc_seleccionado]

            # Detectar si el documento tiene multiples hojas (Excel / CMDB)
            if "## Hoja:" in doc_content:
                partes = doc_content.split("\n## Hoja:")
                header_doc = partes[0].strip()
                if header_doc:
                    st.markdown(header_doc)

                hojas_dict = {}
                for p in partes[1:]:
                    lineas = p.strip().split("\n", 1)
                    s_name = lineas[0].strip()
                    s_body = lineas[1].strip() if len(lineas) > 1 else ""
                    hojas_dict[s_name] = s_body

                if hojas_dict:
                    hoja_activa = st.selectbox(
                        "Seleccionar Hoja del Libro Excel:",
                        list(hojas_dict.keys()),
                        help="Navega entre las diferentes pestañas del archivo Excel de forma individual."
                    )
                    st.divider()
                    st.markdown(f"### Hoja: {hoja_activa}")
                    st.markdown(hojas_dict[hoja_activa])
            else:
                st.divider()
                st.markdown(doc_content)
    else:
        st.warning(
            "No hay documentos indexados. Cargue un archivo en el panel lateral.")

# ----------------- TAB 5: PLANTILLAS Y RUNBOOKS -----------------
with tab_templates:
    st.subheader("Generador Rápido de Documentación y Runbooks")
    st.caption("Crea y publica procedimientos técnicos estandarizados en 2 minutos para que el Copilot los indexe automáticamente.")

    col_t1, col_t2 = st.columns([1, 1], gap="large")

    with col_t1:
        st.markdown("#### 1. Configuración de la Plantilla")
        tipo_plantilla = st.selectbox(
            "Tipo de Procedimiento",
            [
                "Procedimiento de Rollback de Emergencia",
                "Paso a Producción / Despliegue CI/CD",
                "Reporte Postmortem / Incidente P1 (RCA)",
                "Ficha Técnica de Microservicio / API WSO2",
                "Guía de Contingencia y Failover Operativo"
            ]
        )

        autor = st.text_input("Autor / Técnico Responsable", value="Developer / DevOps")
        nombre_servicio = st.text_input("Nombre del Servicio o Componente", value="Booking Core Engine")
        nivel_arq = st.selectbox("Nivel de Arquitectura", ["L4 - Aplicación y Negocio", "L3 - Middleware e Integración", "L2 - Virtualización y Cómputo", "L1 - Hardware e Infraestructura Base"])

        doc_generado_md = ""
        nombre_archivo_sugerido = ""

        if "Rollback" in tipo_plantilla:
            criterio = st.text_area("Criterio de Activación de Rollback", value="Latencia > 500ms en New Relic por más de 3 min o Error Rate 5xx > 2%")
            pasos_rollback = st.text_area("Pasos de Reversión (Comandos / Acciones)", value="1. Ejecutar pipeline de Rollback en Azure DevOps release-v2.4.1\n2. Revertir cambios de esquema en BD Postgres si aplica\n3. Limpiar caché en Redis Sentinel: redis-cli FLUSHDB")
            verificacion = st.text_area("Comandos de Verificación de Salud", value="curl -I https://api.booking.internal/health\nsystemctl status booking-service")

            doc_generado_md = f"""# Procedimiento de Rollback: {nombre_servicio}
* **Autor:** `{autor}`
* **Nivel:** `{nivel_arq}`
* **Tipo:** `Rollback de Emergencia`

---

## 1. Criterios de Activación
{criterio}

## 2. Pasos de Reversión
```bash
{pasos_rollback}
```

## 3. Verificación Post-Rollback
```bash
{verificacion}
```

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
            nombre_archivo_sugerido = f"procedimiento_rollback_{nombre_servicio.lower().replace(' ', '_')}.md"

        elif "Paso a Producción" in tipo_plantilla:
            version = st.text_input("Versión / Tag de Release", value="v2.5.0")
            pipeline_url = st.text_input("Pipeline Azure DevOps / Release ID", value="https://dev.azure.com/smucorp/pipelines/142")
            variables_env = st.text_area("Variables de Entorno / Configuración", value="REDIS_HOST=10.24.0.126\nJWT_SECRET=[CONFIGURADO EN KEYVAULT]\nLOG_LEVEL=INFO")
            smoke_test = st.text_area("Checklist de Validación (Smoke Tests)", value="- [ ] Endpoint /health respondiendo HTTP 200\n- [ ] Transacciones fluyendo en VZOR Suite\n- [ ] Cero alertas críticas en Nagios")

            doc_generado_md = f"""# Guía de Despliegue a Producción: {nombre_servicio} ({version})
* **Autor:** `{autor}`
* **Nivel:** `{nivel_arq}`
* **Pipeline:** `{pipeline_url}`

---

## 1. Variables de Entorno y Secretos
```env
{variables_env}
```

## 2. Checklist de Validación (Smoke Tests)
{smoke_test}

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
            nombre_archivo_sugerido = f"despliegue_{nombre_servicio.lower().replace(' ', '_')}_{version.replace('.', '_')}.md"

        elif "Postmortem" in tipo_plantilla:
            incidente_id = st.text_input("ID del Ticket / Incidente", value="INC-88912")
            impacto = st.text_area("Resumen del Impacto", value="Indisponibilidad del servicio de autorización por 14 minutos. 120 transacciones rechazadas.")
            causa_raiz = st.text_area("Diagnóstico de Causa Raíz (RCA)", value="Agotamiento de pool de conexiones JDBC en WSO2 Enterprise Integrator debido a query no indexada.")
            solucion = st.text_area("Solución Inmediata Aplicada", value="Reinicio del nodo worker WSO2 y ampliación de maxConnections a 150.")
            preventiva = st.text_area("Medida Preventiva para Evitar Recurrencia", value="Creación de índice en tabla t_auth_tokens y ajuste de timeout en WSO2.")

            doc_generado_md = f"""# Reporte Postmortem P1: {incidente_id} - {nombre_servicio}
* **Autor:** `{autor}`
* **Nivel Afectado:** `{nivel_arq}`
* **Incidente:** `{incidente_id}`

---

## 1. Resumen del Impacto
{impacto}

## 2. Causa Raíz (Root Cause Analysis)
{causa_raiz}

## 3. Solución Aplicada
{solucion}

## 4. Acciones Correctivas y Prevención
{preventiva}

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
            nombre_archivo_sugerido = f"postmortem_{incidente_id.lower()}_{nombre_servicio.lower().replace(' ', '_')}.md"

        elif "Microservicio" in tipo_plantilla:
            endpoint = st.text_input("Endpoint Base / Ruta API", value="/api/v1/booking")
            auth_tipo = st.text_input("Método de Autenticación", value="OAuth2 Bearer Token (Redis Sentinel)")
            dependencias = st.text_area("Dependencias Backend y Nodos", value="* VM: VM-BOOKING-01 (10.24.0.125)\n* DB: Postgres HA (10.24.0.130)\n* Gateway: WSO2 API Manager")

            doc_generado_md = f"""# Ficha Técnica de Microservicio: {nombre_servicio}
* **Desarrollador / Líder Técnico:** `{autor}`
* **Nivel:** `{nivel_arq}`
* **Endpoint Base:** `{endpoint}`
* **Autenticación:** `{auth_tipo}`

---

## 1. Dependencias y Nodos de Infraestructura
{dependencias}

## 2. Telemetría y Métricas Clave
* **New Relic APM:** Latencia normal < 40ms
* **Nagios Check:** `check_http -H localhost -p 8080 -u {endpoint}/health`

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
            nombre_archivo_sugerido = f"ficha_servicio_{nombre_servicio.lower().replace(' ', '_')}.md"

        else:  # Failover
            sintoma = st.text_area("Síntoma de Falla / Alerta Disparadora", value="Host ESXi no responde en vCloud o alerta CRITICAL en Nagios por ping timeout.")
            procedimiento_failover = st.text_area("Procedimiento de Conmutación (Failover)", value="1. Conmutar tráfico en HAProxy a BALANCER002 (10.24.0.126)\n2. Activar réplica en VMware vCloud Director\n3. Validar resolución DNS interna")

            doc_generado_md = f"""# Manual de Contingencia y Failover: {nombre_servicio}
* **Autor:** `{autor}`
* **Nivel:** `{nivel_arq}`

---

## 1. Síntoma de Alerta
{sintoma}

## 2. Procedimiento de Conmutación (Failover)
```bash
{procedimiento_failover}
```

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
            nombre_archivo_sugerido = f"contingencia_failover_{nombre_servicio.lower().replace(' ', '_')}.md"

    with col_t2:
        st.markdown("#### 2. Previsualización en Vivo del Documento")
        nombre_final = st.text_input("Nombre de Archivo Final (.md)", value=nombre_archivo_sugerido)

        with st.container(border=True):
            st.markdown(doc_generado_md)

        st.divider()
        if st.button("Guardar y Publicar en Base de Conocimiento", type="primary", use_container_width=True):
            if not nombre_final.endswith(".md"):
                nombre_final += ".md"

            ruta_destino = os.path.join(DOCS_DIR, nombre_final)
            os.makedirs(DOCS_DIR, exist_ok=True)
            with open(ruta_destino, "w", encoding="utf-8") as f:
                f.write(doc_generado_md)

            st.session_state.doc_store[nombre_final] = doc_generado_md
            st.success(f"Documento guardado e indexado exitosamente como **{nombre_final}**.")
            st.info("El Chat Copilot y la búsqueda analítica ya pueden responder preguntas sobre este nuevo procedimiento.")


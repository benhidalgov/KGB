from excel_cleaner import procesar_excel_limpio
from datetime import datetime
import difflib
import glob
import json
import os
import shutil

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

    /* Estilos del Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    [data-testid="stSidebar"] div[data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 1.5px dashed #CBD5E1;
        border-radius: 8px;
        padding: 8px;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] div[data-testid="stFileUploader"]:hover {
        border-color: #3B82F6;
        background-color: #EFF6FF;
    }

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
HISTORY_DIR = os.path.join("data", "history")
AUDIT_LOG_PATH = os.path.join("data", "audit_log.json")


def registrar_evento_auditoria(doc_name: str, accion: str, version_ant: int, version_nueva: int, autor: str, motivo: str):
    """Registra un evento inmutable de trazabilidad en el log central de auditoria."""
    eventos = []
    if os.path.exists(AUDIT_LOG_PATH):
        try:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                eventos = json.load(f)
        except Exception:
            eventos = []

    evento = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "documento": doc_name,
        "accion": accion,
        "version_anterior": f"v{version_ant}" if version_ant > 0 else "-",
        "version_nueva": f"v{version_nueva}",
        "editor_responsable": autor.strip() if autor and autor.strip() else "Desconocido",
        "motivo_justificacion": motivo.strip() if motivo and motivo.strip() else "Sin justificacion"
    }
    eventos.append(evento)

    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(eventos, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def generar_diff_texto(texto_ant: str, texto_nuevo: str, label_ant: str = "Version A", label_nuevo: str = "Version B") -> str:
    """Genera una representacion diff unificada para comparar dos versiones."""
    lineas_ant = texto_ant.splitlines(keepends=True)
    lineas_nuevo = texto_nuevo.splitlines(keepends=True)
    diff = difflib.unified_diff(
        lineas_ant,
        lineas_nuevo,
        fromfile=label_ant,
        tofile=label_nuevo,
        n=2
    )
    diff_text = "".join(diff)
    if not diff_text.strip():
        return "No se detectaron diferencias de contenido entre estas dos versiones."
    return diff_text


def obtener_historial_versiones(doc_name: str) -> list:
    """Obtiene el registro cronologico de versiones de un documento."""
    meta_path = os.path.join(HISTORY_DIR, doc_name, "metadata.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def inicializar_version_inicial_si_no_existe(doc_name: str, contenido_actual: str, autor: str = "Sistema", comentario: str = "Versión base inicial"):
    """Inicializa la version v1 si no existe registro historico previo."""
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    meta_path = os.path.join(doc_hist_dir, "metadata.json")
    if not os.path.exists(meta_path):
        os.makedirs(doc_hist_dir, exist_ok=True)
        v1_filename = "v1.md"
        with open(os.path.join(doc_hist_dir, v1_filename), "w", encoding="utf-8") as f:
            f.write(contenido_actual)

        historial = [
            {
                "version": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "autor": autor,
                "comentario": comentario,
                "archivo_snapshot": v1_filename,
                "caracteres": len(contenido_actual)
            }
        ]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)

        registrar_evento_auditoria(
            doc_name=doc_name,
            accion="CREACION",
            version_ant=0,
            version_nueva=1,
            autor=autor,
            motivo=comentario
        )
        return historial
    return obtener_historial_versiones(doc_name)


def guardar_nueva_version(doc_name: str, nuevo_contenido: str, autor: str, comentario: str) -> int:
    """Guarda una nueva revision incrementando la version (vN+1) y preservando snapshots inmutables."""
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    os.makedirs(doc_hist_dir, exist_ok=True)
    meta_path = os.path.join(doc_hist_dir, "metadata.json")

    historial = obtener_historial_versiones(doc_name)
    if not historial:
        contenido_previo = st.session_state.doc_store.get(doc_name, nuevo_contenido)
        v1_filename = "v1.md"
        with open(os.path.join(doc_hist_dir, v1_filename), "w", encoding="utf-8") as f:
            f.write(contenido_previo)
        historial = [
            {
                "version": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "autor": "Sistema / Creador",
                "comentario": "Versión base inicial",
                "archivo_snapshot": v1_filename,
                "caracteres": len(contenido_previo)
            }
        ]

    version_ant_num = len(historial)
    nueva_v_num = version_ant_num + 1
    snapshot_fname = f"v{nueva_v_num}.md"

    with open(os.path.join(doc_hist_dir, snapshot_fname), "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

    nueva_entry = {
        "version": nueva_v_num,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "autor": autor.strip() if autor and autor.strip() else "Técnico",
        "comentario": comentario.strip() if comentario and comentario.strip() else "Actualización de contenido",
        "archivo_snapshot": snapshot_fname,
        "caracteres": len(nuevo_contenido)
    }
    historial.append(nueva_entry)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)

    # Actualizar archivo activo en DOCS_DIR
    target_path = os.path.join(DOCS_DIR, doc_name)
    ext = os.path.splitext(doc_name)[1].lower()
    if ext in ('.docx', '.pdf', '.pptx', '.xlsx', '.xls'):
        md_name = f"{os.path.splitext(doc_name)[0]}.md"
        target_path = os.path.join(DOCS_DIR, md_name)
        st.session_state.doc_store[md_name] = nuevo_contenido
    else:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)

    st.session_state.doc_store[doc_name] = nuevo_contenido

    accion_tipo = "ROLLBACK" if "rollback" in comentario.lower() else "EDICION"
    registrar_evento_auditoria(
        doc_name=doc_name,
        accion=accion_tipo,
        version_ant=version_ant_num,
        version_nueva=nueva_v_num,
        autor=autor,
        motivo=comentario
    )

    return nueva_v_num


def obtener_contenido_version(doc_name: str, snapshot_fname: str) -> str:
    """Recupera el contenido exacto de un snapshot historico."""
    snap_path = os.path.join(HISTORY_DIR, doc_name, snapshot_fname)
    if os.path.exists(snap_path):
        with open(snap_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def cargar_hoja_excel_dataframe(filepath: str, sheet_name: str) -> pd.DataFrame:
    """Carga una hoja de calculo Excel en un DataFrame normalizado para visualizacion en cuadricula."""
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d')
        df = df.fillna('')
        return df
    except Exception as e:
        return pd.DataFrame({"Mensaje": [f"No se pudo cargar la hoja: {e}"]})


def guardar_nueva_version_excel(doc_name: str, sheet_name: str, df_nuevo: pd.DataFrame, autor: str, comentario: str) -> int:
    """Guarda una nueva version de un libro Excel modificando la hoja seleccionada y preservando el historial inmutable."""
    excel_path = os.path.join(DOCS_DIR, doc_name)
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    os.makedirs(doc_hist_dir, exist_ok=True)
    meta_path = os.path.join(doc_hist_dir, "metadata.json")

    historial = obtener_historial_versiones(doc_name)
    if not historial:
        v1_filename = "v1.md"
        contenido_previo = st.session_state.doc_store.get(doc_name, "")
        with open(os.path.join(doc_hist_dir, v1_filename), "w", encoding="utf-8") as f:
            f.write(contenido_previo)
        historial = [
            {
                "version": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "autor": "Sistema / Creador",
                "comentario": "Version base inicial",
                "archivo_snapshot": v1_filename,
                "caracteres": len(contenido_previo)
            }
        ]

    version_ant_num = len(historial)
    nueva_v_num = version_ant_num + 1
    snapshot_excel_fname = f"v{nueva_v_num}_{doc_name}"

    # 1. Actualizar el archivo Excel en DOCS_DIR
    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_nuevo.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_nuevo.to_excel(writer, sheet_name=sheet_name, index=False)

    # Copiar snapshot del excel modificado
    shutil.copy2(excel_path, os.path.join(doc_hist_dir, snapshot_excel_fname))

    # 2. Re-procesar contenido estructurado para el Copilot
    nuevo_markdown = procesar_excel_limpio(excel_path)
    snapshot_md_fname = f"v{nueva_v_num}.md"
    with open(os.path.join(doc_hist_dir, snapshot_md_fname), "w", encoding="utf-8") as f:
        f.write(nuevo_markdown)

    st.session_state.doc_store[doc_name] = nuevo_markdown

    # 3. Registrar metadata
    nueva_entry = {
        "version": nueva_v_num,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "autor": autor.strip() if autor and autor.strip() else "Tecnico",
        "comentario": f"[{sheet_name}] {comentario.strip()}" if comentario and comentario.strip() else f"Edicion de hoja {sheet_name}",
        "archivo_snapshot": snapshot_md_fname,
        "archivo_excel_snapshot": snapshot_excel_fname,
        "caracteres": len(nuevo_markdown)
    }
    historial.append(nueva_entry)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)

    registrar_evento_auditoria(
        doc_name=doc_name,
        accion="EDICION_EXCEL",
        version_ant=version_ant_num,
        version_nueva=nueva_v_num,
        autor=autor,
        motivo=f"[{sheet_name}] {comentario}"
    )

    return nueva_v_num

# Inicializacion de estado de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "**Sistema de Búsqueda de documentación por palabras clave.**\n\n"
                "Capacidades activas:\n"
                "- Consulta analítica de inventario y mantenimientos por número de serie, servidor o técnico.\n"
                "- Recuperación de procedimientos técnicos, contingencias y despliegues (MarkItDown).\n"
            )
        }
    ]

if "doc_store" not in st.session_state:
    st.session_state.doc_store = {}


# Carga de documentos locales


def cargar_documentos_locales(force: bool = False):
    if os.path.exists(DOCS_DIR):
        if force:
            st.session_state.doc_store = {}
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
                    try:
                        with open(doc_file, "r", encoding="utf-8", errors="ignore") as f:
                            st.session_state.doc_store[fname] = f.read()
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


# ================= SIDEBAR (ACCESO RÁPIDO & CONTROL) =================
with st.sidebar:
    st.markdown("### Acceso Rápido")
    st.caption("Panel de Control e Ingesta Directa")

    st.markdown("---")

    # 1. Ingesta Rápida de Archivos
    st.markdown("#### Subir Archivo(s) Técnico(s)")
    st.caption("Indexación automática en memoria y almacenamiento local.")

    uploaded_files = st.file_uploader(
        "Arrastra o selecciona tus archivos:",
        type=["pdf", "docx", "xlsx", "xls", "csv", "txt", "md", "pptx"],
        accept_multiple_files=True,
        help="Formatos: PDF, Word (.docx), Excel (.xlsx/.xls), Markdown (.md), CSV, TXT, PPTX."
    )

    if uploaded_files:
        for uf in uploaded_files:
            save_path = os.path.join(DOCS_DIR, uf.name)
            os.makedirs(DOCS_DIR, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(uf.getbuffer())

            ext = os.path.splitext(uf.name)[1].lower()
            try:
                if ext in (".xlsx", ".xls"):
                    st.session_state.doc_store[uf.name] = procesar_excel_limpio(save_path)
                    st.success(f"[Excel] {uf.name} (Estructurado)")
                elif ext in (".md", ".txt", ".csv"):
                    with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
                        st.session_state.doc_store[uf.name] = f.read()
                    st.success(f"[Texto] {uf.name}")
                else:
                    from markitdown import MarkItDown
                    md_engine = MarkItDown()
                    res = md_engine.convert(save_path)
                    st.session_state.doc_store[uf.name] = res.text_content
                    st.success(f"[Documento] {uf.name} (Indexado)")
            except Exception as ex:
                try:
                    with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
                        st.session_state.doc_store[uf.name] = f.read()
                    st.info(f"[Texto] {uf.name} (Modo texto fallback)")
                except Exception:
                    st.error(f"Error procesando {uf.name}: {ex}")

    st.markdown("---")

    # 2. Resumen de Documentos Indexados
    cant_docs = len(st.session_state.doc_store)
    st.markdown(f"#### Base Indexada ({cant_docs})")

    if cant_docs > 0:
        conteo_excel = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[1].lower() in ('.xlsx', '.xls'))
        conteo_doc = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[1].lower() in ('.docx', '.pdf', '.pptx', '.doc'))
        conteo_txt = sum(1 for d in st.session_state.doc_store if os.path.splitext(d)[1].lower() in ('.md', '.txt', '.csv'))

        with st.expander("Ver documentos cargados", expanded=False):
            tipo_filtro = st.selectbox(
                "Filtrar por tipo:",
                [
                    f"Todos ({cant_docs})",
                    f"Excel ({conteo_excel})",
                    f"Documentos Word/PDF ({conteo_doc})",
                    f"Markdown / Texto ({conteo_txt})"
                ],
                key="sb_type_filter"
            )

            doc_filter = st.text_input(
                "Buscar por nombre...", key="sb_doc_filter", placeholder="Nombre de archivo...")

            docs_filtrados = []
            for d in sorted(st.session_state.doc_store.keys()):
                ext = os.path.splitext(d)[1].lower()
                if tipo_filtro.startswith("Excel") and ext not in ('.xlsx', '.xls'):
                    continue
                if tipo_filtro.startswith("Documentos") and ext not in ('.docx', '.pdf', '.pptx', '.doc'):
                    continue
                if tipo_filtro.startswith("Markdown") and ext not in ('.md', '.txt', '.csv'):
                    continue
                if doc_filter and doc_filter.lower() not in d.lower():
                    continue
                docs_filtrados.append(d)

            if docs_filtrados:
                for d in docs_filtrados:
                    ext = os.path.splitext(d)[1].lower()
                    tag = "[Excel]" if ext in ('.xlsx', '.xls') else "[Doc]" if ext in ('.pdf', '.docx', '.pptx', '.doc') else "[Txt]"
                    size_kb = len(st.session_state.doc_store[d]) / 1024
                    st.markdown(f"`{tag}` **{d}** *({size_kb:.1f} KB)*")
            else:
                st.caption("No hay documentos que coincidan con el filtro.")
    else:
        st.info("No hay documentos indexados aún.")

    st.markdown("---")

    # 3. Acciones Rápidas
    st.markdown("#### Acciones Rápidas")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Reindexar", help="Recarga todos los documentos desde data/docs/", use_container_width=True):
            cargar_documentos_locales(force=True)
            st.toast("Base documental reindexada con éxito")
            st.rerun()
    with col_btn2:
        if st.button("Limpiar Chat", help="Reinicia la conversación actual", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "**Sistema de Búsqueda de documentación por palabras clave.**\n\n"
                        "Capacidades activas:\n"
                        "- Consulta analítica de inventario y mantenimientos por número de serie, servidor o técnico.\n"
                        "- Recuperación de procedimientos técnicos, contingencias y despliegues (MarkItDown).\n"
                    )
                }
            ]
            st.toast("Historial de chat reiniciado")
            st.rerun()

    st.markdown("---")

    # 4. Estado del Sistema
    st.markdown("#### Estado del Sistema")
    st.markdown(f"""
<div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; font-size: 0.8rem;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
        <span><b>DuckDB SQL:</b></span> <span class="badge-ok">Conectado</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
        <span><b>MarkItDown Engine:</b></span> <span class="badge-ok">Activo</span>
    </div>
    <div style="display: flex; justify-content: space-between;">
        <span><b>Docs Indexados:</b></span> <b>{cant_docs} archivos</b>
    </div>
</div>
""", unsafe_allow_html=True)


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
    st.metric("Documentación cargada",
              f"{total_srvs} Documentos")

# ================= SECCIONES =================
tab_chat, tab_analytics, tab_arch, tab_docs, tab_templates = st.tabs([
    "Consultar dudas (Buscar por palabras)",
    "Historial de Mantenimientos",
    "Preview de arquitecturas",
    "Documentacion Tecnica",
    "Plantillas de documentación"
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
    st.subheader("Repositorio de Documentacion Tecnica Indexada y Versionada")
    st.caption(
        "Manuales de contingencia, procedimientos operativos, edición en vivo y control de cambios.")

    if st.session_state.doc_store:
        col_tipo_t4, col_doc_sel, col_info = st.columns([1.2, 2.5, 1.3])
        with col_tipo_t4:
            filtro_t4 = st.selectbox(
                "Tipo de Documento",
                ["Todos", "Excel (.xlsx, .xls)", "Documentos (.docx, .pdf, .pptx)", "Markdown / Texto (.md, .txt)"],
                key="tab4_type_selector"
            )

        docs_disponibles_t4 = []
        for d in sorted(st.session_state.doc_store.keys()):
            ext = os.path.splitext(d)[1].lower()
            if filtro_t4.startswith("Excel") and ext not in ('.xlsx', '.xls'):
                continue
            if filtro_t4.startswith("Documentos") and ext not in ('.docx', '.pdf', '.pptx', '.doc'):
                continue
            if filtro_t4.startswith("Markdown") and ext not in ('.md', '.txt', '.csv'):
                continue
            docs_disponibles_t4.append(d)

        with col_doc_sel:
            if docs_disponibles_t4:
                doc_seleccionado = st.selectbox(
                    "Seleccionar Documento Activo", docs_disponibles_t4)
            else:
                doc_seleccionado = None
                st.warning("No hay archivos para este tipo.")

        if doc_seleccionado:
            doc_content = st.session_state.doc_store[doc_seleccionado]
            historial = inicializar_version_inicial_si_no_existe(doc_seleccionado, doc_content)
            ultima_version = historial[-1]["version"] if historial else 1
            ultima_fecha = historial[-1]["timestamp"] if historial else "N/A"
            ultimo_autor = historial[-1]["autor"] if historial else "N/A"

            with col_info:
                st.caption(f"**Versión:** `v{ultima_version}` | **Tamaño:** {len(doc_content):,} chars")

            st.markdown(f"""
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 12px; margin-bottom: 12px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center;">
                <span><b>Archivo:</b> <code>{doc_seleccionado}</code></span>
                <span><b>Versión Actual:</b> <span class="badge-ok">v{ultima_version}</span></span>
                <span><b>Autor:</b> <code>{ultimo_autor}</code></span>
                <span><b>Última actualización:</b> {ultima_fecha}</span>
            </div>
            """, unsafe_allow_html=True)

            subtab_view, subtab_edit, subtab_hist = st.tabs([
                "Visualización",
                "Editar Documento",
                f"Historial de Versiones ({len(historial)})"
            ])

            with subtab_view:
                excel_orig_path = os.path.join(DOCS_DIR, doc_seleccionado)
                es_excel = doc_seleccionado.lower().endswith(('.xlsx', '.xls')) and os.path.exists(excel_orig_path)

                if es_excel:
                    try:
                        xls = pd.ExcelFile(excel_orig_path)
                        sheet_names = xls.sheet_names
                    except Exception:
                        sheet_names = []

                    col_sheet, col_mode = st.columns([2, 1])
                    with col_sheet:
                        hoja_activa = st.selectbox(
                            "Seleccionar Hoja del Libro Excel:",
                            sheet_names if sheet_names else ["Hoja1"],
                            help="Navega entre las pestañas del archivo Excel.",
                            key=f"sb_sheet_sel_{doc_seleccionado}"
                        )
                    with col_mode:
                        vista_modo = st.radio(
                            "Modo de Visualización:",
                            ["Cuadrícula Interactiva (Excel)", "Texto Estructurado"],
                            horizontal=True,
                            key=f"mode_view_{doc_seleccionado}"
                        )

                    st.divider()
                    if vista_modo == "Cuadrícula Interactiva (Excel)":
                        df_sheet = cargar_hoja_excel_dataframe(excel_orig_path, hoja_activa)
                        st.markdown(f"**Hoja:** `{hoja_activa}` | **Registros:** {len(df_sheet)} filas | **Columnas:** {len(df_sheet.columns)}")
                        st.dataframe(df_sheet, use_container_width=True, hide_index=True, height=520)
                    else:
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
                            st.markdown(f"### Hoja: {hoja_activa}")
                            st.markdown(hojas_dict.get(hoja_activa, "Contenido no disponible para esta hoja en formato texto."))
                        else:
                            st.markdown(doc_content)

                elif "## Hoja:" in doc_content:
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
                    st.markdown(doc_content)

            with subtab_edit:
                excel_orig_path = os.path.join(DOCS_DIR, doc_seleccionado)
                es_excel = doc_seleccionado.lower().endswith(('.xlsx', '.xls')) and os.path.exists(excel_orig_path)

                if es_excel:
                    try:
                        xls = pd.ExcelFile(excel_orig_path)
                        sheet_names_edit = xls.sheet_names
                    except Exception:
                        sheet_names_edit = []

                    st.markdown("#### Edición en Vivo de Libro Excel")
                    st.caption("Modifique los valores de las celdas directamente en la cuadrícula o inserte nuevas filas. Al guardar se creará una versión incremental.")

                    col_es1, col_es2 = st.columns([1.5, 2.5])
                    with col_es1:
                        hoja_editar = st.selectbox(
                            "Seleccionar Hoja a Modificar:",
                            sheet_names_edit if sheet_names_edit else ["Hoja1"],
                            key=f"edit_sheet_sel_{doc_seleccionado}"
                        )
                    with col_es2:
                        col_ae1, col_ae2 = st.columns(2)
                        with col_ae1:
                            autor_edit = st.text_input(
                                "Editor / Técnico Responsable (*)",
                                value="",
                                placeholder="Ej: Juan Pérez / DevOps",
                                key=f"author_input_grid_{doc_seleccionado}"
                            )
                        with col_ae2:
                            motivo_edit = st.text_input(
                                "Motivo del Cambio (*)",
                                placeholder="Ej: Actualización de IP de nodo",
                                key=f"motive_input_grid_{doc_seleccionado}"
                            )

                    df_to_edit = cargar_hoja_excel_dataframe(excel_orig_path, hoja_editar)

                    st.markdown(f"**Cuadrícula de la Hoja:** `{hoja_editar}` *(Doble clic en una celda para editar, use el botón final para agregar filas)*")
                    df_modificado = st.data_editor(
                        df_to_edit,
                        use_container_width=True,
                        num_rows="dynamic",
                        height=480,
                        key=f"grid_editor_{doc_seleccionado}_{hoja_editar}"
                    )

                    col_btn_save, col_btn_info = st.columns([2, 3])
                    with col_btn_save:
                        if st.button(
                            f"Guardar y Publicar Versión v{ultima_version + 1}",
                            type="primary",
                            use_container_width=True,
                            key=f"btn_save_grid_{doc_seleccionado}"
                        ):
                            if not autor_edit or not autor_edit.strip():
                                st.error("Error de Auditoría: Debe ingresar el Editor / Técnico Responsable para guardar la nueva versión.")
                            elif not motivo_edit or not motivo_edit.strip():
                                st.error("Error de Auditoría: Debe ingresar el Motivo del Cambio para mantener la trazabilidad.")
                            else:
                                nueva_v = guardar_nueva_version_excel(
                                    doc_name=doc_seleccionado,
                                    sheet_name=hoja_editar,
                                    df_nuevo=df_modificado,
                                    autor=autor_edit.strip(),
                                    comentario=motivo_edit.strip()
                                )
                                st.toast(f"Versión v{nueva_v} guardada y reindexada exitosamente")
                                st.success(f"¡Versión [Version v{nueva_v}] creada con éxito! Responsable: {autor_edit.strip()}. La hoja '{hoja_editar}' y el Copilot han sido actualizados.")
                                st.rerun()
                    with col_btn_info:
                        st.caption("*Al guardar, se preservará un snapshot del libro Excel y la base documental se reindexará automáticamente con registro de auditoría.*")

                else:
                    st.markdown("#### Edición en Vivo y Generación de Nueva Versión")
                    st.caption("Modifique los procedimientos, IPs o parámetros. Al guardar, se preservará una copia histórica inmutable de la versión previa.")

                    col_e1, col_e2 = st.columns([1, 2])
                    with col_e1:
                        autor_edit = st.text_input(
                            "Editor / Técnico Responsable (*)",
                            value="",
                            placeholder="Ej: Juan Pérez / DevOps",
                            key=f"author_input_{doc_seleccionado}"
                        )
                    with col_e2:
                        motivo_edit = st.text_input(
                            "Motivo o Resumen del Cambio (*)",
                            placeholder="Ej: Actualización de IP de nodo primario a 10.24.0.126",
                            key=f"motive_input_{doc_seleccionado}"
                        )

                    texto_editado = st.text_area(
                        "Contenido del Documento (Markdown)",
                        value=doc_content,
                        height=450,
                        key=f"textarea_edit_{doc_seleccionado}"
                    )

                    col_btn_save, col_btn_info = st.columns([2, 3])
                    with col_btn_save:
                        if st.button(
                            f"Guardar y Publicar Versión v{ultima_version + 1}",
                            type="primary",
                            use_container_width=True,
                            key=f"btn_save_{doc_seleccionado}"
                        ):
                            if not autor_edit or not autor_edit.strip():
                                st.error("Error de Auditoría: Debe ingresar el Editor / Técnico Responsable para guardar la nueva versión.")
                            elif not motivo_edit or not motivo_edit.strip():
                                st.error("Error de Auditoría: Debe ingresar el Motivo del Cambio para mantener la trazabilidad.")
                            else:
                                nueva_v = guardar_nueva_version(
                                    doc_name=doc_seleccionado,
                                    nuevo_contenido=texto_editado,
                                    autor=autor_edit.strip(),
                                    comentario=motivo_edit.strip()
                                )
                                st.toast(f"Versión v{nueva_v} guardada y reindexada exitosamente")
                                st.success(f"¡Versión [Version v{nueva_v}] creada con éxito! Responsable: {autor_edit.strip()}. El Copilot y el RAG han sido actualizados en memoria.")
                                st.rerun()
                    with col_btn_info:
                        st.caption("*Al guardar, la versión actual pasará al historial y el asistente Copilot responderá con la información actualizada inmediatamente.*")

            with subtab_hist:
                st.markdown("#### Registro Histórico y Trazabilidad")
                st.caption("Historial inmutable de todas las revisiones aplicadas sobre este documento.")

                df_hist = pd.DataFrame(historial)[["version", "timestamp", "autor", "comentario", "caracteres"]]
                df_hist.columns = ["Versión", "Fecha y Hora", "Editor / Responsable", "Motivo del Cambio", "Tamaño (caracteres)"]
                st.dataframe(df_hist, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("##### Comparador Visual de Cambios (Diff)")
                st.caption("Compare las diferencias exactas de contenido entre dos versiones de este documento.")

                if len(historial) >= 2:
                    col_cmp1, col_cmp2 = st.columns(2)
                    nombres_versiones = [f"v{item['version']} - {item['timestamp']} ({item['autor']})" for item in historial]
                    mapa_versiones = {f"v{item['version']} - {item['timestamp']} ({item['autor']})": item for item in historial}

                    with col_cmp1:
                        ver_base_sel = st.selectbox(
                            "Versión Base (Anterior):",
                            nombres_versiones,
                            index=0,
                            key=f"diff_base_{doc_seleccionado}"
                        )
                    with col_cmp2:
                        ver_comp_sel = st.selectbox(
                            "Versión a Comparar (Nueva):",
                            nombres_versiones,
                            index=len(nombres_versiones) - 1,
                            key=f"diff_comp_{doc_seleccionado}"
                        )

                    item_base = mapa_versiones[ver_base_sel]
                    item_comp = mapa_versiones[ver_comp_sel]

                    texto_base = obtener_contenido_version(doc_seleccionado, item_base["archivo_snapshot"])
                    texto_comp = obtener_contenido_version(doc_seleccionado, item_comp["archivo_snapshot"])

                    diff_resultado = generar_diff_texto(
                        texto_ant=texto_base,
                        texto_nuevo=texto_comp,
                        label_ant=f"v{item_base['version']} ({item_base['autor']})",
                        label_nuevo=f"v{item_comp['version']} ({item_comp['autor']})"
                    )

                    with st.expander(f"Ver Diferencias (Diff): v{item_base['version']} vs v{item_comp['version']}", expanded=True):
                        st.code(diff_resultado, language="diff")
                else:
                    st.caption("Se requieren al menos 2 versiones para comparar diferencias.")

                st.markdown("---")
                st.markdown("##### Inspeccionar Versión Histórica")

                opciones_versiones = {
                    f"v{item['version']} - {item['timestamp']} ({item['autor']}): {item['comentario']}": item
                    for item in reversed(historial)
                }

                v_sel_label = st.selectbox(
                    "Seleccione una versión para previsualizar:",
                    list(opciones_versiones.keys()),
                    key=f"select_hist_ver_{doc_seleccionado}"
                )

                item_seleccionado = opciones_versiones[v_sel_label]
                contenido_snapshot = obtener_contenido_version(doc_seleccionado, item_seleccionado["archivo_snapshot"])

                with st.expander(f"Previsualizar contenido de la Versión v{item_seleccionado['version']}", expanded=False):
                    st.markdown(contenido_snapshot)

                if item_seleccionado["version"] != ultima_version:
                    st.markdown(f"##### Revertir Documento a la Versión v{item_seleccionado['version']} (Rollback)")
                    st.caption("Para garantizar la trazabilidad corporativa, debe especificar el Editor y la justificación técnica del Rollback.")

                    col_rb_a, col_rb_m = st.columns([1, 2])
                    with col_rb_a:
                        autor_rb = st.text_input(
                            "Editor / Técnico que ejecuta el Rollback (*)",
                            value="",
                            placeholder="Ej: Juan Pérez / SysAdmin",
                            key=f"author_rb_{doc_seleccionado}_{item_seleccionado['version']}"
                        )
                    with col_rb_m:
                        motivo_rb = st.text_input(
                            "Motivo o Justificación del Rollback (*)",
                            value="",
                            placeholder=f"Ej: Reversión por inconsistencia en v{ultima_version}",
                            key=f"motive_rb_{doc_seleccionado}_{item_seleccionado['version']}"
                        )

                    if st.button(
                        f"Confirmar y Ejecutar Rollback a la Versión v{item_seleccionado['version']}",
                        type="primary",
                        key=f"btn_confirm_rollback_{doc_seleccionado}_{item_seleccionado['version']}"
                    ):
                        if not autor_rb or not autor_rb.strip():
                            st.error("Error de Auditoría: Debe ingresar el Editor / Técnico responsable de ejecutar el Rollback.")
                        elif not motivo_rb or not motivo_rb.strip():
                            st.error("Error de Auditoría: Debe ingresar la justificación técnica del Rollback.")
                        else:
                            excel_snap = item_seleccionado.get("archivo_excel_snapshot")
                            snap_full_path = os.path.join(HISTORY_DIR, doc_seleccionado, excel_snap) if excel_snap else ""
                            if excel_snap and os.path.exists(snap_full_path):
                                shutil.copy2(snap_full_path, os.path.join(DOCS_DIR, doc_seleccionado))
                                nuevo_md = procesar_excel_limpio(os.path.join(DOCS_DIR, doc_seleccionado))
                                nueva_v = guardar_nueva_version(
                                    doc_name=doc_seleccionado,
                                    nuevo_contenido=nuevo_md,
                                    autor=autor_rb.strip(),
                                    comentario=f"[Rollback a v{item_seleccionado['version']}] {motivo_rb.strip()}"
                                )
                            else:
                                nueva_v = guardar_nueva_version(
                                    doc_name=doc_seleccionado,
                                    nuevo_contenido=contenido_snapshot,
                                    autor=autor_rb.strip(),
                                    comentario=f"[Rollback a v{item_seleccionado['version']}] {motivo_rb.strip()}"
                                )
                            st.toast(f"Documento restaurado a v{item_seleccionado['version']} (Registrado como v{nueva_v})")
                            st.success(f"Rollback completado con éxito. Se generó la versión [Version v{nueva_v}] restaurando la versión [Version v{item_seleccionado['version']}]. Responsable: {autor_rb.strip()}")
                            st.rerun()
                else:
                    st.info(f"La versión v{item_seleccionado['version']} es la versión activa actual. Para ejecutar un Rollback, elija una versión previa (como v1) en el selector superior.")
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
            inicializar_version_inicial_si_no_existe(
                doc_name=nombre_final,
                contenido_actual=doc_generado_md,
                autor=autor,
                comentario=f"Creación inicial mediante plantilla: {tipo_plantilla}"
            )
            st.success(f"Documento guardado e indexado exitosamente como **{nombre_final}** (Versión v1).")
            st.info("El Chat Copilot y la búsqueda analítica ya pueden responder preguntas sobre este nuevo procedimiento.")


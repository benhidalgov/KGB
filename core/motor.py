import duckdb
import pandas as pd
from core.configuracion import CSV_PATH


def ejecutar_consulta_sql(query_sql: str) -> pd.DataFrame:
    """Ejecuta una sentencia SQL en memoria sobre mantenimientos.csv mediante DuckDB."""
    try:
        con = duckdb.connect(database=':memory:')
        con.execute(f"CREATE TABLE mantenimientos AS SELECT * FROM read_csv_auto('{CSV_PATH}')")
        df = con.execute(query_sql).df()
        con.close()
        return df
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})


def buscar_servidores_duckdb(termino: str) -> pd.DataFrame:
    """Realiza busqueda estructurada de servidores en DuckDB por IP, serie, servidor o tecnico."""
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


def buscar_en_documentos(query: str, doc_store: dict) -> list:
    """Realiza una busqueda textual por tokens en el repositorio documental indexado."""
    resultados = []
    tokens = [t.lower() for t in query.split() if len(t) > 3]
    for doc_name, content in doc_store.items():
        score = sum(content.lower().count(token) for token in tokens)
        if score > 0 or any(token in doc_name.lower() for token in tokens):
            resultados.append((doc_name, content, score))
    resultados.sort(key=lambda x: x[2], reverse=True)
    return resultados


def generar_respuesta_asistente(prompt_usuario: str, doc_store: dict) -> str:
    """Genera la respuesta tecnica del Copilot correlacionando DuckDB y la base documental."""
    df_srv = buscar_servidores_duckdb(prompt_usuario)
    doc_matches = buscar_en_documentos(prompt_usuario, doc_store)

    if not df_srv.empty:
        total_coincidencias = len(df_srv)
        row = df_srv.iloc[0]
        estado_label = f"[{row['estado'].upper()}]"

        tabla_md = f"""### Registro de Infraestructura Encontrado ({total_coincidencias} resultado(s))

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
            tabla_md += f"\n\n*Nota: Existen {total_coincidencias - 1} registro(s) adicionales en la base de datos. Ver pestaña Analítica DuckDB.*"

        return tabla_md

    elif doc_matches:
        doc_name, content, _ = doc_matches[0]
        return f"""### Informacion Recuperada de Documentacion: {doc_name}

{content[:1400]}...

---
*Origen de datos: Base documental indexada*
"""
    else:
        return (
            f"No se encontraron registros de inventario ni procedimientos tecnicos para el termino: **{prompt_usuario}**.\n\n"
            "Verifique la referencia por numero de serie, identificador de servidor, direccion IP o manual tecnico."
        )

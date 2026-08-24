import re
import html
import unicodedata
import duckdb
import pandas as pd
from core.configuracion import CSV_PATH


def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando acentos, caracteres especiales y convirtiendo a minúsculas."""
    if not texto:
        return ""
    texto_sin_acentos = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto_sin_acentos.lower()


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
    """Realiza búsqueda estructurada de servidores en DuckDB por IP, serie, servidor, componente o técnico."""
    termino_sanitizado = normalizar_texto(termino.strip().replace("'", ""))
    if not termino_sanitizado:
        return pd.DataFrame()

    tokens = [t for t in termino_sanitizado.split() if len(t) >= 2]
    if not tokens:
        tokens = [termino_sanitizado]

    condiciones = []
    for token in tokens:
        condiciones.append(f"""(
            LOWER(servidor_id) LIKE LOWER('%{token}%')
            OR LOWER(numero_serie) LIKE LOWER('%{token}%')
            OR LOWER(ip) LIKE LOWER('%{token}%')
            OR LOWER(tecnico) LIKE LOWER('%{token}%')
            OR LOWER(descripcion) LIKE LOWER('%{token}%')
            OR LOWER(componente) LIKE LOWER('%{token}%')
            OR LOWER(vcloud_vm) LIKE LOWER('%{token}%')
        )""")

    where_clause = " OR ".join(condiciones)

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
        WHERE {where_clause}
        ORDER BY fecha DESC
    """
    try:
        return duckdb.sql(query_sql).df()
    except Exception:
        return pd.DataFrame()


def buscar_en_documentos(query: str, doc_store: dict) -> list:
    """Realiza una búsqueda textual insensible a mayúsculas y acentos con soporte de siglas cortas (>= 2 caracteres)."""
    resultados = []
    query_norm = normalizar_texto(query)
    tokens = [t for t in query_norm.split() if len(t) >= 2]

    if not tokens and query_norm:
        tokens = [query_norm]

    if not tokens:
        return []

    for doc_name, content in doc_store.items():
        content_norm = normalizar_texto(content)
        name_norm = normalizar_texto(doc_name)

        score = 0
        # 1. Coincidencia de frase exacta
        if query_norm in content_norm:
            score += 30

        # 2. Coincidencia en el nombre del documento
        for token in tokens:
            if token in name_norm:
                score += 20

        # 3. Frecuencia de tokens en el contenido
        for token in tokens:
            count = content_norm.count(token)
            if count > 0:
                score += count * 2

        if score > 0:
            resultados.append((doc_name, content, score))

    resultados.sort(key=lambda x: x[2], reverse=True)
    return resultados


def limpiar_encabezados_snippet(snippet: str) -> str:
    """Convierte encabezados Markdown (#, ##, ###) en texto negrita estructurado para no distorsionar el chat."""
    lineas = snippet.split("\n")
    lineas_limpias = []
    for line in lineas:
        stripped = line.strip()
        if stripped.startswith("#"):
            texto = re.sub(r"^#+\s*", "", stripped).strip()
            if texto:
                lineas_limpias.append(f"**{texto}**")
        elif stripped.startswith("---"):
            continue
        else:
            lineas_limpias.append(line)
    return "\n".join(lineas_limpias).strip()


def resaltar_terminos_en_html(texto: str, query: str) -> str:
    """Envuelve los términos de búsqueda con etiquetas de resaltado visual."""
    query_norm = normalizar_texto(query)
    tokens = [t for t in query_norm.split() if len(t) >= 2]
    if not tokens and query_norm:
        tokens = [query_norm]

    # Ordenar tokens por longitud descendente
    tokens = sorted(list(set(tokens)), key=len, reverse=True)

    resultado = texto
    for token in tokens:
        if not token.strip():
            continue
        # Búsqueda insensible a mayúsculas y acentos aproximada
        patron = re.compile(rf'(\b{re.escape(token)}\w*)', re.IGNORECASE)
        resultado = patron.sub(r'<span class="search-highlight">\1</span>', resultado)

    return resultado


def extraer_fragmento_relevante(content: str, query: str, max_chars: int = 900) -> str:
    """Extrae el fragmento más relevante del documento alrededor de la primera coincidencia del término."""
    query_norm = normalizar_texto(query)
    tokens = [t for t in query_norm.split() if len(t) >= 2]
    content_norm = normalizar_texto(content)

    primer_idx = -1
    for token in tokens:
        idx = content_norm.find(token)
        if idx != -1:
            if primer_idx == -1 or idx < primer_idx:
                primer_idx = idx

    if primer_idx == -1:
        return content[:max_chars].strip()

    inicio = max(0, primer_idx - 120)
    fin = min(len(content), inicio + max_chars)

    # Ajustar a inicio de párrafo o línea
    if inicio > 0:
        idx_nl = content.find("\n", inicio)
        if idx_nl != -1 and idx_nl < inicio + 60:
            inicio = idx_nl + 1

    fragmento = content[inicio:fin].strip()
    if inicio > 0:
        fragmento = "... " + fragmento
    if fin < len(content):
        fragmento = fragmento + " ..."

    return fragmento


def generar_respuesta_asistente(prompt_usuario: str, doc_store: dict) -> str:
    """Genera la respuesta técnica del Copilot en formato de tarjeta estructurada con resaltado visual."""
    df_srv = buscar_servidores_duckdb(prompt_usuario)
    doc_matches = buscar_en_documentos(prompt_usuario, doc_store)

    # Caso 1: Coincidencia en Inventario DuckDB
    if not df_srv.empty:
        total_coincidencias = len(df_srv)
        row = df_srv.iloc[0]
        estado_badge = "badge-ok" if row['estado'].lower() == "operativo" else "badge-warn" if "revision" in row['estado'].lower() else "badge-crit"

        desc_resaltada = resaltar_terminos_en_html(row['descripcion'], prompt_usuario)

        tabla_html = f"""<div class="search-result-card" style="border-left: 3.5px solid #10B981;">
    <div class="search-header-row">
        <div>
            <span class="badge-info">[Inventario CMDB]</span>
            <span class="search-doc-title" style="margin-left: 8px;">{row['servidor_id']}</span>
        </div>
        <div>
            <span class="{estado_badge}">[{row['estado'].upper()}]</span>
            <span class="badge-tag" style="margin-left: 6px;">{row['nivel_arquitectura']}</span>
        </div>
    </div>

| Atributo Técnico | Detalle Registrado |
| :--- | :--- |
| **Identificador Servidor** | `{row['servidor_id']}` |
| **Número de Serie** | `{row['numero_serie']}` |
| **Dirección IP / VM vCloud** | `{row['ip']}` ({row['vcloud_vm']}) |
| **Componente de Arquitectura** | {row['componente']} |
| **Fecha de Última Intervención** | {row['fecha']} |
| **Tipo de Mantenimiento** | {row['tipo_mantenimiento']} |
| **Técnico Responsable** | `{row['tecnico']}` |
| **Monitoreo Nagios / APM** | `{row['nagios_check']}` |

<div style="margin-top: 12px; font-size: 0.88rem; line-height: 1.5;">
    <b>Descripción de la Intervención:</b><br/>
    {desc_resaltada}
</div>

<div class="search-meta-footer">
    <span>Origen: DuckDB SQL Engine (data/mantenimientos.csv)</span>
    <span>{total_coincidencias} registro(s) encontrado(s)</span>
</div>
</div>"""

        if total_coincidencias > 1:
            tabla_html += f"\n\n*Nota: Existen {total_coincidencias - 1} registro(s) adicionales coincidentes. Consulte la pestaña Historial de Mantenimientos para ver la tabla completa.*"

        return tabla_html

    # Caso 2: Coincidencia en Documentación Técnica / Diagramas
    elif doc_matches:
        doc_name, content, score = doc_matches[0]
        fragmento_crudo = extraer_fragmento_relevante(content, prompt_usuario)
        fragmento_limpio = limpiar_encabezados_snippet(fragmento_crudo)
        fragmento_resaltado = resaltar_terminos_en_html(fragmento_limpio, prompt_usuario)

        tipo_badge = "[Diagrama]" if doc_name.startswith("DIAGRAMA__") else "[Documento]"
        score_label = "Alta" if score >= 20 else "Media"

        resultado_html = f"""<div class="search-result-card" style="border-left: 3.5px solid #6366F1;">
    <div class="search-header-row">
        <div>
            <span class="badge-info">{tipo_badge}</span>
            <span class="search-doc-title" style="margin-left: 8px;">{doc_name}</span>
        </div>
        <div>
            <span class="badge-ok">Relevancia: {score_label} ({score} pts)</span>
        </div>
    </div>
    
    <div style="font-size: 0.82rem; font-weight: 600; opacity: 0.85; margin-bottom: 6px;">Fragmento Recuperado:</div>
    <div class="search-snippet-content">{fragmento_resaltado}</div>

    <div class="search-meta-footer">
        <span>Origen: Repositorio Documental Indexado</span>
        <span>Consulte el archivo completo en la pestaña <b>Documentación Técnica</b></span>
    </div>
</div>"""

        # Si hay más documentos coincidentes, agregamos tarjetas secundarias compactas
        total_docs = len(doc_matches)
        if total_docs > 1:
            resultado_html += f"\n\n**Otros documentos coincidentes ({total_docs - 1}):**\n"
            for i, (sec_name, sec_content, sec_score) in enumerate(doc_matches[1:3], start=2):
                sec_frag = limpiar_encabezados_snippet(extraer_fragmento_relevante(sec_content, prompt_usuario, max_chars=250))
                sec_frag_res = resaltar_terminos_en_html(sec_frag, prompt_usuario)
                sec_badge = "[Diagrama]" if sec_name.startswith("DIAGRAMA__") else "[Documento]"
                resultado_html += f"""
<div style="background-color: rgba(128, 128, 128, 0.03); border: 1px solid rgba(128, 128, 128, 0.18); border-radius: 6px; padding: 10px; margin-top: 8px; font-size: 0.85rem;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
        <span><b>{sec_badge} {sec_name}</b></span>
        <span class="badge-tag">Score: {sec_score} pts</span>
    </div>
    <div style="font-size: 0.82rem; opacity: 0.9; line-height: 1.4;">{sec_frag_res}</div>
</div>"""

        return resultado_html

    # Caso 3: Sin coincidencias
    else:
        return f"""<div class="search-result-card" style="border-left: 3.5px solid #D97706;">
    <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 6px;">
        <span class="badge-warn">[SIN COINCIDENCIAS]</span> No se encontraron registros para: <code>{prompt_usuario}</code>
    </div>
    <div style="font-size: 0.85rem; opacity: 0.85; line-height: 1.5;">
        Verifique el término ingresado. Puede buscar por:
        <ul>
            <li><b>Identificador de Servidor:</b> <code>BALANCER001</code>, <code>DB-POSTGRES-01</code></li>
            <li><b>Número de Serie:</b> <code>SN-8842-A</code>, <code>SN-9912-B</code></li>
            <li><b>Dirección IP:</b> <code>10.24.0.125</code>, <code>10.24.0.126</code></li>
            <li><b>Tecnologías y Procedimientos:</b> <code>JWT</code>, <code>WSO2</code>, <code>Redis</code>, <code>Failover</code>, <code>Rollback</code></li>
        </ul>
    </div>
</div>"""

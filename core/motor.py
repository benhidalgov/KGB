import os
import re
import html
import unicodedata
import duckdb
import pandas as pd
from core.configuracion import CSV_PATH
from core.procesador import normalizar_titulo_display
from core.vault import obtener_secreto

_DUCKDB_CON = None
_DUCKDB_LAST_MTIME = -1.0
_DOC_STORE_NORM_CACHE = {}
_QUERY_RESPONSE_CACHE = {}
_MAX_CACHE_ENTRIES = 128


def limpiar_cache_consultas():
    """Invalida todas las caches en memoria del motor."""
    global _QUERY_RESPONSE_CACHE, _DOC_STORE_NORM_CACHE, _DUCKDB_LAST_MTIME
    _QUERY_RESPONSE_CACHE.clear()
    _DOC_STORE_NORM_CACHE.clear()
    _DUCKDB_LAST_MTIME = -1.0


def _obtener_conexion_duckdb():
    """Mantiene una conexión y tabla en memoria persistente en DuckDB con recarga automática."""
    global _DUCKDB_CON, _DUCKDB_LAST_MTIME
    current_mtime = os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0.0
    if _DUCKDB_CON is None or current_mtime != _DUCKDB_LAST_MTIME:
        _DUCKDB_CON = duckdb.connect(database=':memory:')
        if os.path.exists(CSV_PATH):
            _DUCKDB_CON.execute(f"CREATE OR REPLACE TABLE mantenimientos AS SELECT * FROM read_csv_auto('{CSV_PATH}')")
        _DUCKDB_LAST_MTIME = current_mtime
    return _DUCKDB_CON


def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""
    if not texto:
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8').lower()


def _obtener_texto_normalizado(doc_name: str, content: str) -> tuple[str, str]:
    c_len = len(content)
    cached = _DOC_STORE_NORM_CACHE.get(doc_name)
    if cached and cached[0] == c_len:
        return cached[1], cached[2]
    name_norm, content_norm = normalizar_texto(doc_name), normalizar_texto(content)
    _DOC_STORE_NORM_CACHE[doc_name] = (c_len, name_norm, content_norm)
    return name_norm, content_norm


def ejecutar_consulta_sql(query_sql: str) -> pd.DataFrame:
    """Ejecuta una sentencia SQL en memoria sobre mantenimientos.csv mediante DuckDB."""
    try:
        return _obtener_conexion_duckdb().execute(query_sql).df()
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})


def buscar_servidores_duckdb(termino: str) -> pd.DataFrame:
    """Realiza búsqueda estructurada en memoria RAM de servidores en DuckDB."""
    t_norm = normalizar_texto(termino.strip().replace("'", ""))
    if not t_norm:
        return pd.DataFrame()

    tokens = [t for t in t_norm.split() if len(t) >= 2] or [t_norm]
    cols = ["servidor_id", "numero_serie", "ip", "tecnico", "descripcion", "componente", "vcloud_vm"]
    condiciones = [" OR ".join(f"LOWER({c}) LIKE LOWER('%{t}%')" for c in cols) for t in tokens]

    query_sql = f"""
        SELECT servidor_id, numero_serie, ip, vcloud_vm, nivel_arquitectura, componente, fecha, tipo_mantenimiento, tecnico, descripcion, estado, nagios_check
        FROM mantenimientos
        WHERE {' OR '.join(f'({c})' for c in condiciones)}
        ORDER BY fecha DESC
    """
    try:
        return _obtener_conexion_duckdb().execute(query_sql).df()
    except Exception:
        return pd.DataFrame()


def buscar_en_documentos(query: str, doc_store: dict) -> list:
    """Realiza una búsqueda textual acelerada por cache insensible a mayúsculas y acentos."""
    query_norm = normalizar_texto(query)
    tokens = [t for t in query_norm.split() if len(t) >= 2] or ([query_norm] if query_norm else [])
    if not tokens:
        return []

    resultados = []
    for doc_name, content in doc_store.items():
        name_norm, content_norm = _obtener_texto_normalizado(doc_name, content)
        score = (30 if query_norm in content_norm else 0) + sum(20 for t in tokens if t in name_norm) + sum(content_norm.count(t) * 2 for t in tokens)
        if score > 0:
            resultados.append((doc_name, content, score))

    resultados.sort(key=lambda x: x[2], reverse=True)
    return resultados


def limpiar_encabezados_snippet(snippet: str) -> str:
    """Convierte encabezados Markdown (#, ##) en texto estructurado en negrita."""
    lineas = []
    for line in snippet.split("\n"):
        s = line.strip()
        if s.startswith("#"):
            txt = re.sub(r"^#+\s*", "", s).strip()
            if txt:
                lineas.append(f"**{txt}**")
        elif not s.startswith("---"):
            lineas.append(line)
    return "\n".join(lineas).strip()


def resaltar_terminos_en_html(texto: str, query: str) -> str:
    """Envuelve los términos de búsqueda con etiquetas de resaltado visual."""
    tokens = sorted(list(set([t for t in normalizar_texto(query).split() if len(t) >= 2] or ([normalizar_texto(query)] if query else []))), key=len, reverse=True)
    res = texto
    for token in tokens:
        if token.strip():
            res = re.sub(rf'(\b{re.escape(token)}\w*)', r'<span class="search-highlight">\1</span>', res, flags=re.IGNORECASE)
    return res


def extraer_fragmento_relevante(content: str, query: str, max_chars: int = 900) -> str:
    """Extrae el fragmento más relevante del documento alrededor de la primera coincidencia."""
    tokens = [t for t in normalizar_texto(query).split() if len(t) >= 2]
    content_norm = normalizar_texto(content)

    idx_list = [content_norm.find(t) for t in tokens if content_norm.find(t) != -1]
    primer_idx = min(idx_list) if idx_list else -1

    if primer_idx == -1:
        return content[:max_chars].strip()

    inicio = max(0, primer_idx - 120)
    fin = min(len(content), inicio + max_chars)
    if inicio > 0:
        idx_nl = content.find("\n", inicio)
        if idx_nl != -1 and idx_nl < inicio + 60:
            inicio = idx_nl + 1

    frag = content[inicio:fin].strip()
    return f"{'... ' if inicio > 0 else ''}{frag}{' ...' if fin < len(content) else ''}"


def construir_contexto_rag(prompt_usuario: str, df_srv: pd.DataFrame, doc_matches: list) -> str:
    """Compila la evidencia técnica recuperada de DuckDB y de la base documental para inyección en Gemini."""
    secciones = []
    if df_srv is not None and not df_srv.empty:
        lineas = ["### EVIDENCIA DE INVENTARIO Y MANTENIMIENTOS (DuckDB CMDB):"]
        for _, row in df_srv.head(4).iterrows():
            lineas.append(
                f"- Servidor: {row.get('servidor_id', '-')} | IP: {row.get('ip', '-')} | VM: {row.get('vcloud_vm', '-')} | "
                f"Capa: {row.get('nivel_arquitectura', '-')} | Componente: {row.get('componente', '-')} | "
                f"Estado: {row.get('estado', '-')} | Mantenimiento: {row.get('tipo_mantenimiento', '-')} ({row.get('fecha', '-')}) | "
                f"Técnico: {row.get('tecnico', '-')} | Nagios: {row.get('nagios_check', '-')} | Detalle: {row.get('descripcion', '-')}"
            )
        secciones.append("\n".join(lineas))

    if doc_matches:
        lineas_docs = ["### EVIDENCIA DE BASE DE CONOCIMIENTO TÉCNICA:"]
        for doc_name, content, score in doc_matches[:3]:
            frag = extraer_fragmento_relevante(content, prompt_usuario, max_chars=600)
            lineas_docs.append(f"**Documento [{doc_name}] (Score {score} pts):**\n{frag}\n")
        secciones.append("\n".join(lineas_docs))

    return "\n\n".join(secciones) or "No se encontraron coincidencias directas en la CMDB ni en los documentos técnicos locales."


def consultar_gemini_rag(prompt_usuario: str, contexto_rag: str, api_key: str) -> tuple[bool, str, str]:
    """Ejecuta la inferencia RAG sobre el SDK oficial de Google Gemini respetando directrices."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=25000))
        instruccion = (
            "Eres el Copilot de Infraestructura y Operaciones, un Ingeniero Principal de Infraestructura senior corporativo.\n"
            "DIRECTRICES ESTRICTAS:\n"
            "1. PROHIBICION TOTAL DE EMOJIS: Queda estrictamente prohibido incluir cualquier emoji o icono visual Unicode.\n"
            "2. PROHIBICION TOTAL DE LA PALABRA 'AIOps': Utiliza terminos como 'Operaciones', 'Infraestructura' o 'Consola de Operaciones'.\n"
            "3. ZERO HALLUCINATIONS: Basa tus respuestas unicamente en la evidencia provista en el contexto.\n"
            "4. ESTILO CORPORATIVO: Sobrio, formal, tablas Markdown y bloques de configuracion cuando sea pertinente."
        )

        prompt_full = f"CONSULTA DEL OPERADOR:\n{prompt_usuario}\n\nCONTEXTO TÉCNICO RECUPERADO (CMDB Y DOCUMENTOS):\n{contexto_rag}\n\nInstrucción: Proporciona una respuesta técnica completa y estructurada basándote en el contexto."

        for modelo in ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]:
            try:
                res = client.models.generate_content(
                    model=modelo,
                    contents=prompt_full,
                    config=types.GenerateContentConfig(system_instruction=instruccion, temperature=0.2)
                )
                if res and res.text:
                    return True, res.text.strip(), modelo
            except Exception as e:
                err_s = str(e)
                if "403" in err_s:
                    return False, "403 PERMISSION_DENIED: Sin permisos en Google Cloud / AI Studio", ""
                if "429" in err_s:
                    return False, "429 Cuota agotada en la API de Google", ""
                continue

        return False, "Servicio Gemini temporalmente saturado", ""
    except Exception as e:
        return False, str(e)[:120], ""


def generar_respuesta_asistente_local(prompt_usuario: str, doc_store: dict, df_srv: pd.DataFrame = None, doc_matches: list = None) -> str:
    """Genera la respuesta técnica determinista del motor local autónomo (DuckDB + Text Search)."""
    if df_srv is None:
        df_srv = buscar_servidores_duckdb(prompt_usuario)
    if doc_matches is None:
        doc_matches = buscar_en_documentos(prompt_usuario, doc_store)

    if df_srv is not None and not df_srv.empty:
        total = len(df_srv)
        row = df_srv.iloc[0]
        st_badge = "badge-ok" if row['estado'].lower() == "operativo" else ("badge-warn" if "revision" in row['estado'].lower() else "badge-crit")
        desc = resaltar_terminos_en_html(row['descripcion'], prompt_usuario)

        html_out = f"""<div class="search-result-card" style="border-left: 3.5px solid #10B981;">
    <div class="search-header-row">
        <div><span class="badge-info">[Inventario CMDB]</span><span class="search-doc-title" style="margin-left: 8px;">{row['servidor_id']}</span></div>
        <div><span class="{st_badge}">[{row['estado'].upper()}]</span><span class="badge-tag" style="margin-left: 6px;">{row['nivel_arquitectura']}</span></div>
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

<div style="margin-top: 12px; font-size: 0.88rem; line-height: 1.5;"><b>Descripción de la Intervención:</b><br/>{desc}</div>
<div class="search-meta-footer"><span>Motor: Local Autónomo | DuckDB + MarkItDown</span><span>{total} registro(s) encontrado(s)</span></div>
</div>"""
        if total > 1:
            html_out += f"\n\n*Nota: Existen {total - 1} registro(s) adicionales coincidentes. Consulte la pestaña Historial de Mantenimientos.*"
        return html_out

    if doc_matches:
        doc_name, content, score = doc_matches[0]
        frag = resaltar_terminos_en_html(limpiar_encabezados_snippet(extraer_fragmento_relevante(content, prompt_usuario)), prompt_usuario)
        tipo_badge = "[Diagrama]" if doc_name.startswith("DIAGRAMA__") else "[Documento]"
        score_label = "Alta" if score >= 20 else "Media"

        html_out = f"""<div class="search-result-card" style="border-left: 3.5px solid #6366F1;">
    <div class="search-header-row">
        <div><span class="badge-info">{tipo_badge}</span><span class="search-doc-title" style="margin-left: 8px;">{normalizar_titulo_display(doc_name)}</span><span style="font-family: monospace; font-size: 0.72rem; opacity: 0.65; margin-left: 6px;">({doc_name})</span></div>
        <div><span class="badge-ok">Relevancia: {score_label} ({score} pts)</span></div>
    </div>
    <div style="font-size: 0.82rem; font-weight: 600; opacity: 0.85; margin-bottom: 6px;">Fragmento Recuperado:</div>
    <div class="search-snippet-content">{frag}</div>
    <div class="search-meta-footer"><span>Motor: Local Autónomo | DuckDB + MarkItDown</span><span>Consulte el archivo en la pestaña <b>Documentación Técnica</b></span></div>
</div>"""
        if len(doc_matches) > 1:
            html_out += f"\n\n**Otros documentos coincidentes ({len(doc_matches) - 1}):**\n"
            for sec_name, sec_content, sec_score in doc_matches[1:3]:
                sec_frag = resaltar_terminos_en_html(limpiar_encabezados_snippet(extraer_fragmento_relevante(sec_content, prompt_usuario, max_chars=250)), prompt_usuario)
                sec_b = "[Diagrama]" if sec_name.startswith("DIAGRAMA__") else "[Documento]"
                html_out += f"""\n<div style="background-color: rgba(128, 128, 128, 0.03); border: 1px solid rgba(128, 128, 128, 0.18); border-radius: 6px; padding: 10px; margin-top: 8px; font-size: 0.85rem;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
        <span><b>{sec_b} {normalizar_titulo_display(sec_name)}</b> <span style="font-family: monospace; font-size: 0.72rem; opacity: 0.65;">({sec_name})</span></span>
        <span class="badge-tag">Score: {sec_score} pts</span>
    </div>
    <div style="font-size: 0.82rem; opacity: 0.9; line-height: 1.4;">{sec_frag}</div>
</div>"""
        return html_out

    return f"""<div class="search-result-card" style="border-left: 3.5px solid #D97706;">
    <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 6px;"><span class="badge-warn">[SIN COINCIDENCIAS]</span> No se encontraron registros para: <code>{prompt_usuario}</code></div>
    <div style="font-size: 0.85rem; opacity: 0.85; line-height: 1.5;">Verifique el término. Puede buscar por Servidor (<code>BALANCER001</code>), N° Serie (<code>SN-8842-A</code>), IP (<code>10.24.0.125</code>) o Concepto (<code>JWT</code>, <code>Failover</code>).</div>
    <div class="search-meta-footer"><span>Motor: Local Autónomo | DuckDB + MarkItDown</span><span>0 registros</span></div>
</div>"""


def generar_respuesta_asistente(prompt_usuario: str, doc_store: dict) -> str:
    """Genera la respuesta técnica del Copilot con aceleración por caché en RAM."""
    prompt_limpio = prompt_usuario.strip()
    if not prompt_limpio:
        return ""

    mtime_csv = os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0.0
    api_key_gemini = obtener_secreto("GEMINI_API_KEY", "")
    has_api_key = bool(api_key_gemini and api_key_gemini.strip())

    cache_key = f"{normalizar_texto(prompt_limpio)}::{has_api_key}::{mtime_csv}::{len(doc_store)}"
    if cache_key in _QUERY_RESPONSE_CACHE:
        return _QUERY_RESPONSE_CACHE[cache_key]

    df_srv = buscar_servidores_duckdb(prompt_usuario)
    doc_matches = buscar_en_documentos(prompt_usuario, doc_store)

    if has_api_key:
        contexto = construir_contexto_rag(prompt_usuario, df_srv, doc_matches)
        ok_gemini, resp_texto, modelo = consultar_gemini_rag(prompt_usuario, contexto, api_key_gemini)
        if ok_gemini:
            resultado = f"""<div class="search-result-card" style="border-left: 3.5px solid #10B981;">
    <div class="search-header-row">
        <div><span class="badge-ok">[OK]</span><span class="badge-info" style="margin-left: 6px;">[RAG CONTEXTUAL]</span><span class="search-doc-title" style="margin-left: 8px;">Análisis de Infraestructura</span></div>
        <div><span class="badge-tag">Gemini Inferencia</span></div>
    </div>
{resp_texto}
<div class="search-meta-footer"><span>Motor: Google {modelo} | RAG Contextual</span><span>Evidencia: {len(df_srv)} CMDB + {len(doc_matches)} docs</span></div>
</div>"""
        else:
            resp_local = generar_respuesta_asistente_local(prompt_usuario, doc_store, df_srv, doc_matches)
            resultado = f'<div style="font-size:0.75rem; background-color: rgba(217, 119, 6, 0.08); border: 1px solid #D97706; border-radius: 4px; padding: 6px 10px; margin-bottom: 8px;"><span class="badge-warn">[FALLBACK LOCAL]</span> Servicio Gemini no disponible ({resp_texto}). Conmutando a motor local autónomo.</div>' + resp_local
    else:
        resultado = generar_respuesta_asistente_local(prompt_usuario, doc_store, df_srv, doc_matches)

    if len(_QUERY_RESPONSE_CACHE) >= _MAX_CACHE_ENTRIES:
        _QUERY_RESPONSE_CACHE.pop(next(iter(_QUERY_RESPONSE_CACHE)))
    _QUERY_RESPONSE_CACHE[cache_key] = resultado
    return resultado

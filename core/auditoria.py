import os
import json
import html
import shutil
import difflib
import hashlib
import functools
from datetime import datetime
import pandas as pd
import streamlit as st
from excel_cleaner import procesar_excel_limpio
from core.configuracion import HISTORY_DIR, AUDIT_LOG_PATH, DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR


def calcular_sha256_texto(texto: str) -> str:
    """Calcula el hash criptográfico SHA-256 de una cadena de texto en UTF-8."""
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest() if texto is not None else ""


def _meta_path(doc_name: str) -> str:
    return os.path.join(HISTORY_DIR, doc_name, "metadata.json")


def _cargar_meta_raw(doc_name: str) -> list:
    p = _meta_path(doc_name)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _guardar_meta(doc_name: str, data: list):
    p = _meta_path(doc_name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@functools.lru_cache(maxsize=512)
def _obtener_historial_versiones_cached(doc_name: str, mtime: float) -> list:
    return _cargar_meta_raw(doc_name)


def obtener_historial_versiones(doc_name: str) -> list:
    """Obtiene el registro cronológico de versiones de un documento con cache basada en mtime."""
    p = _meta_path(doc_name)
    mtime = os.path.getmtime(p) if os.path.exists(p) else 0.0
    return list(_obtener_historial_versiones_cached(doc_name, mtime))


@functools.lru_cache(maxsize=512)
def _obtener_fecha_carga_cached(doc_name: str, mtime: float):
    hist = obtener_historial_versiones(doc_name)
    if hist and "timestamp" in hist[0]:
        try:
            return datetime.strptime(str(hist[0]["timestamp"]).strip().split()[0], "%Y-%m-%d").date()
        except Exception:
            pass

    for ruta_base in [DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR]:
        p = os.path.join(ruta_base, doc_name)
        if os.path.exists(p):
            try:
                return datetime.fromtimestamp(os.path.getmtime(p)).date()
            except Exception:
                pass
    return datetime.now().date()


def obtener_fecha_carga_documento(doc_name: str):
    """Obtiene la fecha (date) de carga o creación inicial de un documento con cache basada en mtime."""
    p = _meta_path(doc_name)
    mtime = os.path.getmtime(p) if os.path.exists(p) else 0.0
    return _obtener_fecha_carga_cached(doc_name, mtime)


def registrar_evento_auditoria(doc_name: str, accion: str, version_ant: int, version_nueva: int, autor: str, motivo: str):
    """Registra un evento inmutable de trazabilidad en el log central de auditoría."""
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
        "motivo_justificacion": motivo.strip() if motivo and motivo.strip() else "Sin justificación"
    }
    eventos.append(evento)
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(eventos, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def generar_diff_texto(texto_ant: str, texto_nuevo: str, label_ant: str = "Version A", label_nuevo: str = "Version B") -> str:
    """Genera una representación diff unificada para comparar dos versiones."""
    diff = difflib.unified_diff(
        texto_ant.splitlines(keepends=True),
        texto_nuevo.splitlines(keepends=True),
        fromfile=label_ant,
        tofile=label_nuevo,
        n=2
    )
    diff_text = "".join(diff)
    return diff_text if diff_text.strip() else "No se detectaron diferencias de contenido entre estas dos versiones."


def verificar_integridad_snapshot(doc_name: str, version_num: int) -> dict:
    """Verifica si el snapshot en disco coincide exactamente con el hash SHA-256 registrado."""
    for entry in obtener_historial_versiones(doc_name):
        if entry.get("version") == version_num:
            snap_file = entry.get("archivo_snapshot")
            expected_hash = entry.get("sha256")
            if not snap_file:
                return {"valido": False, "motivo": "Sin referencia a archivo snapshot"}
            snap_path = os.path.join(HISTORY_DIR, doc_name, snap_file)
            if not os.path.exists(snap_path):
                return {"valido": False, "motivo": "Archivo snapshot no encontrado"}
            with open(snap_path, "r", encoding="utf-8") as f:
                actual_hash = calcular_sha256_texto(f.read())
            if not expected_hash:
                return {"valido": True, "motivo": "Sin firma previa", "sha256": actual_hash}
            es_valido = (actual_hash == expected_hash)
            return {"valido": es_valido, "motivo": "Integridad verificada" if es_valido else "Hash no coincide", "sha256": actual_hash}
    return {"valido": False, "motivo": f"Version {version_num} no encontrada"}


def inicializar_version_inicial_si_no_existe(doc_name: str, contenido_actual: str, autor: str = "Sistema", comentario: str = "Versión base inicial") -> list:
    """Inicializa la versión v1 si no existe registro histórico previo con su firma SHA-256."""
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    if not os.path.exists(os.path.join(doc_hist_dir, "metadata.json")):
        os.makedirs(doc_hist_dir, exist_ok=True)
        v1_name = "v1.md"
        with open(os.path.join(doc_hist_dir, v1_name), "w", encoding="utf-8") as f:
            f.write(contenido_actual)

        excel_snap = None
        orig_p = os.path.join(DOCS_DIR, doc_name)
        if doc_name.lower().endswith(('.xlsx', '.xls')) and os.path.exists(orig_p):
            excel_snap = f"v1_{doc_name}"
            shutil.copy2(orig_p, os.path.join(doc_hist_dir, excel_snap))

        historial = [{
            "version": 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "autor": autor,
            "comentario": comentario,
            "archivo_snapshot": v1_name,
            "archivo_excel_snapshot": excel_snap,
            "sha256": calcular_sha256_texto(contenido_actual),
            "caracteres": len(contenido_actual)
        }]
        _guardar_meta(doc_name, historial)
        registrar_evento_auditoria(doc_name=doc_name, accion="CREACION", version_ant=0, version_nueva=1, autor=autor, motivo=comentario)
        return historial
    return obtener_historial_versiones(doc_name)


def guardar_nueva_version(doc_name: str, nuevo_contenido: str, autor: str, comentario: str, doc_store: dict) -> int:
    """Guarda una nueva revisión incrementando la versión (vN+1) registrando SHA-256."""
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    os.makedirs(doc_hist_dir, exist_ok=True)
    nuevo_hash = calcular_sha256_texto(nuevo_contenido)
    historial = obtener_historial_versiones(doc_name)

    if historial and historial[-1].get("sha256") == nuevo_hash:
        return len(historial)

    if not historial:
        contenido_prev = doc_store.get(doc_name, nuevo_contenido)
        with open(os.path.join(doc_hist_dir, "v1.md"), "w", encoding="utf-8") as f:
            f.write(contenido_prev)
        historial = [{
            "version": 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "autor": "Sistema / Creador",
            "comentario": "Versión base inicial",
            "archivo_snapshot": "v1.md",
            "sha256": calcular_sha256_texto(contenido_prev),
            "caracteres": len(contenido_prev)
        }]

    version_ant = len(historial)
    nueva_v = version_ant + 1
    snap_name = f"v{nueva_v}.md"
    with open(os.path.join(doc_hist_dir, snap_name), "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

    historial.append({
        "version": nueva_v,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "autor": (autor or "Técnico").strip(),
        "comentario": (comentario or "Actualización de contenido").strip(),
        "archivo_snapshot": snap_name,
        "sha256": nuevo_hash,
        "caracteres": len(nuevo_contenido)
    })
    _guardar_meta(doc_name, historial)

    ext = os.path.splitext(doc_name)[1].lower()
    target_path = os.path.join(DOCS_DIR, f"{os.path.splitext(doc_name)[0]}.md" if ext in ('.docx', '.pdf', '.pptx', '.xlsx', '.xls') else doc_name)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

    doc_store[doc_name] = nuevo_contenido
    if ext in ('.docx', '.pdf', '.pptx', '.xlsx', '.xls'):
        doc_store[os.path.basename(target_path)] = nuevo_contenido

    accion = "ROLLBACK" if "rollback" in (comentario or "").lower() else "EDICION"
    registrar_evento_auditoria(doc_name=doc_name, accion=accion, version_ant=version_ant, version_nueva=nueva_v, autor=autor, motivo=comentario)
    return nueva_v


def guardar_nueva_version_excel(doc_name: str, sheet_name: str, df_nuevo: pd.DataFrame, autor: str, comentario: str, doc_store: dict) -> int:
    """Guarda una nueva versión de un libro Excel modificando la hoja seleccionada."""
    excel_path = os.path.join(DOCS_DIR, doc_name)
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    os.makedirs(doc_hist_dir, exist_ok=True)
    historial = obtener_historial_versiones(doc_name) or inicializar_version_inicial_si_no_existe(doc_name, doc_store.get(doc_name, ""))

    version_ant = len(historial)
    nueva_v = version_ant + 1
    snap_excel = f"v{nueva_v}_{doc_name}"

    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_nuevo.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_nuevo.to_excel(writer, sheet_name=sheet_name, index=False)

    shutil.copy2(excel_path, os.path.join(doc_hist_dir, snap_excel))
    nuevo_md = procesar_excel_limpio(excel_path)
    snap_md = f"v{nueva_v}.md"
    with open(os.path.join(doc_hist_dir, snap_md), "w", encoding="utf-8") as f:
        f.write(nuevo_md)

    doc_store[doc_name] = nuevo_md
    historial.append({
        "version": nueva_v,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "autor": (autor or "Técnico").strip(),
        "comentario": f"[{sheet_name}] {(comentario or f'Edición de hoja {sheet_name}').strip()}",
        "archivo_snapshot": snap_md,
        "archivo_excel_snapshot": snap_excel,
        "sha256": calcular_sha256_texto(nuevo_md),
        "caracteres": len(nuevo_md)
    })
    _guardar_meta(doc_name, historial)
    registrar_evento_auditoria(doc_name=doc_name, accion="EDICION_EXCEL", version_ant=version_ant, version_nueva=nueva_v, autor=autor, motivo=f"[{sheet_name}] {comentario}")
    return nueva_v


def obtener_contenido_version(doc_name: str, snapshot_fname: str) -> str:
    """Recupera el contenido exacto de un snapshot histórico."""
    snap_path = os.path.join(HISTORY_DIR, doc_name, snapshot_fname)
    if os.path.exists(snap_path):
        with open(snap_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


@st.cache_data(show_spinner=False)
def obtener_nombres_hojas_excel(filepath: str, mtime: float = 0.0) -> list:
    """Obtiene los nombres de las hojas de un libro Excel con cache."""
    try:
        return pd.ExcelFile(filepath).sheet_names
    except Exception:
        return ["Hoja1"]


@st.cache_data(show_spinner=False)
def cargar_hoja_excel_dataframe(filepath: str, sheet_name: str, mtime: float = 0.0) -> pd.DataFrame:
    """Carga una hoja de cálculo Excel en un DataFrame normalizado."""
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name).dropna(how='all', axis=0).dropna(how='all', axis=1)
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d')
        return df.fillna('')
    except Exception as e:
        return pd.DataFrame({"Mensaje": [f"No se pudo cargar la hoja: {e}"]})


def obtener_bytes_snapshot(doc_name: str, filename_snapshot: str) -> bytes | None:
    """Recupera los bytes binarios de un snapshot histórico."""
    if not filename_snapshot:
        return None
    snap_path = os.path.join(HISTORY_DIR, doc_name, filename_snapshot)
    if os.path.exists(snap_path):
        with open(snap_path, "rb") as f:
            return f.read()
    return None


def generar_diff_lado_a_lado_html(texto_ant: str, texto_nuevo: str, label_ant: str = "Versión A", label_nuevo: str = "Versión B") -> dict:
    """Genera una vista visual diff lado a lado en HTML Theme-Safe con conteo de cambios."""
    todas_ant = texto_ant.splitlines()
    todas_nuevo = texto_nuevo.splitlines()
    MAX_DIFF = 400
    lineas_ant, lineas_nuevo = todas_ant[:MAX_DIFF], todas_nuevo[:MAX_DIFF]
    es_truncado = len(todas_ant) > MAX_DIFF or len(todas_nuevo) > MAX_DIFF

    matcher = difflib.SequenceMatcher(None, lineas_ant, lineas_nuevo)
    filas_html = []
    adiciones = eliminaciones = modificaciones = sin_cambio = 0

    def _cell(num, txt, cls=""):
        t = html.escape(txt) if txt else "&nbsp;"
        n = str(num) if num != "" else ""
        return f'<div class="diff-cell {cls}"><span class="diff-num">{n}</span><span class="diff-text">{t}</span></div>'

    for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
        ca, cb = ahi - alo, bhi - blo
        if tag == 'equal':
            sin_cambio += ca
            for i in range(ca):
                filas_html.append(f'<div class="diff-row">{_cell(alo + i + 1, lineas_ant[alo + i])}{_cell(blo + i + 1, lineas_nuevo[blo + i])}</div>')
        elif tag == 'replace':
            modificaciones += max(ca, cb)
            for i in range(max(ca, cb)):
                l = _cell(alo + i + 1, f"- {lineas_ant[alo + i]}", "diff-del") if i < ca else _cell("", "", "diff-empty")
                r = _cell(blo + i + 1, f"+ {lineas_nuevo[blo + i]}", "diff-add") if i < cb else _cell("", "", "diff-empty")
                filas_html.append(f'<div class="diff-row">{l}{r}</div>')
        elif tag == 'delete':
            eliminaciones += ca
            for i in range(ca):
                filas_html.append(f'<div class="diff-row">{_cell(alo + i + 1, f"- {lineas_ant[alo + i]}", "diff-del")}{_cell("", "", "diff-empty")}</div>')
        elif tag == 'insert':
            adiciones += cb
            for i in range(cb):
                filas_html.append(f'<div class="diff-row">{_cell("", "", "diff-empty")}{_cell(blo + i + 1, f"+ {lineas_nuevo[blo + i]}", "diff-add")}</div>')

    tag_truncado = '<span class="badge-warn">[Muestra: 400 líneas]</span>' if es_truncado else ''
    body_html = "".join(filas_html) or '<div style="padding: 16px; opacity: 0.8;">No hay contenido que comparar.</div>'

    diff_html = f"""<div class="diff-container">
    <div class="diff-stats-bar">
        <div class="diff-stat-group">
            <span class="badge-ok">+{adiciones} adiciones</span>
            <span class="badge-crit">-{eliminaciones} eliminaciones</span>
            <span class="badge-warn">~{modificaciones} modificaciones</span>
            <span class="badge-tag">{sin_cambio} líneas iguales</span>
            {tag_truncado}
        </div>
        <div><span class="badge-info">Comparación Lado a Lado</span></div>
    </div>
    <div class="diff-header-row">
        <div class="diff-header-col">[Versión Base] {label_ant}</div>
        <div class="diff-header-col">[Versión Comparada] {label_nuevo}</div>
    </div>
    <div class="diff-body">{body_html}</div>
</div>"""

    return {"html": diff_html, "stats": {"adiciones": adiciones, "eliminaciones": eliminaciones, "modificaciones": modificaciones, "sin_cambio": sin_cambio, "total_lineas": len(filas_html)}}


@functools.lru_cache(maxsize=16)
def _obtener_todos_los_eventos_auditoria_cached(mtime: float) -> list:
    if os.path.exists(AUDIT_LOG_PATH):
        try:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                return list(reversed(json.load(f)))
        except Exception:
            return []
    return []


def obtener_todos_los_eventos_auditoria() -> list:
    """Recupera todos los eventos registrados en el log global de auditoría en orden cronológico inverso."""
    mtime = os.path.getmtime(AUDIT_LOG_PATH) if os.path.exists(AUDIT_LOG_PATH) else 0.0
    return list(_obtener_todos_los_eventos_auditoria_cached(mtime))


def generar_timeline_versiones_html(historial: list) -> str:
    """Genera una vista visual de línea de tiempo cronológica para el historial de versiones."""
    if not historial:
        return ""
    items_html = []
    for item in reversed(historial):
        v_num = item.get("version", 1)
        ts = item.get("timestamp", "N/A")
        autor = item.get("autor", "Desconocido")
        comentario = item.get("comentario", "")
        caracteres = item.get("caracteres", 0)

        badge_tipo = '<span class="badge-crit">[ROLLBACK]</span>' if "rollback" in comentario.lower() else ('<span class="badge-ok">[BASE v1]</span>' if v_num == 1 else '<span class="badge-info">[REVISIÓN]</span>')
        items_html.append(f"""
        <div class="version-timeline-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <div>{badge_tipo}<span style="font-weight: 700; font-size: 0.95rem; margin-left: 6px;">Versión v{v_num}</span></div>
                <div style="font-size: 0.8rem; opacity: 0.8;">{ts}</div>
            </div>
            <div style="font-size: 0.88rem; margin: 4px 0;"><b>Motivo:</b> {html.escape(comentario)}</div>
            <div style="font-size: 0.78rem; opacity: 0.75; display: flex; justify-content: space-between; margin-top: 6px; border-top: 1px dashed rgba(128,128,128,0.2); padding-top: 4px;">
                <span><b>Editor:</b> {html.escape(autor)}</span>
                <span><b>Tamaño:</b> {caracteres} caracteres</span>
            </div>
        </div>""")
    return f'<div class="version-timeline-container">{"".join(items_html)}</div>'

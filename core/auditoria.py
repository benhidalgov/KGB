import os
import json
import html
import shutil
import difflib
from datetime import datetime
import pandas as pd
from excel_cleaner import procesar_excel_limpio
from core.configuracion import HISTORY_DIR, AUDIT_LOG_PATH, DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR


def obtener_fecha_carga_documento(doc_name: str):
    """Obtiene la fecha (date) de carga o creacion inicial de un documento."""
    hist = obtener_historial_versiones(doc_name)
    if hist and len(hist) > 0 and "timestamp" in hist[0]:
        try:
            ts_str = str(hist[0]["timestamp"]).strip()
            fecha_str = ts_str.split()[0]
            return datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except Exception:
            pass

    for ruta_base in [DOCS_DIR, ASSETS_DIR, ORIGINALS_DIR]:
        p = os.path.join(ruta_base, doc_name)
        if os.path.exists(p):
            try:
                mtime = os.path.getmtime(p)
                return datetime.fromtimestamp(mtime).date()
            except Exception:
                pass

    return datetime.now().date()


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


def inicializar_version_inicial_si_no_existe(doc_name: str, contenido_actual: str, autor: str = "Sistema", comentario: str = "Versión base inicial") -> list:
    """Inicializa la version v1 si no existe registro historico previo."""
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    meta_path = os.path.join(doc_hist_dir, "metadata.json")
    if not os.path.exists(meta_path):
        os.makedirs(doc_hist_dir, exist_ok=True)
        v1_filename = "v1.md"
        with open(os.path.join(doc_hist_dir, v1_filename), "w", encoding="utf-8") as f:
            f.write(contenido_actual)

        snapshot_excel_fname = None
        doc_orig_path = os.path.join(DOCS_DIR, doc_name)
        if doc_name.lower().endswith(('.xlsx', '.xls')) and os.path.exists(doc_orig_path):
            snapshot_excel_fname = f"v1_{doc_name}"
            shutil.copy2(doc_orig_path, os.path.join(doc_hist_dir, snapshot_excel_fname))

        historial = [
            {
                "version": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "autor": autor,
                "comentario": comentario,
                "archivo_snapshot": v1_filename,
                "archivo_excel_snapshot": snapshot_excel_fname,
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


def guardar_nueva_version(doc_name: str, nuevo_contenido: str, autor: str, comentario: str, doc_store: dict) -> int:
    """Guarda una nueva revision incrementando la version (vN+1) y preservando snapshots inmutables."""
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    os.makedirs(doc_hist_dir, exist_ok=True)
    meta_path = os.path.join(doc_hist_dir, "metadata.json")

    historial = obtener_historial_versiones(doc_name)
    if not historial:
        contenido_previo = doc_store.get(doc_name, nuevo_contenido)
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

    target_path = os.path.join(DOCS_DIR, doc_name)
    ext = os.path.splitext(doc_name)[1].lower()
    if ext in ('.docx', '.pdf', '.pptx', '.xlsx', '.xls'):
        md_name = f"{os.path.splitext(doc_name)[0]}.md"
        target_path = os.path.join(DOCS_DIR, md_name)
        doc_store[md_name] = nuevo_contenido
    else:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)

    doc_store[doc_name] = nuevo_contenido

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


def guardar_nueva_version_excel(doc_name: str, sheet_name: str, df_nuevo: pd.DataFrame, autor: str, comentario: str, doc_store: dict) -> int:
    """Guarda una nueva version de un libro Excel modificando la hoja seleccionada y preservando el historial inmutable."""
    excel_path = os.path.join(DOCS_DIR, doc_name)
    doc_hist_dir = os.path.join(HISTORY_DIR, doc_name)
    os.makedirs(doc_hist_dir, exist_ok=True)
    meta_path = os.path.join(doc_hist_dir, "metadata.json")

    historial = obtener_historial_versiones(doc_name)
    if not historial:
        v1_filename = "v1.md"
        contenido_previo = doc_store.get(doc_name, "")
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

    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_nuevo.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_nuevo.to_excel(writer, sheet_name=sheet_name, index=False)

    shutil.copy2(excel_path, os.path.join(doc_hist_dir, snapshot_excel_fname))

    nuevo_markdown = procesar_excel_limpio(excel_path)
    snapshot_md_fname = f"v{nueva_v_num}.md"
    with open(os.path.join(doc_hist_dir, snapshot_md_fname), "w", encoding="utf-8") as f:
        f.write(nuevo_markdown)

    doc_store[doc_name] = nuevo_markdown

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


def obtener_bytes_snapshot(doc_name: str, filename_snapshot: str) -> bytes | None:
    """Recupera los bytes binarios de un snapshot historico (ej. .xlsx, .docx, .pdf, .md)."""
    if not filename_snapshot:
        return None
    snap_path = os.path.join(HISTORY_DIR, doc_name, filename_snapshot)
    if os.path.exists(snap_path):
        with open(snap_path, "rb") as f:
            return f.read()
    return None


def generar_diff_lado_a_lado_html(texto_ant: str, texto_nuevo: str, label_ant: str = "Versión A", label_nuevo: str = "Versión B") -> dict:
    """Genera una vista visual diff lado a lado (Split Diff) en HTML Theme-Safe con conteo de cambios."""
    lineas_ant = texto_ant.splitlines()
    lineas_nuevo = texto_nuevo.splitlines()

    matcher = difflib.SequenceMatcher(None, lineas_ant, lineas_nuevo)
    filas_html = []

    adiciones = 0
    eliminaciones = 0
    modificaciones = 0
    sin_cambio = 0

    for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
        if tag == 'equal':
            for i in range(ahi - alo):
                sin_cambio += 1
                num_a = alo + i + 1
                num_b = blo + i + 1
                txt = html.escape(lineas_ant[alo + i]) if lineas_ant[alo + i] else "&nbsp;"
                filas_html.append(f"""
                <div class="diff-row">
                    <div class="diff-cell"><span class="diff-num">{num_a}</span><span class="diff-text">{txt}</span></div>
                    <div class="diff-cell"><span class="diff-num">{num_b}</span><span class="diff-text">{txt}</span></div>
                </div>""")
        elif tag == 'replace':
            count_a = ahi - alo
            count_b = bhi - blo
            modificaciones += max(count_a, count_b)
            max_c = max(count_a, count_b)
            for i in range(max_c):
                if i < count_a:
                    num_a = alo + i + 1
                    txt_a = html.escape(lineas_ant[alo + i]) if lineas_ant[alo + i] else "&nbsp;"
                    left_html = f'<div class="diff-cell diff-del"><span class="diff-num">{num_a}</span><span class="diff-text">- {txt_a}</span></div>'
                else:
                    left_html = '<div class="diff-cell diff-empty"><span class="diff-num"></span><span class="diff-text"></span></div>'

                if i < count_b:
                    num_b = blo + i + 1
                    txt_b = html.escape(lineas_nuevo[blo + i]) if lineas_nuevo[blo + i] else "&nbsp;"
                    right_html = f'<div class="diff-cell diff-add"><span class="diff-num">{num_b}</span><span class="diff-text">+ {txt_b}</span></div>'
                else:
                    right_html = '<div class="diff-cell diff-empty"><span class="diff-num"></span><span class="diff-text"></span></div>'

                filas_html.append(f'<div class="diff-row">{left_html}{right_html}</div>')
        elif tag == 'delete':
            count_a = ahi - alo
            eliminaciones += count_a
            for i in range(count_a):
                num_a = alo + i + 1
                txt_a = html.escape(lineas_ant[alo + i]) if lineas_ant[alo + i] else "&nbsp;"
                left_html = f'<div class="diff-cell diff-del"><span class="diff-num">{num_a}</span><span class="diff-text">- {txt_a}</span></div>'
                right_html = '<div class="diff-cell diff-empty"><span class="diff-num"></span><span class="diff-text"></span></div>'
                filas_html.append(f'<div class="diff-row">{left_html}{right_html}</div>')
        elif tag == 'insert':
            count_b = bhi - blo
            adiciones += count_b
            for i in range(count_b):
                num_b = blo + i + 1
                txt_b = html.escape(lineas_nuevo[blo + i]) if lineas_nuevo[blo + i] else "&nbsp;"
                left_html = '<div class="diff-cell diff-empty"><span class="diff-num"></span><span class="diff-text"></span></div>'
                right_html = f'<div class="diff-cell diff-add"><span class="diff-num">{num_b}</span><span class="diff-text">+ {txt_b}</span></div>'
                filas_html.append(f'<div class="diff-row">{left_html}{right_html}</div>')

    stats = {
        "adiciones": adiciones,
        "eliminaciones": eliminaciones,
        "modificaciones": modificaciones,
        "sin_cambio": sin_cambio,
        "total_lineas": len(filas_html)
    }

    if not filas_html:
        diff_html = '<div class="diff-container"><div style="padding: 16px; opacity: 0.8;">No hay contenido que comparar.</div></div>'
    else:
        diff_html = f"""<div class="diff-container">
    <div class="diff-stats-bar">
        <div class="diff-stat-group">
            <span class="badge-ok">+{adiciones} adiciones</span>
            <span class="badge-crit">-{eliminaciones} eliminaciones</span>
            <span class="badge-warn">~{modificaciones} modificaciones</span>
            <span class="badge-tag">{sin_cambio} líneas iguales</span>
        </div>
        <div>
            <span class="badge-info">Comparación Lado a Lado</span>
        </div>
    </div>
    <div class="diff-header-row">
        <div class="diff-header-col">[Versión Base] {label_ant}</div>
        <div class="diff-header-col">[Versión Comparada] {label_nuevo}</div>
    </div>
    <div class="diff-body">
        {"".join(filas_html)}
    </div>
</div>"""

    return {
        "html": diff_html,
        "stats": stats
    }


def obtener_todos_los_eventos_auditoria() -> list:
    """Recupera todos los eventos registrados en el log global de auditoría en orden cronológico inverso."""
    if os.path.exists(AUDIT_LOG_PATH):
        try:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                eventos = json.load(f)
                return list(reversed(eventos))
        except Exception:
            return []
    return []


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

        es_rollback = "rollback" in comentario.lower()
        if es_rollback:
            badge_tipo = '<span class="badge-crit">[ROLLBACK]</span>'
        elif v_num == 1:
            badge_tipo = '<span class="badge-ok">[BASE v1]</span>'
        else:
            badge_tipo = '<span class="badge-info">[REVISIÓN]</span>'

        items_html.append(f"""
        <div class="version-timeline-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <div>
                    {badge_tipo}
                    <span style="font-weight: 700; font-size: 0.95rem; margin-left: 6px;">Versión v{v_num}</span>
                </div>
                <div style="font-size: 0.8rem; opacity: 0.8;">{ts}</div>
            </div>
            <div style="font-size: 0.88rem; margin: 4px 0;"><b>Motivo:</b> {html.escape(comentario)}</div>
            <div style="font-size: 0.78rem; opacity: 0.75; display: flex; justify-content: space-between; margin-top: 6px; border-top: 1px dashed rgba(128,128,128,0.2); padding-top: 4px;">
                <span><b>Editor:</b> {html.escape(autor)}</span>
                <span><b>Tamaño:</b> {caracteres} caracteres</span>
            </div>
        </div>""")

    return f'<div class="version-timeline-container">{"".join(items_html)}</div>'


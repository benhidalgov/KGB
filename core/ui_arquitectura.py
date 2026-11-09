"""Sección Arquitectura: embebe el diagrama versionado del repositorio.

El HTML vive en `assets/arquitectura/arquitectura.html` (versionado, fuera de
`data/`) y se sirve sin transformarlo salvo por el tema activo, sustituido en
`%%TEMA%%`. Si el archivo se actualiza, basta con commitearlo: se recarga por mtime.
"""
import os
import streamlit as st

from core.configuracion import ARQ_HTML_PATH

_CACHE = {"mtime": 0.0, "html": ""}

# Umbral "Alta" que ya usa core/motor.py para una coincidencia de documento.
_UMBRAL_ALTA = 20


def _categoria_de_servicio(nombre: str) -> str:
    """Categoría del servicio en el modelo (vacío si no está, p. ej. en tests)."""
    try:
        from core.arq_render import cargar_modelo
        for capa in cargar_modelo()["capas"]:
            for s in capa["servicios"]:
                if s["nombre"] == nombre:
                    return s["categoria"]
    except Exception:
        pass
    return ""


def _buscar_documentos(servicio: str, doc_store: dict) -> list:
    """Documentos del servicio, probando también su categoría como boost.

    La categoría del modelo ("Monitoreo", "POS / Cajas"…) es la tag que el
    servicio ya trae: sumarla a la consulta sube de 52 a 64 de 70 servicios
    con coincidencia fuerte. Se fusiona por score máximo, así la consulta más
    larga (que pierde el +30 de frase) nunca empeora el resultado.
    """
    from core.motor import buscar_en_documentos

    encontrados = buscar_en_documentos(servicio, doc_store)
    categoria = _categoria_de_servicio(servicio)
    if not categoria:
        return encontrados
    fusion = {n: (c, s) for n, c, s in encontrados}
    for n, c, s in buscar_en_documentos(servicio + " " + categoria, doc_store):
        if s > fusion.get(n, ("", -1))[1]:
            fusion[n] = (c, s)
    return sorted(((n, c, s) for n, (c, s) in fusion.items()),
                  key=lambda x: x[2], reverse=True)


def procesar_parametros_arquitectura(doc_store: dict) -> None:
    """Convierte un clic del diagrama (?arq_lee / ?arq_rel) en navegación de la consola.

    El visor vive en un iframe y Streamlit no devuelve valores desde uno: el único
    canal hacia Python es la URL. El visor escribe el parámetro y fuerza el rerun
    con un clic en la radio del sidebar; aquí se lee y se limpia.

    Limpiar es obligatorio: con el parámetro plantado, Streamlit deja de reenviar
    la URL viva y el siguiente clic del diagrama se pierde.
    """
    leer = str(st.query_params.get("arq_lee") or "").strip()
    relacionar = str(st.query_params.get("arq_rel") or "").strip()
    if not leer and not relacionar:
        return
    try:
        st.query_params.clear()
    except Exception:
        pass

    servicio = leer or relacionar
    encontrados = _buscar_documentos(servicio, doc_store)

    # Modo lectura directo solo con coincidencia fuerte: con ruido de contenido
    # se abre un documento equivocado; sin umbral se prefiere la lista.
    if leer and encontrados and encontrados[0][2] >= _UMBRAL_ALTA:
        st.session_state["zen_doc_sel"] = encontrados[0][0]
        st.session_state["zen_studio_activo"] = True
        return

    st.session_state["arq_docs_relacionados"] = {
        "etiqueta": servicio,
        "docs": [nombre for nombre, _, _ in encontrados[:5]],
    }
    st.session_state["nav_seccion_activa"] = "Documentación Técnica"
    st.session_state["tab4_cat_selector"] = "Todas"
    st.session_state["tab4_type_selector"] = "Todos"


def cargar_html_arquitectura(tema: str = "Claro") -> str:
    """Devuelve el HTML de arquitectura con el tema aplicado (vacío si no existe)."""
    if not os.path.exists(ARQ_HTML_PATH):
        return ""
    mtime = os.path.getmtime(ARQ_HTML_PATH)
    if mtime != _CACHE["mtime"]:
        with open(ARQ_HTML_PATH, "r", encoding="utf-8") as f:
            _CACHE["html"] = f.read()
        _CACHE["mtime"] = mtime
    return _CACHE["html"].replace("%%TEMA%%", "tema-oscuro" if tema == "Oscuro" else "tema-claro")


def renderizar_seccion_arquitectura():
    """Renderiza el esquema de arquitectura en un iframe autocontenido."""
    contenido = cargar_html_arquitectura(st.session_state.get("tema_visual", "Claro"))
    if not contenido:
        st.info("No se encontró el diagrama de arquitectura en `assets/arquitectura/arquitectura.html`.")
        return
    st.caption("Arquitectura de plataforma · versión del repositorio")
    st.components.v1.html(contenido, height=1120, scrolling=False)

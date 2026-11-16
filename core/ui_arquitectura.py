"""Sección Arquitectura: embebe el diagrama versionado del repositorio.

El HTML vive en `assets/arquitectura/arquitectura.html` (versionado, fuera de
`data/`) y se sirve sin transformarlo salvo por el tema activo, sustituido en
`%%TEMA%%`. Si el archivo se actualiza, basta con commitearlo: se recarga por mtime.
"""
import os
import re
import streamlit as st

from core.configuracion import ARQ_HTML_PATH

_CACHE = {"mtime": 0.0, "html": ""}

# Umbral "Alta" que ya usa core/motor.py para una coincidencia de documento.
_UMBRAL_ALTA = 20

# Corte de relevancia para la relación diagrama-documento: la tag genérica de
# categoría aporta +25 en el motor y metía diarios y formularios personales
# (p. ej. "WAF (HTTPS / TLS)" traía el diario APT122 con score 31). Con 40,
# sólo entra el que menciona el propio servicio (query base) o el que alcanza
# coincidencia fuerte con la categoría (nombre +20 o varios hits de contenido).
_UMBRAL_RELACION = 40

# Documentos de cartera personal (autoevaluación APT122, formularios de
# prácticas): aparecen en cualquier búsqueda porque mencionan palabras comunes
# ("correo", "control", "gestión"), pero nunca son documentación de un
# servicio del diagrama. Sigue siendo buscable en la pestaña de consulta.
_DOCS_PERSONALES = re.compile(r"apt122|centro_practica", re.I)


def _consulta_sin_ruido(texto: str) -> str:
    """Consulta sin tokens de 1-2 caracteres.

    El motor suma 2 pts por ocurrencia de cada token y acepta tokens desde 2
    caracteres: la "de" de categorías como "Base de datos" o de servicios como
    "Tablets de autoservicio" aparece en casi cualquier documento y reventaba
    el corte de relevancia (diarios personales con score 180 en SQL Server).
    """
    from core.motor import normalizar_texto
    return " ".join(t for t in normalizar_texto(texto).split() if len(t) >= 3)


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
    servicio ya trae: sumarla a la consulta sube la cobertura de servicios con
    coincidencia. Se fusiona por score máximo, así la consulta más larga (que
    pierde el +30 de frase) nunca empeora el resultado.

    Relevancia: sólo entra el documento que menciona el propio servicio (está
    en la query base) o el que alcanza _UMBRAL_RELACION solo con la categoría;
    sin ese corte, la tag genérica inflaba el score de documentos ajenos. Las
    dos consultas pasan por _consulta_sin_ruido (ver ahí el porqué).
    """
    from core.motor import buscar_en_documentos

    consulta = _consulta_sin_ruido(servicio)
    base = buscar_en_documentos(consulta, doc_store)
    menciona = {n for n, _, _ in base}
    fusion = {n: (c, s) for n, c, s in base}
    categoria = _categoria_de_servicio(servicio)
    if categoria:
        for n, c, s in buscar_en_documentos(
                consulta + " " + _consulta_sin_ruido(categoria), doc_store):
            if s > fusion.get(n, ("", -1))[1]:
                fusion[n] = (c, s)
    relevantes = [(n, c, s) for n, (c, s) in fusion.items()
                  if not _DOCS_PERSONALES.search(n)
                  and (n in menciona or s >= _UMBRAL_RELACION)]
    return sorted(relevantes, key=lambda x: x[2], reverse=True)


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
    # El rango de fechas también: con un rango viejo activo, el caption prometía
    # los relacionados y la lista salía vacía.
    st.session_state["tab4_date_range_selector"] = ()


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

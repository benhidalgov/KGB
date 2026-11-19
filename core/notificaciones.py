"""
Sistema de notificaciones persistentes para la sesión.

Las notificaciones se almacenan en st.session_state para que sobrevivan a
reruns dentro de la misma sesión de usuario. Se muestran en un expander del
panel lateral para que el usuario pueda consultarlas en cualquier momento.
"""
from datetime import datetime
from typing import Optional

from core.configuracion import escribir_atomico

_NOTIFICACIONES_KEY = "notificaciones_sesion"
_MAX_NOTIFICACIONES = 50


def notificar(mensaje: str, tipo: str = "info") -> None:
    """Añade una notificación a la sesión actual.

    tipo: "info", "exito", "advertencia", "error"
    """
    import streamlit as st

    if _NOTIFICACIONES_KEY not in st.session_state:
        st.session_state[_NOTIFICACIONES_KEY] = []

    notificaciones = st.session_state[_NOTIFICACIONES_KEY]
    notificaciones.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo,
        "mensaje": mensaje,
    })

    # Mantener solo las últimas N notificaciones
    if len(notificaciones) > _MAX_NOTIFICACIONES:
        notificaciones[:] = notificaciones[-_MAX_NOTIFICACIONES:]


def obtener_notificaciones() -> list:
    """Devuelve la lista de notificaciones de la sesión (más recientes primero)."""
    import streamlit as st

    return list(reversed(st.session_state.get(_NOTIFICACIONES_KEY, [])))


def limpiar_notificaciones() -> None:
    """Limpia todas las notificaciones de la sesión."""
    import streamlit as st

    st.session_state[_NOTIFICACIONES_KEY] = []


def renderizar_notificaciones_sidebar() -> None:
    """Renderiza las notificaciones recientes en el panel lateral."""
    import streamlit as st

    notificaciones = obtener_notificaciones()
    if not notificaciones:
        return

    iconos = {
        "exito": "[OK]",
        "advertencia": "[WARN]",
        "error": "[ERR]",
        "info": "[INFO]",
    }

    with st.expander(f"Notificaciones recientes ({len(notificaciones)})", expanded=False):
        for n in notificaciones[:10]:
            icono = iconos.get(n["tipo"], "[INFO]")
            st.caption(f"{icono} {n['timestamp']} — {n['mensaje']}")
        if len(notificaciones) > 10:
            st.caption(f"... y {len(notificaciones) - 10} más")
        if st.button("Limpiar notificaciones", key="btn_limpiar_notificaciones"):
            limpiar_notificaciones()
            st.rerun()

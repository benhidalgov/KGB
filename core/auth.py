"""Modulo de Autenticacion, Sesiones y Control de Acceso Basado en Roles (RBAC)."""
import os
import json
import hashlib
from typing import Optional, Dict, Any
import streamlit as st
from core.auditoria import registrar_evento_auditoria

AUTH_USERS_PATH = os.path.join("data", "users.json")
DEFAULT_SALT = "infra_console_security_salt_2026"

ROLES_PERMISOS = {
    "Administrador": {
        "descripcion": "Acceso total: Consultas al Asistente, Búsqueda DuckDB, Ingesta Batch, Gestión de Bóveda y Auditoría.",
        "puede_ver_vault": True, "puede_editar_vault": True, "puede_ingestar_archivos": True, "puede_editar_docs": True, "puede_rollback": True,
    },
    "Operador": {
        "descripcion": "Acceso técnico: Consultas al Asistente, Búsqueda DuckDB, Visor Lado a Lado y Registro de Incidencias.",
        "puede_ver_vault": False, "puede_editar_vault": False, "puede_ingestar_archivos": True, "puede_editar_docs": True, "puede_rollback": False,
    },
    "Auditor": {
        "descripcion": "Acceso de auditoría: Búsqueda de documentos, visualización de CMDB y verificación de eventos.",
        "puede_ver_vault": False, "puede_editar_vault": False, "puede_ingestar_archivos": False, "puede_editar_docs": False, "puede_rollback": False,
    }
}


def generar_hash_password(password_plana: str, salt: str = DEFAULT_SALT) -> str:
    """Genera hash seguro PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", password_plana.strip().encode("utf-8"), salt.encode("utf-8"), 100_000).hex()


def inicializar_almacen_usuarios() -> Dict[str, Any]:
    """Carga o inicializa data/users.json con cuentas base seguras."""
    if os.path.exists(AUTH_USERS_PATH):
        try:
            with open(AUTH_USERS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    usuarios_base = {
        "admin": {"nombre": "Administrador Principal", "rol": "Administrador", "hash": generar_hash_password("admin2026"), "activo": True},
        "operador": {"nombre": "Operador de Infraestructura", "rol": "Operador", "hash": generar_hash_password("operador2026"), "activo": True},
        "auditor": {"nombre": "Auditor de Seguridad", "rol": "Auditor", "hash": generar_hash_password("auditor2026"), "activo": True}
    }

    try:
        os.makedirs(os.path.dirname(AUTH_USERS_PATH), exist_ok=True)
        with open(AUTH_USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(usuarios_base, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return usuarios_base


def verificar_credenciales(username_input: str, password_input: str) -> Optional[Dict[str, Any]]:
    """Valida el usuario y contraseña contra el almacen o secrets."""
    u, p = username_input.strip().lower(), password_input.strip()
    if not u or not p:
        return None

    try:
        if hasattr(st, "secrets") and u == "admin" and "ADMIN_PASSWORD" in st.secrets and p == str(st.secrets["ADMIN_PASSWORD"]).strip():
            return {"username": "admin", "nombre": "Administrador (Cloud Secrets)", "rol": "Administrador", "activo": True}
    except Exception:
        pass

    usuarios = inicializar_almacen_usuarios()
    if u in usuarios and usuarios[u].get("activo", True):
        if generar_hash_password(p) == usuarios[u].get("hash"):
            return {"username": u, "nombre": usuarios[u].get("nombre", u), "rol": usuarios[u].get("rol", "Operador"), "activo": True}
    return None


def es_usuario_autenticado() -> bool:
    return bool(st.session_state.get("auth_activa") and st.session_state.get("usuario_actual"))


def obtener_usuario_actual() -> Dict[str, Any]:
    return st.session_state.get("usuario_actual", {"username": "anonimo", "nombre": "Invitado no autenticado", "rol": "Invitado"})


def es_administrador() -> bool:
    return obtener_usuario_actual().get("rol") == "Administrador"


def tiene_permiso(permiso_clave: str) -> bool:
    return ROLES_PERMISOS.get(obtener_usuario_actual().get("rol", "Invitado"), {}).get(permiso_clave, False)


def cerrar_sesion():
    """Cierra la sesión del usuario, limpiando el estado de autenticación."""
    user = obtener_usuario_actual().get("username", "desconocido")
    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGOUT", version_ant=1, version_nueva=1, autor=user, motivo="Cierre voluntario de sesión en consola web.")
    st.session_state["auth_activa"] = False
    st.session_state["usuario_actual"] = None
    st.toast("[INFO] Sesión cerrada correctamente.")
    st.rerun()


def renderizar_pantalla_login():
    """Renderiza la pantalla corporativa de inicio de sesión."""
    _, col_centro, _ = st.columns([1, 1.8, 1])
    with col_centro:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <span class="navbar-brand-badge" style="font-size: 0.85rem; padding: 3px 10px;">[CLI]</span>
                <h3 style="margin-top: 10px; margin-bottom: 4px; font-weight: 700; color: #6366F1;">Consola de Infraestructura y Operaciones</h3>
                <div style="font-size: 0.82rem; opacity: 0.8;">Acceso Restringido a Consola de Operaciones e Inventario CMDB</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form(key="form_corporate_login", clear_on_submit=False):
                username_in = st.text_input("Usuario:", placeholder="admin, operador, auditor")
                password_in = st.text_input("Contraseña:", type="password", placeholder="Ingrese contraseña")
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                btn_login = st.form_submit_button("Iniciar Sesión", type="primary", width="stretch")

            if btn_login:
                user_info = verificar_credenciales(username_in, password_in)
                if user_info:
                    st.session_state["auth_activa"] = True
                    st.session_state["usuario_actual"] = user_info
                    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGIN_EXITOSO", version_ant=1, version_nueva=1, autor=user_info["username"], motivo=f"Inicio exitoso [{user_info['rol']}].")
                    st.toast(f"[OK] Sesión iniciada como {user_info['nombre']} [{user_info['rol']}]")
                    st.rerun()
                else:
                    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGIN_FALLIDO", version_ant=1, version_nueva=1, autor=username_in.strip() or "desconocido", motivo="Credenciales inválidas.")
                    st.error("[ERROR] Credenciales no válidas. Verifique su usuario y contraseña.")

            st.markdown("---")
            with st.expander("Información de Cuentas Preconfiguradas para Pruebas", expanded=False):
                st.markdown("""
                | Usuario | Rol Asignado | Clave Inicial | Nivel de Acceso |
                | :--- | :--- | :--- | :--- |
                | `admin` | Administrador | `admin2026` | Acceso total (Bóveda, Ingesta, Edición, Rollback) |
                | `operador` | Operador | `operador2026` | Consultas al Asistente, Búsqueda DuckDB, Ingesta |
                | `auditor` | Auditor | `auditor2026` | Solo lectura (Búsqueda y Visor) |
                """)

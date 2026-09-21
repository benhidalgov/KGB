"""Modulo de Autenticacion, Sesiones y Control de Acceso Basado en Roles (RBAC)."""
import os
import json
import time
import hmac
import hashlib
from typing import Optional, Dict, Any
import streamlit as st
from core.auditoria import registrar_evento_auditoria
from core.manual import activar_manual_en_inicio, renderizar_manual_lanzamiento
from core.db import es_postgres_disponible, obtener_usuarios_pg, actualizar_ultimo_login_pg

from core.configuracion import USERS_PATH as AUTH_USERS_PATH, ES_PRODUCCION
DEFAULT_SALT = "infra_console_security_salt_2026"

_ROLES_MAESTROS = {"admin": "Administrador", "operador": "Operador", "auditor": "Auditor"}
_NOMBRES_MAESTROS = {"admin": "Administrador Principal", "operador": "Operador de Infraestructura", "auditor": "Auditor de Seguridad"}

# Limite de intentos fallidos por usuario (mitigacion en proceso).
# ponytail: estado local del proceso; para bloqueo real entre varias instancias,
# usar el proxy inverso o un almacen compartido. Se reinicia al reiniciar el contenedor.
_INTENTOS_FALLIDOS: Dict[str, list] = {}
_MAX_INTENTOS = 5
_VENTANA_BLOQUEO_S = 60.0


def _esta_bloqueado(usuario: str) -> bool:
    ahora = time.time()
    vigentes = [t for t in _INTENTOS_FALLIDOS.get(usuario, []) if ahora - t < _VENTANA_BLOQUEO_S]
    _INTENTOS_FALLIDOS[usuario] = vigentes
    return len(vigentes) >= _MAX_INTENTOS


def _registrar_fallo(usuario: str):
    _INTENTOS_FALLIDOS.setdefault(usuario, []).append(time.time())


def _limpiar_fallos(usuario: str):
    _INTENTOS_FALLIDOS.pop(usuario, None)


def _obtener_password_maestra(usuario: str) -> str:
    """Resuelve la contrasena maestra inyectada por entorno (Docker / Cloud) para el usuario indicado."""
    claves = {"admin": "ADMIN_PASSWORD", "operador": "OPERADOR_PASSWORD", "auditor": "AUDITOR_PASSWORD"}
    clave = claves.get(usuario)
    if not clave:
        return ""
    valor = os.environ.get(clave, "").strip()
    if not valor:
        try:
            if hasattr(st, "secrets") and clave in st.secrets:
                valor = str(st.secrets[clave]).strip()
        except Exception:
            pass
    return valor


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

    claves = {u: _obtener_password_maestra(u) for u in ("admin", "operador", "auditor")}
    faltantes = [u for u, p in claves.items() if not p]
    if faltantes:
        if ES_PRODUCCION:
            nombres = ", ".join(f"{u.upper()}_PASSWORD" for u in faltantes)
            raise RuntimeError(f"Defina las variables maestras de acceso: {nombres} (ver .env.example).")
        claves = {u: p or f"{u}2026" for u, p in claves.items()}

    usuarios_base = {
        "admin": {"nombre": "Administrador Principal", "rol": "Administrador", "hash": generar_hash_password(claves["admin"]), "activo": True},
        "operador": {"nombre": "Operador de Infraestructura", "rol": "Operador", "hash": generar_hash_password(claves["operador"]), "activo": True},
        "auditor": {"nombre": "Auditor de Seguridad", "rol": "Auditor", "hash": generar_hash_password(claves["auditor"]), "activo": True}
    }

    try:
        os.makedirs(os.path.dirname(AUTH_USERS_PATH), exist_ok=True)
        with open(AUTH_USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(usuarios_base, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return usuarios_base


def _verificar_hash(password_plana: str, hash_esperado: Optional[str]) -> bool:
    """Compara la contraseña contra un hash PBKDF2 en tiempo constante."""
    if not hash_esperado:
        return False
    return hmac.compare_digest(generar_hash_password(password_plana), str(hash_esperado))


def verificar_credenciales(username_input: str, password_input: str) -> Optional[Dict[str, Any]]:
    """Valida el usuario y contraseña contra PostgreSQL, almacén local o secrets."""
    u, p = username_input.strip().lower(), password_input.strip()
    if not u or not p or _esta_bloqueado(u):
        return None

    # 0. Contraseñas maestras inyectadas por entorno (Docker / Streamlit Cloud)
    master = _obtener_password_maestra(u)
    if master and hmac.compare_digest(p.encode("utf-8"), master.encode("utf-8")):
        _limpiar_fallos(u)
        return {"username": u, "nombre": _NOMBRES_MAESTROS.get(u, u.capitalize()), "rol": _ROLES_MAESTROS.get(u, "Operador"), "activo": True}

    # 1. Verificación primaria contra PostgreSQL si está disponible
    if es_postgres_disponible():
        try:
            usuarios_pg = obtener_usuarios_pg()
            if u in usuarios_pg and usuarios_pg[u].get("activo", True):
                if _verificar_hash(p, usuarios_pg[u].get("hash")):
                    _limpiar_fallos(u)
                    actualizar_ultimo_login_pg(u)
                    return {
                        "username": u,
                        "nombre": usuarios_pg[u].get("nombre", u),
                        "rol": usuarios_pg[u].get("rol", "Operador"),
                        "activo": True
                    }
        except Exception:
            pass

    # 2. Fallback automático a archivo local users.json (deshabilitado en producción)
    if not ES_PRODUCCION:
        usuarios = inicializar_almacen_usuarios()
        if u in usuarios and usuarios[u].get("activo", True):
            if _verificar_hash(p, usuarios[u].get("hash")):
                _limpiar_fallos(u)
                return {"username": u, "nombre": usuarios[u].get("nombre", u), "rol": usuarios[u].get("rol", "Operador"), "activo": True}

    _registrar_fallo(u)
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
    st.toast("Sesión cerrada.")
    st.rerun()


def _cb_autocompletar_cuenta_auth(usuario: str):
    """Autocompleta solo el nombre de usuario; la contraseña siempre la escribe la persona."""
    st.session_state["login_username_val"] = usuario
    st.session_state["login_password_val"] = ""


def renderizar_pantalla_login():
    """Renderiza la pantalla corporativa dividida: formulario a la izquierda y manual a la derecha."""
    st.markdown("""
    <style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
    </style>
    <div class="search-result-card" style="border-left: 4px solid #6366F1; margin: 8px 0 18px 0;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
                <span class="navbar-brand-badge" style="font-size: 0.78rem; padding: 3px 10px;">[CLI]</span>
                <span class="search-doc-title" style="margin-left: 8px;">Consola de Infraestructura y Operaciones</span>
            </div>
            <span class="badge-info">[INICIO]</span>
        </div>
        <div style="font-size: 0.84rem; opacity: 0.85; margin-top: 6px;">
            Inicia sesión para ver el inventario y los documentos. A la derecha tienes una guía rápida.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "login_username_val" not in st.session_state:
        st.session_state["login_username_val"] = ""
    if "login_password_val" not in st.session_state:
        st.session_state["login_password_val"] = ""

    col_login, col_manual = st.columns([1.05, 1.55], gap="large")
    with col_login:
        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 10px;">
                <span class="badge-info">[ACCESO]</span>
                <div style="font-size: 1.05rem; font-weight: 700; margin-top: 8px;">Inicio de sesión</div>
                <div style="font-size: 0.82rem; opacity: 0.8;">Escribe tu usuario y contraseña</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='font-size:0.75rem;opacity:0.75;margin-bottom:4px;'>Cuentas de prueba:</div>", unsafe_allow_html=True)
            col_q1, col_q2, col_q3 = st.columns(3, gap="small")
            with col_q1:
                st.button("admin", key="btn_fill_admin", width="stretch", help="Rol: Administrador", on_click=_cb_autocompletar_cuenta_auth, args=("admin",))
            with col_q2:
                st.button("operador", key="btn_fill_operador", width="stretch", help="Rol: Operador", on_click=_cb_autocompletar_cuenta_auth, args=("operador",))
            with col_q3:
                st.button("auditor", key="btn_fill_auditor", width="stretch", help="Rol: Auditor", on_click=_cb_autocompletar_cuenta_auth, args=("auditor",))

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

            with st.form(key="form_corporate_login", clear_on_submit=False):
                username_in = st.text_input("Usuario:", key="login_username_val")
                password_in = st.text_input("Contraseña:", type="password", key="login_password_val")
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                btn_login = st.form_submit_button("Iniciar Sesión", type="primary", width="stretch")

            if btn_login:
                user_info = verificar_credenciales(username_in, password_in)
                if user_info:
                    st.session_state["auth_activa"] = True
                    st.session_state["usuario_actual"] = user_info
                    activar_manual_en_inicio()
                    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGIN_EXITOSO", version_ant=1, version_nueva=1, autor=user_info["username"], motivo=f"Inicio exitoso [{user_info['rol']}].")
                    st.toast(f"Bienvenido, {user_info['nombre']}.")
                    st.rerun()
                else:
                    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGIN_FALLIDO", version_ant=1, version_nueva=1, autor=username_in.strip() or "desconocido", motivo="Credenciales inválidas.")
                    st.error("Usuario o contraseña incorrectos.")

    with col_manual:
        with st.container(border=True):
            renderizar_manual_lanzamiento()

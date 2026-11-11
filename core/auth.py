"""Modulo de Autenticacion, Sesiones y Control de Acceso Basado en Roles (RBAC)."""
import os
import json
import time
import hmac
import hashlib
import secrets
from typing import Optional, Dict, Any
import streamlit as st
from core.auditoria import registrar_evento_auditoria
from core.manual import renderizar_manual_lanzamiento
from core.db import es_postgres_disponible, obtener_usuarios_pg, actualizar_ultimo_login_pg

from core.configuracion import USERS_PATH as AUTH_USERS_PATH, ES_PRODUCCION
DEFAULT_SALT = "infra_console_security_salt_2026"
_PBKDF2_ITERATIONS = 100_000

_ROLES_MAESTROS = {"admin": "Administrador", "operador": "Operador", "auditor": "Auditor"}
_NOMBRES_MAESTROS = {"admin": "Administrador Principal", "operador": "Operador de Infraestructura", "auditor": "Auditor de Seguridad"}

# Limite de intentos fallidos por (usuario, origen) (mitigacion en proceso).
# ponytail: estado local del proceso; para bloqueo real entre varias instancias,
# usar el proxy inverso o un almacen compartido. Se reinicia al reiniciar el contenedor.
# Sin cambio: la ventana es de 60 s, asi que persistir entre reinicios no baja los
# intentos reales (5 por minuto se obtienen igual) y hoy solo hay un proceso.
# El upgrade llega con el proxy inverso del P2 pendiente.
_INTENTOS_FALLIDOS: Dict[str, list] = {}
_MAX_INTENTOS = 5
_VENTANA_BLOQUEO_S = 60.0
_MAX_CLAVES_INTENTOS = 4096
_REVALIDAR_SEG = 60.0
try:
    _MAX_INACTIVIDAD_SEG = float(os.environ.get("SESSION_TIMEOUT_MIN", "30")) * 60
except ValueError:
    _MAX_INACTIVIDAD_SEG = 30 * 60


def _esta_bloqueado(clave: str) -> bool:
    ahora = time.time()
    vigentes = [t for t in _INTENTOS_FALLIDOS.get(clave, []) if ahora - t < _VENTANA_BLOQUEO_S]
    _INTENTOS_FALLIDOS[clave] = vigentes
    return len(vigentes) >= _MAX_INTENTOS


def _registrar_fallo(clave: str):
    global _INTENTOS_FALLIDOS
    _INTENTOS_FALLIDOS.setdefault(clave, []).append(time.time())
    if len(_INTENTOS_FALLIDOS) < _MAX_CLAVES_INTENTOS:
        return
    # Un atacante que envia usuarios aleatorios nunca vuelve a consultar la
    # clave objetivo, asi que el podado de _esta_bloqueado no lo alcanza.
    ahora = time.time()
    vigentes = {
        k: [t for t in v if ahora - t < _VENTANA_BLOQUEO_S]
        for k, v in _INTENTOS_FALLIDOS.items()
    }
    vigentes = {k: v for k, v in vigentes.items() if v}
    if len(vigentes) >= _MAX_CLAVES_INTENTOS:
        # Descartar primero las claves con menos fallos: una cuenta bloqueada
        # (5 intentos) no debe caer antes que el ruido de un solo intento.
        orden = sorted(vigentes, key=lambda k: (len(vigentes[k]), min(vigentes[k])))
        for k in orden[:len(vigentes) - _MAX_CLAVES_INTENTOS + 1]:
            vigentes.pop(k, None)
    _INTENTOS_FALLIDOS = vigentes


def _limpiar_fallos(clave: str):
    _INTENTOS_FALLIDOS.pop(clave, None)


def _obtener_password_maestra(usuario: str) -> str:
    """Resuelve la contrasena maestra inyectada por entorno (Docker / Cloud) para el usuario indicado."""
    clave = {"admin": "ADMIN_PASSWORD", "operador": "OPERADOR_PASSWORD", "auditor": "AUDITOR_PASSWORD"}.get(usuario, "")
    if not clave:
        return ""
    sec = ""
    try:
        sec = str(st.secrets[clave]).strip() if hasattr(st, "secrets") and clave in st.secrets else ""
    except Exception:
        pass
    return os.environ.get(clave, "").strip() or sec


ROLES_PERMISOS = {
    "Administrador": {
        "descripcion": "Acceso total: Consultas al Asistente, Búsqueda DuckDB, Ingesta Batch, Gestión de Bóveda y Auditoría.",
        "puede_ver_vault": True, "puede_editar_vault": True, "puede_ingestar_archivos": True, "puede_editar_docs": True, "puede_rollback": True, "puede_ejecutar_sql": True, "puede_ver_auditoria": True,
    },
    "Operador": {
        "descripcion": "Acceso técnico: Consultas al Asistente, Búsqueda DuckDB, Ingesta Batch y edición de documentos.",
        "puede_ver_vault": False, "puede_editar_vault": False, "puede_ingestar_archivos": True, "puede_editar_docs": True, "puede_rollback": False, "puede_ver_auditoria": False,
    },
    "Auditor": {
        "descripcion": "Acceso de auditoría: Búsqueda de documentos, visualización de CMDB y verificación de eventos.",
        "puede_ver_vault": False, "puede_editar_vault": False, "puede_ingestar_archivos": False, "puede_editar_docs": False, "puede_rollback": False, "puede_ver_auditoria": True,
    }
}


def generar_hash_password(password_plana: str, salt: Optional[str] = None) -> str:
    """Genera hash PBKDF2-HMAC-SHA256 con sal aleatoria por usuario.

    Formato: pbkdf2_sha256$<iteraciones>$<salt>$<hash_hex>
    Si se omite la sal, se genera una nueva (no determinista entre llamadas).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password_plana.strip().encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


# Hash de descarte: un usuario inexistente paga el mismo PBKDF2 que uno real,
# para que el tiempo de respuesta no delate que cuentas existen.
_HASH_DUMMY = generar_hash_password(secrets.token_hex(16))


def inicializar_almacen_usuarios() -> Dict[str, Any]:
    """Carga o inicializa data/users.json con cuentas base seguras."""
    if os.path.exists(AUTH_USERS_PATH):
        try:
            with open(AUTH_USERS_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            # Archivo corrupto: no se sobrescribe (se perderían las cuentas
            # personalizadas); el login fallará hasta que se repare a mano.
            return {}

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
    """Compara la contraseña contra un hash PBKDF2 en tiempo constante.
    Soporta formato nuevo pbkdf2_sha256$ y compatibilidad con formato legado de 64 caracteres.
    """
    if not hash_esperado:
        return False
    valor = str(hash_esperado)
    if valor.startswith("pbkdf2_sha256$"):
        try:
            _, iteraciones, salt, digest = valor.split("$", 3)
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password_plana.strip().encode("utf-8"),
                salt.encode("utf-8"),
                int(iteraciones),
            )
            return hmac.compare_digest(dk.hex(), digest)
        except (ValueError, TypeError):
            return False
    # Compatibilidad con hashes legados de 64 caracteres hex
    legacy = hashlib.pbkdf2_hmac(
        "sha256",
        password_plana.strip().encode("utf-8"),
        DEFAULT_SALT.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return hmac.compare_digest(legacy, valor)


def _origen_actual() -> str:
    """IP del cliente para separar los bloqueos por origen (vacia si no hay)."""
    try:
        return str(getattr(st.context, "ip_address", "") or "")
    except Exception:
        return ""


def _clave_intentos(username: str, origen: str) -> str:
    """Identidad de bloqueo (usuario normalizado + origen). Compartida entre la
    verificación y el login: el aviso de cuenta bloqueada debe apuntar al mismo candado."""
    return f"{username.strip().lower()}|{origen}"


def verificar_credenciales(username_input: str, password_input: str, origen: str = "") -> Optional[Dict[str, Any]]:
    """Valida el usuario y contraseña contra PostgreSQL, almacén local o secrets.

    El bloqueo se cuenta por usuario+origen: un atacante desde una IP no deja
    fuera al usuario legitimo que entra desde otra.
    """
    u, p = username_input.strip().lower(), password_input.strip()
    clave = _clave_intentos(username_input, origen)
    if not u or not p or _esta_bloqueado(clave):
        return None

    encontrado = False

    # 0. Contraseñas maestras inyectadas por entorno (Docker / Streamlit Cloud)
    master = _obtener_password_maestra(u)
    if master and hmac.compare_digest(p.encode("utf-8"), master.encode("utf-8")):
        # En produccion, sin PostgreSQL no se puede confirmar que la cuenta siga
        # activa: se falla cerrado en vez de dejar pasar la clave maestra.
        if ES_PRODUCCION and not es_postgres_disponible():
            _registrar_fallo(clave)
            return None
        # La clave maestra no debe bypasear la desactivación del usuario en PG.
        if es_postgres_disponible():
            try:
                usuarios_pg = obtener_usuarios_pg()
                if u in usuarios_pg and not usuarios_pg[u].get("activo", True):
                    _verificar_hash(p, _HASH_DUMMY)
                    _registrar_fallo(clave)
                    return None
            except Exception:
                # Sin poder leer el catálogo no se puede confirmar la cuenta.
                if ES_PRODUCCION:
                    _registrar_fallo(clave)
                    return None
        _limpiar_fallos(clave)
        return {"username": u, "nombre": _NOMBRES_MAESTROS.get(u, u.capitalize()), "rol": _ROLES_MAESTROS.get(u, "Operador"), "activo": True}

    # 1. Verificación primaria contra PostgreSQL si está disponible
    if es_postgres_disponible():
        try:
            usuarios_pg = obtener_usuarios_pg()
            if u in usuarios_pg:
                encontrado = True
                if not usuarios_pg[u].get("activo", True):
                    _verificar_hash(p, _HASH_DUMMY)
                    _registrar_fallo(clave)
                    return None
                if _verificar_hash(p, usuarios_pg[u].get("hash")):
                    _limpiar_fallos(clave)
                    actualizar_ultimo_login_pg(u)
                    return {
                        "username": u,
                        "nombre": usuarios_pg[u].get("nombre", u),
                        "rol": usuarios_pg[u].get("rol", "Operador"),
                        "activo": True
                    }
        except Exception:
            pass

    # 2. Fallback automático a archivo local users.json (deshabilitado en producción).
    # Un usuario desactivado en PG no revive vía el users.json local.
    if not ES_PRODUCCION:
        try:
            usuarios = inicializar_almacen_usuarios()
        except Exception:
            usuarios = {}
        if u in usuarios:
            encontrado = True
            if not usuarios[u].get("activo", True):
                _verificar_hash(p, _HASH_DUMMY)
            elif _verificar_hash(p, usuarios[u].get("hash")):
                _limpiar_fallos(clave)
                return {"username": u, "nombre": usuarios[u].get("nombre", u), "rol": usuarios[u].get("rol", "Operador"), "activo": True}

    if not encontrado:
        # Mismo costo que un usuario real: no se puede enumerar por tiempo.
        _verificar_hash(p, _HASH_DUMMY)
    _registrar_fallo(clave)
    return None


def _limpiar_estado_sesion():
    """Cierra la sesión y borra lo que no debe heredar el próximo usuario."""
    st.session_state["auth_activa"] = False
    st.session_state["usuario_actual"] = None
    for clave in ("login_password_val", "login_username_val", "historial_busquedas",
                  "nav_seccion_activa", "tab4_doc_selector",
                  "auth_chequeo", "auth_ultima_actividad"):
        st.session_state.pop(clave, None)


def _leer_registro(usuario: str):
    """Registro vigente del usuario; None si no existe, "error" si no se pudo leer."""
    if es_postgres_disponible():
        try:
            return obtener_usuarios_pg().get(usuario)
        except Exception:
            return "error"
    if not ES_PRODUCCION:
        try:
            return inicializar_almacen_usuarios().get(usuario)
        except Exception:
            return "error"
    return "error"


def _sesion_vigente() -> bool:
    """Cierra la sesión por inactividad o si el usuario cambió en el origen."""
    if not st.session_state.get("auth_activa") or not st.session_state.get("usuario_actual"):
        return False

    ahora = time.time()
    ultima = st.session_state.get("auth_ultima_actividad")
    if ultima and ahora - ultima > _MAX_INACTIVIDAD_SEG:
        _limpiar_estado_sesion()
        return False
    st.session_state["auth_ultima_actividad"] = ahora

    if ahora - (st.session_state.get("auth_chequeo") or 0) < _REVALIDAR_SEG:
        return True

    usuario = st.session_state.get("usuario_actual") or {}
    nombre_usuario = usuario.get("username", "")
    registro = _leer_registro(nombre_usuario)
    if registro is None and nombre_usuario in _ROLES_MAESTROS and _obtener_password_maestra(nombre_usuario):
        # Las cuentas maestras existen por entorno aunque no estén en PG.
        registro = {"rol": _ROLES_MAESTROS[nombre_usuario],
                    "nombre": _NOMBRES_MAESTROS[nombre_usuario], "activo": True}

    if not registro or registro == "error" or not registro.get("activo", True):
        _limpiar_estado_sesion()
        return False

    st.session_state["usuario_actual"] = {
        **usuario,
        "rol": registro.get("rol", usuario.get("rol")),
        "nombre": registro.get("nombre", usuario.get("nombre")),
        "activo": True,
    }
    st.session_state["auth_chequeo"] = ahora
    return True


def es_usuario_autenticado() -> bool:
    return _sesion_vigente()


def obtener_usuario_actual() -> Dict[str, Any]:
    # `or` y no default de .get(): cerrar_sesion() guarda None explícito.
    return st.session_state.get("usuario_actual") or {"username": "anonimo", "nombre": "Invitado no autenticado", "rol": "Invitado"}


def es_administrador() -> bool:
    return obtener_usuario_actual().get("rol") == "Administrador"


def tiene_permiso(permiso_clave: str) -> bool:
    return ROLES_PERMISOS.get(obtener_usuario_actual().get("rol", "Invitado"), {}).get(permiso_clave, False)


def cerrar_sesion():
    """Cierra la sesión del usuario, limpiando el estado de autenticación."""
    user = obtener_usuario_actual().get("username", "desconocido")
    # Limpiar el estado ANTES de auditar: registrar_evento_auditoria lanza en
    # producción si PG falla, y el logout no debe dejar la sesión abierta.
    _limpiar_estado_sesion()
    try:
        registrar_evento_auditoria(doc_name="autenticacion", accion="LOGOUT", version_ant=1, version_nueva=1, autor=user, motivo="Cierre voluntario de sesión en consola web.")
    except Exception:
        # El cierre ya es efectivo; un fallo de bitácora no debe reabrir la sesión.
        pass
    st.toast("Sesión cerrada.")
    st.rerun()


def _obtener_password_demo(usuario: str) -> str:
    """Clave de pruebas para autocompletado del formulario de acceso.

    Nunca devuelve la contrasena maestra del entorno: la pantalla de login es
    alcanzable sin autenticar y precargar la clave real la expondria.
    """
    if ES_PRODUCCION:
        return ""
    return f"{usuario}2026"


def _cb_autocompletar_cuenta_auth(usuario: str):
    """Autocompleta el nombre de usuario y su contrasena de prueba correspondiente."""
    st.session_state["login_username_val"] = usuario
    demo = _obtener_password_demo(usuario)
    if demo:
        st.session_state["login_password_val"] = demo


def _cb_cambiar_tema_auth():
    nuevo = st.session_state.get("seg_theme_login")
    if nuevo in ("Claro", "Oscuro"):
        st.session_state["tema_visual"] = nuevo
        st.session_state["segmented_theme_sidebar"] = nuevo
    else:
        st.session_state["seg_theme_login"] = st.session_state.get("tema_visual", "Claro")


def renderizar_pantalla_login():
    """Renderiza la pantalla corporativa dividida: formulario a la izquierda y manual a la derecha."""
    st.html("<style>[data-testid=\"stSidebar\"], [data-testid=\"stSidebarCollapsedControl\"] { display: none !important; }</style>")

    col_h_left, col_h_right = st.columns([3.8, 1.2], vertical_alignment="center")
    with col_h_left:
        st.markdown("""
        <div class="bento-card" style="margin: 4px 0 16px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="search-doc-title" style="margin-left: 8px;">Consola de Infraestructura y Operaciones</span>
                </div>
                <span class="badge-info">[Inicio]</span>
            </div>
            <div style="font-size: 0.84rem; color: var(--text-secondary); margin-top: 6px;">
                Inicia sesión para consultar la base técnica y el inventario operativo.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_h_right:
        tema_actual_auth = st.session_state.get("tema_visual", "Claro")
        if "seg_theme_login" not in st.session_state or st.session_state["seg_theme_login"] not in ("Claro", "Oscuro"):
            st.session_state["seg_theme_login"] = tema_actual_auth
        st.segmented_control(
            "Tema:",
            options=["Claro", "Oscuro"],
            key="seg_theme_login",
            on_change=_cb_cambiar_tema_auth,
            label_visibility="collapsed"
        )

    if "login_username_val" not in st.session_state:
        st.session_state["login_username_val"] = ""
    if "login_password_val" not in st.session_state:
        st.session_state["login_password_val"] = ""

    col_login, col_manual = st.columns([1.05, 1.55], gap="large")
    with col_login:
        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 12px;">
                <span class="badge-info">[Acceso]</span>
                <div style="font-family: var(--font-serif); font-size: 1.3rem; font-weight: 500; margin-top: 8px; color: var(--text-primary);">Inicio de sesión</div>
                <div style="font-size: 0.82rem; color: var(--text-secondary);">Credenciales autorizadas de infraestructura</div>
            </div>
            """, unsafe_allow_html=True)

            if not ES_PRODUCCION:
                st.markdown("<div style='font-size:0.78rem; font-weight:500; color:var(--text-secondary); margin-bottom:6px;'>Cuentas de prueba:</div>", unsafe_allow_html=True)
                col_q1, col_q2, col_q3 = st.columns(3, gap="small")
                with col_q1:
                    st.button("admin", key="btn_fill_admin", width="stretch", help="Rol: Administrador | Clave: admin2026", on_click=_cb_autocompletar_cuenta_auth, args=("admin",))
                with col_q2:
                    st.button("operador", key="btn_fill_operador", width="stretch", help="Rol: Operador | Clave: operador2026", on_click=_cb_autocompletar_cuenta_auth, args=("operador",))
                with col_q3:
                    st.button("auditor", key="btn_fill_auditor", width="stretch", help="Rol: Auditor | Clave: auditor2026", on_click=_cb_autocompletar_cuenta_auth, args=("auditor",))

                st.markdown("<div style='font-size: 0.72rem; color: var(--text-muted); margin-top: 4px; margin-bottom: 10px;'>Clave predeterminada: <code>[usuario]2026</code> (se rellena automáticamente).</div>", unsafe_allow_html=True)

            with st.form(key="form_corporate_login", clear_on_submit=False):
                username_in = st.text_input("Usuario:", key="login_username_val")
                password_in = st.text_input("Contraseña:", type="password", key="login_password_val")
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                btn_login = st.form_submit_button("Iniciar Sesión", type="primary", width="stretch")

            if btn_login:
                user_info = verificar_credenciales(username_in, password_in, origen=_origen_actual())
                if user_info:
                    # Auditar ANTES de autenticar: si la bitácora falla en
                    # producción, no debe quedar una sesión activa sin evento.
                    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGIN_EXITOSO", version_ant=1, version_nueva=1, autor=user_info["username"], motivo=f"Inicio exitoso [{user_info['rol']}].")
                    st.session_state["auth_activa"] = True
                    st.session_state["usuario_actual"] = user_info
                    st.session_state["auth_ultima_actividad"] = time.time()
                    st.session_state["auth_chequeo"] = time.time()
                    st.toast(f"Bienvenido, {user_info['nombre']}.")
                    st.rerun()
                else:
                    registrar_evento_auditoria(doc_name="autenticacion", accion="LOGIN_FALLIDO", version_ant=1, version_nueva=1, autor=username_in.strip() or "desconocido", motivo="Credenciales inválidas.")
                    if username_in.strip() and _esta_bloqueado(_clave_intentos(username_in, _origen_actual())):
                        st.error("Cuenta bloqueada por intentos fallidos. Espera unos minutos y vuelve a intentar.")
                    else:
                        st.error("Usuario o contraseña incorrectos.")

    with col_manual:
        with st.container(border=True):
            renderizar_manual_lanzamiento()

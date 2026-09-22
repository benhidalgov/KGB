"""
Modulo de Boveda de Seguridad Local (Vault).
Custodia de credenciales y API keys con cifrado simetrico AES-256 (Fernet) y auditoria inmutable.
"""
import os
import json
import base64
import hashlib
from typing import Dict, List
from cryptography.fernet import Fernet
from core.configuracion import VAULT_FILE_PATH, VAULT_KEY_PATH, ES_PRODUCCION
from core.auditoria import registrar_evento_auditoria

CLAVES_ESTANDAR_RECOMENDADAS = [
    "GEMINI_API_KEY", "SAP_ENDPOINT", "SAP_CLIENT_ID", "SAP_CLIENT_SECRET", "NAGIOS_API_TOKEN", "VCLOUD_API_TOKEN"
]

_KDF_SALT = b"kgb-vault-kdf-v1"
_KDF_ITERATIONS = 200_000


class ErrorBoveda(RuntimeError):
    """El archivo de bóveda existe pero no se pudo descifrar (clave incorrecta o corrupto)."""


def _derivar_claves_fernet(clave_origen: str) -> List[bytes]:
    """Claves candidatas a partir de una passphrase: PBKDF2 (actual) y SHA-256 (legado)."""
    pbkdf2 = hashlib.pbkdf2_hmac(
        "sha256", clave_origen.encode("utf-8"), _KDF_SALT, _KDF_ITERATIONS
    )
    nueva = base64.urlsafe_b64encode(pbkdf2)
    legado = base64.urlsafe_b64encode(hashlib.sha256(clave_origen.encode("utf-8")).digest())
    return [nueva, legado]


def _claves_candidatas() -> List[bytes]:
    """Claves a probar al descifrar; la primera se usa para cifrar."""
    env_key = os.environ.get("VAULT_MASTER_KEY", "").strip()
    if env_key:
        try:
            Fernet(env_key.encode("utf-8"))
            return [env_key.encode("utf-8")]
        except Exception:
            return _derivar_claves_fernet(env_key)

    # En producción no se genera una clave local junto a la bóveda cifrada:
    # quien acceda al volumen tendría texto y llave en el mismo lugar.
    if ES_PRODUCCION:
        raise RuntimeError("VAULT_MASTER_KEY es obligatoria en producción (ver .env.example).")

    if os.path.exists(VAULT_KEY_PATH):
        try:
            with open(VAULT_KEY_PATH, "rb") as f:
                kb = f.read().strip()
                if kb:
                    Fernet(kb)
                    return [kb]
        except Exception:
            pass

    nueva_clave = Fernet.generate_key()
    try:
        os.makedirs(os.path.dirname(VAULT_KEY_PATH), exist_ok=True)
        with open(VAULT_KEY_PATH, "wb") as f:
            f.write(nueva_clave)
    except Exception:
        pass
    return [nueva_clave]


def obtener_clave_maestra() -> bytes:
    """Clave primaria Fernet para cifrar la bóveda."""
    return _claves_candidatas()[0]


def _descifrar_boveda(cifrado: bytes) -> Dict[str, str]:
    ultimo_error: Exception | None = None
    for kb in _claves_candidatas():
        try:
            return json.loads(Fernet(kb).decrypt(cifrado).decode("utf-8"))
        except Exception as e:
            ultimo_error = e
    raise ErrorBoveda(
        "No se pudo descifrar la bóveda: clave maestra incorrecta o archivo corrupto. "
        "No se sobrescribirá para evitar pérdida de secretos."
    ) from ultimo_error


def _leer_todos_los_secretos_boveda() -> Dict[str, str]:
    """Lee todos los secretos. Lanza ErrorBoveda si el archivo existe pero no se puede descifrar."""
    if not os.path.exists(VAULT_FILE_PATH):
        return {}
    try:
        with open(VAULT_FILE_PATH, "rb") as f:
            cifrado = f.read()
    except OSError as e:
        raise ErrorBoveda(f"No se pudo leer el archivo de bóveda: {e}") from e
    if not cifrado:
        return {}
    return _descifrar_boveda(cifrado)


def _guardar_todos_los_secretos_boveda(secretos: Dict[str, str]) -> bool:
    try:
        fernet = Fernet(obtener_clave_maestra())
        cifrado = fernet.encrypt(json.dumps(secretos, ensure_ascii=False).encode("utf-8"))
        os.makedirs(os.path.dirname(VAULT_FILE_PATH), exist_ok=True)
        with open(VAULT_FILE_PATH, "wb") as f:
            f.write(cifrado)
        return True
    except Exception:
        return False


def obtener_secreto(nombre_secreto: str, valor_defecto: str = "") -> str:
    """Recupera un secreto por jerarquia: OS env -> Streamlit secrets -> Vault AES-256 -> default."""
    k = nombre_secreto.strip().upper()
    if k in os.environ and os.environ[k].strip():
        return os.environ[k].strip()

    try:
        import streamlit as st
        if hasattr(st, "secrets") and k in st.secrets and str(st.secrets[k]).strip():
            return str(st.secrets[k]).strip()
    except Exception:
        pass

    try:
        secretos = _leer_todos_los_secretos_boveda()
    except ErrorBoveda:
        return valor_defecto
    return secretos.get(k, valor_defecto).strip() if k in secretos else valor_defecto


def guardar_secreto(nombre_secreto: str, valor: str, autor: str = "Operador / Consola") -> bool:
    """Guarda o actualiza un secreto en la bóveda cifrada local registrando auditoría.

    Si la bóveda no se puede descifrar, lanza ErrorBoveda y no escribe nada.
    """
    k = nombre_secreto.strip().upper()
    if not k:
        return False
    secretos = _leer_todos_los_secretos_boveda()
    es_nuevo = k not in secretos
    secretos[k] = valor.strip()
    if _guardar_todos_los_secretos_boveda(secretos):
        registrar_evento_auditoria(doc_name="vault", accion="CREACION_CREDENCIAL_VAULT" if es_nuevo else "ACTUALIZACION_CREDENCIAL_VAULT", version_ant=1, version_nueva=1, autor=autor, motivo=f"Gestión de credencial [{k}] en bóveda.")
        return True
    return False


def eliminar_secreto(nombre_secreto: str, autor: str = "Operador / Consola") -> bool:
    """Elimina un secreto de la bóveda cifrada registrando auditoría.

    Si la bóveda no se puede descifrar, lanza ErrorBoveda y no escribe nada.
    """
    k = nombre_secreto.strip().upper()
    secretos = _leer_todos_los_secretos_boveda()
    if k in secretos:
        del secretos[k]
        if _guardar_todos_los_secretos_boveda(secretos):
            registrar_evento_auditoria(doc_name="vault", accion="REVOCACION_CREDENCIAL_VAULT", version_ant=1, version_nueva=1, autor=autor, motivo=f"Eliminación de credencial [{k}].")
            return True
    return False


def listar_secretos_disponibles() -> List[Dict[str, str]]:
    """Retorna el estado de las llaves conocidas sin exponer valores sensibles.

    Lanza ErrorBoveda si la bóveda local existe pero no se puede descifrar.
    """
    secretos = _leer_todos_los_secretos_boveda()
    todas = list(dict.fromkeys(CLAVES_ESTANDAR_RECOMENDADAS + list(secretos.keys())))
    res = []
    for k in todas:
        origen, estado, prev = "No Configurado", "[NO CONFIGURADO]", "-"
        if k in os.environ and os.environ[k].strip():
            origen, estado, prev = "Variable de Entorno (OS)", "[CONFIGURADO]", "••••••••••••"
        else:
            try:
                import streamlit as st
                if hasattr(st, "secrets") and k in st.secrets:
                    origen, estado, prev = "Streamlit Secrets", "[CONFIGURADO]", "••••••••••••"
            except Exception:
                pass
        if origen == "No Configurado" and k in secretos and secretos[k].strip():
            origen, estado, prev = "Bóveda Local Cifrada (AES-256)", "[CONFIGURADO]", "••••••••••••"
        res.append({"clave": k, "origen": origen, "estado": estado, "vista_previa": prev})
    return res

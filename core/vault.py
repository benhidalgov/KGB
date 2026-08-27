import os
import json
import base64
import hashlib
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
from core.configuracion import VAULT_FILE_PATH, VAULT_KEY_PATH
from core.auditoria import registrar_evento_auditoria

"""
Modulo de Boveda de Seguridad Local (Vault).
Implementa custodia de credenciales y API keys con cifrado simetrico AES-256 (Fernet),
jerarquia de resolucion en cascada y auditoria inmutable de gestion de secretos.
"""

CLAVES_ESTANDAR_RECOMENDADAS = [
    "GEMINI_API_KEY",
    "SAP_ENDPOINT",
    "SAP_CLIENT_ID",
    "SAP_CLIENT_SECRET",
    "NAGIOS_API_TOKEN",
    "VCLOUD_API_TOKEN"
]


def _derivar_clave_fernet(clave_origen: str) -> bytes:
    """Genera una clave Fernet valida (32 bytes en base64) a partir de cualquier cadena o passphrase."""
    digest = hashlib.sha256(clave_origen.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def obtener_clave_maestra() -> bytes:
    """
    Obtiene la clave maestra para la boveda.
    Prioridad 1: Variable de entorno del sistema VAULT_MASTER_KEY.
    Prioridad 2: Archivo local data/.vault.key generado automaticamente.
    """
    env_key = os.environ.get("VAULT_MASTER_KEY")
    if env_key and env_key.strip():
        try:
            # Probar si ya es clave Fernet valida
            Fernet(env_key.strip().encode("utf-8"))
            return env_key.strip().encode("utf-8")
        except Exception:
            return _derivar_clave_fernet(env_key.strip())

    if os.path.exists(VAULT_KEY_PATH):
        try:
            with open(VAULT_KEY_PATH, "rb") as f:
                key_bytes = f.read().strip()
                if key_bytes:
                    Fernet(key_bytes)
                    return key_bytes
        except Exception:
            pass

    # Generar nueva clave Fernet aleatoria y persistir localmente
    nueva_clave = Fernet.generate_key()
    try:
        os.makedirs(os.path.dirname(VAULT_KEY_PATH), exist_ok=True)
        with open(VAULT_KEY_PATH, "wb") as f:
            f.write(nueva_clave)
    except Exception:
        pass

    return nueva_clave


def _leer_todos_los_secretos_boveda() -> Dict[str, str]:
    """Descifra y carga el diccionario completo de secretos desde data/.vault.enc."""
    if not os.path.exists(VAULT_FILE_PATH):
        return {}

    try:
        clave = obtener_clave_maestra()
        fernet = Fernet(clave)
        with open(VAULT_FILE_PATH, "rb") as f:
            datos_cifrados = f.read()

        if not datos_cifrados:
            return {}

        datos_claros = fernet.decrypt(datos_cifrados)
        return json.loads(datos_claros.decode("utf-8"))
    except Exception:
        return {}


def _guardar_todos_los_secretos_boveda(secretos: Dict[str, str]) -> bool:
    """Cifra y persiste el diccionario completo de secretos en data/.vault.enc."""
    try:
        clave = obtener_clave_maestra()
        fernet = Fernet(clave)
        datos_json = json.dumps(secretos, ensure_ascii=False).encode("utf-8")
        datos_cifrados = fernet.encrypt(datos_json)

        os.makedirs(os.path.dirname(VAULT_FILE_PATH), exist_ok=True)
        with open(VAULT_FILE_PATH, "wb") as f:
            f.write(datos_cifrados)
        return True
    except Exception:
        return False


def obtener_secreto(nombre_secreto: str, valor_defecto: str = "") -> str:
    """
    Recupera un secreto siguiendo la jerarquia de resolucion en cascada:
    1. Variable de entorno del sistema operativo (os.environ).
    2. Archivo de secretos de Streamlit (.streamlit/secrets.toml) si esta disponible.
    3. Boveda local cifrada (data/.vault.enc).
    4. Valor por defecto proporcionado.
    """
    nombre_limpio = nombre_secreto.strip().upper()

    # Nivel 1: Variable de entorno del sistema
    if nombre_limpio in os.environ and os.environ[nombre_limpio].strip():
        return os.environ[nombre_limpio].strip()

    # Nivel 2: Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and nombre_limpio in st.secrets:
            val_st = str(st.secrets[nombre_limpio]).strip()
            if val_st:
                return val_st
    except Exception:
        pass

    # Nivel 3: Boveda cifrada local
    secretos = _leer_todos_los_secretos_boveda()
    if nombre_limpio in secretos and secretos[nombre_limpio].strip():
        return secretos[nombre_limpio].strip()

    return valor_defecto


def guardar_secreto(nombre_secreto: str, valor: str, autor: str = "Operador / Consola") -> bool:
    """
    Guarda o actualiza un secreto en la boveda cifrada local y registra el evento en auditoria.
    Por directriz de seguridad estricta, el valor sensible jamas se incluye en logs.
    """
    nombre_limpio = nombre_secreto.strip().upper()
    if not nombre_limpio:
        return False

    secretos = _leer_todos_los_secretos_boveda()
    es_nuevo = nombre_limpio not in secretos
    secretos[nombre_limpio] = valor.strip()

    exito = _guardar_todos_los_secretos_boveda(secretos)
    if exito:
        accion_desc = "CREACION_CREDENCIAL_VAULT" if es_nuevo else "ACTUALIZACION_CREDENCIAL_VAULT"
        registrar_evento_auditoria(
            doc_name="vault",
            accion=accion_desc,
            version_ant=1,
            version_nueva=1,
            autor=autor,
            motivo=f"Gestion segura de credencial [{nombre_limpio}] en boveda cifrada."
        )
    return exito


def eliminar_secreto(nombre_secreto: str, autor: str = "Operador / Consola") -> bool:
    """Elimina un secreto de la boveda cifrada y registra la accion en auditoria."""
    nombre_limpio = nombre_secreto.strip().upper()
    secretos = _leer_todos_los_secretos_boveda()

    if nombre_limpio in secretos:
        del secretos[nombre_limpio]
        exito = _guardar_todos_los_secretos_boveda(secretos)
        if exito:
            registrar_evento_auditoria(
                doc_name="vault",
                accion="REVOCACION_CREDENCIAL_VAULT",
                version_ant=1,
                version_nueva=1,
                autor=autor,
                motivo=f"Eliminacion de credencial [{nombre_limpio}] de la boveda cifrada."
            )
        return exito
    return False


def listar_secretos_disponibles() -> List[Dict[str, str]]:
    """
    Retorna el estado de configuracion de las llaves conocidas y personalizadas
    sin exponer los valores en texto plano.
    """
    secretos_boveda = _leer_todos_los_secretos_boveda()
    todas_las_claves = list(dict.fromkeys(CLAVES_ESTANDAR_RECOMENDADAS + list(secretos_boveda.keys())))

    resultado = []
    for clave in todas_las_claves:
        origen = "No Configurado"
        estado_badge = "[NO CONFIGURADO]"
        enmascarado = "-"

        # 1. Chequeo variable de entorno
        if clave in os.environ and os.environ[clave].strip():
            origen = "Variable de Entorno (OS)"
            estado_badge = "[CONFIGURADO]"
            enmascarado = "••••••••••••"
        # 2. Chequeo streamlit secrets
        else:
            try:
                import streamlit as st
                if hasattr(st, "secrets") and clave in st.secrets:
                    origen = "Streamlit Secrets"
                    estado_badge = "[CONFIGURADO]"
                    enmascarado = "••••••••••••"
            except Exception:
                pass

        # 3. Chequeo boveda local si no se detecto previamente
        if origen == "No Configurado" and clave in secretos_boveda and secretos_boveda[clave].strip():
            origen = "Bóveda Local Cifrada (AES-256)"
            estado_badge = "[CONFIGURADO]"
            enmascarado = "••••••••••••"

        resultado.append({
            "clave": clave,
            "origen": origen,
            "estado": estado_badge,
            "vista_previa": enmascarado
        })

    return resultado

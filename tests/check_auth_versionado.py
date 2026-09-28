"""Auto-verificación de autenticación (hash, límite de intentos) y versionado.

Ejecutar:  python tests/check_auth_versionado.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.auditoria as aud
import core.auth as auth


def check_hash():
    h1 = auth.generar_hash_password("secreta", salt="sal_fija_unica")
    h2 = auth.generar_hash_password("secreta", salt="sal_fija_unica")
    assert h1 == h2, "con la misma sal el hash debe ser determinista"
    assert h1 != auth.generar_hash_password("otra", salt="sal_fija_unica"), "debe depender del contenido"
    assert h1 != auth.generar_hash_password("secreta", salt="otra"), "debe depender de la sal"
    assert auth.generar_hash_password("secreta") != auth.generar_hash_password("secreta"), "sin sal explícita debe usar sal aleatoria"
    assert h1.startswith("pbkdf2_sha256$"), "el formato nuevo debe llevar prefijo"
    assert auth._verificar_hash("secreta", h1)
    assert not auth._verificar_hash("incorrecta", h1)
    assert not auth._verificar_hash("secreta", None)


def check_throttle():
    u = "usuario_throttle_test"
    auth._limpiar_fallos(u)
    for _ in range(auth._MAX_INTENTOS):
        assert not auth._esta_bloqueado(u)
        auth._registrar_fallo(u)
    assert auth._esta_bloqueado(u), "debe bloquear tras los intentos permitidos"
    auth._limpiar_fallos(u)
    assert not auth._esta_bloqueado(u), "un login exitoso debe limpiar el bloqueo"


def check_versionado(ruta_tmp):
    aud.HISTORY_DIR = os.path.join(ruta_tmp, "history")
    aud.DOCS_DIR = os.path.join(ruta_tmp, "docs")
    aud.AUDIT_LOG_PATH = os.path.join(ruta_tmp, "audit_log.json")
    os.makedirs(aud.DOCS_DIR, exist_ok=True)
    aud._obtener_historial_versiones_cached.cache_clear()

    store = {}
    historial = aud.inicializar_version_inicial_si_no_existe("d.md", "contenido uno", "Sistema", "inicial")
    assert len(historial) == 1 and historial[0]["version"] == 1

    v2 = aud.guardar_nueva_version("d.md", "contenido dos", "tester", "edicion", store)
    assert v2 == 2, f"esperado v2, obtenido v{v2}"

    v3 = aud.guardar_nueva_version("d.md", "contenido dos", "tester", "sin cambio", store)
    assert v3 == 2, "contenido idéntico no debe generar una versión nueva"

    assert len(aud.obtener_historial_versiones("d.md")) == 2


if __name__ == "__main__":
    check_hash()
    check_throttle()
    with tempfile.TemporaryDirectory() as tmp:
        check_versionado(tmp)
    print("[OK] check_auth_versionado")

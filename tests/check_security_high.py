import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.auth as auth
import core.vault as vault
from core.ui_mantenimientos import _es_consulta_solo_lectura


def check_hash():
    h = auth.generar_hash_password("secreta", salt="fija")
    assert auth._verificar_hash("secreta", h)
    assert not auth._verificar_hash("mala", h)
    legado = __import__("hashlib").pbkdf2_hmac(
        "sha256", b"secreta", auth._LEGACY_SALT.encode(), auth._PBKDF2_ITERATIONS
    ).hex()
    assert auth._verificar_hash("secreta", legado)
    print("[OK] hash")


def check_sql_guard():
    assert _es_consulta_solo_lectura("SELECT 1")
    assert _es_consulta_solo_lectura("SELECT 1;")
    assert _es_consulta_solo_lectura("WITH x AS (SELECT 1) SELECT * FROM x")
    assert not _es_consulta_solo_lectura("SELECT 1; DROP TABLE t")
    assert not _es_consulta_solo_lectura("DELETE FROM t")
    assert not _es_consulta_solo_lectura("SELECT 1; ATTACH 'f.db'")
    assert not _es_consulta_solo_lectura("COPY t TO 'x'")
    print("[OK] sql guard")


def check_vault_no_destruye():
    with tempfile.TemporaryDirectory() as td:
        vault.VAULT_FILE_PATH = os.path.join(td, ".vault.enc")
        vault.VAULT_KEY_PATH = os.path.join(td, ".vault.key")
        old_env = os.environ.get("VAULT_MASTER_KEY")
        try:
            os.environ["VAULT_MASTER_KEY"] = "passphrase_vault_correcta_123"
            assert vault.guardar_secreto("ALPHA", "valor_secreto")
            assert vault.obtener_secreto("ALPHA") == "valor_secreto"

            os.environ["VAULT_MASTER_KEY"] = "passphrase_completamente_distinta_xyz"
            try:
                vault.guardar_secreto("BETA", "otro")
                raise AssertionError("debio lanzar ErrorBoveda")
            except vault.ErrorBoveda:
                pass

            os.environ["VAULT_MASTER_KEY"] = "passphrase_vault_correcta_123"
            assert vault.obtener_secreto("ALPHA") == "valor_secreto", "secretos no deben perderse"
            assert vault.obtener_secreto("BETA") == "", "BETA no debio guardarse"
            print("[OK] vault no destruye")
        finally:
            if old_env is None:
                os.environ.pop("VAULT_MASTER_KEY", None)
            else:
                os.environ["VAULT_MASTER_KEY"] = old_env


if __name__ == "__main__":
    check_hash()
    check_sql_guard()
    check_vault_no_destruye()
    print("[OK] security_high")

"""Smoke test de runtime: ejercita la logica principal sin Streamlit server."""
import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ok, fail = [], []


def t(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append((name, e))
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()


import core.configuracion as cfg
t("config rutas", lambda: [cfg.DATA_DIR, cfg.CSV_PATH, cfg.ESTILOS_CSS_PATH])

import core.auth as auth
t("hash roundtrip", lambda: (_ for _ in ()).throw(AssertionError("hash no verifica")) if not auth._verificar_hash("x", auth.generar_hash_password("x")) else None)
t("users store", lambda: auth.inicializar_almacen_usuarios())
t("login master env", lambda: (_ for _ in ()).throw(AssertionError("login fallo")) if not auth.verificar_credenciales(
    "admin", os.environ.get("ADMIN_PASSWORD", "no")) else None)
t("login malo rechazado", lambda: (_ for _ in ()).throw(AssertionError("clave mala aceptada")) if auth.verificar_credenciales(
    "admin", "clave_incorrecta_xyz") else None)

import core.vault as vault
t("vault listar", lambda: vault.listar_secretos_disponibles())
t("vault leer GEMINI", lambda: vault.obtener_secreto("GEMINI_API_KEY"))

import core.motor as motor
t("duckdb conn", lambda: motor._obtener_conexion_duckdb())
t("sql SELECT 1", lambda: (_ for _ in ()).throw(AssertionError("SELECT 1 fallo")) if motor.ejecutar_consulta_sql("SELECT 1").empty else None)
t("sql ';' rechazado", lambda: (_ for _ in ()).throw(AssertionError("';' no rechazado")) if "Error" not in motor.ejecutar_consulta_sql(";").columns else None)
t("sql OFFSET permitido", lambda: (_ for _ in ()).throw(AssertionError("OFFSET bloqueado")) if "Error" in motor.ejecutar_consulta_sql("SELECT 1 OFFSET 2").columns else None)
t("firma doc", lambda: motor._firma_documental({"a": "x"}))
t("firma cambia con contenido", lambda: (_ for _ in ()).throw(AssertionError("firma ignora ediciones")) if motor._firma_documental({"a": "xy"}) == motor._firma_documental({"a": "xz"}) else None)

import core.procesador as proc
t("ext soportadas", lambda: proc.SUPPORTED_EXTENSIONS)

import core.db as db
t("pg check", lambda: db.es_postgres_disponible())

import core.migraciones, core.estilos, core.tags, core.plantillas, core.visor, core.manual
t("estilos css", lambda: len(core.estilos.cargar_estilos_css()) > 0)

import pandas as pd
if os.path.exists(cfg.CSV_PATH):
    df = pd.read_csv(cfg.CSV_PATH)
    t("csv leer", lambda: len(df))

    import core.ui_mantenimientos as um
    t("filtro inyectado vacio", lambda: len(df[
        df["tecnico"].astype(str).str.contains("' OR 1=1--", case=False, na=False, regex=False)
    ]))

    t("busqueda servidores", lambda: motor.buscar_servidores_duckdb("BALANCER"))
    t("sql custom valido", lambda: motor.ejecutar_consulta_sql(
        "SELECT count(*) FROM mantenimientos"))
    t("sql custom DROP rechazado", lambda: (
        (lambda r: r if "Error" in r.columns else (_ for _ in ()).throw(AssertionError("no rechazado")))
        (motor.ejecutar_consulta_sql("DROP TABLE mantenimientos"))
    ))

import core.auditoria as aud
t("audit leer", lambda: aud._leer_eventos_locales())

print()
print(f"OK: {len(ok)}  FAIL: {len(fail)}")
for n, e in fail:
    print(f"  - {n}: {e}")
sys.exit(1 if fail else 0)

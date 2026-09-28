"""Auto-verificación del log de auditoría local (append-only NDJSON).

Ejecutar:  python tests/check_auditoria_log.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.auditoria as aud


def _con_log_temporal(ruta: str):
    aud.AUDIT_LOG_PATH = ruta
    aud._obtener_todos_los_eventos_auditoria_cached.cache_clear()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "audit_log.json")

        # 1. Dos eventos => dos líneas independientes (append, sin reescritura total)
        _con_log_temporal(ruta)
        aud.registrar_evento_auditoria("d1", "CREACION", 0, 1, "tester", "m1")
        aud.registrar_evento_auditoria("d2", "EDICION", 1, 2, "tester", "m2")
        with open(ruta, encoding="utf-8") as f:
            lineas = [l for l in f.read().splitlines() if l.strip()]
        assert len(lineas) == 2, f"esperado 2 lineas, hay {len(lineas)}"
        assert [e["documento"] for e in aud._leer_eventos_locales()] == ["d1", "d2"]

        # 2. El lector tolera el formato antiguo (arreglo JSON completo)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump([{"documento": "viejo", "accion": "LEGADO"}], f)
        assert aud._leer_eventos_locales() == [{"documento": "viejo", "accion": "LEGADO"}]

        # 3. Una línea corrupta no rompe la lectura del resto
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(json.dumps({"documento": "ok"}) + "\n{no-json\n")
        assert len(aud._leer_eventos_locales()) == 1

    print("[OK] check_auditoria_log")


if __name__ == "__main__":
    main()

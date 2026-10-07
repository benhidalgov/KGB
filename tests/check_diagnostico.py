"""Auto-verificacion del autodiagnostico de portabilidad.

Ejecutar:  python tests/check_diagnostico.py
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.diagnostico as diag
from core.diagnostico import NIVEL_AVISO, NIVEL_ERROR, NIVEL_INFO, NIVEL_OK

NIVELES_VALIDOS = {NIVEL_OK, NIVEL_INFO, NIVEL_AVISO, NIVEL_ERROR}


def check_estructura():
    """Cada comprobacion debe ser unica, con nivel valido y accion cuando exige correccion."""
    comprobaciones = diag.ejecutar_diagnostico()
    assert comprobaciones, "el diagnostico debe devolver comprobaciones"
    ids = [c.id for c in comprobaciones]
    assert len(ids) == len(set(ids)), f"ids duplicados: {ids}"
    # El visor de imagenes es un fallo ya ocurrido: su comprobacion no debe desaparecer.
    assert "diagramas" in ids, "falta la comprobacion de diagramas e imagenes"
    for c in comprobaciones:
        assert c.nivel in NIVELES_VALIDOS, f"nivel invalido en {c.id}: {c.nivel}"
        assert c.titulo and c.detalle, f"comprobacion incompleta: {c.id}"
        # INFO describe el entorno; solo lo que exige correccion necesita accion.
        if c.nivel in (NIVEL_AVISO, NIVEL_ERROR):
            assert c.accion, f"toda comprobacion conforme a corregir debe indicar accion: {c.id}"
        if c.bloqueante:
            assert c.nivel == NIVEL_ERROR, f"solo un hallazgo critico puede ser bloqueante: {c.id}"
    print(f"[OK] estructura ({len(comprobaciones)} comprobaciones)")


def check_reporte():
    """El reporte de texto y el JSON deben describir el mismo conjunto."""
    comprobaciones = diag.ejecutar_diagnostico()
    texto = diag.formatear_texto(comprobaciones)
    assert "RESULTADO" in texto, "el reporte debe incluir el resumen"
    assert "DIAGNOSTICO DE PORTABILIDAD" in texto

    datos = diag.formatear_json(comprobaciones)
    assert datos["resultado"]["total"] == len(comprobaciones)
    assert len(datos["comprobaciones"]) == len(comprobaciones)
    assert datos["resultado"]["crit"] == sum(1 for c in comprobaciones if c.nivel == NIVEL_ERROR)
    assert diag.hay_criticos(comprobaciones) == (datos["resultado"]["crit"] > 0)
    # El informe JSON que emite la consola debe ser serializable y volver intacto.
    assert json.loads(json.dumps(datos, ensure_ascii=False))["comprobaciones"] == datos["comprobaciones"]
    print("[OK] reporte de texto y JSON")


def check_ejemplos():
    """El juego de ejemplo debe viajar en el repositorio y respetar el esquema del motor."""
    ruta_cmdb = os.path.join(diag.EJEMPLOS_DIR, "mantenimientos.csv")
    assert os.path.exists(ruta_cmdb), f"falta el ejemplo de CMDB: {ruta_cmdb}"
    with open(ruta_cmdb, "r", encoding="utf-8") as f:
        cabecera = next(csv.reader(f))
    assert [c.strip() for c in cabecera] == diag.COLUMNAS_CMDB, f"cabecera inesperada: {cabecera}"

    ruta_docs = os.path.join(diag.EJEMPLOS_DIR, "docs")
    assert os.path.isdir(ruta_docs), f"falta la carpeta de documentos de ejemplo: {ruta_docs}"
    documentos = [n for n in os.listdir(ruta_docs) if n.endswith(".md")]
    assert documentos, "debe haber al menos un documento de ejemplo"
    print(f"[OK] ejemplos ({len(documentos)} documentos)")


def check_siembra_bloqueada_en_produccion():
    """En produccion la siembra debe rechazarse sin escribir nada."""
    original = diag.ES_PRODUCCION
    destino = os.path.join(diag.APP_DIR, ".no-debe-crearse")
    try:
        diag.ES_PRODUCCION = True
        resultado = diag.sembrar_datos_ejemplo(destino_data=destino, permitir_produccion=False)
        assert resultado["error"], "en produccion la siembra debe rechazarse con un motivo"
        assert not resultado["copiados"], "no debe copiarse nada en produccion"
        assert not os.path.exists(destino), "no debe crearse ningun archivo"
    finally:
        diag.ES_PRODUCCION = original
    print("[OK] siembra bloqueada en produccion")


if __name__ == "__main__":
    check_estructura()
    check_reporte()
    check_ejemplos()
    check_siembra_bloqueada_en_produccion()
    print("[OK] check_diagnostico")

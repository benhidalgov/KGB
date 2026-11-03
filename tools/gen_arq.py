"""Genera `assets/arquitectura/modelo.json` desde el inventario Excel.

El Excel manda: es la unica entrada de datos del esquema. Este script solo lo
traduce a un modelo estable (capas, servicios, hosts, relaciones y flujos) que
despues consume el render. El .xlsx no se versiona; el JSON si.

    python tools/gen_arq.py --xlsx "C:\\ruta\\Inventario_Servidores_SMUCORP.xlsx"

Los flujos transaccionales no estan en el Excel: se mantienen aca y se validan
contra los servicios de la hoja "Servicios" al generar.
"""
import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(ROOT, "assets", "arquitectura", "modelo.json")

sys.path.insert(0, ROOT)
from core.arq_render import generar as generar_html          # noqa: E402

# La capa 8 no existe en el Excel: el plano de gestion se separo en operacion
# (7) y hosting/entrega (8). Estos dos servicios salen de la hoja "Servicios".
REUBICADOS = {"Azure DevOps": 8, "vCloud GTD (IaaS 2.0 / 2.1)": 8}
NOMBRE_CAPA_8 = "Hosting, entrega y despliegue"
PLANO = {6: "externo", 7: "gestion", 8: "gestion"}

# Relaciones entre capas: conocimiento estructural, no esta en el Excel.
RELACIONES = [
    {"desde": 1, "hasta": 2, "etiqueta": "HTTPS", "tipo": "flujo"},
    {"desde": 2, "hasta": 3, "etiqueta": "IPSec", "tipo": "flujo"},
    {"desde": 3, "hasta": 4, "etiqueta": "ISO 8583", "tipo": "flujo"},
    {"desde": 4, "hasta": 5, "etiqueta": "JDBC", "tipo": "flujo"},
    {"desde": 1, "hasta": 6, "etiqueta": "REST", "tipo": "flujo"},
    {"desde": 3, "hasta": 6, "etiqueta": "ISO 8583", "tipo": "flujo"},
    {"desde": 4, "hasta": 6, "etiqueta": "JDBC", "tipo": "flujo"},
    {"desde": 7, "hasta": 5, "etiqueta": "monitorea", "tipo": "gestion"},
    {"desde": 7, "hasta": 4, "etiqueta": "monitorea", "tipo": "gestion"},
]

# Cada paso es (capa, servicio, via): `via` etiqueta el tramo que llega al paso,
# tomada de RELACIONES cuando existe; vacia cuando el dato no esta confirmado.
FLUJOS = [
    {"id": "compra-pos", "nombre": "Compra en POS", "pasos": [
        (1, "Geocom / BBR SW de Cajas", ""), (2, "Firewalls FortiGate 100E (HA)", "HTTPS"),
        (3, "Switch transaccional Unicard (ISO 8583)", "IPSec"),
        (4, "App Booking Unicard Transaccional", "ISO 8583"),
        (5, "SQL Server – BD Canales", "JDBC"),
        (6, "Minsait Payments / NUEK (Switch Core)", "")]},
    {"id": "compra-wallet", "nombre": "Compra desde wallet Unipay", "pasos": [
        (1, "App Móvil Unipay (Wallet)", ""), (2, "Firewalls FortiGate 100E (HA)", "HTTPS"),
        (3, "WSO2 API Manager & ESB (clúster)", "IPSec"),
        (4, "Pasarelas de canales", "REST"),
        (5, "SQL Server – BD Canales", "JDBC"),
        (6, "Minsait Payments / NUEK (Switch Core)", "")]},
    {"id": "portal-unipay", "nombre": "Autogestión en portal web", "pasos": [
        (1, "Portal Web Clientes Unipay", ""), (2, "Firewalls FortiGate 100E (HA)", "HTTPS"),
        (3, "WSO2 API Manager & ESB (clúster)", "IPSec"),
        (4, "CRM Engage", "REST"),
        (5, "SQL Server – BD Engage", "JDBC")]},
    {"id": "recaudacion", "nombre": "Recaudación externa", "pasos": [
        (1, "Portal Unired / cajas XCash", ""),
        (3, "WSO2 API Manager & ESB (clúster)", "HTTPS"),
        (4, "Pasarelas de canales", "REST"),
        (5, "SQL Server – BD Canales", "JDBC"), (6, "Unired", "")]},
    {"id": "conciliacion-batch", "nombre": "Conciliación batch nocturna", "pasos": [
        (1, "WebServices REST y lotes SFTP diarios", ""),
        (3, "Servidor SFTP", "SFTP"),
        (5, "Jenkins (malla batch nocturna)", ""), (5, "Datamart BI", "")]},
]


def _id(texto: str) -> str:
    """Slug estable usado como id de servicio."""
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", plano.lower())).strip("-")


def _capa_de_host(sistema: str, nivel: str) -> int:
    """Mapea un servidor a capa: Nivel infraestructura y, si es transversal, Sistema."""
    n = nivel.strip().lower()
    if n in ("frontend", "back-end", "backend"):
        return 4
    if n == "middleware":
        return 3
    if n == "base de datos":
        return 5
    if n == "gtd":
        return 8
    if n in ("explotacion", "explotación", "monitoreo"):
        return 7
    s = sistema.strip().upper()
    if "BALANCEADOR" in s:
        return 2
    if s in ("ACTIVE DIRECTORY", "WSO2 TRUST", "SFTP"):
        return 3
    if s in ("DOCUMENTAL", "CORREO USO VZOR", "SHAREPOINT"):
        return 4
    if s in ("JENKINS", "CANALES"):
        return 5
    return 0


def construir(xlsx: str) -> dict:
    inventario = pd.ExcelFile(xlsx).parse("Inventario", dtype=str).fillna("")
    servicios_xls = pd.ExcelFile(xlsx).parse("Servicios", dtype=str).fillna("")

    capas = {i: {"id": i, "nombre": "", "plano": PLANO.get(i, "trafico"),
                 "servicios": [], "servidores": 0, "criticos": 0} for i in range(1, 9)}

    for _, fila in servicios_xls.iterrows():
        nombre = str(fila.iloc[2]).strip()
        capa_txt = str(fila.iloc[0]).strip()
        if not nombre or not re.match(r"^\d+\.", capa_txt):
            continue                                     # filas de totales
        numero = int(capa_txt.split(".")[0])
        numero = REUBICADOS.get(nombre, numero)
        capas[numero]["nombre"] = capas[numero]["nombre"] or capa_txt.split(".", 1)[1].strip()
        capas[numero]["servicios"].append({
            "id": _id(nombre), "nombre": nombre,
            "categoria": str(fila.iloc[1]).strip(),
            "descripcion": str(fila.iloc[3]).strip(),
            "externo": str(fila.iloc[4]).strip().lower() == "externo",
        })
    capas[8]["nombre"] = NOMBRE_CAPA_8

    hosts, sin_capa = [], []
    for _, fila in inventario.iterrows():
        sistema = str(fila.iloc[6]).strip()
        nivel = str(fila.iloc[13]).strip()
        host = str(fila.iloc[1]).strip()
        if not host:
            continue
        capa = _capa_de_host(sistema, nivel)
        if not capa:
            sin_capa.append(host)
        critico = str(fila.iloc[5]).strip().upper() == "CRITICO"
        hosts.append({"hostname": host, "ip": str(fila.iloc[0]).strip(), "sistema": sistema,
                      "nivel": nivel, "capa": capa, "critico": critico})
        if capa:
            capas[capa]["servidores"] += 1
            capas[capa]["criticos"] += int(critico)
    if sin_capa:
        raise SystemExit(f"servidores sin capa asignada: {sin_capa}")

    ids = {s["id"] for c in capas.values() for s in c["servicios"]}
    flujos = []
    for flujo in FLUJOS:
        pasos = []
        for capa, nombre, via in flujo["pasos"]:
            sid = _id(nombre)
            if sid not in ids:
                raise SystemExit(f"flujo {flujo['id']}: servicio desconocido {nombre!r}")
            pasos.append({"capa": capa, "servicio": sid, "via": via})
        flujos.append({"id": flujo["id"], "nombre": flujo["nombre"], "pasos": pasos})

    mtime = datetime.date.fromtimestamp(os.path.getmtime(xlsx)).isoformat()
    return {
        "meta": {
            "fuente": os.path.basename(xlsx),
            "fuente_actualizada": mtime,
            "total_servidores": len(hosts),
            "total_servicios": sum(len(c["servicios"]) for c in capas.values()),
            "total_criticos": sum(1 for h in hosts if h["critico"]),
        },
        "capas": [c for c in capas.values() if c["servicios"] or c["servidores"]],
        "hosts": hosts,
        "relaciones": RELACIONES,
        "flujos": flujos,
    }


def main():
    ap = argparse.ArgumentParser(description="Genera modelo.json del esquema de arquitectura")
    ap.add_argument("--xlsx", required=True, help="ruta al Inventario_Servidores_SMUCORP.xlsx")
    ap.add_argument("--salida", default=SALIDA)
    args = ap.parse_args()

    modelo = construir(args.xlsx)
    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    with open(args.salida, "w", encoding="utf-8", newline="\n") as f:
        json.dump(modelo, f, ensure_ascii=False, indent=1)
        f.write("\n")
    ruta_html = generar_html(args.salida)

    for capa in modelo["capas"]:
        print(f"  capa {capa['id']} · {capa['nombre']}: {len(capa['servicios'])} servicios, "
              f"{capa['servidores']} servidores, {capa['criticos']} criticos")
    m = modelo["meta"]
    print(f"[OK] {args.salida}: {m['total_servicios']} servicios, "
          f"{m['total_servidores']} servidores, {m['total_criticos']} criticos, "
          f"{len(modelo['flujos'])} flujos")
    print(f"[OK] {ruta_html}")


if __name__ == "__main__":
    main()

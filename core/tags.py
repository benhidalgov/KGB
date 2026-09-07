"""
Módulo de Gestión de Categorías y Tags Documentales.
Permite clasificar, filtrar y persistir etiquetas para la base documental corporativa.
"""
import os
import json
import re
import importlib

try:
    import core.configuracion
    if not hasattr(core.configuracion, "CATEGORIAS_PATH"):
        importlib.reload(core.configuracion)
    CATEGORIAS_PATH = getattr(core.configuracion, "CATEGORIAS_PATH", os.path.join("data", "categorias.json"))
except Exception:
    CATEGORIAS_PATH = os.path.join("data", "categorias.json")

SIGLAS_COMUNES = {
    "CMDB", "DRP", "SSL", "TLS", "API", "REST", "SOAP", "BD", "SQL", "SAN",
    "NAS", "IP", "DNS", "SSH", "VPN", "VLAN", "DMZ", "APM", "SAP", "QA",
    "PRD", "DEV", "SOP", "CPU", "RAM", "HA", "DR", "LAN", "WAN", "VM", "ESXI"
}


def normalizar_categoria(cat: str) -> str:
    """Limpia y estandariza el nombre de una categoría conservando siglas técnicas."""
    if not cat:
        return ""
    c = cat.strip()
    c = re.sub(r'\s+', ' ', c)
    palabras = c.split()
    res = []
    for p in palabras:
        if p.upper() in SIGLAS_COMUNES:
            res.append(p.upper())
        elif len(p) <= 2:
            res.append(p.lower() if p.lower() in {"de", "en", "y", "a"} else p.upper())
        else:
            res.append(p.capitalize())
    return " ".join(res)


def cargar_datos_categorias() -> dict:
    """Carga el catálogo de categorías y mapeo de documentos desde data/categorias.json."""
    if os.path.exists(CATEGORIAS_PATH):
        try:
            with open(CATEGORIAS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "categorias" not in data or not isinstance(data["categorias"], list):
                        data["categorias"] = []
                    if "documentos" not in data or not isinstance(data["documentos"], dict):
                        data["documentos"] = {}
                    return data
        except Exception:
            pass
    return {"categorias": [], "documentos": {}}


def guardar_datos_categorias(data: dict) -> bool:
    """Guarda atómicamente el catálogo de categorías y mapeo de documentos."""
    try:
        os.makedirs(os.path.dirname(CATEGORIAS_PATH), exist_ok=True)
        tmp_path = f"{CATEGORIAS_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if os.path.exists(CATEGORIAS_PATH):
            os.replace(tmp_path, CATEGORIAS_PATH)
        else:
            os.rename(tmp_path, CATEGORIAS_PATH)
        return True
    except Exception:
        return False


def obtener_categorias_disponibles() -> list[str]:
    """Retorna la lista ordenada de todas las categorías registradas en el sistema."""
    data = cargar_datos_categorias()
    return sorted(list(set([normalizar_categoria(c) for c in data.get("categorias", []) if c.strip()])))


def registrar_categoria(cat_nombre: str) -> str | None:
    """Registra una nueva categoría en el catálogo si es válida y no existe."""
    cat_limpia = normalizar_categoria(cat_nombre)
    if not cat_limpia or len(cat_limpia) < 2:
        return None
    data = cargar_datos_categorias()
    if cat_limpia not in data["categorias"]:
        data["categorias"].append(cat_limpia)
        data["categorias"].sort()
        guardar_datos_categorias(data)
    return cat_limpia


def obtener_tags_documento(doc_name: str) -> list[str]:
    """Retorna la lista de tags/categorías asociadas a un documento específico."""
    data = cargar_datos_categorias()
    docs = data.get("documentos", {})
    if doc_name in docs:
        return docs[doc_name]
    # Búsqueda por coincidencia de nombre base para diagramas
    if doc_name.startswith("DIAGRAMA__"):
        base_alias = doc_name.replace("DIAGRAMA__", "").replace(".md", "")
        for k, v in docs.items():
            if base_alias in k:
                return v
    return []


def asignar_tags_documento(doc_name: str, tags: list[str], autor: str = "Técnico") -> bool:
    """Asocia una lista de tags/categorías a un documento y asegura su registro en el catálogo."""
    tags_limpios = []
    for t in tags:
        norm = normalizar_categoria(t)
        if norm and norm not in tags_limpios:
            tags_limpios.append(norm)

    if not tags_limpios:
        return False

    data = cargar_datos_categorias()
    # Asegurar que cada tag esté presente en la lista global de categorías
    for t in tags_limpios:
        if t not in data["categorias"]:
            data["categorias"].append(t)
    data["categorias"].sort()

    data.setdefault("documentos", {})[doc_name] = tags_limpios
    return guardar_datos_categorias(data)


def filtrar_documentos_por_categoria(doc_list: list[str], categoria: str) -> list[str]:
    """Filtra una lista de nombres de documentos según la categoría seleccionada."""
    if not categoria or categoria == "Todas":
        return doc_list
    data = cargar_datos_categorias()
    docs = data.get("documentos", {})
    res = []
    for d in doc_list:
        tags_d = docs.get(d, [])
        if categoria in tags_d:
            res.append(d)
        elif d.startswith("DIAGRAMA__"):
            base_alias = d.replace("DIAGRAMA__", "").replace(".md", "")
            for k, v in docs.items():
                if base_alias in k and categoria in v:
                    res.append(d)
                    break
    return res


REGLAS_SUGERENCIA = [
    ("Almacenamiento y SAN", ["san", "purestorage", "storage", "disco", "lun", "raid", "nfs", "iscsi"]),
    ("Redes y Conectividad", ["red", "redes", "vlan", "nsx", "cisco", "switch", "router", "firewall", "vpn", "ip", "dns", "balancer", "f5"]),
    ("Servidores y Datacenter", ["vmware", "esxi", "blade", "hpe", "servidor", "srv", "chasis", "datacenter", "hardware"]),
    ("Middleware y APIs", ["wso2", "synapse", "api", "rest", "soap", "orquestador", "jwt", "gateway", "microservicio"]),
    ("Bases de Datos y Cache", ["db", "sql", "mysql", "postgresql", "oracle", "redis", "mongo", "database", "cluster_cache"]),
    ("Monitoreo y Alertas", ["nagios", "newrelic", "alertamiento", "metricas", "log", "logs", "postmortem", "incidente", "p1"]),
    ("Continuidad y DRP", ["backup", "veeam", "contingencia", "rollback", "drp", "recuperacion", "failover"]),
    ("Seguridad y Accesos", ["seguridad", "acceso", "formulario", "auditoria", "antivirus", "parchado", "credencial", "usuarios"]),
    ("Procedimientos y Release", ["booking", "despliegue", "pipeline", "procedimiento", "manual", "runbook", "release"]),
    ("Arquitectura y Sistemas", ["arquitectura", "flujo", "diagrama", "unicard", "sistema", "topologia", "cmdb"]),
]


def sugerir_categoria_documento(doc_name: str, content: str = "") -> str:
    """Sugiere una categoría apropiada según heurísticas de nombre y contenido técnico."""
    doc_tokens = set(re.split(r'[^a-z0-9]+', doc_name.lower()))
    for cat, keywords in REGLAS_SUGERENCIA:
        for kw in keywords:
            if " " in kw:
                if kw in doc_name.lower():
                    return cat
            else:
                if kw.lower() in doc_tokens:
                    return cat

    if content:
        sample_lower = content[:2000].lower()
        sample_tokens = set(re.split(r'[^a-z0-9]+', sample_lower))
        for cat, keywords in REGLAS_SUGERENCIA:
            for kw in keywords:
                if " " in kw:
                    if kw in sample_lower:
                        return cat
                else:
                    if kw.lower() in sample_tokens:
                        return cat

    return "Infraestructura General"


def obtener_documentos_sin_categoria(doc_list: list[str]) -> list[str]:
    """Retorna los documentos de la lista que no tienen categoría asignada."""
    data = cargar_datos_categorias()
    docs = data.get("documentos", {})
    pendientes = []
    for d in doc_list:
        tags = docs.get(d, [])
        if not tags and d.startswith("DIAGRAMA__"):
            base_alias = d.replace("DIAGRAMA__", "").replace(".md", "")
            for k, v in docs.items():
                if base_alias in k and v:
                    tags = v
                    break
        if not tags:
            pendientes.append(d)
    return pendientes


def asignar_tags_en_lote(doc_tags_map: dict[str, list[str]], autor: str = "Operaciones") -> int:
    """Asigna categorías a múltiples documentos en una única operación atómica."""
    if not doc_tags_map:
        return 0

    data = cargar_datos_categorias()
    categorias_set = set(data.get("categorias", []))
    docs_map = data.setdefault("documentos", {})

    actualizados = 0
    for doc_name, tags in doc_tags_map.items():
        tags_limpios = []
        for t in tags:
            norm = normalizar_categoria(t)
            if norm and norm not in tags_limpios:
                tags_limpios.append(norm)

        if tags_limpios:
            for t in tags_limpios:
                categorias_set.add(t)
            docs_map[doc_name] = tags_limpios
            actualizados += 1

    data["categorias"] = sorted(list(categorias_set))
    guardar_datos_categorias(data)
    return actualizados


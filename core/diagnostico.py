"""Modulo de Autodiagnostico de Portabilidad (doctor).

Comprueba si esta maquina puede ejecutar la consola y explica, en lenguaje
operativo, que falta cuando no puede: version de Python, dependencias reales
frente a requirements.txt, rutas y permisos de escritura, datos de arranque,
boveda y cuentas, servicios externos (PostgreSQL y Gemini), puerto de escucha
y cadena de importacion de la aplicacion.

Uso:
    python -m core.diagnostico
    python -m core.diagnostico --crear-datos-ejemplo
    python -m core.diagnostico --informe diagnostico.txt
    python -m core.diagnostico --json

Codigo de salida: 0 si no hay hallazgos criticos, 1 si hay alguno.
"""
import argparse
import csv
import importlib
import importlib.metadata
import importlib.util
import json
import locale
import logging
import os
import platform
import shutil
import socket
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

def _silenciar_avisos_de_streamlit() -> None:
    """Eleva los registradores de Streamlit antes de importar los modulos del proyecto.

    Streamlit avisa por consola cuando no hay runtime de servidor, y el
    diagnostico importa la aplicacion completa: sin esto, el informe queda
    enterrado entre advertencias.
    """
    try:
        import streamlit  # noqa: F401  (crea los registradores hijos que se van a elevar)
    except Exception:
        return
    logging.getLogger("streamlit").setLevel(logging.ERROR)
    for nombre in list(logging.root.manager.loggerDict):
        if nombre.startswith("streamlit"):
            logging.getLogger(nombre).setLevel(logging.ERROR)


_silenciar_avisos_de_streamlit()

from core.configuracion import (
    APP_DIR,
    CATEGORIAS_PATH,
    CSV_PATH,
    DATA_DIR,
    DOCS_DIR,
    ES_PRODUCCION,
    ESTILOS_CSS_PATH,
    HISTORY_DIR,
    ORIGINALS_DIR,
    USERS_PATH,
    VAULT_FILE_PATH,
    VAULT_KEY_PATH,
)

NIVEL_OK = "OK"
NIVEL_INFO = "INFO"
NIVEL_AVISO = "WARN"
NIVEL_ERROR = "CRIT"

BANDERAS = {
    NIVEL_OK: "[OK]",
    NIVEL_INFO: "[INFO]",
    NIVEL_AVISO: "[WARN]",
    NIVEL_ERROR: "[CRIT]",
}

REQUISITOS_PATH = os.path.join(APP_DIR, "requirements.txt")
EJEMPLOS_DIR = os.path.join(APP_DIR, "ejemplos")
PUERTO_POR_DEFECTO = 8501

# Esquema exigido por core/motor.py al cargar la CMDB en DuckDB.
COLUMNAS_CMDB = [
    "servidor_id", "numero_serie", "ip", "vcloud_vm", "nivel_arquitectura",
    "componente", "fecha", "tipo_mantenimiento", "tecnico", "descripcion",
    "estado", "nagios_check",
]

MODULOS_CRITICOS = (
    "core.configuracion",
    "core.motor",
    "core.procesador",
    "core.visor",
    "core.auditoria",
    "core.auth",
    "core.tags",
    "core.plantillas",
    "core.manual",
    "core.estilos",
    "core.migraciones",
    "core.ui_sidebar",
)

CUENTAS_MAESTRAS = ("admin", "operador", "auditor")
MARCAS_CONFLICTO = ("<<<<<<<", ">>>>>>>")


@dataclass
class Comprobacion:
    """Resultado de una verificacion concreta."""

    id: str
    titulo: str
    nivel: str
    detalle: str
    accion: str = ""
    bloqueante: bool = False


@dataclass
class EstadoBoveda:
    """Estado de la boveda cifrada y los secretos que se pudieron leer."""

    estado: str
    secretos: Dict[str, str] = field(default_factory=dict)
    detalle: str = ""


class Contexto:
    """Hechos costosos de obtener, calculados una sola vez por diagnostico."""

    def __init__(self) -> None:
        self._base_datos: Optional[Tuple[bool, bool, str]] = None
        self._boveda: Optional[EstadoBoveda] = None

    @property
    def base_datos(self) -> Tuple[bool, bool, str]:
        """(configurada, responde, error)."""
        if self._base_datos is None:
            self._base_datos = self._calcular_base_datos()
        return self._base_datos

    @property
    def boveda(self) -> EstadoBoveda:
        if self._boveda is None:
            self._boveda = self._calcular_boveda()
        return self._boveda

    def _calcular_base_datos(self) -> Tuple[bool, bool, str]:
        configurada = bool(os.environ.get("DATABASE_URL") or os.environ.get("DB_HOST"))
        if not configurada:
            return False, False, "sin configuracion"
        _silenciar_avisos_de_streamlit()
        try:
            import core.db as db
        except Exception as e:
            return True, False, f"no se pudo importar core.db: {e}"
        try:
            return True, bool(db.es_postgres_disponible()), ""
        except Exception as e:
            return True, False, f"{type(e).__name__}: {e}"

    def _calcular_boveda(self) -> EstadoBoveda:
        clave_env = os.environ.get("VAULT_MASTER_KEY", "").strip()
        hay_archivo = os.path.exists(VAULT_FILE_PATH)
        hay_llave = os.path.exists(VAULT_KEY_PATH)
        if not hay_archivo:
            return EstadoBoveda("sin_boveda", {}, "no hay boveda cifrada en la carpeta de datos")
        # No se invoca a core.vault sin llave disponible: en desarrollo, leer
        # generaria un data/.vault.key nuevo y romperia la boveda existente.
        if not clave_env and not hay_llave:
            return EstadoBoveda(
                "sin_clave", {},
                "existe data/.vault.enc pero no hay VAULT_MASTER_KEY ni data/.vault.key",
            )
        _silenciar_avisos_de_streamlit()
        try:
            import core.vault as vault
        except Exception as e:
            return EstadoBoveda("ilegible", {}, f"no se pudo importar core.vault: {e}")
        try:
            secretos = vault._leer_todos_los_secretos_boveda()
            return EstadoBoveda("ok", dict(secretos), f"{len(secretos)} secreto(s) legibles")
        except Exception as e:
            return EstadoBoveda("ilegible", {}, str(e))


def _destino_base_datos() -> str:
    """Describe el destino de PostgreSQL sin exponer credenciales."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        try:
            partes = urlsplit(url)
            base = (partes.path or "/").lstrip("/") or "?"
            return f"{partes.hostname or '?'}:{partes.port or 5432}/{base}"
        except Exception:
            return "DATABASE_URL definida (no se pudo interpretar)"
    return f"{os.environ.get('DB_HOST', '?')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', '?')}"


def _version_instalada(nombre: str) -> Optional[str]:
    try:
        return importlib.metadata.version(nombre)
    except Exception:
        return None


def _cumple_especificador(instalada: str, especificador: str) -> bool:
    if not especificador:
        return True
    try:
        from packaging.specifiers import SpecifierSet
    except Exception:
        return True  # Sin packaging no se puede verificar: no se reporta como error.
    try:
        return SpecifierSet(especificador).contains(instalada, prereleases=True)
    except Exception:
        return True


def _parsear_requisito(linea: str) -> Tuple[Optional[str], str, bool, str]:
    """(nombre, especificador, aplica_en_este_interprete, error)."""
    try:
        from packaging.requirements import Requirement
    except Exception:
        return _parsear_requisito_simple(linea)
    try:
        requisito = Requirement(linea)
    except Exception as e:
        return None, "", False, f"{linea}: {e}"
    aplica = requisito.marker.evaluate() if requisito.marker else True
    return requisito.name, str(requisito.specifier), bool(aplica), ""


def _parsear_requisito_simple(linea: str) -> Tuple[Optional[str], str, bool, str]:
    """Respaldo sin packaging: se ignoran marcadores y extras."""
    cuerpo = linea.split(";", 1)[0].strip()
    if ";" in linea:
        return None, "", False, f"{linea}: marcador no evaluable sin packaging"
    for indice, caracter in enumerate(cuerpo):
        if caracter in "<>=!":
            nombre = cuerpo[:indice].split("[", 1)[0].strip()
            return nombre, cuerpo[indice:].strip(), True, ""
    return cuerpo.split("[", 1)[0].strip(), "", True, ""


def _leer_requisitos() -> Tuple[List[str], str]:
    if not os.path.exists(REQUISITOS_PATH):
        return [], f"no existe {REQUISITOS_PATH}"
    try:
        with open(REQUISITOS_PATH, "r", encoding="utf-8") as f:
            lineas = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    except OSError as e:
        return [], str(e)
    return lineas, ""


# ---------------------------------------------------------------------------
# Comprobaciones
# ---------------------------------------------------------------------------

def _comprobar_equipo() -> List[Comprobacion]:
    detalle = (
        f"{platform.system()} {platform.release()} | equipo {platform.node()} | "
        f"{platform.python_implementation()} {platform.python_version()} | "
        f"zona horaria {time.tzname[0]} | codificacion preferida {locale.getpreferredencoding(False)}"
    )
    return [Comprobacion("equipo", "Equipo e interprete", NIVEL_INFO, detalle)]


def _comprobar_python() -> List[Comprobacion]:
    salida: List[Comprobacion] = []
    version = sys.version_info
    texto = f"Python {platform.python_version()} en {sys.executable}"
    if version < (3, 10):
        salida.append(Comprobacion(
            "python_version", "Version de Python", NIVEL_ERROR,
            f"{texto}. La aplicacion usa sintaxis de Python 3.10 o superior (uniones de tipo X | None).",
            "Instale Python 3.12 y recree el entorno: py -3.12 -m venv .venv", True,
        ))
    elif version[:2] != (3, 12):
        salida.append(Comprobacion(
            "python_version", "Version de Python", NIVEL_AVISO,
            f"{texto}. El contenedor y el entorno verificado usan Python 3.12; con otra version "
            "alguna dependencia fijada puede no ofrecer rueda precompilada.",
            "Use Python 3.12 para reproducir el entorno de referencia.",
        ))
    else:
        salida.append(Comprobacion("python_version", "Version de Python", NIVEL_OK, texto))

    en_venv = sys.prefix != sys.base_prefix
    venv_proyecto = os.path.normcase(os.path.abspath(sys.prefix)) == os.path.normcase(
        os.path.abspath(os.path.join(APP_DIR, ".venv"))
    )
    if venv_proyecto:
        salida.append(Comprobacion(
            "entorno_virtual", "Entorno virtual", NIVEL_OK,
            f"Se ejecuta desde el entorno del proyecto: {sys.prefix}",
        ))
    elif en_venv:
        salida.append(Comprobacion(
            "entorno_virtual", "Entorno virtual", NIVEL_AVISO,
            f"Se ejecuta desde otro entorno virtual: {sys.prefix}",
            "Active el entorno del proyecto: .venv\\Scripts\\activate",
        ))
    else:
        salida.append(Comprobacion(
            "entorno_virtual", "Entorno virtual", NIVEL_AVISO,
            "Se ejecuta con el interprete global del sistema, no con un entorno del proyecto.",
            "Cree el entorno: python -m venv .venv  y luego  .venv\\Scripts\\python -m pip install -r requirements.txt",
        ))
    return salida


def _comprobar_dependencias() -> List[Comprobacion]:
    lineas, error = _leer_requisitos()
    if error:
        return [Comprobacion(
            "dependencias", "Dependencias", NIVEL_ERROR,
            f"No se pudo leer requirements.txt: {error}",
            "Restaure requirements.txt desde el repositorio.", True,
        )]

    faltantes: List[str] = []
    desalineadas: List[str] = []
    omitidas: List[str] = []
    sin_evaluar: List[str] = []
    aplicables = 0
    for linea in lineas:
        nombre, especificador, aplica, fallo = _parsear_requisito(linea)
        if fallo:
            sin_evaluar.append(fallo)
            continue
        if not aplica:
            omitidas.append(nombre or linea)
            continue
        aplicables += 1
        instalada = _version_instalada(nombre or linea)
        if instalada is None:
            faltantes.append(f"{nombre} ({especificador or 'sin pin'})")
        elif not _cumple_especificador(instalada, especificador):
            desalineadas.append(f"{nombre}: instalado {instalada}, se espera {especificador}")

    salida: List[Comprobacion] = []
    if faltantes:
        salida.append(Comprobacion(
            "dependencias", "Dependencias", NIVEL_ERROR,
            "Paquetes exigidos que no estan instalados: " + "; ".join(faltantes),
            "Instale el entorno completo: .venv\\Scripts\\python -m pip install -r requirements.txt",
        ))
    if desalineadas:
        salida.append(Comprobacion(
            "dependencias_version", "Versiones de dependencias", NIVEL_AVISO,
            "Diferencias frente a requirements.txt: " + "; ".join(desalineadas),
            "Reinstale para igualar el entorno de referencia: pip install -r requirements.txt",
        ))
    if not faltantes and not desalineadas:
        salida.append(Comprobacion(
            "dependencias", "Dependencias", NIVEL_OK,
            f"{aplicables} paquete(s) aplicables instalados y alineados con requirements.txt",
        ))
    if omitidas:
        salida.append(Comprobacion(
            "dependencias_omitidas", "Dependencias segun version de Python", NIVEL_INFO,
            "No aplican en este interprete: " + ", ".join(omitidas),
        ))
    if sin_evaluar:
        salida.append(Comprobacion(
            "dependencias_sin_evaluar", "Dependencias no evaluadas", NIVEL_AVISO,
            "; ".join(sin_evaluar),
            "Instale packaging para verificar todos los requisitos: pip install packaging",
        ))
    return salida


def _probar_creacion(carpeta: str, etiqueta: str) -> str:
    """Intenta crear y borrar un archivo de prueba. Devuelve "" si pudo escribir."""
    if not os.path.isdir(carpeta):
        return f"la carpeta no existe ({carpeta})"
    ruta = os.path.join(carpeta, f".diagnostico_{etiqueta}_{os.getpid()}.tmp")
    error = ""
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("diagnostico")
    except OSError as e:
        error = f"{type(e).__name__}: {e}"
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass
    return error


def _comprobar_rutas() -> List[Comprobacion]:
    salida: List[Comprobacion] = []
    faltantes = [r for r in (APP_DIR, DATA_DIR, DOCS_DIR) if not os.path.isdir(r)]
    if faltantes:
        salida.append(Comprobacion(
            "rutas", "Rutas del proyecto", NIVEL_ERROR,
            "No existen carpetas requeridas: " + "; ".join(faltantes),
            "Verifique que copio el proyecto completo; core/configuracion.py recrea data/ al importarse.", True,
        ))
    else:
        salida.append(Comprobacion(
            "rutas", "Rutas del proyecto", NIVEL_OK,
            f"Carpeta base: {APP_DIR} | datos: {DATA_DIR}",
        ))

    if os.path.exists(ESTILOS_CSS_PATH):
        salida.append(Comprobacion(
            "estilos", "Hoja de estilos", NIVEL_OK,
            f"core/estilos.css presente ({os.path.getsize(ESTILOS_CSS_PATH)} bytes)",
        ))
    else:
        salida.append(Comprobacion(
            "estilos", "Hoja de estilos", NIVEL_ERROR,
            f"No se encontro {ESTILOS_CSS_PATH}",
            "Restaure core/estilos.css desde el repositorio.",
        ))

    # La carpeta de datos es la unica que la aplicacion escribe en caliente
    # (auditoria, ingesta, usuarios, boveda). Se prueba tambien la raiz del
    # proyecto: si la raiz acepta escritura y data/ no, el bloqueo es de la
    # carpeta; si ninguna acepta, el bloqueo es del propio proceso.
    error_datos = _probar_creacion(DATA_DIR, "datos")
    if not error_datos:
        salida.append(Comprobacion(
            "permisos_escritura", "Permisos de escritura en data/", NIVEL_OK,
            f"Escritura verificada en {DATA_DIR}",
        ))
    else:
        error_raiz = _probar_creacion(APP_DIR, "raiz")
        if error_raiz:
            salida.append(Comprobacion(
                "permisos_escritura", "Permisos de escritura en data/", NIVEL_AVISO,
                f"No se pudo escribir ni en {DATA_DIR} ({error_datos}) ni en {APP_DIR} ({error_raiz}): una capa de "
                "confinamiento (sandbox de la sesion, antivirus o politica de la carpeta) bloquea a este proceso.",
                "Repita el diagnostico desde la misma consola con la que arranca la aplicacion para obtener el veredicto real.",
            ))
        else:
            salida.append(Comprobacion(
                "permisos_escritura", "Permisos de escritura en data/", NIVEL_ERROR,
                f"No se pueden crear archivos en {DATA_DIR} ({error_datos}) aunque la raiz del proyecto si acepta "
                "escritura: la consola no podra auditar, ingerir documentos ni guardar usuarios.",
                "Otorgue control total a su usuario sobre la carpeta data/ (Propiedades, Seguridad) o copie el proyecto "
                "a una ruta local propia; si el bloqueo viene de un confinamiento o del antivirus, repita el diagnostico "
                "desde la consola con la que arranca la aplicacion.", True,
            ))
    return salida


def _comprobar_ubicacion() -> List[Comprobacion]:
    riesgos: List[str] = []
    minuscula = APP_DIR.lower()
    for nombre in ("onedrive", "dropbox", "google drive", "icloud"):
        if nombre in minuscula:
            riesgos.append(f"esta dentro de una carpeta sincronizada ({nombre}); la sincronizacion puede bloquear archivos o corromper el entorno")
    if not APP_DIR.isascii():
        riesgos.append("la ruta contiene caracteres no ASCII")
    if " " in APP_DIR:
        riesgos.append("la ruta contiene espacios")
    if riesgos:
        return [Comprobacion(
            "ubicacion", "Ubicacion del proyecto", NIVEL_AVISO,
            f"{APP_DIR}: " + "; ".join(riesgos),
            "Copie el proyecto a una ruta local simple, por ejemplo C:\\Prototipo.",
        )]
    return [Comprobacion(
        "ubicacion", "Ubicacion del proyecto", NIVEL_OK,
        f"Ruta local sin riesgos de sincronizacion: {APP_DIR}",
    )]


def _comprobar_codigo_fuente() -> List[Comprobacion]:
    """Compila los .py del proyecto y detecta marcadores de conflicto sin resolver."""
    problemas: List[str] = []
    revisados = 0
    ignorar = {".venv", "venv", "env", "__pycache__", ".git", "node_modules", ".dsh-acl-recovery"}
    for base, directorios, ficheros in os.walk(APP_DIR):
        directorios[:] = [d for d in directorios if d not in ignorar]
        for nombre in ficheros:
            if not nombre.endswith(".py"):
                continue
            ruta = os.path.join(base, nombre)
            relativa = os.path.relpath(ruta, APP_DIR)
            revisados += 1
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except OSError:
                continue
            for numero, linea in enumerate(contenido.splitlines(), 1):
                if linea.startswith(MARCAS_CONFLICTO):
                    problemas.append(f"{relativa}:{numero} tiene un marcador de conflicto de fusion sin resolver")
                    break
            else:
                try:
                    compile(contenido, ruta, "exec")
                except SyntaxError as e:
                    problemas.append(f"{relativa}:{e.lineno} error de sintaxis: {e.msg}")

    if problemas:
        return [Comprobacion(
            "codigo_fuente", "Codigo fuente", NIVEL_ERROR,
            f"{len(problemas)} problema(s) en {revisados} archivo(s): " + "; ".join(problemas),
            "Corrija el primer archivo listado; la aplicacion no arrancara hasta entonces.", True,
        )]
    return [Comprobacion(
        "codigo_fuente", "Codigo fuente", NIVEL_OK,
        f"{revisados} archivo(s) .py compilan y no hay marcadores de conflicto",
    )]


def _comprobar_cmdb(contexto: Contexto) -> List[Comprobacion]:
    configurada, responde, _ = contexto.base_datos
    existe = os.path.exists(CSV_PATH)
    columnas: List[str] = []
    filas = 0
    error = ""
    if existe:
        try:
            import pandas as pd
            tabla = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
            columnas = [str(c).strip() for c in tabla.columns]
            filas = int(len(tabla))
        except Exception as e:
            try:
                with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
                    lector = csv.reader(f)
                    columnas = [c.strip() for c in next(lector, [])]
                    filas = sum(1 for _ in lector)
            except Exception as e2:
                error = f"{type(e).__name__}: {e} (respaldo: {e2})"

    salida: List[Comprobacion] = []
    if error:
        salida.append(Comprobacion(
            "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_ERROR,
            f"El archivo existe pero no se pudo leer: {error}",
            "Reemplace el archivo por uno valido o siembre los datos de ejemplo: python -m core.diagnostico --crear-datos-ejemplo",
        ))
        return salida

    if not existe:
        if configurada and responde:
            salida.append(Comprobacion(
                "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_INFO,
                "No hay CSV local; la CMDB se lee desde PostgreSQL.",
            ))
        elif ES_PRODUCCION:
            salida.append(Comprobacion(
                "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_ERROR,
                "En produccion no hay CSV de respaldo y PostgreSQL no responde: la consola arrancara sin inventario.",
                "Restaure PostgreSQL o cargue el CSV antes de servir la consola.", True,
            ))
        else:
            salida.append(Comprobacion(
                "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_AVISO,
                "No hay CMDB en este equipo: las busquedas de inventario devolveran cero resultados.",
                "Siembre los datos de ejemplo: python -m core.diagnostico --crear-datos-ejemplo",
            ))
        return salida

    faltantes = [c for c in COLUMNAS_CMDB if c not in columnas]
    if faltantes:
        salida.append(Comprobacion(
            "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_ERROR,
            f"Faltan columnas exigidas por el motor: {', '.join(faltantes)} (encontradas: {', '.join(columnas) or 'ninguna'})",
            "Ajuste la cabecera del CSV al esquema documentado o siembre los datos de ejemplo.",
        ))
    elif filas == 0:
        salida.append(Comprobacion(
            "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_AVISO,
            "El archivo tiene la cabecera correcta pero cero registros.",
            "Cargue la CMDB o siembre los datos de ejemplo: python -m core.diagnostico --crear-datos-ejemplo",
        ))
    else:
        salida.append(Comprobacion(
            "cmdb", "CMDB (data/mantenimientos.csv)", NIVEL_OK,
            f"{filas} registro(s) y {len(columnas)} columna(s) conforme al esquema del motor",
        ))
    return salida


def _comprobar_documentos() -> List[Comprobacion]:
    extensiones = (".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".png", ".jpg", ".jpeg", ".svg", ".msg")
    cantidad = 0
    if os.path.isdir(DOCS_DIR):
        for nombre in os.listdir(DOCS_DIR):
            if nombre.lower().endswith(extensiones) and os.path.isfile(os.path.join(DOCS_DIR, nombre)):
                cantidad += 1
    historial = 0
    if os.path.isdir(HISTORY_DIR):
        historial = sum(1 for n in os.listdir(HISTORY_DIR) if os.path.isdir(os.path.join(HISTORY_DIR, n)))
    salida = [Comprobacion(
        "documentos", "Documentacion tecnica", NIVEL_OK if cantidad else NIVEL_AVISO,
        f"{cantidad} documento(s) en data/docs y {historial} documento(s) con historial de versiones"
        + ("" if cantidad else ". La busqueda documental y el visor quedaran vacios."),
        "Siembre los datos de ejemplo: python -m core.diagnostico --crear-datos-ejemplo" if not cantidad else "",
    )]
    if not os.path.exists(CATEGORIAS_PATH):
        salida.append(Comprobacion(
            "categorias", "Categorias de documentos", NIVEL_AVISO,
            f"No existe {CATEGORIAS_PATH}; se usaran las categorias por defecto del modulo de etiquetas.",
            "Restaure data/categorias.json desde el repositorio (si viaja en git).",
        ))
    else:
        salida.append(Comprobacion(
            "categorias", "Categorias de documentos", NIVEL_OK,
            "data/categorias.json presente",
        ))
    return salida


def _comprobar_diagramas() -> List[Comprobacion]:
    """Verifica que cada ficha de diagrama tenga una imagen real que el visor pueda abrir.

    Sin la imagen, el visor cae al texto de la ficha; con un archivo que no es
    imagen, la pagina fallaba con UnidentifiedImageError.
    """
    if not os.path.isdir(DOCS_DIR):
        return [Comprobacion("diagramas", "Diagramas e imagenes", NIVEL_INFO, "No hay carpeta de documentos")]

    try:
        _silenciar_avisos_de_streamlit()
        from core.procesador import obtener_ruta_original
        from core.visor import es_imagen_visualizable
    except Exception as e:
        return [Comprobacion(
            "diagramas", "Diagramas e imagenes", NIVEL_AVISO,
            f"No se pudo verificar el visor de imagenes: {type(e).__name__}: {e}",
            "Revise la cadena de importacion de la aplicacion.",
        )]

    fichas = sorted(
        n for n in os.listdir(DOCS_DIR)
        if n.startswith("DIAGRAMA__") and n.lower().endswith(".md") and os.path.isfile(os.path.join(DOCS_DIR, n))
    )
    if not fichas:
        return [Comprobacion("diagramas", "Diagramas e imagenes", NIVEL_INFO, "No hay fichas de diagrama en este equipo")]

    sin_imagen: List[str] = []
    for ficha in fichas:
        ruta = obtener_ruta_original(ficha)
        if not ruta or not es_imagen_visualizable(ruta):
            origen = os.path.basename(ruta) if ruta else "sin archivo original"
            sin_imagen.append(f"{ficha} (origen: {origen})")

    if sin_imagen:
        return [Comprobacion(
            "diagramas", "Diagramas e imagenes", NIVEL_AVISO,
            f"{len(sin_imagen)} de {len(fichas)} ficha(s) sin imagen valida: " + "; ".join(sin_imagen),
            "Copie los archivos de data/docs/assets o vuelva a ingerir las imagenes; el visor mostrara el texto de la ficha.",
        )]
    return [Comprobacion(
        "diagramas", "Diagramas e imagenes", NIVEL_OK,
        f"{len(fichas)} ficha(s) de diagrama con imagen valida verificada",
    )]


def _comprobar_usuarios() -> List[Comprobacion]:
    existe = os.path.exists(USERS_PATH)
    cuentas: Dict[str, object] = {}
    if existe:
        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                cuentas = json.load(f)
        except Exception:
            cuentas = {}
    sin_env = [f"{u.upper()}_PASSWORD" for u in CUENTAS_MAESTRAS if not os.environ.get(f"{u.upper()}_PASSWORD", "").strip()]

    if existe and not cuentas:
        return [Comprobacion(
            "usuarios", "Cuentas de acceso", NIVEL_ERROR,
            f"{USERS_PATH} existe pero esta vacio o corrupto: ningun usuario podra iniciar sesion.",
            "Elimine el archivo para regenerar las cuentas base (se perdera el RBAC guardado).",
        )]

    if existe:
        return [Comprobacion(
            "usuarios", "Cuentas de acceso", NIVEL_OK,
            f"data/users.json presente con {len(cuentas)} cuenta(s)"
            + ("" if not sin_env else "; las contrasenas maestras no estan en el entorno, se usan las guardadas"),
        )]

    if ES_PRODUCCION:
        if sin_env:
            return [Comprobacion(
                "usuarios", "Cuentas de acceso", NIVEL_ERROR,
                "PRODUCCION=1, no existe data/users.json y faltan: " + ", ".join(sin_env),
                "Defina las contrasenas maestras en .env (ver .env.example); sin ellas la aplicacion no arranca.", True,
            )]
        return [Comprobacion(
            "usuarios", "Cuentas de acceso", NIVEL_OK,
            "Se crearan las cuentas base con las contrasenas maestras definidas en el entorno",
        )]

    if sin_env:
        return [Comprobacion(
            "usuarios", "Cuentas de acceso", NIVEL_AVISO,
            "No existe data/users.json y no hay contrasenas maestras en el entorno: se crearan las cuentas "
            "de fabrica (admin2026, operador2026, auditor2026).",
            "Defina ADMIN_PASSWORD, OPERADOR_PASSWORD y AUDITOR_PASSWORD en .env para no usar cuentas de fabrica.",
        )]
    return [Comprobacion(
        "usuarios", "Cuentas de acceso", NIVEL_OK,
        "Se crearan las cuentas base con las contrasenas maestras definidas en el entorno",
    )]


def _comprobar_boveda(contexto: Contexto) -> List[Comprobacion]:
    salida: List[Comprobacion] = []
    clave_env = os.environ.get("VAULT_MASTER_KEY", "").strip()

    if ES_PRODUCCION and not clave_env:
        salida.append(Comprobacion(
            "boveda_clave", "Clave maestra de la boveda", NIVEL_ERROR,
            "PRODUCCION=1 exige VAULT_MASTER_KEY y no esta definida.",
            "Defina VAULT_MASTER_KEY (32 bytes en base64) en .env; sin ella la boveda no se abre.", True,
        ))
    elif clave_env:
        try:
            from cryptography.fernet import Fernet
            try:
                Fernet(clave_env.encode("utf-8"))
                detalle = "VAULT_MASTER_KEY valida (formato Fernet)"
            except Exception:
                detalle = "VAULT_MASTER_KEY no es base64 Fernet; se derivara una clave con PBKDF2-SHA256 (200000 iteraciones)"
            salida.append(Comprobacion("boveda_clave", "Clave maestra de la boveda", NIVEL_OK, detalle))
        except ImportError:
            salida.append(Comprobacion(
                "boveda_clave", "Clave maestra de la boveda", NIVEL_ERROR,
                "VAULT_MASTER_KEY definida pero falta el paquete cryptography para usarla.",
                "Instale el entorno completo: pip install -r requirements.txt",
            ))
    else:
        salida.append(Comprobacion(
            "boveda_clave", "Clave maestra de la boveda", NIVEL_INFO,
            "Sin VAULT_MASTER_KEY: en desarrollo se usa data/.vault.key (no viaja en git)",
        ))

    estado = contexto.boveda
    if estado.estado == "sin_boveda":
        salida.append(Comprobacion(
            "boveda", "Boveda de secretos", NIVEL_INFO,
            "No hay data/.vault.enc; se creara al guardar el primer secreto.",
        ))
    elif estado.estado == "ok":
        salida.append(Comprobacion(
            "boveda", "Boveda de secretos", NIVEL_OK,
            f"data/.vault.enc descifrada: {estado.detalle}",
        ))
    elif estado.estado == "sin_clave":
        salida.append(Comprobacion(
            "boveda", "Boveda de secretos", NIVEL_ERROR,
            f"{estado.detalle}: los secretos guardados son irrecuperables en este equipo.",
            "Copie data/.vault.key desde el equipo original o defina la misma VAULT_MASTER_KEY; sin una de las dos no hay recuperacion.",
        ))
    else:
        salida.append(Comprobacion(
            "boveda", "Boveda de secretos", NIVEL_ERROR,
            f"data/.vault.enc no se puede descifrar: {estado.detalle}",
            "Verifique la VAULT_MASTER_KEY o restaure el archivo desde un respaldo; no se sobrescribe para evitar perdida de secretos.",
        ))
    return salida


def _comprobar_postgres(contexto: Contexto) -> List[Comprobacion]:
    configurada, responde, error = contexto.base_datos
    if not configurada:
        return [Comprobacion(
            "postgres", "PostgreSQL", NIVEL_INFO,
            "Sin DATABASE_URL ni DB_HOST: la consola opera en modo local (DuckDB en RAM sobre el CSV). "
            "No habra migraciones, RBAC ni auditoria en base de datos.",
        )]

    salida: List[Comprobacion] = []
    destino = _destino_base_datos()
    faltan = [m for m in ("sqlalchemy", "psycopg2", "psycopg") if importlib.util.find_spec(m) is None]
    if "sqlalchemy" in faltan:
        salida.append(Comprobacion(
            "postgres_driver", "Controlador de PostgreSQL", NIVEL_ERROR,
            f"Hay configuracion de base de datos ({destino}) pero faltan: {', '.join(faltan)}. "
            "El motor devuelve None de forma silenciosa y la consola cae al CSV.",
            "Instale el entorno completo: pip install -r requirements.txt",
        ))
    elif len(faltan) == 2:
        salida.append(Comprobacion(
            "postgres_driver", "Controlador de PostgreSQL", NIVEL_ERROR,
            f"Hay configuracion de base de datos ({destino}) pero no hay controlador psycopg2 ni psycopg.",
            "Instale el entorno completo: pip install -r requirements.txt",
        ))

    if responde:
        salida.append(Comprobacion(
            "postgres", "PostgreSQL", NIVEL_OK,
            f"El servidor responde en {destino}",
        ))
    elif ES_PRODUCCION:
        salida.append(Comprobacion(
            "postgres", "PostgreSQL", NIVEL_ERROR,
            f"PRODUCCION=1 configurado para {destino} y el servidor no responde"
            + (f" ({error})" if error else ""),
            "Levante PostgreSQL o corrija DATABASE_URL/DB_HOST antes de servir la consola.", True,
        ))
    else:
        salida.append(Comprobacion(
            "postgres", "PostgreSQL", NIVEL_AVISO,
            f"Configurado para {destino} pero no responde"
            + (f" ({error})" if error else "")
            + "; la consola usara el CSV local.",
            "Verifique que el servicio este arriba y que las credenciales sean correctas.",
        ))
    return salida


def _comprobar_gemini(contexto: Contexto) -> List[Comprobacion]:
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return [Comprobacion("gemini", "Asistente Gemini", NIVEL_OK, "GEMINI_API_KEY definida en el entorno")]
    if contexto.boveda.estado == "ok" and contexto.boveda.secretos.get("GEMINI_API_KEY"):
        return [Comprobacion("gemini", "Asistente Gemini", NIVEL_OK, "GEMINI_API_KEY recuperada de la boveda")]
    return [Comprobacion(
        "gemini", "Asistente Gemini", NIVEL_INFO,
        "Sin GEMINI_API_KEY: el asistente responde en modo local autonomo (busqueda DuckDB y documental).",
        "Defina GEMINI_API_KEY en .env o guardela en la boveda para habilitar el asistente remoto.",
    )]


def _comprobar_puerto() -> List[Comprobacion]:
    try:
        puerto = int(os.environ.get("STREAMLIT_SERVER_PORT", PUERTO_POR_DEFECTO) or PUERTO_POR_DEFECTO)
    except ValueError:
        return [Comprobacion(
            "puerto", "Puerto de escucha", NIVEL_ERROR,
            f"STREAMLIT_SERVER_PORT no es un numero: {os.environ.get('STREAMLIT_SERVER_PORT')!r}",
            "Corrija la variable o elimine la para usar el puerto 8501.",
        )]

    sonda = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sonda.bind(("127.0.0.1", puerto))
        return [Comprobacion("puerto", "Puerto de escucha", NIVEL_OK, f"El puerto {puerto} esta libre")]
    except OSError:
        pass
    finally:
        sonda.close()

    en_uso = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        en_uso.settimeout(1.0)
        atiende = en_uso.connect_ex(("127.0.0.1", puerto)) == 0
    except OSError:
        atiende = False
    finally:
        en_uso.close()

    if atiende:
        return [Comprobacion(
            "puerto", "Puerto de escucha", NIVEL_AVISO,
            f"El puerto {puerto} esta ocupado y algo responde alli: probablemente la consola ya esta en ejecucion.",
            f"Abra http://localhost:{puerto} o detenga la instancia anterior antes de arrancar otra.",
        )]
    return [Comprobacion(
        "puerto", "Puerto de escucha", NIVEL_AVISO,
        f"El puerto {puerto} esta ocupado por otro proceso que no responde.",
        f"Cambie APP_PORT/STREAMLIT_SERVER_PORT o libere el puerto {puerto}.",
    )]


def _comprobar_importaciones() -> List[Comprobacion]:
    _silenciar_avisos_de_streamlit()
    fallos: List[str] = []
    inicio = time.perf_counter()
    for modulo in MODULOS_CRITICOS:
        try:
            importlib.import_module(modulo)
        except Exception as e:
            fallos.append(f"{modulo}: {type(e).__name__}: {e}")
    duracion = time.perf_counter() - inicio

    if fallos:
        return [Comprobacion(
            "importaciones", "Importacion de la aplicacion", NIVEL_ERROR,
            f"{len(fallos)} modulo(s) no se pudieron importar: " + "; ".join(fallos),
            "Corrija el primer modulo listado; suele ser una dependencia faltante o un error de sintaxis.", True,
        )]
    return [Comprobacion(
        "importaciones", "Importacion de la aplicacion", NIVEL_OK,
        f"{len(MODULOS_CRITICOS)} modulo(s) importados correctamente en {duracion:.1f} s",
    )]


# ---------------------------------------------------------------------------
# Datos de ejemplo
# ---------------------------------------------------------------------------

def sembrar_datos_ejemplo(destino_data: Optional[str] = None, permitir_produccion: bool = False) -> Dict[str, object]:
    """Copia el juego de ejemplo (CMDB y documentos) sin sobrescribir nada existente."""
    destino_data = destino_data or DATA_DIR
    resultado: Dict[str, object] = {"copiados": [], "omitidos": [], "error": ""}
    copiados: List[str] = resultado["copiados"]  # type: ignore[assignment]
    omitidos: List[str] = resultado["omitidos"]  # type: ignore[assignment]

    if ES_PRODUCCION and not permitir_produccion:
        resultado["error"] = (
            "PRODUCCION=1: los datos de ejemplo no se siembran en produccion "
            "(la CMDB proviene de PostgreSQL y no se admite contenido de demostracion)."
        )
        return resultado
    if not os.path.isdir(EJEMPLOS_DIR):
        resultado["error"] = f"No se encontro la carpeta de ejemplos: {EJEMPLOS_DIR}"
        return resultado

    try:
        origen_cmdb = os.path.join(EJEMPLOS_DIR, "mantenimientos.csv")
        if os.path.exists(origen_cmdb):
            destino_cmdb = os.path.join(destino_data, "mantenimientos.csv")
            if os.path.exists(destino_cmdb):
                omitidos.append("data/mantenimientos.csv (ya existe)")
            else:
                os.makedirs(destino_data, exist_ok=True)
                shutil.copy2(origen_cmdb, destino_cmdb)
                copiados.append("data/mantenimientos.csv")

        origen_docs = os.path.join(EJEMPLOS_DIR, "docs")
        if os.path.isdir(origen_docs):
            destino_docs = os.path.join(destino_data, "docs")
            os.makedirs(destino_docs, exist_ok=True)
            for nombre in sorted(os.listdir(origen_docs)):
                origen = os.path.join(origen_docs, nombre)
                if not os.path.isfile(origen):
                    continue
                destino = os.path.join(destino_docs, nombre)
                if os.path.exists(destino):
                    omitidos.append(f"data/docs/{nombre} (ya existe)")
                else:
                    shutil.copy2(origen, destino)
                    copiados.append(f"data/docs/{nombre}")
    except OSError as e:
        resultado["error"] = f"{type(e).__name__}: {e}"
    return resultado


# ---------------------------------------------------------------------------
# Orquestacion y reporte
# ---------------------------------------------------------------------------

def ejecutar_diagnostico() -> List[Comprobacion]:
    """Ejecuta todas las comprobaciones en orden y devuelve los resultados."""
    contexto = Contexto()
    comprobaciones: List[Comprobacion] = []
    comprobaciones += _comprobar_equipo()
    comprobaciones += _comprobar_python()
    comprobaciones += _comprobar_ubicacion()
    comprobaciones += _comprobar_rutas()
    comprobaciones += _comprobar_dependencias()
    comprobaciones += _comprobar_codigo_fuente()
    comprobaciones += _comprobar_cmdb(contexto)
    comprobaciones += _comprobar_documentos()
    comprobaciones += _comprobar_diagramas()
    comprobaciones += _comprobar_usuarios()
    comprobaciones += _comprobar_boveda(contexto)
    comprobaciones += _comprobar_postgres(contexto)
    comprobaciones += _comprobar_gemini(contexto)
    comprobaciones += _comprobar_puerto()
    comprobaciones += _comprobar_importaciones()
    return comprobaciones


def resumir(comprobaciones: List[Comprobacion]) -> Dict[str, int]:
    conteo = {NIVEL_OK: 0, NIVEL_INFO: 0, NIVEL_AVISO: 0, NIVEL_ERROR: 0}
    for comprobacion in comprobaciones:
        conteo[comprobacion.nivel] = conteo.get(comprobacion.nivel, 0) + 1
    return {
        "ok": conteo[NIVEL_OK],
        "info": conteo[NIVEL_INFO],
        "warn": conteo[NIVEL_AVISO],
        "crit": conteo[NIVEL_ERROR],
        "bloqueantes": sum(1 for c in comprobaciones if c.nivel == NIVEL_ERROR and c.bloqueante),
        "total": len(comprobaciones),
    }


def hay_criticos(comprobaciones: List[Comprobacion]) -> bool:
    return any(c.nivel == NIVEL_ERROR for c in comprobaciones)


def formatear_texto(comprobaciones: List[Comprobacion]) -> str:
    """Reporte legible para consola o para adjuntar a un ticket."""
    conteo = resumir(comprobaciones)
    ancho = 74
    lineas = [
        "=" * ancho,
        " AUTO DIAGNOSTICO DE PORTABILIDAD",
        f" Consola de Infraestructura y Operaciones | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * ancho,
    ]
    for comprobacion in comprobaciones:
        lineas.append(f"{BANDERAS.get(comprobacion.nivel, '[?]'):<7} {comprobacion.titulo}")
        lineas.append(f"        {comprobacion.detalle}")
        if comprobacion.accion:
            lineas.append(f"        Accion: {comprobacion.accion}")
    lineas.append("-" * ancho)
    resumen = (
        f" RESULTADO: {conteo['ok']} [OK] | {conteo['warn']} [WARN] | {conteo['crit']} [CRIT]"
        f" | {conteo['info']} [INFO]"
    )
    if conteo["bloqueantes"]:
        resumen += f"  ({conteo['bloqueantes']} impide(n) el arranque)"
    lineas.append(resumen)

    pendientes = [c for c in comprobaciones if c.nivel in (NIVEL_ERROR, NIVEL_AVISO) and c.accion]
    if pendientes:
        lineas.append(" ACCIONES SUGERIDAS:")
        for indice, comprobacion in enumerate(pendientes, 1):
            lineas.append(f"  {indice}. {BANDERAS[comprobacion.nivel]} {comprobacion.titulo}: {comprobacion.accion}")
    elif not hay_criticos(comprobaciones):
        lineas.append(" Sin acciones pendientes: esta maquina puede ejecutar la consola.")
    lineas.append("-" * ancho)
    lineas.append(" Guarde este informe con: python -m core.diagnostico --informe diagnostico.txt")
    return "\n".join(lineas)


def formatear_json(comprobaciones: List[Comprobacion]) -> Dict[str, object]:
    return {
        "resultado": resumir(comprobaciones),
        "comprobaciones": [
            {
                "id": c.id,
                "titulo": c.titulo,
                "nivel": c.nivel,
                "detalle": c.detalle,
                "accion": c.accion,
                "bloqueante": c.bloqueante,
            }
            for c in comprobaciones
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m core.diagnostico",
        description="Verifica si esta maquina puede ejecutar la consola y que falta cuando no puede.",
    )
    analizador.add_argument("--json", action="store_true", help="emite el informe en JSON")
    analizador.add_argument("--informe", metavar="RUTA", help="guarda el informe en un archivo de texto UTF-8")
    analizador.add_argument(
        "--crear-datos-ejemplo", action="store_true",
        help="siembra CMDB y documentos de ejemplo antes de diagnosticar (nunca sobrescribe archivos)",
    )
    argumentos = analizador.parse_args(argv)

    # En una consola real Python escribe con la API de Windows y respeta los
    # acentos; solo se fuerza UTF-8 cuando la salida va a una tuberia o archivo.
    if not sys.stdout.isatty():
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if argumentos.crear_datos_ejemplo:
        siembra = sembrar_datos_ejemplo()
        print("=" * 74)
        print(" DATOS DE EJEMPLO")
        print("=" * 74)
        if siembra["error"]:
            print(f"[CRIT] {siembra['error']}")
        for ruta in siembra["copiados"]:  # type: ignore[union-attr]
            print(f"[OK]   copiado {ruta}")
        for ruta in siembra["omitidos"]:  # type: ignore[union-attr]
            print(f"[INFO] omitido {ruta}")
        if not siembra["copiados"] and not siembra["error"]:  # type: ignore[arg-type]
            print("[INFO] no habia nada que copiar")
        print()

    comprobaciones = ejecutar_diagnostico()
    texto = formatear_texto(comprobaciones)
    print(texto)

    if argumentos.informe:
        try:
            # utf-8-sig: el informe se abre y se adjunta desde herramientas de Windows.
            with open(argumentos.informe, "w", encoding="utf-8-sig") as f:
                f.write(texto + "\n")
            print(f"[OK] Informe guardado en {os.path.abspath(argumentos.informe)}")
        except OSError as e:
            print(f"[CRIT] No se pudo guardar el informe: {e}")

    if argumentos.json:
        print(json.dumps(formatear_json(comprobaciones), ensure_ascii=False, indent=2))

    return 1 if hay_criticos(comprobaciones) else 0


if __name__ == "__main__":
    sys.exit(main())

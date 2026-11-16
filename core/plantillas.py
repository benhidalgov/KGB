"""
Plantillas oficiales de documentacion tecnica, generadores de Runbooks y gestion de plantillas personalizadas.
"""
import os
import json

from core.configuracion import PLANTILLAS_CUSTOM_PATH, escribir_atomico

PLANTILLAS_BASE_RESERVADAS = [
    "Procedimiento de Rollback de Emergencia",
    "Paso a Producción / Despliegue CI/CD",
    "Reporte Postmortem / Incidente P1 (RCA)",
    "Ficha Técnica de Microservicio / API WSO2",
    "Guía de Contingencia y Failover Operativo",
    "Procedimiento de Parchado y Mantenimiento de SO",
    "Renovación de Certificados SSL/TLS y Secretos",
    "Procedimiento de Disaster Recovery (DRP)",
    "Plan de Respaldo y Restauración de Base de Datos"
]


def cargar_plantillas_personalizadas() -> dict:
    """Carga las plantillas personalizadas guardadas desde el archivo JSON."""
    if os.path.exists(PLANTILLAS_CUSTOM_PATH):
        try:
            with open(PLANTILLAS_CUSTOM_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Un JSON válido pero no-dict ([] o un string) crasheaba .keys() en la pestaña.
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def guardar_plantilla_personalizada(nombre: str, descripcion: str, campos: list) -> bool:
    """Guarda una nueva plantilla personalizada en el catalogo local."""
    plantillas = cargar_plantillas_personalizadas()
    plantillas[nombre] = {"descripcion": descripcion, "campos": campos}
    try:
        escribir_atomico(PLANTILLAS_CUSTOM_PATH, json.dumps(plantillas, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


def obtener_todos_los_tipos_plantillas() -> list:
    """Devuelve la lista de plantillas disponibles (personalizadas y opcion de crear nueva)."""
    custom = list(cargar_plantillas_personalizadas().keys())
    return [f"[Plantilla] {k}" for k in custom] + ["[+ Crear Nueva Plantilla / Procedimiento...]"]


# Catálogo único de plantillas: match de tipo, campos del formulario, título,
# metadatos, secciones y nombre de archivo en un solo lugar. Antes eran dos
# cadenas if paralelas (esquema y generador) sincronizadas a mano: si
# divergían, el schema pedía campos que el generador jamás leía.
#
# Campos: (clave, etiqueta, valor_defecto, tipo_control).
# Secciones: (título, clave_en_params, contenido, modo); con clave None el
# tercer campo es un contenido literal (constante, p. ej. telemetría).
# Títulos y fnames se rinden con str.format sobre el contexto: las plantillas
# son constantes del repo y los valores con llaves se insertan tal cual.
_PLANTILLAS = {
    "Rollback": {
        "match": ("Rollback",),
        "campos": [
            ("criterio", "Criterio de Activación", "Latencia > 500ms o Error Rate > 2%", "area"),
            ("pasos", "Pasos de Reversión", "1. Ejecutar pipeline rollback release-v2.4.1\n2. Revertir esquema BD\n3. redis-cli FLUSHDB", "area"),
            ("verif", "Verificación de Salud", "curl -I https://api.booking.internal/health\nsystemctl status booking-service", "area"),
        ],
        "titulo": "Procedimiento de Rollback: {servicio}",
        "meta": (
            "* **Tipo de Procedimiento:** `Rollback de Emergencia`",
            "* **Ventana de Mantenimiento:** `{ventana}`",
        ),
        "secciones": (
            ("1. Criterios de Activación de Rollback", "criterio", "", "text"),
            ("2. Pasos de Reversión y Comandos", "pasos", "", "bash"),
            ("3. Verificación Post-Rollback y Pruebas de Salud", "verif", "", "bash"),
        ),
        "fname": "procedimiento_rollback_{srv_clean}.md",
    },
    "Paso a Producción": {
        "match": ("Paso a Producción",),
        "campos": [
            ("version", "Versión / Tag", "v2.5.0", "text"),
            ("pipeline", "Pipeline URL", "https://dev.azure.com/smucorp/pipelines/142", "text"),
            ("variables", "Variables de Entorno", "REDIS_HOST=10.24.0.126\nLOG_LEVEL=INFO", "area"),
            ("smoke", "Checklist Smoke Tests", "- [ ] Endpoint /health HTTP 200\n- [ ] Cero alertas en Nagios", "area"),
        ],
        "titulo": "Guía de Despliegue a Producción: {servicio} ({version})",
        "meta": (
            "* **Tipo de Procedimiento:** `Paso a Producción / Release CI/CD`",
            "* **Pipeline / Release:** `{pipeline}`",
        ),
        "secciones": (
            ("1. Variables de Entorno y Configuración", "variables", "", "env"),
            ("2. Checklist de Validación (Smoke Tests)", "smoke", "", "text"),
        ),
        "fname": "despliegue_{srv_clean}_{version_slug}.md",
    },
    "Postmortem": {
        "match": ("Postmortem",),
        "campos": [
            ("incidente_id", "Ticket ID", "INC-88912", "text"),
            ("impacto", "Impacto", "Indisponibilidad de 14 minutos. 120 transacciones rechazadas.", "area"),
            ("causa", "Causa Raíz (RCA)", "Agotamiento de pool de conexiones JDBC.", "area"),
            ("solucion", "Solución Inmediata", "Reinicio worker WSO2 y ampliación de maxConnections.", "area"),
            ("preventiva", "Medida Preventiva", "Creación de índice y ajuste de timeout.", "area"),
        ],
        "titulo": "Reporte Postmortem P1: {incidente_id} - {servicio}",
        "meta": ("* **Incidente:** `{incidente_id}`",),
        "secciones": (
            ("1. Resumen del Impacto y Duración", "impacto", "", "text"),
            ("2. Causa Raíz (Root Cause Analysis - RCA)", "causa", "", "text"),
            ("3. Solución Inmediata Aplicada", "solucion", "", "text"),
            ("4. Acciones Correctivas y Plan Preventivo", "preventiva", "", "text"),
        ),
        "fname": "postmortem_{incidente_id_slug}_{srv_clean}.md",
    },
    "Microservicio": {
        "match": ("Microservicio",),
        "campos": [
            ("endpoint", "Endpoint Base", "/api/v1/booking", "text"),
            ("auth", "Autenticación", "OAuth2 Bearer Token (Redis Sentinel)", "text"),
            ("dependencias", "Dependencias", "* VM: VM-BOOKING-01 (10.24.0.125)\n* DB: Postgres HA (10.24.0.130)", "area"),
        ],
        "titulo": "Ficha Técnica de Microservicio / API: {servicio}",
        "meta": (
            "* **Endpoint Base:** `{endpoint}`",
            "* **Método de Autenticación:** `{auth}`",
        ),
        "secciones": (
            ("1. Dependencias y Nodos de Infraestructura", "dependencias", "", "text"),
            ("2. Telemetría y Monitoreo Asociado", None,
             "* **APM (New Relic / VZOR):** Monitoreo de latencia y transacciones por segundo.\n"
             "* **Nagios / PRTG Check:** Chequeo periódico de endpoint `/health`.", "text"),
        ),
        "fname": "ficha_servicio_{srv_clean}.md",
    },
    "Contingencia": {
        "match": ("Contingencia", "Failover"),
        "campos": [
            ("sintoma", "Síntoma de Falla", "Host ESXi no responde o alerta CRITICAL en Nagios.", "area"),
            ("pasos", "Procedimiento Failover", "1. Conmutar en HAProxy a BALANCER002\n2. Activar réplica en vCloud", "area"),
        ],
        "titulo": "Manual de Contingencia y Failover Operativo: {servicio}",
        "meta": (),
        "secciones": (
            ("1. Síntomas de Alerta y Disparadores", "sintoma", "", "text"),
            ("2. Procedimiento de Conmutación (Failover)", "pasos", "", "bash"),
        ),
        "fname": "contingencia_failover_{srv_clean}.md",
    },
    "Parchado": {
        "match": ("Parchado", "Mantenimiento de SO"),
        "campos": [
            ("paquetes", "Paquetes", "Actualización mensual del kernel y OpenSSL.", "area"),
            ("pasos_parchado", "Pasos de Parchado", "1. Snapshot en vCloud\n2. yum update -y\n3. Reboot nodo secundario", "area"),
            ("rollback_parchado", "Plan de Reversión", "Revertir al snapshot de VM en vCloud.", "area"),
        ],
        "titulo": "Procedimiento de Parchado y Mantenimiento de SO: {servicio}",
        "meta": ("* **Ventana de Mantenimiento:** `{ventana}`",),
        "secciones": (
            ("1. Alcance y Paquetes a Actualizar", "paquetes", "Actualización de seguridad mensual.", "text"),
            ("2. Pasos de Aplicación de Parches", "pasos_parchado", "", "bash"),
            ("3. Plan de Reversión Inmediato", "rollback_parchado", "", "text"),
        ),
        "fname": "parchado_so_{srv_clean}.md",
    },
    "Certificados": {
        "match": ("Certificados", "SSL"),
        "campos": [
            ("dominio", "Dominio / CN", "*.smucorp.internal", "text"),
            ("ruta_cert", "Ruta de Instalación", "/etc/ssl/certs/api_smucorp.crt", "text"),
            ("comandos_renov", "Comandos Generación", "openssl req -new -newkey rsa:2048 -nodes -keyout api.key -out api.csr", "area"),
            ("validacion_ssl", "Validación SSL", "echo | openssl s_client -connect localhost:443 -servername api.smucorp.internal 2>/dev/null | openssl x509 -noout -dates", "area"),
        ],
        "titulo": "Procedimiento de Renovación de Certificados SSL/TLS: {servicio}",
        "meta": (
            "* **Dominio / CN:** `{dominio}`",
            "* **Ubicación en Servidor:** `{ruta_cert}`",
        ),
        "secciones": (
            ("1. Comandos de Generación y Carga de Certificado", "comandos_renov", "", "bash"),
            ("2. Validación de Vigencia y Handshake", "validacion_ssl", "", "bash"),
        ),
        "fname": "renovacion_cert_{srv_clean}.md",
    },
    "Disaster Recovery": {
        "match": ("Disaster Recovery", "DRP"),
        "campos": [
            ("rpo_rto", "RPO / RTO", "RPO: 15 min | RTO: 1 hora", "text"),
            ("activacion_drp", "Criterios Activación DRP", "Indisponibilidad total del Datacenter Principal.", "area"),
            ("pasos_drp", "Pasos Conmutación", "1. Conmutar DNS\n2. Promover réplica PostgreSQL\n3. Iniciar workers", "area"),
        ],
        "titulo": "Plan de Recuperación ante Desastres (DRP): {servicio}",
        "meta": ("* **Objetivos:** `{rpo_rto}`",),
        "secciones": (
            ("1. Criterios de Activación del DRP", "activacion_drp", "", "text"),
            ("2. Procedimiento de Conmutación a Datacenter Secundario", "pasos_drp", "", "bash"),
        ),
        "fname": "drp_{srv_clean}.md",
    },
    "Respaldo": {
        "match": ("Respaldo", "Base de Datos"),
        "campos": [
            ("motor_bd", "Motor de BD", "PostgreSQL 15 HA", "text"),
            ("comando_backup", "Script Backup", "pg_dump -h 10.24.0.130 -U admin -Fc db_booking > backup.dump", "area"),
            ("comando_restore", "Script Restore", "pg_restore -h 10.24.0.130 -U admin -d db_booking backup.dump", "area"),
        ],
        "titulo": "Plan de Respaldo y Restauración de Base de Datos: {servicio}",
        "meta": ("* **Motor de BD:** `{motor_bd}`",),
        "secciones": (
            ("1. Procedimiento de Respaldo (Backup)", "comando_backup", "", "bash"),
            ("2. Procedimiento de Restauración (Restore)", "comando_restore", "", "bash"),
        ),
        "fname": "backup_restore_db_{srv_clean}.md",
    },
}

# Sin match: plantillas personalizadas y el tipo inventado caen aquí.
_GENERICA = {
    "campos": [
        ("objetivo", "Objetivo y Alcance", "Procedimiento para {tipo_plantilla} en {servicio}.", "area"),
        ("prerequisitos", "Requisitos Previos", "* Acceso SSH con sudo\n* Notificación a Operaciones\n* Snapshot preventivo", "area"),
        ("pasos_custom", "Pasos Detallados", "1. Validar estado: systemctl status servicio\n2. Ejecutar script\n3. Verificar logs", "area"),
        ("verificacion_custom", "Validación", "* Cero errores 5xx\n* Nagios check_http en OK", "area"),
        ("rollback_custom", "Plan de Contingencia", "1. Detener script\n2. Restaurar backup\n3. Reiniciar servicio", "area"),
    ],
    "titulo": "Procedimiento Técnico: {tipo_limpio} - {servicio}",
    "meta": (
        "* **Tipo de Procedimiento:** `{tipo_limpio}`",
        "* **Ventana de Mantenimiento:** `{ventana}`",
    ),
    "secciones": (
        ("1. Objetivo y Alcance", "objetivo", "", "text"),
        ("2. Requisitos Previos y Permisos", "prerequisitos", "", "text"),
        ("3. Pasos de Ejecución Detallados", "pasos_custom", "", "bash"),
        ("4. Validación y Criterios de Aceptación", "verificacion_custom", "", "text"),
        ("5. Plan de Contingencia / Reversión", "rollback_custom", "", "text"),
    ),
    "fname": "proc_{tipo_slug}_{srv_clean}.md",
}


def _definicion(tipo: str) -> dict:
    """Entrada del catálogo que coincide con el tipo (o la genérica)."""
    for entrada in _PLANTILLAS.values():
        if any(palabra in tipo for palabra in entrada["match"]):
            return entrada
    return _GENERICA


def obtener_esquema_campos(tipo: str) -> list[tuple[str, str, str, str]]:
    """Retorna la lista de tuplas (clave, etiqueta, valor_defecto, tipo_control) para una plantilla."""
    # El mismo catálogo que lee el generador: no puede haber campos que el
    # documento no use ni secciones sin campo que las rellene.
    return _definicion(tipo)["campos"]


def generar_doc_plantilla(tipo: str, autor: str, servicio: str, nivel: str, params: dict) -> tuple[str, str]:
    """Genera el contenido Markdown y el nombre de archivo sugerido segun la plantilla seleccionada."""
    srv_clean = servicio.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
    ctx = {
        "servicio": servicio,
        "srv_clean": srv_clean,
        "ventana": params.get("ventana", "No requerida / En línea"),
        "tipo_limpio": tipo.replace("[Personalizado]", "").replace("[Plantilla]", "").strip(),
        "version": params.get("version", "v1.0.0"),
        "incidente_id": params.get("incidente_id", "INC-001"),
        "pipeline": params.get("pipeline", ""),
        "endpoint": params.get("endpoint", ""),
        "auth": params.get("auth", ""),
        "dominio": params.get("dominio", "*.empresa.internal"),
        "ruta_cert": params.get("ruta_cert", "/etc/ssl/certs/"),
        "rpo_rto": params.get("rpo_rto", "RPO: 15 min | RTO: 1 hora"),
        "motor_bd": params.get("motor_bd", "PostgreSQL HA"),
    }
    ctx["tipo_slug"] = ctx["tipo_limpio"].lower().replace(" ", "_")
    ctx["version_slug"] = ctx["version"].replace(".", "_")
    ctx["incidente_id_slug"] = ctx["incidente_id"].lower()

    entrada = _definicion(tipo)
    titulo = entrada["titulo"].format(**ctx)
    extra_meta = [m.format(**ctx) for m in entrada["meta"]]
    secciones = [
        (titulo_sec, params.get(clave, defecto) if clave is not None else defecto, modo)
        for (titulo_sec, clave, defecto, modo) in entrada["secciones"]
    ]
    fname = entrada["fname"].format(**ctx)

    ambiente = params.get("ambiente", "Producción")
    criticidad = params.get("criticidad", "Media (P3)")
    servidores = params.get("servidores", "No especificado")

    # Ensamblado uniforme del documento Markdown
    meta_lines = [
        f"# {titulo}",
        f"* **Autor / Responsable:** `{autor}`",
        f"* **Nivel de Arquitectura:** `{nivel}`",
        f"* **Ambiente Objetivo:** `{ambiente}`",
        f"* **Criticidad:** `{criticidad}`",
    ] + extra_meta + [
        f"* **Sistemas / Servidores Involucrados:** `{servidores}`",
        "",
        "---",
        ""
    ]

    body_sections = []
    for sec_title, sec_content, sec_mode in secciones:
        body_sections.append(f"## {sec_title}")
        if sec_mode in ("bash", "env", "sql", "json"):
            body_sections.append(f"```{sec_mode}\n{sec_content}\n```\n")
        else:
            body_sections.append(f"{sec_content}\n")
        body_sections.append("---\n")

    body_sections.append("*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*\n")

    return "\n".join(meta_lines) + "\n" + "\n".join(body_sections), fname

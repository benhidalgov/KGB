"""
Plantillas oficiales de documentacion tecnica, generadores de Runbooks y gestion de plantillas personalizadas.
"""
import os
import json

PLANTILLAS_CUSTOM_PATH = os.path.join("data", "plantillas_custom.json")

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
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_plantilla_personalizada(nombre: str, descripcion: str, campos: list) -> bool:
    """Guarda una nueva plantilla personalizada en el catalogo local."""
    os.makedirs("data", exist_ok=True)
    plantillas = cargar_plantillas_personalizadas()
    plantillas[nombre] = {"descripcion": descripcion, "campos": campos}
    try:
        with open(PLANTILLAS_CUSTOM_PATH, "w", encoding="utf-8") as f:
            json.dump(plantillas, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def obtener_todos_los_tipos_plantillas() -> list:
    """Devuelve la lista de plantillas disponibles (personalizadas y opcion de crear nueva)."""
    custom = list(cargar_plantillas_personalizadas().keys())
    return [f"[Plantilla] {k}" for k in custom] + ["[+ Crear Nueva Plantilla / Procedimiento...]"]


def generar_doc_plantilla(tipo: str, autor: str, servicio: str, nivel: str, params: dict) -> tuple[str, str]:
    """Genera el contenido Markdown y el nombre de archivo sugerido segun la plantilla seleccionada."""
    srv_clean = servicio.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
    ambiente = params.get("ambiente", "Producción")
    criticidad = params.get("criticidad", "Media (P3)")
    ventana = params.get("ventana", "No requerida / En línea")
    servidores = params.get("servidores", "No especificado")

    # Mapeo estructurado de tipos de plantilla
    if "Rollback" in tipo:
        titulo = f"Procedimiento de Rollback: {servicio}"
        extra_meta = [f"* **Tipo de Procedimiento:** `Rollback de Emergencia`", f"* **Ventana de Mantenimiento:** `{ventana}`"]
        secciones = [
            ("1. Criterios de Activación de Rollback", params.get("criterio", ""), "text"),
            ("2. Pasos de Reversión y Comandos", params.get("pasos", ""), "bash"),
            ("3. Verificación Post-Rollback y Pruebas de Salud", params.get("verif", ""), "bash"),
        ]
        fname = f"procedimiento_rollback_{srv_clean}.md"

    elif "Paso a Producción" in tipo:
        version = params.get("version", "v1.0.0")
        titulo = f"Guía de Despliegue a Producción: {servicio} ({version})"
        extra_meta = [
            f"* **Tipo de Procedimiento:** `Paso a Producción / Release CI/CD`",
            f"* **Pipeline / Release:** `{params.get('pipeline', '')}`"
        ]
        secciones = [
            ("1. Variables de Entorno y Configuración", params.get("variables", ""), "env"),
            ("2. Checklist de Validación (Smoke Tests)", params.get("smoke", ""), "text"),
        ]
        fname = f"despliegue_{srv_clean}_{version.replace('.', '_')}.md"

    elif "Postmortem" in tipo:
        inc_id = params.get("incidente_id", "INC-001")
        titulo = f"Reporte Postmortem P1: {inc_id} - {servicio}"
        extra_meta = [f"* **Incidente:** `{inc_id}`"]
        secciones = [
            ("1. Resumen del Impacto y Duración", params.get("impacto", ""), "text"),
            ("2. Causa Raíz (Root Cause Analysis - RCA)", params.get("causa", ""), "text"),
            ("3. Solución Inmediata Aplicada", params.get("solucion", ""), "text"),
            ("4. Acciones Correctivas y Plan Preventivo", params.get("preventiva", ""), "text"),
        ]
        fname = f"postmortem_{inc_id.lower()}_{srv_clean}.md"

    elif "Microservicio" in tipo:
        titulo = f"Ficha Técnica de Microservicio / API: {servicio}"
        extra_meta = [
            f"* **Endpoint Base:** `{params.get('endpoint', '')}`",
            f"* **Método de Autenticación:** `{params.get('auth', '')}`"
        ]
        telemetria_def = (
            "* **APM (New Relic / VZOR):** Monitoreo de latencia y transacciones por segundo.\n"
            "* **Nagios / PRTG Check:** Chequeo periódico de endpoint `/health`."
        )
        secciones = [
            ("1. Dependencias y Nodos de Infraestructura", params.get("dependencias", ""), "text"),
            ("2. Telemetría y Monitoreo Asociado", telemetria_def, "text"),
        ]
        fname = f"ficha_servicio_{srv_clean}.md"

    elif "Contingencia" in tipo or "Failover" in tipo:
        titulo = f"Manual de Contingencia y Failover Operativo: {servicio}"
        extra_meta = []
        secciones = [
            ("1. Síntomas de Alerta y Disparadores", params.get("sintoma", ""), "text"),
            ("2. Procedimiento de Conmutación (Failover)", params.get("pasos", ""), "bash"),
        ]
        fname = f"contingencia_failover_{srv_clean}.md"

    elif "Parchado" in tipo or "Mantenimiento de SO" in tipo:
        titulo = f"Procedimiento de Parchado y Mantenimiento de SO: {servicio}"
        extra_meta = [f"* **Ventana de Mantenimiento:** `{ventana}`"]
        secciones = [
            ("1. Alcance y Paquetes a Actualizar", params.get("paquetes", "Actualización de seguridad mensual."), "text"),
            ("2. Pasos de Aplicación de Parches", params.get("pasos_parchado", ""), "bash"),
            ("3. Plan de Reversión Inmediato", params.get("rollback_parchado", ""), "text"),
        ]
        fname = f"parchado_so_{srv_clean}.md"

    elif "Certificados" in tipo or "SSL" in tipo:
        titulo = f"Procedimiento de Renovación de Certificados SSL/TLS: {servicio}"
        extra_meta = [
            f"* **Dominio / CN:** `{params.get('dominio', '*.empresa.internal')}`",
            f"* **Ubicación en Servidor:** `{params.get('ruta_cert', '/etc/ssl/certs/')}`"
        ]
        secciones = [
            ("1. Comandos de Generación y Carga de Certificado", params.get("comandos_renov", ""), "bash"),
            ("2. Validación de Vigencia y Handshake", params.get("validacion_ssl", ""), "bash"),
        ]
        fname = f"renovacion_cert_{srv_clean}.md"

    elif "Disaster Recovery" in tipo or "DRP" in tipo:
        titulo = f"Plan de Recuperación ante Desastres (DRP): {servicio}"
        extra_meta = [f"* **Objetivos:** `{params.get('rpo_rto', 'RPO: 15 min | RTO: 1 hora')}`"]
        secciones = [
            ("1. Criterios de Activación del DRP", params.get("activacion_drp", ""), "text"),
            ("2. Procedimiento de Conmutación a Datacenter Secundario", params.get("pasos_drp", ""), "bash"),
        ]
        fname = f"drp_{srv_clean}.md"

    elif "Respaldo" in tipo or "Base de Datos" in tipo:
        titulo = f"Plan de Respaldo y Restauración de Base de Datos: {servicio}"
        extra_meta = [f"* **Motor de BD:** `{params.get('motor_bd', 'PostgreSQL HA')}`"]
        secciones = [
            ("1. Procedimiento de Respaldo (Backup)", params.get("comando_backup", ""), "bash"),
            ("2. Procedimiento de Restauración (Restore)", params.get("comando_restore", ""), "bash"),
        ]
        fname = f"backup_restore_db_{srv_clean}.md"

    else:
        tipo_limpio = tipo.replace("[Personalizado]", "").replace("[Plantilla]", "").strip()
        titulo = f"Procedimiento Técnico: {tipo_limpio} - {servicio}"
        extra_meta = [f"* **Tipo de Procedimiento:** `{tipo_limpio}`", f"* **Ventana de Mantenimiento:** `{ventana}`"]
        secciones = [
            ("1. Objetivo y Alcance", params.get("objetivo", ""), "text"),
            ("2. Requisitos Previos y Permisos", params.get("prerequisitos", ""), "text"),
            ("3. Pasos de Ejecución Detallados", params.get("pasos_custom", ""), "bash"),
            ("4. Validación y Criterios de Aceptación", params.get("verificacion_custom", ""), "text"),
            ("5. Plan de Contingencia / Reversión", params.get("rollback_custom", ""), "text"),
        ]
        tipo_slug = tipo_limpio.lower().replace(" ", "_")
        fname = f"proc_{tipo_slug}_{srv_clean}.md"

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

"""
Plantillas oficiales de documentacion tecnica, generadores de Runbooks y gestion de plantillas personalizadas.
"""
import os
import json

PLANTILLAS_CUSTOM_PATH = os.path.join("data", "plantillas_custom.json")

PLANTILLAS_PREDEFINIDAS = [
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
    """Carga las plantillas personalizadas guardadas por los técnicos desde el archivo JSON."""
    if os.path.exists(PLANTILLAS_CUSTOM_PATH):
        try:
            with open(PLANTILLAS_CUSTOM_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_plantilla_personalizada(nombre: str, descripcion: str, campos: list) -> bool:
    """Guarda una nueva plantilla personalizada para que quede disponible en el sistema."""
    os.makedirs("data", exist_ok=True)
    plantillas = cargar_plantillas_personalizadas()
    plantillas[nombre] = {
        "descripcion": descripcion,
        "campos": campos
    }
    try:
        with open(PLANTILLAS_CUSTOM_PATH, "w", encoding="utf-8") as f:
            json.dump(plantillas, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def obtener_todos_los_tipos_plantillas() -> list:
    """Devuelve la lista unificada de tipos predefinidos y tipos personalizados."""
    custom = list(cargar_plantillas_personalizadas().keys())
    return PLANTILLAS_PREDEFINIDAS + [f"[Personalizado] {k}" for k in custom] + ["[+ Crear Nuevo Tipo de Procedimiento...]"]


def generar_doc_plantilla(tipo: str, autor: str, servicio: str, nivel: str, params: dict) -> tuple[str, str]:
    """Genera el contenido Markdown y el nombre de archivo sugerido según la plantilla seleccionada."""
    srv_clean = servicio.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
    ambiente = params.get("ambiente", "Producción")
    criticidad = params.get("criticidad", "Media (P3)")
    ventana = params.get("ventana", "No requerida / En línea")
    servidores = params.get("servidores", "No especificado")

    # 1. Rollback de Emergencia
    if "Rollback" in tipo:
        criterio = params.get("criterio", "")
        pasos = params.get("pasos", "")
        verif = params.get("verif", "")
        doc_md = f"""# Procedimiento de Rollback: {servicio}
* **Autor / Responsable:** `{autor}`
* **Nivel de Arquitectura:** `{nivel}`
* **Tipo de Procedimiento:** `Rollback de Emergencia`
* **Ambiente Objetivo:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Ventana de Mantenimiento:** `{ventana}`
* **Sistemas / Servidores Involucrados:** `{servidores}`

---

## 1. Criterios de Activación de Rollback
{criterio}

---

## 2. Pasos de Reversión y Comandos
```bash
{pasos}
```

---

## 3. Verificación Post-Rollback y Pruebas de Salud
```bash
{verif}
```

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"procedimiento_rollback_{srv_clean}.md"
        return doc_md, fname

    # 2. Paso a Producción
    elif "Paso a Producción" in tipo:
        version = params.get("version", "v1.0.0")
        pipeline = params.get("pipeline", "")
        variables = params.get("variables", "")
        smoke = params.get("smoke", "")
        doc_md = f"""# Guía de Despliegue a Producción: {servicio} ({version})
* **Autor / Responsable:** `{autor}`
* **Nivel de Arquitectura:** `{nivel}`
* **Tipo de Procedimiento:** `Paso a Producción / Release CI/CD`
* **Ambiente:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Pipeline / Release:** `{pipeline}`
* **Sistemas Involucrados:** `{servidores}`

---

## 1. Variables de Entorno y Configuración
```env
{variables}
```

---

## 2. Checklist de Validación (Smoke Tests)
{smoke}

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"despliegue_{srv_clean}_{version.replace('.', '_')}.md"
        return doc_md, fname

    # 3. Postmortem / Incidente P1
    elif "Postmortem" in tipo:
        incidente_id = params.get("incidente_id", "INC-001")
        impacto = params.get("impacto", "")
        causa = params.get("causa", "")
        solucion = params.get("solucion", "")
        preventiva = params.get("preventiva", "")
        doc_md = f"""# Reporte Postmortem P1: {incidente_id} - {servicio}
* **Autor / Líder de Incidente:** `{autor}`
* **Nivel Afectado:** `{nivel}`
* **Incidente:** `{incidente_id}`
* **Ambiente Afectado:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Sistemas Afectados:** `{servidores}`

---

## 1. Resumen del Impacto y Duración
{impacto}

---

## 2. Causa Raíz (Root Cause Analysis - RCA)
{causa}

---

## 3. Solución Inmediata Aplicada
{solucion}

---

## 4. Acciones Correctivas y Plan Preventivo
{preventiva}

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"postmortem_{incidente_id.lower()}_{srv_clean}.md"
        return doc_md, fname

    # 4. Microservicio / API
    elif "Microservicio" in tipo:
        endpoint = params.get("endpoint", "")
        auth = params.get("auth", "")
        dependencias = params.get("dependencias", "")
        doc_md = f"""# Ficha Técnica de Microservicio / API: {servicio}
* **Líder Técnico / Autor:** `{autor}`
* **Nivel:** `{nivel}`
* **Ambiente:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Endpoint Base:** `{endpoint}`
* **Método de Autenticación:** `{auth}`
* **Servidores y VMs:** `{servidores}`

---

## 1. Dependencias y Nodos de Infraestructura
{dependencias}

---

## 2. Telemetría y Monitoreo Asociado
* **APM (New Relic / VZOR):** Monitoreo de latencia y transacciones por segundo.
* **Nagios / PRTG Check:** Chequeo periódico de endpoint `/health`.

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"ficha_servicio_{srv_clean}.md"
        return doc_md, fname

    # 5. Failover / Contingencia
    elif "Contingencia" in tipo or "Failover" in tipo:
        sintoma = params.get("sintoma", "")
        pasos = params.get("pasos", "")
        doc_md = f"""# Manual de Contingencia y Failover Operativo: {servicio}
* **Autor / Responsable:** `{autor}`
* **Nivel:** `{nivel}`
* **Ambiente:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Sistemas / Balanceadores:** `{servidores}`

---

## 1. Síntomas de Alerta y Disparadores
{sintoma}

---

## 2. Procedimiento de Conmutación (Failover)
```bash
{pasos}
```

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"contingencia_failover_{srv_clean}.md"
        return doc_md, fname

    # 6. Parchado y Mantenimiento de SO
    elif "Parchado" in tipo or "Mantenimiento de SO" in tipo:
        paquetes = params.get("paquetes", "Actualización de seguridad mensual del kernel y paquetes críticos.")
        pasos_parchado = params.get("pasos_parchado", "1. Snapshot previo en VMware vCloud\n2. yum update -y / apt-get upgrade -y\n3. Reboot de nodo secundario\n4. Validación de servicios")
        rollback_parchado = params.get("rollback_parchado", "Revertir snapshot de VM en vCloud Director.")
        doc_md = f"""# Procedimiento de Parchado y Mantenimiento de SO: {servicio}
* **Autor / Administrador:** `{autor}`
* **Nivel:** `{nivel}`
* **Ambiente:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Ventana de Mantenimiento:** `{ventana}`
* **Nodos / Servidores a Intervenir:** `{servidores}`

---

## 1. Alcance y Paquetes a Actualizar
{paquetes}

---

## 2. Pasos de Aplicación de Parches
```bash
{pasos_parchado}
```

---

## 3. Plan de Reversión Inmediato
{rollback_parchado}

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"parchado_so_{srv_clean}.md"
        return doc_md, fname

    # 7. Renovación de Certificados SSL/TLS
    elif "Certificados" in tipo or "SSL" in tipo:
        dominio = params.get("dominio", "*.empresa.internal")
        ruta_cert = params.get("ruta_cert", "/etc/ssl/certs/")
        comandos_renov = params.get("comandos_renov", "openssl req -new -newkey rsa:2048 -nodes ...")
        validacion_ssl = params.get("validacion_ssl", "echo | openssl s_client -connect localhost:443 -servername api.internal")
        doc_md = f"""# Procedimiento de Renovación de Certificados SSL/TLS: {servicio}
* **Autor / Responsable de Seguridad:** `{autor}`
* **Nivel:** `{nivel}`
* **Dominio / CN:** `{dominio}`
* **Ubicación en Servidor:** `{ruta_cert}`
* **Ambiente:** `{ambiente}`
* **Servidores y Nodos Afectados:** `{servidores}`

---

## 1. Comandos de Generación y Carga de Certificado
```bash
{comandos_renov}
```

---

## 2. Validación de Vigencia y Handshake
```bash
{validacion_ssl}
```

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"renovacion_cert_{srv_clean}.md"
        return doc_md, fname

    # 8. Disaster Recovery (DRP)
    elif "Disaster Recovery" in tipo or "DRP" in tipo:
        rpo_rto = params.get("rpo_rto", "RPO: 15 minutos | RTO: 1 hora")
        activacion_drp = params.get("activacion_drp", "Declaración formal de contingencia por Gerencia de Operaciones.")
        pasos_drp = params.get("pasos_drp", "1. Conmutar DNS externo al Datacenter Secundario\n2. Promover réplica de Base de Datos a Primario\n3. Levantar workers WSO2 en sitio secundario")
        doc_md = f"""# Plan de Recuperación ante Desastres (DRP): {servicio}
* **Autor / Coordinador DRP:** `{autor}`
* **Nivel:** `{nivel}`
* **Objetivos:** `{rpo_rto}`
* **Ambiente:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Sitios y Nodos Involucrados:** `{servidores}`

---

## 1. Criterios de Activación del DRP
{activacion_drp}

---

## 2. Procedimiento de Conmutación a Datacenter Secundario
```bash
{pasos_drp}
```

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"drp_{srv_clean}.md"
        return doc_md, fname

    # 9. Respaldo y Restauración de Base de Datos
    elif "Respaldo" in tipo or "Base de Datos" in tipo:
        motor_bd = params.get("motor_bd", "PostgreSQL HA / Oracle RAC")
        comando_backup = params.get("comando_backup", "pg_dump -h 10.24.0.130 -U admin -Fc db_booking > backup.dump")
        comando_restore = params.get("comando_restore", "pg_restore -h 10.24.0.130 -U admin -d db_booking backup.dump")
        doc_md = f"""# Plan de Respaldo y Restauración de Base de Datos: {servicio}
* **Autor / DBA Responsable:** `{autor}`
* **Nivel:** `{nivel}`
* **Motor de BD:** `{motor_bd}`
* **Ambiente:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Nodos de BD:** `{servidores}`

---

## 1. Procedimiento de Respaldo (Backup)
```bash
{comando_backup}
```

---

## 2. Procedimiento de Restauración (Restore)
```bash
{comando_restore}
```

---
*Documento generado mediante Plantilla Oficial de Operaciones e Infraestructura.*
"""
        fname = f"backup_restore_db_{srv_clean}.md"
        return doc_md, fname

    # 10. Plantilla Personalizada o Tipo Dinámico
    else:
        tipo_limpio = tipo.replace("[Personalizado]", "").strip()
        objetivo = params.get("objetivo", "")
        prerequisitos = params.get("prerequisitos", "")
        pasos_custom = params.get("pasos_custom", "")
        verificacion_custom = params.get("verificacion_custom", "")
        rollback_custom = params.get("rollback_custom", "")

        doc_md = f"""# Procedimiento Técnico: {tipo_limpio} - {servicio}
* **Autor / Responsable:** `{autor}`
* **Tipo de Procedimiento:** `{tipo_limpio}`
* **Nivel de Arquitectura:** `{nivel}`
* **Ambiente Objetivo:** `{ambiente}`
* **Criticidad:** `{criticidad}`
* **Ventana de Mantenimiento:** `{ventana}`
* **Sistemas / Servidores Involucrados:** `{servidores}`

---

## 1. Objetivo y Alcance
{objetivo}

---

## 2. Requisitos Previos y Permisos
{prerequisitos}

---

## 3. Pasos de Ejecución Detallados
```bash
{pasos_custom}
```

---

## 4. Validación y Criterios de Aceptación
{verificacion_custom}

---

## 5. Plan de Contingencia / Reversión
{rollback_custom}

---
*Documento generado mediante Generador de Procedimientos de Infraestructura.*
"""
        tipo_slug = tipo_limpio.lower().replace(" ", "_")
        fname = f"proc_{tipo_slug}_{srv_clean}.md"
        return doc_md, fname

"""
Plantillas oficiales de documentacion tecnica y generadores de Runbooks.
"""

def generar_doc_plantilla(tipo: str, autor: str, servicio: str, nivel: str, params: dict) -> tuple[str, str]:
    """Genera el contenido Markdown y el nombre de archivo sugerido segun la plantilla seleccionada."""
    srv_clean = servicio.lower().replace(" ", "_")

    if "Rollback" in tipo:
        criterio = params.get("criterio", "")
        pasos = params.get("pasos", "")
        verif = params.get("verif", "")
        doc_md = f"""# Procedimiento de Rollback: {servicio}
* **Autor:** `{autor}`
* **Nivel:** `{nivel}`
* **Tipo:** `Rollback de Emergencia`

---

## 1. Criterios de Activación
{criterio}

## 2. Pasos de Reversión
```bash
{pasos}

```

## 3. Verificación Post-Rollback
```bash
{verif}
```

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
        fname = f"procedimiento_rollback_{srv_clean}.md"
        return doc_md, fname

    elif "Paso a Producción" in tipo:
        version = params.get("version", "v1.0.0")
        pipeline = params.get("pipeline", "")
        variables = params.get("variables", "")
        smoke = params.get("smoke", "")
        doc_md = f"""# Guía de Despliegue a Producción: {servicio} ({version})
* **Autor:** `{autor}`
* **Nivel:** `{nivel}`
* **Pipeline:** `{pipeline}`

---

## 1. Variables de Entorno y Secretos
```env
{variables}
```

## 2. Checklist de Validación (Smoke Tests)
{smoke}

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
        fname = f"despliegue_{srv_clean}_{version.replace('.', '_')}.md"
        return doc_md, fname

    elif "Postmortem" in tipo:
        incidente_id = params.get("incidente_id", "INC-001")
        impacto = params.get("impacto", "")
        causa = params.get("causa", "")
        solucion = params.get("solucion", "")
        preventiva = params.get("preventiva", "")
        doc_md = f"""# Reporte Postmortem P1: {incidente_id} - {servicio}
* **Autor:** `{autor}`
* **Nivel Afectado:** `{nivel}`
* **Incidente:** `{incidente_id}`

---

## 1. Resumen del Impacto
{impacto}

## 2. Causa Raíz (Root Cause Analysis)
{causa}

## 3. Solución Aplicada
{solucion}

## 4. Acciones Correctivas y Prevención
{preventiva}

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
        fname = f"postmortem_{incidente_id.lower()}_{srv_clean}.md"
        return doc_md, fname

    elif "Microservicio" in tipo:
        endpoint = params.get("endpoint", "")
        auth = params.get("auth", "")
        dependencias = params.get("dependencias", "")
        doc_md = f"""# Ficha Técnica de Microservicio: {servicio}
* **Desarrollador / Líder Técnico:** `{autor}`
* **Nivel:** `{nivel}`
* **Endpoint Base:** `{endpoint}`
* **Autenticación:** `{auth}`

---

## 1. Dependencias y Nodos de Infraestructura
{dependencias}

## 2. Telemetría y Métricas Clave
* **New Relic APM:** Latencia normal < 40ms
* **Nagios Check:** `check_http -H localhost -p 8080 -u {endpoint}/health`

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
        fname = f"ficha_servicio_{srv_clean}.md"
        return doc_md, fname

    else:  # Failover
        sintoma = params.get("sintoma", "")
        pasos = params.get("pasos", "")
        doc_md = f"""# Manual de Contingencia y Failover: {servicio}
* **Autor:** `{autor}`
* **Nivel:** `{nivel}`

---

## 1. Síntoma de Alerta
{sintoma}

## 2. Procedimiento de Conmutación (Failover)
```bash
{pasos}
```

*Documento generado mediante Plantilla Oficial de Operaciones AIOps.*
"""
        fname = f"contingencia_failover_{srv_clean}.md"
        return doc_md, fname

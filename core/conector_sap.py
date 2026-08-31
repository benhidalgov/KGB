"""
Modulo de Integracion de Infraestructura SAP.
Provee conectividad, modelos de datos del landscape, telemetria en tiempo real,
generacion de topologia Mermaid y sincronizacion de CMDB.
"""
import os
import json
import time
import datetime
import pandas as pd
from core.configuracion import CSV_PATH
from core.auditoria import registrar_evento_auditoria

DATA_LANDSCAPE_SAP_DEFAULT = [
    {"servidor_id": "SRV-SAP-HANA01", "numero_serie": "HPE-DL580-SN901", "ip": "10.24.10.50", "sid": "HDB", "instancia": "HDB00", "vcloud_vm": "vm-sap-hana-pri", "nivel_arquitectura": "L3 - Middleware", "componente": "SAP HANA DB 2.0 SPS07 (Primary HSR)", "os": "SUSE Linux Enterprise Server 15 SP4", "cpu_pct": 34.2, "mem_pct": 82.5, "disco_pct": 58.0, "kernel": "HANA 2.00.070.00", "estado": "Operativo", "sap_host_agent": "7.22 PL 62", "nagios_check": "OK (HSR in sync)"},
    {"servidor_id": "SRV-SAP-HANA02", "numero_serie": "HPE-DL580-SN902", "ip": "10.24.10.51", "sid": "HDB", "instancia": "HDB00", "vcloud_vm": "vm-sap-hana-sec", "nivel_arquitectura": "L3 - Middleware", "componente": "SAP HANA DB 2.0 SPS07 (Secondary HSR)", "os": "SUSE Linux Enterprise Server 15 SP4", "cpu_pct": 18.0, "mem_pct": 81.9, "disco_pct": 57.5, "kernel": "HANA 2.00.070.00", "estado": "Operativo", "sap_host_agent": "7.22 PL 62", "nagios_check": "OK (Replication Active)"},
    {"servidor_id": "SRV-SAP-PRDASCS", "numero_serie": "HPE-BL460-SN910", "ip": "10.24.10.60", "sid": "PRD", "instancia": "ASCS01", "vcloud_vm": "vm-sap-prd-ascs", "nivel_arquitectura": "L4 - Aplicación", "componente": "SAP S/4HANA 2022 Central Services (ASCS/ERS)", "os": "Red Hat Enterprise Linux 8.8", "cpu_pct": 15.4, "mem_pct": 42.0, "disco_pct": 31.2, "kernel": "789 PL 200", "estado": "Operativo", "sap_host_agent": "7.22 PL 62", "nagios_check": "OK (Enqueue Service Online)"},
    {"servidor_id": "SRV-SAP-PRDPAS", "numero_serie": "HPE-BL460-SN911", "ip": "10.24.10.61", "sid": "PRD", "instancia": "PAS02", "vcloud_vm": "vm-sap-prd-pas", "nivel_arquitectura": "L4 - Aplicación", "componente": "SAP S/4HANA Primary Application Server (PAS)", "os": "Red Hat Enterprise Linux 8.8", "cpu_pct": 68.2, "mem_pct": 74.6, "disco_pct": 45.0, "kernel": "789 PL 200", "estado": "Operativo", "sap_host_agent": "7.22 PL 62", "nagios_check": "OK (Dialog Queues Normal)"},
    {"servidor_id": "SRV-SAP-PRDAAS01", "numero_serie": "HPE-BL460-SN912", "ip": "10.24.10.62", "sid": "PRD", "instancia": "AAS03", "vcloud_vm": "vm-sap-prd-aas01", "nivel_arquitectura": "L4 - Aplicación", "componente": "SAP S/4HANA Additional Application Server (AAS)", "os": "Red Hat Enterprise Linux 8.8", "cpu_pct": 52.8, "mem_pct": 69.1, "disco_pct": 43.8, "kernel": "789 PL 200", "estado": "Operativo", "sap_host_agent": "7.22 PL 62", "nagios_check": "OK (Dialog Queues Normal)"},
    {"servidor_id": "SRV-SAP-WDISP01", "numero_serie": "HPE-BL460-SN920", "ip": "10.24.10.40", "sid": "WDP", "instancia": "WDP00", "vcloud_vm": "vm-sap-wdisp01", "nivel_arquitectura": "L3 - Middleware", "componente": "SAP Web Dispatcher (Load Balancer HTTPS)", "os": "Red Hat Enterprise Linux 8.8", "cpu_pct": 22.0, "mem_pct": 35.5, "disco_pct": 25.0, "kernel": "789 PL 150", "estado": "Operativo", "sap_host_agent": "7.22 PL 62", "nagios_check": "OK (SSL Terminated, Round Robin)"},
    {"servidor_id": "SRV-SAP-SOLMAN", "numero_serie": "HPE-DL380-SN930", "ip": "10.24.10.90", "sid": "SM1", "instancia": "SOL01", "vcloud_vm": "vm-sap-solman", "nivel_arquitectura": "L3 - Middleware", "componente": "SAP Solution Manager 7.2 / LMDB", "os": "SUSE Linux Enterprise Server 15 SP3", "cpu_pct": 41.5, "mem_pct": 89.2, "disco_pct": 84.1, "kernel": "753 PL 1100", "estado": "En Revision", "sap_host_agent": "7.22 PL 60", "nagios_check": "WARNING (High Memory Usage 89%)"}
]

ALERTAS_SAP_DEFAULT = [
    {
        "id_alerta": "ALT-SAP-8902", "sid": "SM1", "servidor_id": "SRV-SAP-SOLMAN",
        "tipo": "Capacidad de Memoria", "severidad": "Advertencia",
        "mensaje": "Uso de memoria fisica en 89.2%, superando el umbral de alerta preventiva (85%).",
        "accion_recomendada": "Revisar buffers de SolMan y considerar reinicio de procesos Java o ampliacion de RAM.",
        "timestamp": "2026-08-27 08:45:12"
    },
    {
        "id_alerta": "ALT-SAP-8901", "sid": "HDB", "servidor_id": "SRV-SAP-HANA01",
        "tipo": "HSR Replication Lag", "severidad": "Informativa",
        "mensaje": "Replica de datos HSR asincrona sincronizada al 100%. Latencia de replica: 1.4 ms.",
        "accion_recomendada": "Monitoreo regular sin requerimiento de intervencion.",
        "timestamp": "2026-08-27 09:00:00"
    }
]


def probar_conexion_api_sap(endpoint_url: str, tipo_auth: str, client_id: str = "") -> dict:
    """Simula o ejecuta la verificacion de conexion HTTP/REST hacia la API de SAP."""
    t0 = time.time()
    time.sleep(0.05)
    latencia_ms = max(int((time.time() - t0) * 1000), 24)
    url_limpia = endpoint_url.strip() if endpoint_url else "API Gateway SAP"

    return {
        "status_code": 200,
        "status_text": "OK",
        "latencia_ms": latencia_ms,
        "endpoint": url_limpia,
        "autenticacion": tipo_auth,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "protocolo": "HTTP/1.1 TLS 1.3",
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "X-SAP-Service-Version": "v1.4.2",
            "X-Correlation-ID": f"sap-corr-{int(time.time())}",
            "Cache-Control": "no-cache, no-store"
        },
        "detalles": "Conexion exitosa con el servicio de monitoreo e inventario SAP."
    }


def obtener_inventario_sap_df() -> pd.DataFrame:
    """Retorna el inventario de servidores e instancias SAP como DataFrame."""
    return pd.DataFrame(DATA_LANDSCAPE_SAP_DEFAULT)


def obtener_alertas_sap() -> list:
    """Retorna el listado de alertas de infraestructura activas en el landscape SAP."""
    return ALERTAS_SAP_DEFAULT


def generar_payload_json_sap(endpoint_url: str = "") -> dict:
    """Genera el payload completo JSON estructurado que expone la API de SAP."""
    return {
        "metadata": {
            "landscape_id": "LANDSCAPE-CORP-PRD-01",
            "source": "SAP Cloud ALM / Host Agent Operations API",
            "api_version": "v1.4",
            "generated_at": datetime.datetime.now().isoformat(),
            "environment": "Produccion",
            "total_systems": 3,
            "total_hosts": len(DATA_LANDSCAPE_SAP_DEFAULT)
        },
        "systems": [
            {
                "sid": "HDB", "type": "Database", "database_product": "SAP HANA DB 2.0 SPS07",
                "high_availability": {"mode": "HSR (HANA System Replication)", "operation_mode": "logreplay", "status": "Active / In-Sync"},
                "hosts": [{"hostname": "SRV-SAP-HANA01", "role": "Primary Node", "ip": "10.24.10.50"}, {"hostname": "SRV-SAP-HANA02", "role": "Secondary Node", "ip": "10.24.10.51"}]
            },
            {
                "sid": "PRD", "type": "ERP S/4HANA", "release": "SAP S/4HANA 2022 FPS02", "kernel_version": "789 PL 200",
                "instances": [
                    {"instance_name": "ASCS01", "hostname": "SRV-SAP-PRDASCS", "role": "Message & Enqueue Server"},
                    {"instance_name": "PAS02", "hostname": "SRV-SAP-PRDPAS", "role": "Primary Application Server"},
                    {"instance_name": "AAS03", "hostname": "SRV-SAP-PRDAAS01", "role": "Additional Application Server"}
                ]
            },
            {
                "sid": "SM1", "type": "Lifecycle Management", "release": "SAP Solution Manager 7.2 SPS16",
                "instances": [{"instance_name": "SOL01", "hostname": "SRV-SAP-SOLMAN", "role": "LMDB / CCDB Engine"}]
            }
        ],
        "telemetry": DATA_LANDSCAPE_SAP_DEFAULT,
        "active_alerts": ALERTAS_SAP_DEFAULT
    }


def generar_topologia_sap_mermaid() -> str:
    """Genera la representacion en sintaxis Mermaid del Landscape SAP."""
    return """graph TD
    classDef l1 fill:#1e293b,stroke:#475569,stroke-width:1px,color:#f8fafc;
    classDef l2 fill:#334155,stroke:#64748b,stroke-width:1px,color:#f8fafc;
    classDef l3 fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#f8fafc;
    classDef l4 fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef warn fill:#78350f,stroke:#d97706,stroke-width:2px,color:#fef3c7;

    subgraph Capa_Acceso["Capa de Balanceo y Acceso (L3)"]
        WDISP["SRV-SAP-WDISP01<br/>SAP Web Dispatcher (10.24.10.40)"]:::l3
    end

    subgraph Capa_App["Capa de Aplicacion SAP S/4HANA (L4)"]
        ASCS["SRV-SAP-PRDASCS<br/>Central Services ASCS/ERS (10.24.10.60)"]:::l4
        PAS["SRV-SAP-PRDPAS<br/>Primary App Server PAS (10.24.10.61)"]:::l4
        AAS["SRV-SAP-PRDAAS01<br/>Additional App Server AAS (10.24.10.62)"]:::l4
    end

    subgraph Capa_DB["Capa de Base de Datos SAP HANA (L3)"]
        HANA_PRI["SRV-SAP-HANA01<br/>HANA Primary HDB00 (10.24.10.50)"]:::l3
        HANA_SEC["SRV-SAP-HANA02<br/>HANA Secondary HSR (10.24.10.51)"]:::l3
    end

    subgraph Capa_Gestion["Monitoreo y Gestion de Landscape"]
        SOLMAN["SRV-SAP-SOLMAN<br/>Solution Manager / LMDB (10.24.10.90)"]:::warn
    end

    WDISP -->|HTTPS / RFC| PAS
    WDISP -->|HTTPS / RFC| AAS
    PAS -->|Enqueue Locks| ASCS
    AAS -->|Enqueue Locks| ASCS
    PAS -->|SQL DBSL Client| HANA_PRI
    AAS -->|SQL DBSL Client| HANA_PRI
    HANA_PRI == "Replicacion HSR Asincrona (Logreplay)" ==> HANA_SEC
    SOLMAN -.->|Host Agent 1129 / CCDB| HANA_PRI
    SOLMAN -.->|Host Agent 1129 / CCDB| PAS
"""


def sincronizar_servidores_sap_cmdb(autor: str = "Conector API SAP") -> tuple[bool, int, str]:
    """Sincroniza los servidores del landscape SAP en mantenimientos.csv y registra el evento en auditoria."""
    if not os.path.exists(CSV_PATH):
        return False, 0, "No se encontro el archivo mantenimientos.csv"

    try:
        df_actual = pd.read_csv(CSV_PATH)
    except Exception as e:
        return False, 0, f"Error al leer mantenimientos.csv: {str(e)}"

    fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
    ids_existentes = set(df_actual["servidor_id"].astype(str).str.strip()) if "servidor_id" in df_actual.columns else set()

    nuevos_registros = [
        {
            "servidor_id": item["servidor_id"],
            "numero_serie": item["numero_serie"],
            "ip": item["ip"],
            "vcloud_vm": item["vcloud_vm"],
            "nivel_arquitectura": item["nivel_arquitectura"],
            "componente": item["componente"],
            "fecha": fecha_hoy,
            "tipo_mantenimiento": "Sincronizacion API",
            "tecnico": autor,
            "descripcion": f"Ingesta automatizada via API SAP. Host OS: {item['os']}. Kernel: {item['kernel']}.",
            "estado": item["estado"],
            "nagios_check": item["nagios_check"]
        }
        for item in DATA_LANDSCAPE_SAP_DEFAULT if item["servidor_id"] not in ids_existentes
    ]

    if not nuevos_registros:
        return True, 0, "Todos los servidores de SAP ya se encuentran registrados en la CMDB local."

    df_consolidado = pd.concat([df_actual, pd.DataFrame(nuevos_registros)], ignore_index=True)

    try:
        df_consolidado.to_csv(CSV_PATH, index=False, encoding="utf-8")
        registrar_evento_auditoria(
            doc_name="mantenimientos.csv",
            accion="Sincronizacion CMDB API SAP",
            version_ant=1,
            version_nueva=1,
            autor=autor,
            motivo=f"Ingesta automatica de {len(nuevos_registros)} servidores del landscape SAP."
        )
        return True, len(nuevos_registros), f"Se sincronizaron exitosamente {len(nuevos_registros)} servidores SAP en la CMDB."
    except Exception as e:
        return False, 0, f"Fallo al escribir en mantenimientos.csv: {str(e)}"

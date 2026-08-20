"""
Definicion del diagrama topologico Mermaid y especificacion de componentes por capas.
"""

TOPOLOGY_MERMAID = """graph TD
    subgraph DevOps ["Capa DevOps y Despliegues (CI/CD)"]
        GitLab["GitLab (Control de Versiones y SCM)"]
        Jenkins["Jenkins (PRODJENK001/002 - Despliegues)"]
        PasosProd["Pasos a Producción Unicard (Procedimientos)"]
        GitLab --> Jenkins
        PasosProd -. Rige a .-> Jenkins
    end

    subgraph L4 ["Nivel 4: Aplicaciones y Negocio de Producción"]
        CreditMaker["CREDITMAKER (Evaluación y Venta de Créditos)"]
        Engage["ENGAGE (Sitio y Call Centers 10.24.0.12)"]
        BookingApp["Booking Core Engine (Motor de Negocio)"]
    end

    subgraph L3 ["Nivel 3: Middleware e Integración"]
        WSO2["WSO2 Suite (API Manager, EI, Identity Server)"]
        Balancer["HAProxy (BALANCER001/002 - 10.24.0.125/126)"]
        Redis["Redis Sentinel (Caché de Tokens)"]
    end

    subgraph L2 ["Nivel 2: Virtualización y Cómputo"]
        VCloud["VMware vCloud (vDCs, ESXi Clusters Microsoft/Linux)"]
    end

    subgraph L1 ["Nivel 1: Infraestructura Base / Hardware"]
        HPE["Blades HPE Synergy / ProLiant DL385 G7 / DL360"]
        SAN["SAN Pure Storage FlashArray (Fibre Channel)"]
    end

    subgraph Obs ["Capa Transversal de Observabilidad"]
        PRTG["PRTG Network Monitor (Sensores CPU/RAM/Disco/SLA)"]
        NAG["Nagios Core (Host Checks, Pings, SNMP)"]
        NR["New Relic (APM y Latencia de Microservicios)"]
    end

    Jenkins -. Despliega en .-> L4
    Jenkins -. Despliega en .-> WSO2
    CreditMaker --> Balancer
    Engage --> Balancer
    BookingApp --> Balancer
    Balancer --> WSO2
    WSO2 --> Redis
    WSO2 --> VCloud
    VCloud --> HPE
    VCloud --> SAN

    PRTG -. Monitorea .-> WSO2
    PRTG -. Monitorea .-> VCloud
    NAG -. Monitorea .-> VCloud
    NAG -. Monitorea .-> HPE
    NR -. Monitorea .-> L4"""

PLANTILLAS_DIAGRAMAS = {
    "Topología Completa 4 Niveles (Default)": TOPOLOGY_MERMAID,
    "Flujo API Gateway y Autenticación": """sequenceDiagram
    autonumber
    actor Cliente as Cliente / Frontend
    participant HAProxy as HAProxy (BALANCER001/002)
    participant WSO2 as WSO2 API Manager (10.24.0.125)
    participant Redis as Redis Sentinel (Caché Tokens)
    participant Backend as Microservicio Backend (L4)
    participant DB as Postgres HA (10.24.0.130)

    Cliente->>HAProxy: HTTPS Request con Bearer Token
    HAProxy->>WSO2: Enruta tráfico balanceado
    WSO2->>Redis: Validar Token OAuth2 en caché
    Redis-->>WSO2: Token Válido (TTL OK)
    WSO2->>Backend: Forward Request saneada
    Backend->>DB: Query SQL de Negocio
    DB-->>Backend: Result Set
    Backend-->>WSO2: Respuesta JSON 200 OK
    WSO2-->>HAProxy: Respuesta
    HAProxy-->>Cliente: Respuesta HTTP 200 OK""",
    "Pipeline CI/CD y Despliegue": """graph LR
    Dev[Desarrollador] -->|git push| GitLab[GitLab SCM]
    GitLab -->|Webhook| Jenkins[Jenkins CI/CD]
    
    subgraph Pipeline ["Pipeline de Despliegue Unicard"]
        Build[Build & Unit Tests]
        Sonar[SonarQube Quality Gate]
        DeployStg[Deploy a Staging]
        Approval{Aprobación Operaciones}
        DeployProd[Deploy a Producción vCloud]
    end

    Jenkins --> Build
    Build --> Sonar
    Sonar --> DeployStg
    DeployStg --> Approval
    Approval -->|Aprobado| DeployProd
    Approval -->|Rechazado| Rollback[Notificación / Rollback]""",
    "Alta Disponibilidad y Failover HAProxy": """graph TD
    User((Usuarios / Clientes)) --> VIP[IP Virtual HAProxy: 10.24.0.120]
    
    subgraph Balancers ["Capa de Balanceo HA"]
        Node1["BALANCER001 (10.24.0.125 - Activo)"]
        Node2["BALANCER002 (10.24.0.126 - Pasivo / VRRP)"]
    end
    
    VIP --> Node1
    Node1 -. Keepalived Heartbeat .-> Node2

    subgraph Workers ["Nodos de Trabajo WSO2 EI"]
        W1[WSO2 Worker 01 - 10.24.0.131]
        W2[WSO2 Worker 02 - 10.24.0.132]
    end

    Node1 --> W1
    Node1 --> W2
    Node2 -. Standby Failover .-> W1
    Node2 -. Standby Failover .-> W2"""
}

INFRA_SPECS = {
    "L1": ("L1: Hardware Base", "- HPE ProLiant DL385/DL360\n- Pure Storage SAN FlashArray\n- Redes Fibre Channel 16Gbps\n- Fuentes Redundantes 7x24"),
    "L2": ("L2: Virtualización", "- VMware vCloud Director\n- Clusters ESXi Intesis & Lidice\n- Redes SDN NSX-T\n- Datastores VMFS"),
    "L3": ("L3: Middleware", "- WSO2 API Manager 2.5.0\n- WSO2 Enterprise Integrator 6.2\n- HAProxy (BALANCER001/002)\n- Redis Sentinel Cluster"),
    "L4": ("L4: Aplicaciones", "- CREDITMAKER (Créditos)\n- ENGAGE (Call Center)\n- Jenkins / GitLab CI/CD\n- Booking Core Engine")
}


"""
Modulo de Red Neuronal de Infraestructura y Topologia Relacional.
Implementa el formalismo de grafo neuronal para inferencia de impacto,
analisis de causa raiz y simulacion de propagacion de fallas entre capas L1-L4.
"""

import math
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd


class RedNeuronalInfraestructura:
    """
    Grafo Neuronal Dirigido y Ponderado para modelar Elementos de Configuracion (CIs)
    como nodos neuronales y dependencias operativas como sinapsis con pesos de acoplamiento.
    """

    def __init__(self):
        self.nodos: Dict[str, Dict[str, Any]] = {}
        self.sinapsis_salientes: Dict[str, List[Dict[str, Any]]] = {}
        self.sinapsis_entrantes: Dict[str, List[Dict[str, Any]]] = {}
        self._inicializar_topologia_corporativa()

    def agregar_nodo(
        self,
        ci_id: str,
        capa: str,
        ip: str = "-",
        criticidad: str = "CRITICO",
        sistema: str = "Core",
        datacenter: str = "Intesis EY",
        rol: str = "Servidor",
        umbral_activacion: float = 0.75
    ) -> None:
        """Registra un nuevo nodo (CI) en la red neuronal."""
        self.nodos[ci_id] = {
            "id": ci_id,
            "capa": capa,
            "ip": ip,
            "criticidad": criticidad,
            "sistema": sistema,
            "datacenter": datacenter,
            "rol": rol,
            "umbral": umbral_activacion,
            "estado_basal": 0.0,
            "estado_actual": 0.0
        }
        if ci_id not in self.sinapsis_salientes:
            self.sinapsis_salientes[ci_id] = []
        if ci_id not in self.sinapsis_entrantes:
            self.sinapsis_entrantes[ci_id] = []

    def agregar_sinapsis(
        self,
        origen: str,
        destino: str,
        peso: float = 0.90,
        tipo_relacion: str = "DEPENDS_ON"
    ) -> None:
        """Registra una arista sinaptica dirigida con peso de transmision de impacto."""
        if origen not in self.nodos or destino not in self.nodos:
            return

        sinapsis_info = {
            "origen": origen,
            "destino": destino,
            "peso": min(max(peso, 0.0), 1.0),
            "tipo": tipo_relacion
        }
        self.sinapsis_salientes[origen].append(sinapsis_info)
        self.sinapsis_entrantes[destino].append(sinapsis_info)

    def simular_propagacion_impacto(
        self,
        nodo_origen: str,
        intensidad_inicial: float = 1.0,
        max_iteraciones: int = 5
    ) -> Dict[str, Any]:
        """
        Calcula la propagacion de impacto (Forward Propagation) a traves de las sinapsis.
        Retorna los niveles de activacion resultantes para cada CI y los servicios afectados en L4.
        """
        if nodo_origen not in self.nodos:
            return {"error": f"Nodo {nodo_origen} no existe en la red"}

        # Reset de activaciones
        activaciones: Dict[str, float] = {ci: 0.0 for ci in self.nodos}
        activaciones[nodo_origen] = min(max(intensidad_inicial, 0.0), 1.0)
        
        historial_iteraciones = []
        historial_iteraciones.append(dict(activaciones))

        for _ in range(max_iteraciones):
            nuevas_activaciones = dict(activaciones)
            hubo_cambios = False

            for ci_id, info in self.nodos.items():
                # Obtener estimulo transmitido por nodos entrantes
                entrantes = self.sinapsis_entrantes.get(ci_id, [])
                if not entrantes:
                    continue

                suma_estimulos = 0.0
                for sin in entrantes:
                    u = sin["origen"]
                    w = sin["peso"]
                    h_u = activaciones[u]
                    suma_estimulos += h_u * w

                if suma_estimulos > 0:
                    # Funcion de activacion sigmoidea: sigma(z) = 1 / (1 + exp(-k*(z - theta)))
                    umbral = info["umbral"]
                    z = suma_estimulos - (umbral * 0.5)
                    activacion_calculada = 1.0 / (1.0 + math.exp(-4.0 * z)) if -10 < z < 10 else (1.0 if z >= 10 else 0.0)
                    
                    valor_final = max(activaciones[ci_id], activacion_calculada)
                    if abs(valor_final - activaciones[ci_id]) > 0.01:
                        nuevas_activaciones[ci_id] = valor_final
                        hubo_cambios = True

            activaciones = nuevas_activaciones
            historial_iteraciones.append(dict(activaciones))
            if not hubo_cambios:
                break

        # Clasificacion por criticidad y estado
        resultados_nodos = []
        servicios_l4_afectados = []

        for ci_id, valor in activaciones.items():
            meta = self.nodos[ci_id]
            if valor >= 0.75:
                badge_estado = "[CRIT]"
            elif valor >= 0.40:
                badge_estado = "[WARN]"
            else:
                badge_estado = "[OK]"

            item = {
                "ci_id": ci_id,
                "capa": meta["capa"],
                "rol": meta["rol"],
                "ip": meta["ip"],
                "datacenter": meta["datacenter"],
                "nivel_impacto": round(valor, 4),
                "badge": badge_estado
            }
            resultados_nodos.append(item)

            if meta["capa"] == "L4" and valor >= 0.40:
                servicios_l4_afectados.append({
                    "servicio": ci_id,
                    "rol": meta["rol"],
                    "impacto": round(valor * 100, 1),
                    "estado": badge_estado
                })

        # Ordenar por nivel de impacto descendente
        resultados_nodos.sort(key=lambda x: x["nivel_impacto"], reverse=True)
        servicios_l4_afectados.sort(key=lambda x: x["impacto"], reverse=True)

        return {
            "nodo_origen": nodo_origen,
            "intensidad_inicial": intensidad_inicial,
            "nodos_afectados": [r for r in resultados_nodos if r["nivel_impacto"] >= 0.20],
            "servicios_l4_criticos": servicios_l4_afectados,
            "total_afectados": len([r for r in resultados_nodos if r["nivel_impacto"] >= 0.40]),
            "historial": historial_iteraciones
        }

    def diagnosticar_causa_raiz(self, nodo_afectado: str) -> List[Dict[str, Any]]:
        """
        Ejecuta retropropagacion para identificar los nodos upstream mas probables de haber originado la falla.
        """
        if nodo_afectado not in self.nodos:
            return []

        candidatos = []
        visitados = set()
        cola = [(nodo_afectado, 1.0, 0)]  # (nodo, peso_acumulado, profundidad)

        while cola:
            actual, peso_acum, prof = cola.pop(0)
            if actual != nodo_afectado and actual not in visitados:
                visitados.add(actual)
                meta = self.nodos[actual]
                candidatos.append({
                    "ci_id": actual,
                    "capa": meta["capa"],
                    "rol": meta["rol"],
                    "ip": meta["ip"],
                    "datacenter": meta["datacenter"],
                    "probabilidad_origen": round(peso_acum, 4),
                    "profundidad_relacional": prof
                })

            for sin in self.sinapsis_entrantes.get(actual, []):
                origen = sin["origen"]
                peso = sin["peso"]
                if origen not in visitados:
                    cola.append((origen, peso_acum * peso, prof + 1))

        candidatos.sort(key=lambda x: x["probabilidad_origen"], reverse=True)
        return candidatos

    def calcular_analisis_vulnerabilidad(self) -> pd.DataFrame:
        """Calcula grado sinaptico, centralidad y deteccion de puntos unicos de falla (SPOF)."""
        filas = []
        for ci_id, meta in self.nodos.items():
            in_deg = len(self.sinapsis_entrantes.get(ci_id, []))
            out_deg = len(self.sinapsis_salientes.get(ci_id, []))
            total_deg = in_deg + out_deg

            # Identificar SPOF
            es_spof = False
            if meta["capa"] in ["L1", "L2", "L3"] and out_deg >= 2:
                # Verificar si existe failover declarado
                rutas_failover = [s for s in self.sinapsis_salientes.get(ci_id, []) if s["tipo"] in ["FAILOVER_TO", "HA_SYNC"]]
                if not rutas_failover:
                    es_spof = True

            filas.append({
                "CI": ci_id,
                "Capa": meta["capa"],
                "Rol": meta["rol"],
                "IP": meta["ip"],
                "Site": meta["datacenter"],
                "Sinapsis_Entrantes": in_deg,
                "Sinapsis_Salientes": out_deg,
                "Grado_Total": total_deg,
                "Riesgo_SPOF": "[CRIT: SPOF]" if es_spof else "[OK: REDUNDANTE]"
            })

        df = pd.DataFrame(filas)
        return df.sort_values(by=["Grado_Total"], ascending=False)

    def _inicializar_topologia_corporativa(self) -> None:
        """Carga la topologia canonica de la organizacion Unicard."""
        # 1. Nivel L1: Hardware y Almacenamiento
        self.agregar_nodo("SAN_PureStorage", "L1", "-", "CRITICO", "Almacenamiento", "Intesis EY", "SAN Pure Storage FlashArray")
        self.agregar_nodo("HPE_Synergy", "L1", "-", "CRITICO", "Computo Base", "Intesis EY", "Chasis Blade HPE Synergy")
        self.agregar_nodo("DL385_Lidice", "L1", "-", "CRITICO", "Computo Base", "Lidice", "Host Blade ProLiant DL385 G7")
        self.agregar_nodo("DL360_PBX_EY", "L1", "10.24.0.151", "CRITICO", "Telefonia", "Intesis EY", "Asterisk PBX Fisico")
        self.agregar_nodo("DL360_PBX_LID", "L1", "10.24.0.152", "CRITICO", "Telefonia", "Lidice", "Asterisk PBX Fisico")

        # 2. Nivel L2: Virtualizacion y Clusters
        self.agregar_nodo("ClusterBL", "L2", "10.24.0.1", "CRITICO", "VMware", "Intesis EY", "Cloud01-Cluster04-BL460cGen9")
        self.agregar_nodo("ClusterMS", "L2", "10.24.0.1", "CRITICO", "VMware", "Intesis EY", "Cluster-Microsoft-Intel01")
        self.agregar_nodo("ClusterSL", "L2", "10.24.0.1", "CRITICO", "VMware", "Intesis EY", "Cloud02-Cluster01-SL230sGen8")
        self.agregar_nodo("Veeam_Backup", "L2", "10.24.0.80", "MEDIO", "Respaldo", "Intesis EY", "Veeam Backup & Replication Engine")

        # 3. Nivel L3: Middleware, Balanceo e Integracion
        self.agregar_nodo("VIP_HAProxy", "L3", "10.24.0.120", "CRITICO", "Balanceo", "Virtual", "VIP Virtual HAProxy Cluster")
        self.agregar_nodo("BALANCER001", "L3", "10.24.0.125", "CRITICO", "WSO2", "Intesis EY", "HAProxy 1 (Activo)")
        self.agregar_nodo("BALANCER002", "L3", "10.24.0.126", "CRITICO", "WSO2", "Lidice", "HAProxy 2 (Pasivo / GlusterFS)")
        self.agregar_nodo("PRODMIDWARE001", "L3", "10.24.0.128", "CRITICO", "WSO2", "Intesis EY", "WSO2 Publisher / Store Mgr 1")
        self.agregar_nodo("PRODMIDWARE002", "L3", "10.24.0.122", "CRITICO", "WSO2", "Lidice", "WSO2 Publisher / Store Mgr 2")
        self.agregar_nodo("PRODMIDWARE003", "L3", "10.24.0.129", "CRITICO", "WSO2", "Intesis EY", "WSO2 KeyManager / Gateway Wrk 1")
        self.agregar_nodo("PRODMIDWARE004", "L3", "10.24.0.130", "CRITICO", "WSO2", "Lidice", "WSO2 KeyManager / Gateway Wrk 2")
        self.agregar_nodo("Redis_Sentinel", "L3", "10.24.0.135", "CRITICO", "Cache", "Intesis EY", "Cluster Redis Cache Tokens")
        self.agregar_nodo("PRODAPPS001", "L3", "10.24.0.137", "CRITICO", "CMS", "Intesis EY", "Tomcat / NGINX / CMS")

        # 4. Nivel L4: Aplicaciones y Bases de Datos
        self.agregar_nodo("CREDITMAKER", "L4", "10.24.0.50", "CRITICO", "Credito", "Intesis EY", "CreditMaker Core Tablet Venta")
        self.agregar_nodo("ENGAGE_Web_1", "L4", "10.24.0.12", "CRITICO", "Call Center", "Intesis EY", "Engage Call Center Web 1")
        self.agregar_nodo("ENGAGE_Web_2", "L4", "10.24.0.19", "CRITICO", "Call Center", "Intesis EY", "Engage Call Center Web 2")
        self.agregar_nodo("ENGAGE_SQL_1", "L4", "10.24.0.13", "CRITICO", "Call Center", "Intesis EY", "Engage SQL Server 2012 DB1")
        self.agregar_nodo("ENGAGE_SQL_2", "L4", "10.24.0.20", "CRITICO", "Call Center", "Intesis EY", "Engage SQL Server 2012 DB2")
        self.agregar_nodo("CANALES_IIS_1", "L4", "10.24.0.11", "CRITICO", "Canales", "Intesis EY", "Canales Web IIS + SQL Server")
        self.agregar_nodo("CANALES_IIS_2", "L4", "10.24.0.16", "CRITICO", "Canales", "Intesis EY", "Canales Web IIS + SQL Server")
        self.agregar_nodo("CORSEG_App", "L4", "10.24.0.141", "CRITICO", "Seguros", "Intesis EY", "Corredora Seguros App")
        self.agregar_nodo("CORSEG_DB", "L4", "10.24.0.142", "CRITICO", "Seguros", "Intesis EY", "Corredora Seguros Base Datos")
        self.agregar_nodo("DATAMART_SQL", "L4", "10.24.0.21", "CRITICO", "Analitica", "Intesis EY", "Datamart SQL 2012 Core")
        self.agregar_nodo("SAP_BO", "L4", "10.24.0.36", "CRITICO", "ERP", "Intesis EY", "SAP Business One / HANNA")
        self.agregar_nodo("BOOKING_Core", "L4", "10.24.0.75", "CRITICO", "Transaccional", "Intesis EY", "Booking Engine Microservicios")

        # 5. Capa DevOps
        self.agregar_nodo("Jenkins_PROD", "DevOps", "10.24.0.127", "MEDIO", "CI/CD", "Intesis EY", "Jenkins Produccion 1")

        # -------------------------------------------------------------
        # SINAPSIS PONDERADAS (Aristas del Grafo Neuronal)
        # -------------------------------------------------------------
        # L1 -> L2
        self.agregar_sinapsis("SAN_PureStorage", "ClusterBL", 0.99, "STORAGE_FEED")
        self.agregar_sinapsis("SAN_PureStorage", "ClusterMS", 0.99, "STORAGE_FEED")
        self.agregar_sinapsis("SAN_PureStorage", "ClusterSL", 0.99, "STORAGE_FEED")
        self.agregar_sinapsis("HPE_Synergy", "ClusterBL", 0.98, "HOST_HARDWARE")
        self.agregar_sinapsis("HPE_Synergy", "ClusterMS", 0.98, "HOST_HARDWARE")
        self.agregar_sinapsis("DL385_Lidice", "BALANCER002", 0.98, "HOST_HARDWARE")
        self.agregar_sinapsis("DL385_Lidice", "PRODMIDWARE002", 0.98, "HOST_HARDWARE")
        self.agregar_sinapsis("DL385_Lidice", "PRODMIDWARE004", 0.98, "HOST_HARDWARE")

        # L2 -> L3 / L4 Virtualizacion
        self.agregar_sinapsis("ClusterBL", "BALANCER001", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterBL", "PRODMIDWARE001", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterBL", "PRODMIDWARE003", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterBL", "PRODAPPS001", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterBL", "CREDITMAKER", 0.98, "RUNS_ON")

        self.agregar_sinapsis("ClusterMS", "ENGAGE_Web_1", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "ENGAGE_Web_2", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "ENGAGE_SQL_1", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "ENGAGE_SQL_2", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "CANALES_IIS_1", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "CANALES_IIS_2", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "CORSEG_App", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "CORSEG_DB", 0.98, "RUNS_ON")
        self.agregar_sinapsis("ClusterMS", "DATAMART_SQL", 0.98, "RUNS_ON")

        self.agregar_sinapsis("ClusterSL", "SAP_BO", 0.98, "RUNS_ON")

        # L3 Balanceo y Middleware
        self.agregar_sinapsis("VIP_HAProxy", "BALANCER001", 0.95, "BALANCES_TO")
        self.agregar_sinapsis("VIP_HAProxy", "BALANCER002", 0.95, "BALANCES_TO")
        self.agregar_sinapsis("BALANCER001", "BALANCER002", 0.90, "HA_SYNC")
        self.agregar_sinapsis("BALANCER001", "PRODMIDWARE003", 0.90, "BALANCES_TO")
        self.agregar_sinapsis("BALANCER001", "PRODMIDWARE004", 0.90, "BALANCES_TO")
        self.agregar_sinapsis("BALANCER002", "PRODMIDWARE003", 0.90, "BALANCES_TO")
        self.agregar_sinapsis("BALANCER002", "PRODMIDWARE004", 0.90, "BALANCES_TO")

        self.agregar_sinapsis("PRODMIDWARE003", "Redis_Sentinel", 0.92, "AUTHENTICATES_VIA")
        self.agregar_sinapsis("PRODMIDWARE004", "Redis_Sentinel", 0.92, "AUTHENTICATES_VIA")
        self.agregar_sinapsis("PRODMIDWARE003", "PRODMIDWARE001", 0.85, "DEPENDS_ON")
        self.agregar_sinapsis("PRODMIDWARE004", "PRODMIDWARE002", 0.85, "DEPENDS_ON")

        # L4 Aplicaciones a L3 Middleware
        self.agregar_sinapsis("CREDITMAKER", "VIP_HAProxy", 0.95, "CONSUMES_API")
        self.agregar_sinapsis("ENGAGE_Web_1", "VIP_HAProxy", 0.90, "CONSUMES_API")
        self.agregar_sinapsis("ENGAGE_Web_2", "VIP_HAProxy", 0.90, "CONSUMES_API")
        self.agregar_sinapsis("CANALES_IIS_1", "VIP_HAProxy", 0.95, "CONSUMES_API")
        self.agregar_sinapsis("CANALES_IIS_2", "VIP_HAProxy", 0.95, "CONSUMES_API")
        self.agregar_sinapsis("BOOKING_Core", "VIP_HAProxy", 0.95, "CONSUMES_API")

        # L4 Aplicaciones a Bases de Datos
        self.agregar_sinapsis("ENGAGE_Web_1", "ENGAGE_SQL_1", 0.95, "PERSISTS_IN")
        self.agregar_sinapsis("ENGAGE_Web_2", "ENGAGE_SQL_2", 0.95, "PERSISTS_IN")
        self.agregar_sinapsis("CORSEG_App", "CORSEG_DB", 0.95, "PERSISTS_IN")
        self.agregar_sinapsis("CORSEG_App", "DATAMART_SQL", 0.88, "READS_DATA")


# Instancia singleton para uso en toda la aplicacion
instancia_red_neuronal = RedNeuronalInfraestructura()

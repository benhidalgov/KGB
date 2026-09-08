-- Datos Iniciales (Seed Data) para Consola de Infraestructura y Operaciones

-- 1. Usuarios Base RBAC (Contraseñas predeterminadas: admin2026, operador2026, auditor2026)
INSERT INTO usuarios (username, nombre, rol, hash_password, activo)
VALUES 
    ('admin', 'Administrador Principal', 'Administrador', '2d53641fe5795cd4570900c6511d752609040a18d9fffa7e7170f932b9a61e4d', TRUE),
    ('operador', 'Operador de Infraestructura', 'Operador', '3090bb1981848d3688c0c9bc7bfd0fcce18e54764c9e86e3ca84b3dc5a41b82e', TRUE),
    ('auditor', 'Auditor de Seguridad', 'Auditor', 'edc493ad82a0683fe5531dd725e241fdb84dd3cf74f004915fa6daf4bc5df0b7', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 2. Registro Inicial de Auditoría
INSERT INTO registro_auditoria (documento, accion, version_anterior, version_nueva, autor, motivo, sha256_integridad)
VALUES 
    ('sistema', 'INICIALIZACION_BD', 0, 1, 'Sistema', 'Inicialización exitosa del esquema relacional en PostgreSQL.', '')
ON CONFLICT DO NOTHING;

-- 3. Inventario CMDB y Mantenimientos Iniciales
INSERT INTO mantenimientos (servidor_id, numero_serie, ip, vcloud_vm, nivel_arquitectura, componente, fecha, tipo_mantenimiento, tecnico, descripcion, estado, nagios_check)
VALUES 
    ('SRV-BLADE-01', 'SN-8842-A', '10.24.0.10', 'N/A', 'L1 - Hardware', 'HPE Synergy 12000', '2026-03-01', 'Mantenimiento Preventivo', 'Carlos Mendoza', 'Reemplazo de módulo de ventilación y actualización de firmware iLO 6.', 'Operativo', 'CHECK_HARDWARE_OK'),
    ('SRV-SAN-01', 'SN-9912-B', '10.24.0.20', 'N/A', 'L1 - Hardware', 'Pure Storage FlashArray', '2026-03-02', 'Revision de Capacidad', 'Lucia Gomez', 'Expansion de volumen LUN para datastores vCloud.', 'Operativo', 'CHECK_STORAGE_OK'),
    ('VM-VCD-01', 'SN-VCD-101', '10.24.0.50', 'vcd-cell-01', 'L2 - Virtualización', 'VMware vCloud Director', '2026-03-05', 'Parche de Seguridad', 'Marcos Diaz', 'Aplicación de hotfix ESXi y reinicio escalonado de nodos.', 'Operativo', 'CHECK_VMWARE_OK'),
    ('VM-VEEAM-01', 'SN-VEM-202', '10.24.0.55', 'veeam-srv-01', 'L2 - Virtualización', 'Veeam Backup & Replication', '2026-03-06', 'Prueba DRP', 'Lucia Gomez', 'Validación de recuperación instantánea de máquina virtual (Instant VM Recovery).', 'Operativo', 'CHECK_VEEAM_OK'),
    ('BALANCER001', 'SN-WSO2-01', '10.24.0.80', 'vm-wso2-gw', 'L3 - Middleware', 'WSO2 API Gateway', '2026-03-07', 'Actualizacion de Certificados', 'Carlos Mendoza', 'Renovación de certificados TLS/SSL comodín y recarga sin corte de servicio.', 'Operativo', 'CHECK_HTTPS_OK'),
    ('CACHE-REDIS-01', 'SN-RDS-301', '10.24.0.90', 'vm-redis-node1', 'L3 - Middleware', 'Redis Cluster Sentinel', '2026-03-08', 'Optimizacion de Memoria', 'Marcos Diaz', 'Ajuste de directivas maxmemory-policy a allkeys-lru.', 'Operativo', 'CHECK_REDIS_OK'),
    ('VM-BOOKING-01', 'SN-BKG-401', '10.24.0.125', 'vm-booking-core', 'L4 - Aplicación', 'Booking Core Engine', '2026-03-09', 'Despliegue CI/CD', 'Carlos Mendoza', 'Despliegue de release v2.4.0 de microservicios svc-auth y svc-payments.', 'Operativo', 'CHECK_APP_OK'),
    ('SRV-POSTGRES-HA', 'SN-PG-501', '10.24.0.130', 'vm-postgres-pri', 'L4 - Aplicación', 'PostgreSQL 16 HA', '2026-03-10', 'Validacion de Replicacion', 'Marcos Diaz', 'Comprobación de réplica streaming física y estado del cluster Patroni.', 'Operativo', 'CHECK_PG_REPL_OK')
ON CONFLICT DO NOTHING;

-- Esquema DDL para Consola de Infraestructura y Operaciones
-- Base de datos: PostgreSQL 16

-- 1. Tabla de Usuarios y RBAC
CREATE TABLE IF NOT EXISTS usuarios (
    username VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    rol VARCHAR(50) NOT NULL CHECK (rol IN ('Administrador', 'Operador', 'Auditor')),
    hash_password VARCHAR(256) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ultimo_login TIMESTAMP WITH TIME ZONE
);

-- 2. Tabla de Auditoría y Trazabilidad Inmutable
CREATE TABLE IF NOT EXISTS registro_auditoria (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    documento VARCHAR(255) NOT NULL,
    accion VARCHAR(100) NOT NULL,
    version_anterior INTEGER DEFAULT 0,
    version_nueva INTEGER DEFAULT 1,
    autor VARCHAR(100) NOT NULL,
    motivo TEXT,
    sha256_integridad VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_auditoria_doc ON registro_auditoria(documento);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON registro_auditoria(timestamp DESC);

-- 3. Tabla de Inventario y Mantenimientos (CMDB)
CREATE TABLE IF NOT EXISTS mantenimientos (
    id SERIAL PRIMARY KEY,
    servidor_id VARCHAR(100) NOT NULL,
    numero_serie VARCHAR(100),
    ip VARCHAR(45),
    vcloud_vm VARCHAR(100),
    nivel_arquitectura VARCHAR(30),
    componente VARCHAR(100),
    fecha DATE,
    tipo_mantenimiento VARCHAR(100),
    tecnico VARCHAR(150),
    descripcion TEXT,
    estado VARCHAR(50),
    nagios_check VARCHAR(100),
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mantenimientos_srv ON mantenimientos(servidor_id);
CREATE INDEX IF NOT EXISTS idx_mantenimientos_ip ON mantenimientos(ip);
CREATE INDEX IF NOT EXISTS idx_mantenimientos_serie ON mantenimientos(numero_serie);
CREATE INDEX IF NOT EXISTS idx_mantenimientos_nivel ON mantenimientos(nivel_arquitectura);

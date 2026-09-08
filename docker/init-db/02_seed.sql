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

-- 3. Inventario y Mantenimientos
-- (Sin registros placeholder iniciales; listo para ingesta o sincronización)


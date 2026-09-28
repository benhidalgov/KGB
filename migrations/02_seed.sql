-- Datos Iniciales (Seed Data) para Consola de Infraestructura y Operaciones

-- 1. Usuarios Base RBAC
--    No se insertan credenciales por defecto en produccion.
--    Los usuarios se crean mediante:
--      a) Variables maestras del entorno (.env): ADMIN_PASSWORD, OPERADOR_PASSWORD, AUDITOR_PASSWORD
--      b) El almacen local data/users.json gestionado por la aplicacion
--    Si desea precargar usuarios en PostgreSQL, genere el hash PBKDF2-HMAC-SHA256
--    con formato pbkdf2_sha256$100000$<sal_aleatoria>$<hash_hex> (sal unica por usuario)
--    o use el helper core.auth.generar_hash_password(), e insertelo aqui.

-- 2. Registro Inicial de Auditoría
INSERT INTO registro_auditoria (documento, accion, version_anterior, version_nueva, autor, motivo, sha256_integridad)
VALUES 
    ('sistema', 'INICIALIZACION_BD', 0, 1, 'Sistema', 'Inicialización exitosa del esquema relacional en PostgreSQL.', '')
ON CONFLICT DO NOTHING;

-- 3. Inventario y Mantenimientos
-- (Sin registros placeholder iniciales; listo para ingesta o sincronización)

# Consola de Infraestructura y Operaciones

Plataforma corporativa de asistencia técnica: CMDB en memoria (DuckDB), asistente Gemini RAG, gestión documental con versionado inmutable, autenticación RBAC y bóveda AES-256.

---

## Capacidades

- **RBAC:** Tres roles (`Administrador`, `Operador`, `Auditor`), contraseñas PBKDF2-HMAC-SHA256, bitácora inmutable de sesiones.
- **Búsqueda dual:** Textual en RAM via DuckDB (<2 ms) + Asistente técnico Gemini 2.5 Flash con contexto RAG.
- **Gestión documental:** Ingesta de archivos y paquetes ZIP, versionado (`v1`, `v2`...), diff visual y rollback auditado.
- **Bóveda de credenciales:** Cifrado Fernet/AES-256, jerarquía env → secrets → vault, acceso solo para Administrador.
- **PostgreSQL + fallback local:** Auditoría y usuarios en PG en producción; conmuta a archivos `data/` si no hay DB.

---

## Estructura

```text
C:\Prototipo\
├── app.py                   # Entrada principal (Streamlit)
├── excel_cleaner.py         # Normalizador de libros Excel
├── requirements.txt
├── core/
│   ├── auth.py              # RBAC y sesiones
│   ├── auditoria.py         # Versionado, diff y bitácora
│   ├── motor.py             # DuckDB, Gemini RAG y cachés
│   ├── vault.py             # Bóveda AES-256
│   ├── db.py                # PostgreSQL y fallback
│   └── ...                  # ui_*, procesador, tags, plantillas
├── migrations/              # Scripts SQL (aplicados al arrancar)
├── tests/                   # Verificaciones de auditoría y auth
└── data/                    # CMDB, docs, historial, bóveda
```

---

## Instalación local

```cmd
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Requiere Python 3.12, la misma versión del contenedor. El diagnóstico de la sección siguiente lo verifica.

Acceso: `http://localhost:8501`

---

## Diagnóstico en una máquina nueva

```cmd
python -m core.diagnostico
```

Verifica que este equipo pueda ejecutar la consola y explica qué falta cuando no puede: versión de Python, dependencias reales frente a `requirements.txt`, permisos de escritura en `data/`, datos de arranque, bóveda y cuentas, PostgreSQL y Gemini, puerto de escucha y cadena de importación de la aplicación. Termina con `[CRIT]` y código de salida 1 si algo impide el arranque.

```cmd
REM Sembrar CMDB y documentos de ejemplo en un equipo nuevo (nunca sobrescribe)
python -m core.diagnostico --crear-datos-ejemplo

REM Guardar el informe para adjuntarlo a un ticket
python -m core.diagnostico --informe diagnostico.txt
```

El juego de ejemplo vive en `ejemplos/` y viaja en el repositorio, porque `data/` está excluido del control de versiones.

---

## Despliegue con Docker

```bash
# Copiar y completar: POSTGRES_PASSWORD, ADMIN/OPERADOR/AUDITOR_PASSWORD, VAULT_MASTER_KEY
cp .env.example .env

docker compose up --build -d
docker compose ps
docker compose logs -f copilot_app
```

- Consola: `http://localhost:8501`
- PostgreSQL: `localhost:5432` — DB: `infra_copilot`, Usuario: `infra_admin`
- Migraciones aplicadas automáticamente al arrancar desde `migrations/*.sql`

**Respaldo:**
```bash
docker compose exec -T postgres_db pg_dump -U infra_admin infra_copilot > respaldo_$(date +%F).sql
tar czf respaldo_data_$(date +%F).tar.gz data/
```
> Sin `VAULT_MASTER_KEY` el archivo `data/.vault.enc` es irrecuperable. Nunca la guarde junto al respaldo.

---

## Credenciales

| Variable | Rol | Acceso |
|:---|:---|:---|
| `ADMIN_PASSWORD` | Administrador | Total (vault, ingesta, edición, rollback) |
| `OPERADOR_PASSWORD` | Operador | Consultas, búsqueda, visor, ingesta |
| `AUDITOR_PASSWORD` | Auditor | Solo lectura |

Con `PRODUCCION=1` estas variables son obligatorias. Sin ellas la app no arranca.
En desarrollo local sin `PRODUCCION`, si no se definen se crean las cuentas de fábrica `admin2026`, `operador2026` y `auditor2026` en el primer arranque; el diagnóstico avisa de ello.

---

## Tecnologías

| Componente | Tecnología |
|:---|:---|
| Interfaz | Streamlit |
| Motor SQL en RAM | DuckDB + Pandas |
| Asistente IA | Google GenAI SDK (`gemini-2.5-flash`) |
| Autenticación | PBKDF2-HMAC-SHA256 (`hashlib`) |
| Bóveda | Fernet / AES-256 (`cryptography`) |
| Conversión documental | MarkItDown + OpenPyXL |
| Auditoría | SHA-256 + difflib |
| Diagramas | Mermaid.js |

---

## Licencia

GNU Affero General Public License v3.0 — ver [LICENSE](LICENSE).

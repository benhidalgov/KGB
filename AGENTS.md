# AGENTS.md

Consola Streamlit (Python 3.12) de infraestructura y operaciones: CMDB en DuckDB, RBAC, bóveda AES-256, documentación versionada y un diagrama de arquitectura generado. Código, UI y commits en español.

## Comandos

Usar el venv del repo, no el Python global.

- App: `.\.venv\Scripts\python.exe -m streamlit run app.py` (o `.\run_app.ps1`).
- Compilar: `$f = @('app.py','excel_cleaner.py','tools\gen_arq.py') + (Get-ChildItem core\*.py, tests\*.py).FullName; .\.venv\Scripts\python.exe -m py_compile $f`
- No hay pytest. Los tests son scripts sueltos que imprimen `[OK]`:
  `foreach ($t in 'check_seams','check_bugfixes','check_nivel1','check_auditoria_log','check_auth_versionado','check_security_high','check_visor_imagenes') { .\.venv\Scripts\python.exe "tests\$t.py" }`
- `azure-pipelines.yml` corre solo 5 checks: **no** incluye `check_seams` ni `check_bugfixes`, así que el CI no detecta regresiones de arquitectura ni de bugs previos.
- PowerShell imprime `Exited with code 1` por warnings de Streamlit en stderr. El veredicto es el `[OK]` del script, no el código de salida.
- Los checks aíslan con `tempfile` y mocks y no necesitan PostgreSQL, Docker ni navegador; `check_seams` corre la UI con `streamlit.testing.v1.AppTest`.

## El diagrama de arquitectura es generado

`assets/arquitectura/modelo.json` (modelo) → `assets/arquitectura/arquitectura.html` (render). Los dos se versionan; el `.xlsx` de inventario **no** está en el repo.

- Cambios en `core/arq_render.py`: regenerar con `.\.venv\Scripts\python.exe -m core.arq_render`. Con `python core\arq_render.py` falla el import de `core`.
- Cambios en `tools/gen_arq.py` (flujos, relaciones, reubicaciones de capa): hace falta el Excel; `.\.venv\Scripts\python.exe -X utf8 tools\gen_arq.py --xlsx "<ruta>"` escribe JSON y HTML en una corrida.
- `check_seams` compara el HTML versionado con el render del modelo y falla si difieren: commitear los dos artefactos juntos. Normaliza CRLF, así que los avisos de LF/CRLF de git son ruido.
- No editar el HTML a mano. `%%TEMA%%` lo sustituye `core/ui_arquitectura.py`, y el archivo vive fuera de `data/` porque ese directorio es bind mount en Docker.
- El visor se embebe en un iframe de 1120 px de alto (`core/ui_arquitectura.py`); el layout (capas y flujo, zoom, foco) se dimensiona para eso.

## Runtime y datos

- `data/` es estado de ejecución: ignorado por git salvo `categorias.json`, `MANUAL_DE_OPERACIONES.md` y los `.gitkeep`. No commitear salidas, historial ni bóveda.
- Sin PostgreSQL la app cae a archivos locales. Con `PRODUCCION=1` exige `POSTGRES_PASSWORD`, `VAULT_MASTER_KEY` y las tres contraseñas RBAC, y falla si la base no responde.
- `migrations/*.sql` se aplican al arrancar y quedan registradas en `schema_migrations`: no editar una migración ya aplicada, agregar una nueva.
- `.env` es local; `.env.example` es la plantilla. `.vault.key` / `.vault.enc` nunca se versionan: sin la clave el archivo es irrecuperable.
- Rutas y límites de ingesta están centralizados en `core/configuracion.py`.

## Convenciones del proyecto

- Reglas de `GEMINI.md`: sin emojis en código, UI ni documentación; prohibida la palabra "AIOps"; badges y paleta estándar en vez de iconos.
- Toda pantalla debe ser legible en tema Claro y Oscuro (`core/estilos.py`); el diagrama usa su propio `%%TEMA%%`.
- Ediciones de documentos/CMDB: versionado en `data/history/` y registro de autor, timestamp y motivo en `data/audit_log.json`.
- Remotos: `origin` (GitHub) y `azure`. Pushear siempre a `origin`, nunca a `azure`.
- `.agents/skills/security-review` está vendorizado para revisiones de seguridad.

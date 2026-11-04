# Cognitive Second Brain — Backend

Para iniciar en Windows con el entorno virtual del proyecto:

```powershell
.\start-local.ps1
```

Si aparece `ModuleNotFoundError: pwdlib`, comprueba que usas `.venv` y reinstala las
dependencias con `.\.venv\Scripts\python -m pip install -e '.[dev]'`.

Backend independiente Python 3.11+ y FastAPI. Primera entrega funcional del plan:
identidad, workspaces, RBAC, aislamiento multiempresa y auditoría. Arquitectura,
auditoría y siguientes fases en [docs/architecture.md](docs/architecture.md).

Para compartir una base Supabase con otro proyecto usando tablas en un esquema
independiente, ver [docs/supabase.md](docs/supabase.md).

En Windows usar `BRAIN_DATABASE_URL=sqlite:///./brain.db`. Para reutilizar Supabase
autohospedado en Coolify se incluye `compose.coolify.yaml` y `.env.coolify.example`;
ese despliegue necesita el nombre de la red Docker de Supabase y su URL interna.

## Instalación local (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e '.[dev]'
Copy-Item .env.example .env
# Generar secreto y sustituir BRAIN_JWT_SECRET en .env:
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload
```

Se incluye `requirements.lock.txt` con las versiones verificadas en Python 3.11 /
Windows. Para reproducir ese entorno, instalar primero con `pip install -r
requirements.lock.txt` y después `pip install -e .`. Actualizar el archivo tras
verificar cambios de dependencias. El archivo no equivale a validación en Linux.

API: http://127.0.0.1:8000 · Swagger: http://127.0.0.1:8000/docs · OpenAPI:
http://127.0.0.1:8000/openapi.json. Health checks: `/health/live` y `/health/ready`.
Readiness requiere DB accesible y tabla de usuarios migrada.

## Recorrido real

```powershell
$base = 'http://127.0.0.1:8000/api/v1'
$registration = @{email='kevin@example.com'; name='Kevin'; password='Change-me-123456!'} | ConvertTo-Json
Invoke-RestMethod "$base/auth/register" -Method Post -ContentType 'application/json' -Body $registration
$login = @{email='kevin@example.com'; password='Change-me-123456!'} | ConvertTo-Json
$token = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType 'application/json' -Body $login
$headers = @{Authorization="Bearer $($token.access_token)"}
$workspace = Invoke-RestMethod "$base/workspaces" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"name":"Mi segundo cerebro"}'
Invoke-RestMethod "$base/workspaces" -Headers $headers
Invoke-RestMethod "$base/workspaces/$($workspace.id)/audit" -Headers $headers
```

El login recibe JSON (no formulario OAuth). En Swagger usar **Authorize** con el
access_token. Conservar el token fuera de logs. Registro no inicia sesión automáticamente.

| Método | Ruta `/api/v1` | Acceso |
|---|---|---|
| POST | /auth/register | Público, limitado por IP |
| POST | /auth/login | Público, limitado por IP |
| GET | /auth/me | Autenticado |
| POST, GET | /workspaces | Autenticado; listado solo de membresías propias |
| GET | /workspaces/{id} | Miembro |
| GET | /workspaces/{id}/members | Miembro |
| POST | /workspaces/{id}/members | Owner/admin; email registrado y role |
| GET | /workspaces/{id}/audit | Owner/admin |

Listados admiten `limit` (1–100) y `offset`. Roles: owner, admin, project_manager,
member, viewer. No se permite cambiar el plan comercial mediante la API pública.

## Validación

```powershell
.\.venv\Scripts\pytest -q
.\.venv\Scripts\ruff check .
# Con .env configurado y base migrada:
.\.venv\Scripts\alembic check
```

## Despliegue PostgreSQL / Docker / Coolify

Docker no está instalado en el equipo auditado. Se incluye Compose para un entorno
que lo tenga. Configurar `.env` con `POSTGRES_PASSWORD` (valor alfanumérico aleatorio
para evitar caracteres reservados en la URL), `BRAIN_JWT_SECRET` y
`BRAIN_CORS_ORIGINS` (array JSON de orígenes autorizados). Ejecutar:

```powershell
docker compose up --build -d
```

Compose espera PostgreSQL sano, aplica Alembic en un servicio de migración y arranca
la API. No publica el puerto de PostgreSQL. El puerto de API se limita a loopback;
en Coolify conectar el proxy a la red interna y su puerto 8000. Configurar HTTPS,
backups, secretos, y rate limit distribuido en el despliegue con varias réplicas.
La API no depende de Cognitive Core OS. Integración REST/MCP pendiente de la fase 9.

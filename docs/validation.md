# Evidencia de ejecución — fase 1

Validación local con Python 3.11.9 y SQLite:

- `pytest -q`: 12 pruebas aprobadas. Incluyen registro/login, preservación de espacios
  en contraseñas, JWT expirado, validaciones, rate limit, aislamiento de workspaces,
  permisos de viewer/admin, membresías duplicadas, plan comercial no modificable,
  paginación, configuración de producción y upgrade/check/downgrade de migraciones.
- `ruff check .`: sin errores.
- `alembic upgrade head`: esquema local creado.
- `alembic check`: sin operaciones nuevas respecto de los modelos.
- `pip check`: sin dependencias incompatibles.
- Uvicorn arrancó correctamente. Solicitudes HTTP reales a `/health/live`,
  `/health/ready` y `/openapi.json`: 200; OpenAPI expone 9 rutas distintas.

Una advertencia de Starlette informa que el transporte httpx de TestClient está
deprecado en la versión instalada. Las pruebas funcionan; migrar el transporte de
pruebas al actualizar esa dependencia. No se oculta la advertencia.

Se creó `.env` local con secreto aleatorio y `brain.db` migrada. Ambos están excluidos
de Git. El entorno `.venv` es independiente de los paquetes globales del equipo.
No se han ejecutado Docker, PostgreSQL, integraciones externas ni fases posteriores.

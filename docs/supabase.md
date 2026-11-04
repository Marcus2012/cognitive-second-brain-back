# Supabase compartido

## Desarrollo Windows y despliegue Coolify

El `.env` local utiliza explícitamente `BRAIN_DATABASE_URL=sqlite:///./brain.db`.
Esa variable tiene prioridad sobre cualquier `DATABASE_URL` copiada de otro proyecto.
No se utiliza el archivo SQLite de Cognitive Engineering. No hay fallback automático:
la selección de base es explícita para evitar escribir datos en una base inesperada.

Para reutilizar Supabase en Coolify, desplegar **solo** `compose.coolify.yaml` como
Compose del backend. No combinarlo con `compose.yaml`, que crea PostgreSQL propio.
Configurar las variables de `.env.coolify.example` en Coolify, sustituyendo el alias
real del pooler y el nombre de la red Docker existente del servicio Supabase.
`supabase-supavisor` debe resolver desde esa red; no basta con estar en el mismo VPS.
El usuario `postgres.dev_tenant` corresponde al tenant observado en esta instalación.
La contraseña corresponde a `SERVICE_PASSWORD_POSTGRES`, codificada para URL.

La API y el proceso de migración se unen a esa red. Configurar el dominio del backend
en Coolify al puerto interno 8000 y comprobar que el proxy tiene acceso a esa red.
Este Compose no publica PostgreSQL ni crea otro servicio de base de datos. Las
migraciones crean las tablas en `cognitive_brain`. No modifican las del otro producto.
Validar el despliegue en Coolify: Docker no está disponible en el equipo local.

Para acceder a Supabase desde Windows, cambiar **BRAIN_DATABASE_URL** a la URL del
túnel y mantener SSH activo. Cambiar únicamente `DATABASE_URL` no tiene efecto si
`BRAIN_DATABASE_URL` está configurada. Los datos locales no se sincronizan ni se
copian automáticamente a Supabase.

## Conexión PostgreSQL

Si el administrador ya creó `cognitive_brain` con propietario `brain_app`, las
migraciones comprueban su existencia y no ejecutan CREATE SCHEMA. No es necesario
conceder CREATE sobre la base `postgres`. Si el esquema no existe, el arranque de
migraciones intentará crearlo (requiere un rol con ese permiso). En modo SQL offline
(`--sql`) se presupone que el administrador ya provisionó el esquema.

Un error `permission denied for database postgres` en `CREATE SCHEMA IF NOT EXISTS`
con versiones anteriores requiere desplegar esta corrección, manteniendo los permisos
restringidos del usuario. No cambiar a la cuenta administradora para evitarlo.

La misma base PostgreSQL puede alojar los dos proyectos. Este backend usa el esquema
`cognitive_brain`, con tablas `users`, `workspaces`, `memberships`, `audit_events` y
su propio `alembic_version`. Todos los nombres SQL y claves foráneas se califican
con el esquema. No se usa `public` ni `auth.users`. La autenticación sigue siendo
la del backend, independiente de Supabase Auth.

Configurar en `.env`:

```dotenv
BRAIN_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
BRAIN_DATABASE_SCHEMA=cognitive_brain
```

Obtener la conexión PostgreSQL en Connect de Supabase.
La configuración también acepta `DATABASE_URL` si no existe `BRAIN_DATABASE_URL`.
Si ambas existen, `BRAIN_DATABASE_URL` tiene prioridad. Las URLs asyncpg se adaptan
a psycopg y se activa SSL por defecto para hosts de Supabase.

La contraseña debe estar
codificada para URL. Utilizar conexión directa o session pooler para este servidor
persistente y Alembic. Si la red no admite IPv6, usar session pooler. El backend
utiliza psycopg síncrono, no asyncpg. `SUPABASE_URL` y las API keys no sustituyen la
conexión PostgreSQL y no se utilizan en esta fase. `BRAIN_JWT_SECRET` sigue siendo
independiente del secreto del otro proyecto.

```powershell
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\alembic check
```

La migración crea solo el esquema indicado y sus tablas. Alembic mantiene la versión
dentro de ese esquema y su filtro de autogeneración excluye tablas ajenas.
`downgrade base` elimina únicamente las tablas de esta aplicación y conserva el
esquema. No migra los datos de `brain.db`; SQLite local queda independiente.

No agregar este esquema a los esquemas expuestos por la Data API de Supabase:
el acceso se realiza a través de FastAPI. El esquema separa nombres y migraciones;
para limitar también privilegios, usar un usuario PostgreSQL exclusivo con permisos
solo sobre este esquema en producción, en lugar del usuario administrador compartido.

Conexión y SSL: https://supabase.com/docs/guides/database/connecting-to-postgres

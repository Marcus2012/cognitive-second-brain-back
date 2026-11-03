# Arquitectura y auditoría

## Fase 0: entorno observado

El backend y el repositorio hermano del frontend solo contienen `.git`. No hay
código, contratos, servicios ni configuración existente del producto que reutilizar.
Python 3.11.9 y pip están disponibles. Existen paquetes globales de Python con
versiones dispares; se utiliza `.venv` para no modificarlos. Docker no está instalado
en este equipo. No se presupone acceso a PostgreSQL, Redis, S3 o Cognitive Core OS.

## Decisión de arquitectura

Monolito modular FastAPI con REST versionada `/api/v1`, Pydantic 2 para contratos,
SQLAlchemy 2 para persistencia y Alembic para cambios de esquema. Endpoints síncronos
se ejecutan en el threadpool de FastAPI: no bloquean el event loop con SQL o Argon2.
Una sesión por solicitud y transacciones por operación de negocio. No hay creación
automática de tablas al arrancar; el despliegue aplica las migraciones primero.

PostgreSQL es la base de producción. SQLite permite desarrollar y probar sin
servicios externos. Ambos utilizan las mismas migraciones. Las pruebas locales no
sustituyen una validación en PostgreSQL antes de desplegar.

`app/config.py`: variables y validación; `db.py`: sesiones; `models.py`: persistencia;
`schemas.py`: contratos públicos; `security.py`: identidad; `api.py`: casos de uso
de identidad y organizaciones; `main.py`: composición HTTP y controles transversales.
A medida que se agreguen fases, cada dominio tendrá su paquete con router, modelos,
esquemas y servicios. No se crean endpoints vacíos de funcionalidades futuras.

## Identidad y permisos implementados

Registro, inicio de sesión JSON, contraseñas Argon2 y JWT HS256 con emisor, audiencia
y expiración. El secreto es obligatorio; no hay credencial incorporada. Se comprueba
usuario activo en cada solicitud autenticada. No se confía en un workspace enviado
en el token: se verifica la membresía actual desde la base en cada operación.

Un usuario pertenece a varios workspaces mediante Membership. El creador es owner.
Los roles owner/admin administran membresías y consultan auditoría; los demás roles
leen el workspace y sus miembros. Solo owner concede admin. Ningún endpoint concede
owner adicional. No se implementan aún modificación de rol, transferencia ni bajas.
El alta de miembros requiere usuarios previamente registrados; no envía invitaciones.

Todas las consultas de organizaciones verifican membership; una organización ajena
devuelve 404. Toda futura tabla de negocio tendrá workspace_id y toda referencia
entre recursos comprobará que ambos pertenecen al mismo workspace. El aislamiento
actual es de aplicación, sin Row Level Security de PostgreSQL todavía.

La auditoría registra altas y accesos correctos sin contraseñas ni tokens. Eventos y
mutaciones se confirman en la misma transacción. Listados paginados y límites Pydantic.
Rate limit de autenticación por IP del socket, por proceso y ventana de 60 segundos;
no es un límite distribuido. Para múltiples réplicas se debe reemplazar por Redis
o configurar un límite compartido en el proxy. No confiar en cabeceras de proxy
hasta definir explícitamente los proxies autorizados. HTTPS corresponde al proxy.

## Fases siguientes, secuenciales

2. Knowledge Hub: Source por workspace, adaptadores por proveedor, captura manual y
URL; recuperación con protección SSRF también en redirecciones/resolución DNS, límites
de descarga, timeouts y estados con errores recuperables. Nunca evadir restricciones
de plataformas. Redis + un worker ARQ con trabajos persistentes/reintentos.

3. Document Intelligence: objetos privados S3, tamaños y tipos validados, PDF con
referencias por página, chunks/versiones y procedencia. Puerto LLM/embeddings
independiente del proveedor, pgvector y búsqueda híbrida. Contenido externo como
datos no confiables; extracción no concede permisos ni ejecuta herramientas.

4. Ideas y proyectos: fuentes trazables, hipótesis separadas de hechos, conversión
transaccional e idempotente, espacio de conocimiento por proyecto.

5. Tareas: estados explícitos, dependencias sin ciclos, responsables del workspace,
evidencias y aprobación del plan antes de ejecutarlo.

6. Agentes: catálogo de capacidades, ejecución persistida con input/output, fuentes,
errores y herramientas permitidas. Worker aislado y proveedor real; si no está
configurado se reporta indisponibilidad, sin simular resultados. Acciones sensibles
crean aprobación humana ligada al contenido exacto de la acción.

7. Seguimiento: proyecciones de progreso, resultados, auditoría y reportes.

8. Frontend: repositorio independiente que consume OpenAPI; fuera de este backend.

9. Integraciones: adaptador Core OS por API/MCP autenticado, API keys con hash y
scopes, outbox transaccional y webhooks firmados, idempotencia, reintentos y registro.
Servidor MCP separado que utiliza los mismos servicios/permisos; sin compartir DB
con Core OS. La desconexión de Core OS no interrumpe las operaciones internas.

10. Demo identificada como demostrativa y pruebas de punta a punta con fuentes
reales/autorizadas. No afirmar fabricación ni validación física de prototipos.

## Límites de esta entrega

Se completan las fases 0 y 1. No es todavía el MVP completo del documento maestro.
No incluye ingesta, PDF, RAG, agentes, proyectos, tareas, MCP ni pagos. No necesita
claves LLM. Autenticación pendiente de ampliación: recuperación/verificación de correo,
MFA, refresh tokens y revocación inmediata de JWT; un token emitido expira a los 30
minutos por defecto. No se ha validado Docker/PostgreSQL en este entorno.

Referencias de implementación:
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- https://docs.sqlalchemy.org/en/20/orm/session_basics.html

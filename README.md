# MuseoInteractivoAPI

API de juego interactivo para salas (rooms) e “hints” con autenticación por token Bearer, puntuaciones y desbloqueo progresivo. Incluye script de “seeding” totalmente data‑driven mediante `scripts/data.json`.

Tabla de contenidos
- Requisitos y stack
- Configuración de entorno (.env)
- Base de datos (MySQL)
- Instalación y ejecución (dev)
- Seed de datos y formato de `data.json`
- Autenticación y flujo de usuario
- Endpoints principales (ejemplos cURL)
- Puntuación y desbloqueo
- Seguridad
- Despliegue
- Troubleshooting

## Requisitos y stack
- Python 3.10+ (recomendado)
- MySQL 8+ (o compatible)
- Flask, Flask‑SQLAlchemy, Flask‑Login, Flask‑CORS

## Configuración de entorno (.env)
Copia `env.example` a `.env` y completa los valores relevantes.

Variables clave
- `SQLALCHEMY_DATABASE_URI`: cadena de conexión, por ejemplo `mysql+pymysql://user:pass@localhost:3306/museo_interactivo`.
- `SECRET_KEY`: secreto Flask para firmar sesiones (aunque se usa token, sigue siendo requerido por Flask). Si usas `APP_SECRET_KEY` en tu `.env`, renómbralo a `SECRET_KEY`.
- `FLASK_ENV`: `development` o `production`.
- `LIME_SURVEY_HOST`: host base para construir URLs de LimeSurvey (p. ej. `https://encuestas.ejemplo.com`).
- `FILES_HOST`: host base para imágenes de hints (p. ej. `https://cdn.ejemplo.com/hints`).
- SMTP (opcional para recuperar contraseña): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`.

Notas
- El CORS está habilitado para el uso de cabecera `Authorization`.
- La cookie de sesión no se usa para clientes API; la app responde con un token opaco (Bearer).

## Base de datos (MySQL)
La aplicación requiere una base MySQL accesible por `SQLALCHEMY_DATABASE_URI`.

MySQL local (CLI)
```bash
mysql -u root -p -e "CREATE DATABASE museo_interactivo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Crear usuario y permisos (opcional)
```sql
CREATE USER 'mi_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON museo_interactivo.* TO 'mi_user'@'localhost';
FLUSH PRIVILEGES;
```

Docker (MySQL 8)
```bash
docker run -d --name mi-mysql \
    -e MYSQL_ROOT_PASSWORD=tu_contraseña \
    -e MYSQL_DATABASE=museo_interactivo \
    -e MYSQL_USER=mi_user \
    -e MYSQL_PASSWORD=strong_password \
    -p 3306:3306 \
    mysql:8
```

## Instalación y ejecución (dev)
```bash
# 1) Crear y activar virtualenv (zsh)
python3 -m venv .venv
source .venv/bin/activate

# 2) Dependencias
pip install -r requirements.txt

# 3) Variables de entorno
cp env.example .env
# Edita .env y completa SQLALCHEMY_DATABASE_URI, SECRET_KEY, etc.

# 4) Ejecutar (Flask)
export FLASK_APP=main.py
flask run --host=127.0.0.1 --port=5000
```

Endpoint de health: `GET /healthz` → `{ "status": "healthy" }`.

## Seed de datos y formato de data.json
El seed es 100% data‑driven con `scripts/data.json`:
- `test_user`: usuario de prueba creado si no existe.
- `rooms`: lista de salas. Cada sala define `base_name`, `final_code` y `hints`.
- Cada hint es `{ "name": "Pista N", "access_code": "..." }`.
- La sala 1 no tiene hints y se valida por código final (verificando en endpoint dedicado).

Ejecutar el seeder
```bash
python scripts/seeder.py
```

Cómo se construyen URLs de hints
- `LIME_SURVEY_HOST` + `index.php/S{roomId}P{hintIndex}`
- `FILES_HOST` + `S{roomId}P{hintIndex}.png`

## Autenticación y flujo de usuario
La API usa tokens opacos (portador) enviados en `Authorization: Bearer <token>`.

Flujo básico
1) Registro o login → devuelve `sessionToken` y `sessionTokenExpiry` (+info de usuario).
2) Usa el token Bearer en todas las peticiones protegidas.
3) `POST /auth/logout` revoca el token actual.

Notas
- El backend guarda solo el hash SHA‑256 del token y su expiración (1h por defecto).
- No se usan cookies para la sesión en clientes API.

## Endpoints principales (ejemplos)
En todos los ejemplos protegidos, añade: `-H "Authorization: Bearer $TOKEN"`.

Autenticación
```bash
# Registro
curl -X POST http://localhost:5000/auth/register \
    -H 'Content-Type: application/json' \
    -d '{"nombre":"Ana","apellido":"López","email":"ana@example.com","password":"MiPass123"}'

# Login → devuelve sessionToken
TOKEN=$(curl -s -X POST http://localhost:5000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"ana@example.com","password":"MiPass123"}' | jq -r .sessionToken)

# Yo (usuario actual)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/auth/me

# Logout (revoca token actual)
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:5000/auth/logout

# Recuperar contraseña (opcional SMTP)
curl -X POST http://localhost:5000/auth/forgot -H 'Content-Type: application/json' -d '{"email":"ana@example.com"}'
```

Rooms y hints
```bash
# Listar rooms (con flags por usuario)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/rooms
# Respuesta: [ { id, name, finalCode, imageUrl, completed, isUnlocked }, ... ]

# Detalle de room + hints
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/rooms/2
# Respuesta: { id, name, completed, final_code, hints: [ { id, title, limeSurveyUrl, imageUrl, accessCode, completed } ] }

# Completar un hint (solo el propio usuario o un ADMIN)
curl -X POST http://localhost:5000/rooms/complete \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"room_id":2, "hint_id":5, "email":"ana@example.com"}'
```

Verificación de código final (solo sala 1)
```bash
# Verificar código final sala 1
curl -X POST http://localhost:5000/rooms/1/verify_final_code \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"final_code":"1881-1904-1914-1999"}'
# Respuesta (éxito): { "room_id": 1, "correct": true }
# Respuesta (ya completada): { "error": "room already completed" }
# Respuesta (sala != 1): { "error": "final code verification only allowed for room 1" }
```

Admin de usuarios (requiere rol ADMIN)
```bash
# Listar usuarios (paginado)
curl -H "Authorization: Bearer $TOKEN" 'http://localhost:5000/users?page=1&per_page=10'

# Crear usuario
curl -X POST http://localhost:5000/users \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"nombre":"Eva","apellido":"Ruiz","email":"eva@example.com","password":"Password123","role":"USER"}'
```

## Puntuación y desbloqueo
- Completar un hint por primera vez: +30 puntos.
- Verificar correctamente el código final de la sala 1: +100 puntos (solo la primera vez).
- Al completar una sala (todas sus pistas) o al verificar su código final (sala 1), se desbloquea automáticamente la siguiente sala.
- Solo la sala 1 no tiene pistas; el resto funciona por pistas y código final informativo.

## Seguridad
- Autenticación por token portador opaco (hash almacenado en DB, no el token en claro), expiración 1h.
- Revocación de token en `POST /auth/logout`.
- CORS habilitado para cabecera `Authorization`.
- Recomendado en producción: SECRET_KEY robusto, conexión a BD por SSL, rotación de tokens, limitar orígenes CORS, SMTP real con SPF/DKIM.

## Despliegue
General
- Usa `gunicorn` u otro WSGI server (incluido en requirements) y configura variables de entorno.
- Ejecuta el seed una vez por entorno si necesitas datos iniciales: `python scripts/seeder.py`.

Vercel (archivo `vercel.json`)
- El build actual ejecuta el seeder: `{ "buildCommand": "python3 scripts/seeder.py" }`.
- Configura las variables de entorno en el proyecto de Vercel (DB, SECRET_KEY, LIME_SURVEY_HOST, FILES_HOST, SMTP si aplica).

## Troubleshooting
- 401 Unauthorized: falta o es inválido `Authorization: Bearer <token>`.
- 403 Forbidden: acción no permitida (p. ej., verificar código final en sala != 1, o completar hint de otro usuario sin rol ADMIN).
- Error de conexión a BD: revisa `SQLALCHEMY_DATABASE_URI` y accesibilidad del host/puerto.
- SMTP no configurado: el backend imprimirá el código de recuperación en consola (modo dev).

## Estructura del repo (resumen)
```
controllers/       # Blueprints: auth, rooms, users
db/                # Modelos SQLAlchemy (Usuario, Room, Hint, asociaciones, tokens)
scripts/           # seeder y utilidades (data.json como fuente de verdad)
main.py            # bootstrap Flask + registro de blueprints + CORS
requirements.txt   # dependencias
```

### Contribuyentes
    - Hernán Valencia ([Me!🙌](https://github.com/frjr17)): Fullstack Dev
    - Luis Ellis ([@luisellisc](https://github.com/luisellisc)): Generación de Encuestas
    - Eduardo Xavier Pérez: DevOps

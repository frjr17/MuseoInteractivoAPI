# MuseoInteractivoAPI

README breve que describe la estructura del repositorio y el paso necesario de crear la base de datos (solo para entorno de desarrollo).

Importante: en los ejemplos se usa el usuario root; establece la contraseña que prefieras al ejecutarlos.

## Requisito — crear la base de datos primero (entorno de desarrollo)
La aplicación requiere una base de datos MySQL llamada `museo_interactivo` antes de arrancar. Ejemplos para crearla localmente o usando Docker.

Ejemplo (MySQL CLI local — usuario root, introduce la contraseña que desees)
```bash
mysql -u root -p -e "CREATE DATABASE museo_interactivo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Crear usuario y otorgar permisos (opcional)
```sql
CREATE DATABASE museo_interactivo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mi_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON museo_interactivo.* TO 'mi_user'@'localhost';
FLUSH PRIVILEGES;
```

Ejemplo (Docker) — opción 1: iniciar contenedor con BD creada automáticamente
```bash
docker run -d --name mi-mysql \
    -e MYSQL_ROOT_PASSWORD=tu_contraseña \
    -e MYSQL_DATABASE=museo_interactivo \
    -e MYSQL_USER=mi_user \
    -e MYSQL_PASSWORD=strong_password \
    -p 3306:3306 \
    mysql:8
```

Ejemplo (Docker) — opción 2: crear la base en un contenedor ya en ejecución
```bash
docker exec -it mi-mysql \
    mysql -u root -p -e "CREATE DATABASE museo_interactivo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER 'mi_user'@'%' IDENTIFIED BY 'strong_password'; GRANT ALL PRIVILEGES ON museo_interactivo.* TO 'mi_user'@'%'; FLUSH PRIVILEGES;"
```
## Variables de entorno (ejemplo)
Copia `.env.example` a `.env` y ajusta:
```
SQLALCHEMY_DATABASE_URI=
FLASK_ENV=

```
Ajusta DB_HOST si usas Docker o una instancia remota.

## Pasos rápidos para ejecutar
1. Crea y activa el entorno virtual en la carpeta venv:
```bash
python3.9 -m venv venv
# Unix / macOS
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (cmd)
venv\Scripts\activate.bat
```

2. Instala las dependencias desde requirements.txt:
```bash
pip install -r requirements.txt
```

3. Inicia la aplicación con Flask:
```bash
# Si es necesario, indica el módulo/archivo de la app
export FLASK_APP=main.py        # Windows (cmd): set FLASK_APP=main.py
flask run --host=127.0.0.1 --port=5000
```

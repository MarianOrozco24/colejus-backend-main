# Colejus Backend - Sistema de Gestión de Colegio de Abogados

Este es el backend del sistema de gestión y administración de salas de coworking del Colegio de Abogados, desarrollado en **Flask** con base de datos **MySQL** utilizando **SQLAlchemy** como ORM, **Flask-Migrate** para el control de versiones de base de datos y autenticación segura con **JWT**.

---

## 🛠️ Tecnologías Utilizadas

- **Core:** Python 3.10+, Flask
- **Base de Datos:** MySQL
- **ORM:** SQLAlchemy (Flask-SQLAlchemy)
- **Migraciones:** Flask-Migrate (Alembic)
- **Autenticación:** Flask-JWT-Extended (tokens JWT firmados)
- **Integraciones:** Mercado Pago (pagos) y Telegram (alertas/bot)
- **Seguridad:** Encriptación de firmas y contraseñas, limitador de peticiones (Flask-Limiter) y control de accesos granular por IP.

---

## 📂 Estructura del Proyecto

El proyecto sigue una estructura modular y organizada por responsabilidades:

```text
colejus-backend-main/
├── app.py                  # Punto de entrada principal y configuración inicial de Flask
├── config/                 # Configuraciones de base de datos, emails y Mercado Pago
├── models/                 # Modelos ORM de SQLAlchemy (definición de tablas y relaciones)
├── routes/                 # Controladores y definición de endpoints HTTP
├── utils/                  # Funciones de utilidad (loggers, decoradores, seguridad, emails, bot)
├── tests/                  # Suite de pruebas unitarias y de integración (pytest)
├── migrations/             # Scripts e historial de migraciones de la base de datos
├── requirements.txt        # Dependencias de Python del proyecto
└── .env                    # Configuración de variables de entorno (no versionado)
```

---

## 🚀 Instalación y Configuración Local

Sigue estos pasos para levantar el entorno de desarrollo localmente:

### 1. Requisitos Previos
- Tener instalado **Python 3.10 o superior**.
- Tener una instancia de **MySQL Server** en ejecución.

### 2. Clonar y Configurar Entorno Virtual
Desde la raíz del proyecto, activa tu entorno virtual:
```bash
# Crear entorno virtual si no existe
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate
```

### 3. Instalar Dependencias
Instala los paquetes necesarios definidos en `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
Crea un archivo `.env` en la raíz de `colejus-backend-main` con el siguiente formato, reemplazando con tus credenciales:
```env
# Configuración del servidor Flask
FLASK_APP=app.py
FLASK_ENV=development
JWT_SECRET_KEY=tu_clave_secreta_jwt_aqui

# Conexión a Base de Datos MySQL
MYSQL_USER=tu_usuario_mysql
MYSQL_PASSWORD=tu_contraseña_mysql
MYSQL_HOST=127.0.0.1
MYSQL_DATABASE=nombre_de_la_base_de_datos

# Integración con Mercado Pago
MP_ACCESS_TOKEN=tu_access_token_mercado_pago
MP_PUBLIC_KEY=tu_public_key_mercado_pago

# Configuración de Envío de Mails
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion_gmail
MAIL_DEFAULT_SENDER=tu_email@gmail.com

# Alertas y Notificaciones por Telegram
TELEGRAM_BOT_TOKEN=tu_token_de_bot_telegram
TELEGRAM_CHAT_ID=tu_chat_id_de_telegram
```

### 5. Configurar la Base de Datos con Migraciones
Si es la primera vez que configuras la base de datos o hay nuevas modificaciones en los modelos:
```bash
# Aplicar todas las migraciones pendientes
flask db upgrade
```
*Nota: Si estás en un entorno de desarrollo local con tablas ya creadas manualmente, recuerda correr `flask db stamp head` para sincronizar Alembic sin recrear las tablas.*

### 6. Ejecutar el Servidor
Inicia la aplicación de Flask en modo debug:
```bash
python app.py
```
El backend estará disponible en `http://localhost:5000`.

---

## 🗄️ Gestión de Base de Datos (Migraciones)

El proyecto utiliza **Flask-Migrate** para mantener la consistencia del esquema de la base de datos.
- **Crear una nueva migración:** (ejecutar tras modificar cualquier modelo de Python en `models/`):
  ```bash
  flask db migrate -m "explicación del cambio"
  ```
- **Aplicar la migración a la base de datos:**
  ```bash
  flask db upgrade
  ```
- **Revertir la última migración:**
  ```bash
  flask db downgrade
  ```

---

## 🧪 Pruebas Automatizadas

El backend incluye una suite de pruebas para validar la integridad del código. Puedes ejecutar las pruebas usando `pytest`:
```bash
# Ejecutar todas las pruebas
pytest tests/

# Ejecutar con detalles
pytest tests/ -v
```

---

## 🔒 Control de Accesos y Seguridad
El sistema implementa una arquitectura basada en roles (`dev`, `admin`, `lawyer`) que restringe el uso de las rutas de la API a través de decoradores:
- `@token_required`: Valida que el usuario posea un token JWT activo en la cabecera `Authorization`.
- `@access_required('nombre_permiso')`: Comprueba granularmente que el perfil del usuario tenga asignado el permiso correspondiente en la base de datos.

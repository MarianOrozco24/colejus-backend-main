# Carpeta `config/` - Módulos de Configuración e Inicialización

Este directorio contiene las configuraciones e inicializaciones de los servicios principales de la aplicación, incluyendo la conexión de base de datos ORM, la gestión de sesiones JWT, la configuración de envío de correos electrónicos y la pasarela de pagos.

---

## 📂 Archivos del Directorio

### 1. [`config.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/config/config.py)
* **Función:** Inicialización de SQLAlchemy (Base de Datos), JWT (Autenticación) y CORS.
* **Detalles:**
  - Lee los datos de conexión de MySQL desde las variables de entorno (`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_DATABASE`) y construye el URI de SQLAlchemy.
  - Configura el `JWTManager` utilizando la variable `JWT_SECRET_KEY` para firmar y validar tokens de sesión.
  - Inicializa `Flask-Migrate` para registrar la gestión de versiones del esquema de base de datos.
  - Define las políticas de CORS exponiendo la cabecera `Content-Disposition` para permitir la descarga de archivos (como recibos PDF) desde el cliente React.

### 2. [`config_mail.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/config/config_mail.py)
* **Función:** Configuración del cliente SMTP para envío de correos electrónicos.
* **Detalles:**
  - Inicializa la extensión `Flask-Mail`.
  - Lee los parámetros SMTP de entorno como el servidor (`MAIL_SERVER`), puerto (`MAIL_PORT`), TLS, credenciales de autenticación (`MAIL_USERNAME` y `MAIL_PASSWORD`), y el remitente predeterminado (`MAIL_DEFAULT_SENDER`).
  - Utilizado principalmente para enviar confirmaciones de reservas de coworking y notificaciones de pago a los colegiados.

### 3. [`config_mp.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/config/config_mp.py)
* **Función:** Inicialización de la integración oficial con la API de Mercado Pago.
* **Detalles:**
  - Configura el SDK de Mercado Pago a través de la variable `MP_ACCESS_TOKEN`.
  - Imprime advertencias de depuración si detecta tokens inválidos o mal configurados, ayudando en el monitoreo y desarrollo.
  - Permite generar las preferencias de pago utilizadas para el abono de membresías mensuales.

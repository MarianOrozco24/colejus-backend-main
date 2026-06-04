# Carpeta `routes/` - Controladores y Endpoints de la API (Blueprints)

Este directorio alberga los controladores y la definición de rutas HTTP de la aplicación utilizando **Flask Blueprints**. Todas las peticiones entrantes a la API (bajo el prefijo `/api/...`) son enrutadas y procesadas a través de estos módulos.

---

## 🔒 Control de Accesos y Seguridad
Las rutas están protegidas mediante decoradores personalizados importados desde [`utils/decorators.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/decorators.py):
- **`@token_required`:** Obliga a incluir un token JWT válido en el header `Authorization: Bearer <token>`.
- **`@access_required('permiso')`:** Comprueba que el usuario tenga asignado el permiso correspondiente en la base de datos para realizar la acción.

---

## 📂 Archivos y Endpoints

### 🔑 Autenticación y Cuentas
- **[`auth.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/auth.py):**
  Maneja el inicio de sesión (`/api/login`), registro, validación de estado de token y cambio/recuperación de contraseña.
- **[`users.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/users.py):**
  Administración de usuarios de la plataforma (creación, edición, listado de perfiles).
- **[`profiles.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/profiles.py) & [`accesses.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/accesses.py):**
  Gestión de roles y permisos del backoffice (añadir o remover permisos granulares a un perfil).

### 🏢 Coworking y Reservas
- **[`rooms.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/rooms.py):**
  CRUD para salas físicas del coworking. Cuenta con el endpoint `POST /api/rooms/upload-image` para subir imágenes en caliente y guardarlas localmente.
- **[`booking.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/booking.py):**
  Gestiona las reservas de salas. Valida la disponibilidad horaria de bloques, permite la asignación de abogados acompañantes y realiza las comprobaciones de pago de membresía mensuales del solicitante (a menos que se active la omisión global).

### 💳 Finanzas y Membresías
- **[`lawyer_payments.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/lawyer_payments.py):**
  Maneja el registro de pagos de membresías, consulta de deudores, montos históricos y vigentes de las cuotas, e integración con Mercado Pago.
- **[`receipts.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/receipts.py):**
  Generación, almacenamiento y descarga de recibos en PDF.
- **[`rates.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/rates.py):**
  Tasas institucionales y valores arancelarios del Colegio.

### 💼 Panel de Desarrollador
- **[`dev.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/dev.py):**
  Módulo exclusivo del programador (`dev`). Permite la inyección y visualización en tiempo real de logs del sistema (orientado principalmente a fallos SQL de base de datos), el hard-delete de registros de prueba (usuarios, roles, etc.) y la alteración de switches de configuración del backend.

### ⚖️ Portal Profesional y Edictos
- **[`professionals.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/professionals.py):**
  Directorio público y gestión de fichas profesionales de los abogados matriculados.
- **[`edicts.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/edicts.py):**
  Carga, actualización y publicación de edictos judiciales.

### 📰 Publicaciones y Comisiones
- **[`news.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/news.py) & [`trainings.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/trainings.py) & [`tags.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/tags.py):**
  Creación y edición de noticias institucionales, seminarios, charlas de capacitación y gestión de etiquetas temáticas.
- **[`integrantes.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/integrantes.py):**
  Gestión de comisiones y miembros de la comisión directiva del Colegio.

### 📋 Mapeo de Formularios
- **[`forms.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/routes/forms.py):**
  Gestión de las solicitudes de trámites y formularios administrativos del Colegio.

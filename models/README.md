# Carpeta `models/` - Modelos de la Base de Datos (SQLAlchemy)

Este directorio contiene las definiciones de los modelos ORM de **SQLAlchemy** que estructuran la base de datos MySQL. Cada archivo representa una tabla en la base de datos, definiendo sus columnas, tipos de datos, restricciones y relaciones.

---

## 🗄️ Reglas de Nomenclatura del Proyecto
- **Nombres de Tablas y Columnas:** Se escriben estrictamente en minúsculas y utilizando `snake_case` (regla global del proyecto).
- **Tipos de Datos:** Se utilizan los tipos nativos de SQLAlchemy (`sa.Column`, `sa.Integer`, `sa.String`, `sa.Boolean`, `sa.DateTime`, `sa.Text`, `sa.Float`).

---

## 📂 Archivos y Modelos

### 🔐 Seguridad y Usuarios
- **[`user.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/user.py) (`UserModel`):**
  Representa las cuentas de usuario registradas en el sistema. Almacena el correo electrónico, contraseña (encriptada), estado de actividad y la relación con los perfiles/roles.
- **[`profile.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/profile.py) (`ProfileModel`):**
  Define los roles de usuario en el sistema (ej. `dev`, `admin`, `lawyer`). Posee relaciones de muchos a muchos con usuarios y permisos.
- **[`access.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/access.py) (`AccessModel`):**
  Define los permisos granulares asignables a los roles (ej. `manage_rooms`, `view_revenue`).
- **[`profile_user.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/profile_user.py) & [`profile_access.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/profile_access.py):**
  Tablas intermedias auxiliares que estructuran las relaciones muchos a muchos (M:N) de Usuarios ↔️ Roles y Roles ↔️ Permisos respectivamente.

### 🏢 Gestión de Coworking y Reservas
- **[`room.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/room.py) (`RoomModel`):**
  Representa las salas físicas de coworking del Colegio de Abogados. Almacena el nombre, capacidad, descripción, comodidades (amenities guardados como un string JSON), estado de actividad (`is_active`) y la ruta a la imagen de la sala cargada (`image`).
- **[`booking.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/booking.py) (`BookingModel`):**
  Almacena los turnos y reservas de salas de coworking realizadas por los abogados colegiados. Incluye campos como la fecha, bloques horarios individuales, datos del abogado (nombre, matrícula, contacto), motivo, asistentes acompañantes y una clave de idempotencia (`idempotency_key`) para evitar duplicaciones.

### 💳 Membresías y Pagos
- **[`lawyer_payment.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/lawyer_payment.py) (`LawyerPaymentModel`):**
  Registros de pago de membresías efectuados por los abogados.
- **[`membership_fee.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/membership_fee.py) (`MembershipFeeModel`):**
  Define el valor histórico y vigente de la cuota/membresía mensual cobrada a los abogados.
- **[`receipts.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/receipts.py) (`ReceiptModel`):**
  Representa los recibos de transacciones y cobros procesados por el Colegio.

### ⚖️ Directorio Profesional y Edictos
- **[`professional.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/professional.py) (`ProfessionalModel`):**
  Almacena la información profesional de los abogados matriculados (título, dirección, matrícula, etc.). Posee una relación uno a uno (`uuid_user`) con su cuenta de usuario para rellenar datos automáticamente.
- **[`edict.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/edict.py) (`EdictModel`):**
  Edictos judiciales cargados y publicados en el portal.
- **[`derecho_fijo.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/derecho_fijo.py) (`DerechoFijoModel`) & [`price_df.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/price_df.py) (`PriceDerechoFijo`):**
  Tablas para control, montos y vigencias del cobro del Derecho Fijo.

### 📰 Contenidos e Información
- **[`news.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/news.py) (`NewsModel`) & [`training.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/training.py) (`TrainingModel`):**
  Tablas para las publicaciones de noticias y las capacitaciones/cursos ofrecidos por el Colegio de Abogados.
- **[`tags.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/tags.py) (`TagModel`) & relaciones asociativas ([`news_tags.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/news_tags.py) / [`trainings_tags.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/trainings_tags.py)):**
  Categorización y etiquetado de noticias y cursos.
- **[`integrantes.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/integrantes.py) (`IntegranteModel`):**
  Integrantes de la comisión directiva del Colegio de Abogados para la sección "Nosotros".

### ⚙️ Configuración y Seguridad de Red
- **[`config.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/config.py) (`SystemConfigModel`):**
  Configuraciones dinámicas y switches globales persistidos en base de datos. Ejemplo: `disable_membership_validation`.
- **[`ip_manager.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/ip_manager.py) (`IPRegistry`) & [`blocked_region.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/models/blocked_region.py) (`BlockedRegion`):**
  Registro de estadísticas de IPs clientes, intentos de inicio de sesión fallidos, estados de bloqueo e inhabilitación por regiones geográficas.

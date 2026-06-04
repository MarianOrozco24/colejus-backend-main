# Carpeta `utils/` - Módulos de Utilidad y Middleware

Este directorio almacena módulos auxiliares, helpers de validación y middleware de seguridad para todo el backend. Proporciona soluciones transversales como el envío de correos, registros de auditoría localizados, encriptación y bloqueo preventivo de ataques.

---

## 📂 Archivos del Directorio

### 🔐 Seguridad y Autenticación
- **[`decorators.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/decorators.py):**
  Middleware para validación de tokens JWT (`@token_required`) y control de acceso basado en permisos granulares (`@access_required`).
- **[`seguridad_bcm.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/seguridad_bcm.py):**
  Funciones criptográficas del sistema. Maneja la generación y verificación de firmas de seguridad hash para interacciones sensibles y transferencias.

### 🛡️ Control de IPs y Rate Limiting
- **[`ip_manager_cache.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/ip_manager_cache.py):**
  Gestiona la memoria caché local para la supervisión de IPs. Lleva registro de las peticiones concurrentes, solicitudes sospechosas e intentos fallidos de login para disparar bloqueos automáticos ante comportamientos sospechosos o ataques de fuerza bruta.
- **[`ip_location.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/ip_location.py):**
  Lógica para consultar la ubicación geográfica de direcciones IP utilizando APIs de geolocalización. Permite restringir e identificar de dónde proceden las peticiones.

### 📧 Comunicaciones y Notificaciones
- **[`send_mails.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/send_mails.py):**
  Encargado de la lógica de envío de correos electrónicos. Cuenta con plantillas HTML renderizables para el envío de recibos, avisos de reservas, alertas de seguridad y recordatorios de cuotas.
- **[`bot.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/bot.py):**
  Integración con un bot de Telegram. Envía alertas de monitoreo y fallos de seguridad importantes directo a un canal privado de desarrolladores/administradores.

### 📝 Auditoría e Historial (Logs)
- **[`logging_config.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/logging_config.py):**
  Configura el sistema de registro de auditoría local de la aplicación.
  - Implementa `DailyRotatingFileHandler` que rota los ficheros de logs diariamente.
  - Ajusta todos los logs del sistema al huso horario de **Argentina (UTC-3)** de forma predeterminada mediante un formateador personalizado.
  - Cuenta con oyentes dinámicos (`event.listens_for(Engine, "handle_error")`) para capturar automáticamente todos los errores de sintaxis o ejecución de la base de datos SQL y enviarlos directamente al panel de desarrollo.

### 📋 Validaciones de Entrada
- **[`validate_date.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/validate_date.py):**
  Funciones para parsear y validar cadenas de fecha en formatos específicos y comprobar solapamientos.
- **[`validate_fields.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/validate_fields.py):**
  Validador de campos comunes (correos electrónicos, longitud de contraseñas, tipo de datos).

### ❌ Excepciones
- **[`errors.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/utils/errors.py):**
  Definición de clases de error personalizadas y respuestas HTTP de excepción uniformes.

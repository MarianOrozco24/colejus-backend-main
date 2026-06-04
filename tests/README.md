# Carpeta `tests/` - Suite de Pruebas Automatizadas (Pytest)

Este directorio contiene las pruebas unitarias y de integración del backend, diseñadas para validar que los flujos críticos del sistema (como cobros, bloqueo de IPs, control de velocidad de peticiones y webhooks de Mercado Pago) funcionen correctamente ante cualquier actualización.

---

## 📂 Archivos del Directorio

- **[`test_barcode_generation.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/tests/test_barcode_generation.py):**
  Pruebas para comprobar la correcta generación de códigos de barras (PDF/imágenes) para las boletas de pago de tasas y derecho fijo de la Bolsa de Comercio.
- **[`test_ip_management.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/tests/test_ip_management.py):**
  Pruebas sobre el sistema de rastreo de IPs, verificando el guardado de estadísticas en base de datos, el límite de logins erróneos tolerados y el comportamiento de bloqueo.
- **[`test_rate_limit.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/tests/test_rate_limit.py):**
  Verifica que el decorador de límite de peticiones (Flask-Limiter) bloquee con código de error HTTP 429 a los clientes que realicen ráfagas de solicitudes que superen la tasa máxima configurada.
- **[`test_webhook_compatibility.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/tests/test_webhook_compatibility.py):**
  Tests de integración que validan la compatibilidad y firma de las notificaciones webhook de Mercado Pago, asegurando que se registren los pagos y se actualicen los estados de membresía de los abogados.
- **[`test_webhook_parser.py`](file:///c:/Users/Usuario/OneDrive/Documentos/GitHub/Colejus/colejus-backend-main/tests/test_webhook_parser.py):**
  Pruebas unitarias dedicadas a testear el parseador de datos de pago JSON de Mercado Pago, garantizando que extraiga los campos correctos independientemente de variaciones en la estructura de la carga útil.

---

## ⚙️ Requisitos para Correr las Pruebas

Instala `pytest` y las extensiones necesarias en tu entorno virtual:
```bash
pip install pytest pytest-flask
```

---

## 🚀 Cómo Ejecutar los Tests

Desde la raíz de la carpeta `colejus-backend-main`:

### Ejecutar todas las pruebas del proyecto:
```bash
pytest tests/
```

### Ejecutar una suite específica:
```bash
pytest tests/test_ip_management.py
```

### Ejecutar con nivel de detalle (verbose):
```bash
pytest tests/ -v
```

### Mostrar impresiones (`print`) de consola en los tests:
```bash
pytest tests/ -s
```

---

## 📊 Interpretación de Resultados en Consola
- **`.` (punto):** La prueba pasó exitosamente. ✅
- **`F`:** La prueba falló (algún `assert` arrojó un valor incorrecto). ❌
- **`E`:** Hubo un error de ejecución en la estructura de la prueba (ej: dependencias no resueltas). 🔴

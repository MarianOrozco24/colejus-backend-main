## 📝 Descripción

Describe detalladamente los cambios introducidos por este Pull Request, el problema que resuelven y el contexto de la implementación.

---

## 🛠️ Tipo de Cambio

- [ ] Nueva funcionalidad (`feat`)
- [ ] Corrección de errores (`fix`)
- [ ] Refactorización de código (`refactor`)
- [ ] Optimización de rendimiento (`perf`)
- [ ] Documentación (`docs`)
- [ ] Tareas de mantenimiento o configuración (`chore`)

---

## 🔗 Tickets o Issues Asociados

- Asocia el issue o ticket correspondiente (ej. `Fixes #123`, `Closes #456`).

---

## 🗄️ ¿Requiere Cambios en Base de Datos?

- [ ] **No** requiere cambios.
- [ ] **Sí** requiere cambios.
  - [ ] ¿Se generó el script de migración con `flask db migrate`?
  - [ ] ¿El script fue probado localmente con `flask db upgrade` y `flask db downgrade`?
  - [ ] ¿Se actualizó el modelo correspondiente en la carpeta `models/`?

---

## 🧪 ¿Cómo se probó?

Describe las pruebas realizadas para comprobar el correcto funcionamiento del cambio:
- **Pruebas automatizadas:** (ej. `pytest tests/test_rate_limit.py`)
- **Pruebas manuales/endpoints:** (ej. Petición POST a `/api/rooms/upload-image` mediante Postman con un archivo PNG de 1MB)

---

## 📋 Lista de Verificación (Checklist)

- [ ] Mi código sigue las guías de estilo del proyecto (nombres de tablas/columnas estrictamente en minúsculas y snake_case).
- [ ] He realizado una auto-revisión de mi propio código.
- [ ] He agregado comentarios en partes complejas del código.
- [ ] He actualizado la documentación correspondiente (archivos `README.md` locales si aplica).
- [ ] Mis cambios no introducen nuevas advertencias o errores de consola.
- [ ] Todas las pruebas de la suite de testing p6asan correctamente (`pytest`).
- [ ] Las variables de entorno necesarias han sido documentadas y/o cargadas en el archivo `.env.example`.

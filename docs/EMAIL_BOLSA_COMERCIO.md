**Asunto:** Implementación de nuevo formato de código de barras - Colejus

---

Estimados,

Nos dirigimos a ustedes en relación a la **reunión reciente** donde conversamos sobre los inconvenientes que estábamos experimentando con el escaneo de algunas boletas de pago presencial.

Como acordamos, hemos **implementado el cambio en el formato del código de barras** que se discutió en dicha reunión. El nuevo formato elimina todos los caracteres especiales (guiones, guiones bajos y puntos) que estaban interfiriendo con los escáneres, garantizando una **lectura 100% confiable**.

### Resumen del cambio:

**Formato anterior (deprecado):**
```
COD-{UUID}_{NUMERO_JUICIO}_{MONTO}
```

**Formato nuevo (actual):**
```
COD{UUID_SIN_GUIONES}{MONTO_EN_CENTAVOS}
```

El nuevo código tiene **longitud fija de 45 caracteres** y es **completamente alfanumérico**, lo que asegura compatibilidad con todos los modelos de escáneres Code128.

### Aspectos importantes:

1. **Compatibilidad:** Nuestro sistema soporta ambos formatos durante el período de transición, por lo que las boletas antiguas aún en circulación seguirán funcionando sin problemas.

2. **Webhook:** El formato del webhook **permanece exactamente igual**. Solo recibirán el nuevo formato en el campo `cod_cliente` para las boletas generadas a partir de hoy.

3. **Sin cambios de su parte:** No se requiere ninguna modificación en sus sistemas. El código debe ser escaneado, almacenado y retornado en el webhook tal como se recibe actualmente.

### Documentación adjunta:

Adjuntamos la **especificación técnica completa** del nuevo formato, que incluye:
- Estructura detallada del código
- Ejemplos de conversión
- Formato del webhook (sin cambios)
- Tabla de comparación entre formatos

Quedamos a disposición para cualquier consulta o aclaración que necesiten respecto a este cambio.

Saludos cordiales,

**Colegio Público de Abogados y Procuradores**  
Segunda Circunscripción Judicial - Mendoza  
Sistema Colejus - Departamento de Sistemas

---

**Archivo adjunto:** BCM_BARCODE_SPEC.md

# Actualización del Formato de Código de Barras
## Colegio Público de Abogados - Colejus

**Fecha:** 11 de Febrero de 2026  
**Asunto:** Cambio en el formato del código de barras para boletas de pago

---

## 1. Motivo del Cambio

Hemos detectado que algunos códigos de barras **no están siendo escaneados correctamente** en las terminales de la Bolsa de Comercio. 

**Causa identificada:** El formato anterior incluía caracteres especiales (guiones, guiones bajos, puntos) que interfieren con algunos escáneres y el estándar Code128.

**Solución:** Nuevo formato **100% alfanumérico**, sin caracteres especiales, con longitud fija.

---

## 2. Formato Anterior (Deprecado)

```
COD-{UUID}_{NUMERO_JUICIO}_{MONTO}

Ejemplo: COD-9cb06c3b-f14e-486e-a97e-15a4046fff6e_123-2024_100.00
```

**Problemas:**
- ❌ Contiene guiones (`-`)
- ❌ Contiene guiones bajos (`_`)
- ❌ Contiene puntos (`.`)
- ❌ Longitud variable

---

## 3. Formato Nuevo (Actual)

```
COD{UUID_SIN_GUIONES}{MONTO_EN_CENTAVOS}

Ejemplo: COD9cb06c3bf14e486ea97e15a4046fff6e0000010000
```

**Ventajas:**
- ✅ 100% alfanumérico
- ✅ Sin caracteres especiales
- ✅ Longitud fija: **45 caracteres**
- ✅ Compatible con todos los escáneres

---

## 4. Composición Detallada

### Estructura por Posición

| Componente | Posiciones | Longitud | Descripción | Ejemplo |
|------------|------------|----------|-------------|---------|
| **Prefijo** | 0-2 | 3 chars | Siempre "COD" | `COD` |
| **UUID** | 3-34 | 32 chars | Identificador único (sin guiones) | `9cb06c3bf14e486ea97e15a4046fff6e` |
| **Monto** | 35-44 | 10 dígitos | Monto en centavos con padding | `0000010000` |

**Longitud total:** 45 caracteres

### Diagrama Visual

```
COD9cb06c3bf14e486ea97e15a4046fff6e0000010000
│  │                                │          │
│  │                                │          └─ Pos 44 (fin)
│  │                                └─ Pos 35 (monto)
│  └─ Pos 3 (UUID)
└─ Pos 0 (prefijo)
```

### Conversión de UUID

El UUID es el mismo, solo se eliminan los guiones:

```
UUID original:        9cb06c3b-f14e-486e-a97e-15a4046fff6e  (36 caracteres)
UUID en código:       9cb06c3bf14e486ea97e15a4046fff6e     (32 caracteres)
```

### Conversión de Monto

El monto se expresa en **centavos** con **padding de ceros** a la izquierda:

| Monto (Pesos) | Centavos | Código (10 dígitos) |
|---------------|----------|---------------------|
| $1.00 | 100 | `0000000100` |
| $100.00 | 10,000 | `0000010000` |
| $5,000.50 | 500,050 | `0000500050` |
| $25,000.00 | 2,500,000 | `0002500000` |

---

## 5. Ejemplos Completos

### Ejemplo 1: Pago de $100.00
```
Código: COD9cb06c3bf14e486ea97e15a4046fff6e0000010000

Desglose:
- COD                                = Prefijo
- 9cb06c3bf14e486ea97e15a4046fff6e   = UUID sin guiones
- 0000010000                          = 10,000 centavos = $100.00
```

### Ejemplo 2: Pago de $5,000.50
```
Código: CODabc123456789abcdef012345678901230000500050

Desglose:
- COD                                = Prefijo
- abc123456789abcdef0123456789012    = UUID sin guiones
- 0000500050                          = 500,050 centavos = $5,000.50
```

---

## 6. Webhook de Confirmación

### Formato Esperado (Sin Cambios)

Esperamos recibir el POST en nuestro webhook con el código de barras **exactamente como fue escaneado**, junto con el estado de la transacción.

### Campos Requeridos (Mínimo)

```json
{
    "cod_cliente": "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000",
    "estado_transaccion": "Pagado"
}
```

### Campos Opcionales (Máximo)

```json
{
    "cod_cliente": "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000",
    "estado_transaccion": "Pagado",
    "transaction_id": "123456",
    "timestamp": "2026-02-11T15:30:00",
    "notification_type": "confirmation"
}
```

### Campos que Utilizamos

De todos los campos enviados, **solo utilizamos:**
- ✅ `cod_cliente` - Para identificar la boleta
- ✅ `estado_transaccion` - Para confirmar el pago

Los demás campos son opcionales y pueden ser incluidos, pero no son procesados por nuestro sistema.

### Valores de `estado_transaccion`

Aceptamos cualquiera de los siguientes valores:
- `"Pagado"`
- `"pagado"`
- `"aprobado"`
- `"approved"`
- `"aprobada"`

---

## 7. Período de Transición

### Compatibilidad Retroactiva

Nuestro sistema **soporta ambos formatos** durante el período de transición:

| Formato | Estado | Soporte |
|---------|--------|---------|
| **Nuevo:** `COD{uuid}{monto}` | Actual | ✅ Totalmente soportado |
| **Anterior:** `COD-{uuid}_{juicio}_{monto}` | Deprecado | ✅ Aún soportado |

**Importante:**
- Todas las **boletas nuevas** utilizarán el formato nuevo
- Las **boletas antiguas** aún en circulación usan el formato anterior
- Nuestro sistema identifica automáticamente el formato recibido
- No requiere ningún cambio de su parte en el webhook

---

## 8. Validación del Código

Para validar un código nuevo:

1. **Longitud:** Exactamente 45 caracteres
2. **Prefijo:** Debe comenzar con `"COD"`
3. **UUID:** Posiciones 3-34 deben ser hexadecimales (0-9, a-f)
4. **Monto:** Posiciones 35-44 deben ser numéricos (0-9)

**Expresión regular:**
```regex
^COD[0-9a-f]{32}[0-9]{10}$
```

---

## 9. Resumen de Cambios

| Aspecto | Formato Anterior | Formato Nuevo |
|---------|------------------|---------------|
| Ejemplo | `COD-9cb...fff6e_123_100.00` | `COD9cb...fff6e0000010000` |
| Longitud | Variable (40-60 chars) | **Fija: 45 chars** |
| Caracteres especiales | Sí (`-`, `_`, `.`) | **No** |
| Alfanumérico | No | **Sí** |
| Monto | Pesos con decimales | **Centavos enteros** |
| UUID | Con guiones | **Sin guiones** |

---

**Aclaraciones importantes:**

1. El cambio **no afecta** el procesamiento del pago de su parte
2. Solo cambia el **formato del código de barras** en las boletas nuevas
3. El **webhook permanece exactamente igual**, solo recibirá el nuevo formato en `cod_cliente`
4. No se requiere ningún cambio en sus sistemas si el código es almacenado y retornado como string

---


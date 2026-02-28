# Estructura del Código de Barras - Bolsa de Comercio

## Formato General

El código de barras tiene **45 caracteres** en total, dividido en 3 secciones:

```
COD{UUID_SIN_GUIONES}{MONTO_CENTAVOS}
```

---

## Desglose por Posición

### Vista General

```
Posición:  0  1  2  3  4  5  ...  34 35 36 37 38 39 40 41 42 43 44
           |-----|----------32 chars----------|------10 chars-----|
            COD        UUID sin guiones         Monto en centavos
```

### Desglose Detallado

| Sección | Posición Inicio | Posición Fin | Longitud | Descripción |
|---------|----------------|--------------|----------|-------------|
| **Prefijo** | 0 | 2 | 3 chars | Siempre es `"COD"` (identificador) |
| **UUID** | 3 | 34 | 32 chars | UUID sin guiones (hexadecimal) |
| **Monto** | 35 | 44 | 10 chars | Monto en centavos con padding de ceros |

---

## Ejemplo Práctico

### Código de barras completo:
```
COD9cb06c3bf14e486ea97e15a4046fff6e0000010000
```

### Descomposición:

```
Caracteres 0-2:   COD
                  ^^^
                  Prefijo identificador

Caracteres 3-34:  9cb06c3bf14e486ea97e15a4046fff6e
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                  UUID sin guiones (32 caracteres)
                  Corresponde a: 9cb06c3b-f14e-486e-a97e-15a4046fff6e

Caracteres 35-44: 0000010000
                  ^^^^^^^^^^
                  Monto en centavos (10 dígitos)
                  0000010000 = 10,000 centavos = $100.00
```

---

## Tabla de Ejemplos

| UUID Original | Monto | Código de Barras Completo | Explicación |
|--------------|-------|--------------------------|-------------|
| `9cb06c3b-f14e-486e-a97e-15a4046fff6e` | $100.00 | `COD9cb06c3bf14e486ea97e15a4046fff6e0000010000` | 10,000 centavos |
| `12345678-1234-5678-1234-567812345678` | $5000.50 | `COD12345678123456781234567812345678000050050` | 500,050 centavos |
| `abc123de-f456-7890-1234-567890123456` | $1.00 | `CODabc123def4567890123456789012345600000100` | 100 centavos |
| `aaaabbbb-cccc-dddd-eeee-ffff00001111` | $99.99 | `CODaaaabbbbccccddddeeeefffff00001111000009999` | 9,999 centavos |

---

## Detalles de Cada Sección

### 1. Prefijo "COD" (Posiciones 0-2)

- **Longitud**: 3 caracteres
- **Valor fijo**: `"COD"`
- **Propósito**: Identificar que es un código de la Bolsa de Comercio

```python
prefijo = codigo_barra[0:3]  # "COD"
```

### 2. UUID sin guiones (Posiciones 3-34)

- **Longitud**: 32 caracteres
- **Formato**: Hexadecimal (0-9, a-f)
- **Propósito**: Identificador único del derecho fijo
- **Conversión**: Se obtiene removiendo los 4 guiones del UUID estándar

**UUID estándar:**
```
9cb06c3b-f14e-486e-a97e-15a4046fff6e  (36 caracteres con guiones)
```

**UUID en código de barras:**
```
9cb06c3bf14e486ea97e15a4046fff6e  (32 caracteres sin guiones)
```

**Código para extraer:**
```python
uuid_sin_guiones = codigo_barra[3:35]  # 32 caracteres
# Reconstruir UUID con guiones:
uuid_completo = f"{uuid_sin_guiones[0:8]}-{uuid_sin_guiones[8:12]}-{uuid_sin_guiones[12:16]}-{uuid_sin_guiones[16:20]}-{uuid_sin_guiones[20:32]}"
```

### 3. Monto en Centavos (Posiciones 35-44)

- **Longitud**: 10 dígitos
- **Formato**: Numérico con padding de ceros a la izquierda
- **Propósito**: Monto total en centavos (evita problemas con decimales)

**Ejemplos:**

| Monto en Pesos | Monto en Centavos | Código (10 dígitos) |
|----------------|-------------------|---------------------|
| $1.00 | 100 | `0000000100` |
| $100.00 | 10,000 | `0000010000` |
| $5000.50 | 500,050 | `0000500050` |
| $99999.99 | 9,999,999 | `0009999999` |

**Código para extraer:**
```python
monto_str = codigo_barra[35:45]  # "0000010000"
monto_centavos = int(monto_str)  # 10000
monto_pesos = monto_centavos / 100  # 100.00
```

---

## Diagrama Visual Completo

```
COD9cb06c3bf14e486ea97e15a4046fff6e0000010000
│  │                                │          │
│  │                                │          └─ Posición 44 (fin)
│  │                                └─ Posición 35 (inicio monto)
│  └─ Posición 3 (inicio UUID)
└─ Posición 0 (inicio prefijo)

Longitud total: 45 caracteres
├─ Prefijo (3):  posiciones 0-2
├─ UUID (32):    posiciones 3-34
└─ Monto (10):   posiciones 35-44
```

---

## Código de Referencia

### Generación del código de barras:

```python
def generar_codigo_barra(uuid_str: str, total_depositado: float) -> str:
    # 1. Prefijo fijo
    prefijo = "COD"  # Posiciones 0-2
    
    # 2. UUID sin guiones (32 chars)
    uuid_sin_guiones = str(uuid_str).replace("-", "")  # Posiciones 3-34
    
    # 3. Monto en centavos (10 dígitos)
    monto_centavos = int(float(total_depositado) * 100)
    monto_sanitizado = str(monto_centavos).zfill(10)  # Posiciones 35-44
    
    # Concatenar: 3 + 32 + 10 = 45 caracteres
    codigo_barra = f"{prefijo}{uuid_sin_guiones}{monto_sanitizado}"
    
    return codigo_barra
```

### Parsing del código de barras:

```python
def parsear_codigo_barra(codigo: str) -> dict:
    """
    Extrae cada componente del código de barras
    """
    if len(codigo) != 45:
        raise ValueError(f"Código inválido: debe tener 45 caracteres, tiene {len(codigo)}")
    
    # Extraer cada sección por posición
    prefijo = codigo[0:3]           # "COD"
    uuid_sin_guiones = codigo[3:35] # 32 caracteres
    monto_str = codigo[35:45]       # 10 dígitos
    
    # Validar prefijo
    if prefijo != "COD":
        raise ValueError(f"Prefijo inválido: esperado 'COD', encontrado '{prefijo}'")
    
    # Reconstruir UUID con guiones
    uuid_completo = f"{uuid_sin_guiones[0:8]}-{uuid_sin_guiones[8:12]}-{uuid_sin_guiones[12:16]}-{uuid_sin_guiones[16:20]}-{uuid_sin_guiones[20:32]}"
    
    # Convertir monto
    monto_centavos = int(monto_str)
    monto_pesos = monto_centavos / 100
    
    return {
        "prefijo": prefijo,
        "uuid": uuid_completo,
        "uuid_sin_guiones": uuid_sin_guiones,
        "monto_centavos": monto_centavos,
        "monto_pesos": monto_pesos,
        "codigo_completo": codigo
    }
```

### Ejemplo de uso:

```python
codigo = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
resultado = parsear_codigo_barra(codigo)

print(resultado)
# {
#     "prefijo": "COD",
#     "uuid": "9cb06c3b-f14e-486e-a97e-15a4046fff6e",
#     "uuid_sin_guiones": "9cb06c3bf14e486ea97e15a4046fff6e",
#     "monto_centavos": 10000,
#     "monto_pesos": 100.0,
#     "codigo_completo": "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
# }
```

---

## Validaciones Importantes

### 1. Longitud total
```python
assert len(codigo_barra) == 45, "El código debe tener exactamente 45 caracteres"
```

### 2. Prefijo correcto
```python
assert codigo_barra.startswith("COD"), "Debe comenzar con 'COD'"
```

### 3. UUID válido (32 chars hexadecimales)
```python
uuid_parte = codigo_barra[3:35]
assert len(uuid_parte) == 32, "UUID debe tener 32 caracteres"
assert all(c in '0123456789abcdefABCDEF' for c in uuid_parte), "UUID debe ser hexadecimal"
```

### 4. Monto válido (10 dígitos numéricos)
```python
monto_parte = codigo_barra[35:45]
assert len(monto_parte) == 10, "Monto debe tener 10 dígitos"
assert monto_parte.isdigit(), "Monto debe ser numérico"
```

---

## Resumen Rápido

```
Posición  Componente           Longitud  Ejemplo
--------  ------------------   --------  -------------------------------
0-2       Prefijo "COD"        3 chars   COD
3-34      UUID (sin guiones)   32 chars  9cb06c3bf14e486ea97e15a4046fff6e
35-44     Monto (centavos)     10 chars  0000010000

Total: 45 caracteres
```

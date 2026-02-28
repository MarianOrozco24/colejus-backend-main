# Test de Código de Barras - Bolsa de Comercio

Este directorio contiene los tests unitarios para el sistema de generación de códigos de barras y procesamiento de webhooks.

## ¿Qué es un test?

Un **test** es código que verifica que tu código funcione correctamente. Es como un "examen" automático que:
- ✅ Verifica que las funciones produzcan los resultados esperados
- ✅ Detecta errores antes de que lleguen a producción
- ✅ Te da confianza para hacer cambios sin romper nada

## Estructura de archivos

```
tests/
├── README.md                          # Este archivo
├── test_barcode_generation.py        # Tests de generación de códigos de barras
└── test_webhook_parser.py             # Tests de procesamiento de webhooks
```

## Instalación

Primero, instala pytest (el framework de testing):

```bash
pip install pytest pytest-flask
```

## Cómo ejecutar los tests

### Ejecutar todos los tests:
```bash
pytest tests/
```

### Ejecutar un archivo específico:
```bash
pytest tests/test_barcode_generation.py
```

### Ejecutar con más información (verbose):
```bash
pytest tests/ -v
```

### Ver el output de los prints:
```bash
pytest tests/ -s
```

## Estructura de un test

Un test típico se ve así:

```python
def test_nombre_descriptivo():
    # 1. ARRANGE - Preparar los datos
    input_data = "123-456"
    
    # 2. ACT - Ejecutar la función a testear
    result = mi_funcion(input_data)
    
    # 3. ASSERT - Verificar que el resultado sea correcto
    assert result == "123456"
```

## Interpretando los resultados

- **`.` (punto)** = Test pasó ✅
- **`F` (F mayúscula)** = Test falló ❌
- **`E` (E mayúscula)** = Error en el test mismo 🔴

Ejemplo de salida:
```
tests/test_barcode_generation.py ......  [100%]
6 passed in 0.05s
```

Esto significa que los 6 tests pasaron correctamente.

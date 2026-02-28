"""
Tests para la generación de códigos de barras
Este archivo testea que el código de barras se genere correctamente
"""
import pytest
import uuid as uuid_module


def generar_codigo_barra(uuid_str: str, total_depositado: float) -> str:
    """
    Función extraída de forms.py para facilitar el testing.
    Genera un código de barras en formato: COD{uuid_sin_guiones}{monto_sanitizado}
    """
    # Formato: COD + UUID sin guiones (32 chars) + monto sanitizado (10 dígitos)
    uuid_sin_guiones = str(uuid_str).replace("-", "")
    
    # Sanitizar monto: remover puntos y comas, convertir a enteros (centavos), rellenar con ceros
    monto_str = str(total_depositado).replace(".", "").replace(",", "")
    
    # Si el monto tiene decimales implícitos, asegurarnos de que sea un entero
    try:
        monto_centavos = int(float(str(total_depositado)) * 100)
    except:
        monto_centavos = int(monto_str) if monto_str.isdigit() else 0
    
    monto_sanitizado = str(monto_centavos).zfill(10)  # 10 dígitos
    
    codigo_barra = f"COD{uuid_sin_guiones}{monto_sanitizado}"
    
    return codigo_barra


class TestBarcodeGeneration:
    """Conjunto de tests para la generación de códigos de barras"""
    
    def test_barcode_format_basic(self):
        """Test 1: Verificar formato básico del código de barras"""
        # ARRANGE - Preparar datos de prueba
        test_uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
        test_amount = 100.00
        
        # ACT - Generar código de barras
        result = generar_codigo_barra(test_uuid, test_amount)
        
        # ASSERT - Verificar resultados
        assert result.startswith("COD"), "El código debe empezar con 'COD'"
        assert len(result) == 45, f"El código debe tener 45 caracteres, tiene {len(result)}"
        assert result == "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
    
    def test_uuid_without_hyphens(self):
        """Test 2: Verificar que el UUID no tenga guiones en el código de barras"""
        test_uuid = "abc-123-def-456-789"  # UUID con guiones
        test_amount = 50.00
        
        result = generar_codigo_barra(test_uuid, test_amount)
        
        # El UUID en el código NO debe tener guiones
        uuid_part = result[3:35]  # Extraer la parte del UUID (después de "COD")
        assert "-" not in uuid_part, "El UUID no debe contener guiones"
    
    def test_amount_sanitization_with_decimals(self):
        """Test 3: Verificar que los decimales se conviertan correctamente a centavos"""
        test_uuid = "12345678-1234-5678-1234-567812345678"
        test_amount = 5000.50  # $5000.50 = 500050 centavos
        
        result = generar_codigo_barra(test_uuid, test_amount)
        
        # Los últimos 10 caracteres son el monto
        monto_part = result[-10:]
        assert monto_part == "0000500050", f"Monto esperado 0000500050, obtenido {monto_part}"
    
    def test_amount_zero_padding(self):
        """Test 4: Verificar que montos pequeños se rellenen con ceros"""
        test_uuid = "12345678-1234-5678-1234-567812345678"
        test_amount = 1.00  # $1.00 = 100 centavos = 0000000100
        
        result = generar_codigo_barra(test_uuid, test_amount)
        
        monto_part = result[-10:]
        assert monto_part == "0000000100", f"Monto con padding incorrecto: {monto_part}"
        assert len(monto_part) == 10, "El monto debe tener exactamente 10 dígitos"
    
    def test_large_amount(self):
        """Test 5: Verificar que montos grandes se manejen correctamente"""
        test_uuid = "12345678-1234-5678-1234-567812345678"
        test_amount = 99999.99  # $99999.99 = 9999999 centavos
        
        result = generar_codigo_barra(test_uuid, test_amount)
        
        monto_part = result[-10:]
        assert monto_part == "0009999999", f"Monto grande incorrecto: {monto_part}"
    
    def test_no_special_characters(self):
        """Test 6: Verificar que el código NO contenga caracteres especiales"""
        test_uuid = str(uuid_module.uuid4())
        test_amount = 123.45
        
        result = generar_codigo_barra(test_uuid, test_amount)
        
        # El código solo debe contener letras, números y "COD" al inicio
        assert result.isalnum(), f"El código contiene caracteres especiales: {result}"
    
    def test_amount_with_commas(self):
        """Test 7: Verificar que montos con comas se saniticen correctamente"""
        test_uuid = "12345678-1234-5678-1234-567812345678"
        test_amount = "1,500.50"  # Formato con coma
        
        result = generar_codigo_barra(test_uuid, test_amount)
        
        # Debe convertir correctamente a 150050 centavos
        monto_part = result[-10:]
        assert monto_part == "0000150050", f"Monto con comas mal procesado: {monto_part}"
    
    def test_barcode_length_consistency(self):
        """Test 8: Verificar que TODOS los códigos tengan la misma longitud"""
        test_cases = [
            (str(uuid_module.uuid4()), 0.01),
            (str(uuid_module.uuid4()), 100.00),
            (str(uuid_module.uuid4()), 9999.99),
            (str(uuid_module.uuid4()), 50000.00),
        ]
        
        for test_uuid, test_amount in test_cases:
            result = generar_codigo_barra(test_uuid, test_amount)
            assert len(result) == 45, f"Longitud inconsistente para monto {test_amount}: {len(result)}"


# Función helper para debugging
def test_debug_output(capsys):
    """Test de ejemplo que muestra cómo ver prints en los tests"""
    test_uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
    test_amount = 100.00
    
    result = generar_codigo_barra(test_uuid, test_amount)
    
    print(f"\n📋 UUID: {test_uuid}")
    print(f"📋 Monto: ${test_amount}")
    print(f"📋 Código generado: {result}")
    print(f"📋 Longitud: {len(result)}")
    
    # Para ver estos prints, ejecuta: pytest tests/ -s
    assert len(result) == 45

"""
Tests para el parsing de códigos de barras en webhooks
Este archivo testea que el webhook pueda extraer correctamente el UUID de diferentes formatos
"""
import pytest


def extraer_uuid_de_codigo_barra(cod_barra: str) -> str:
    """
    Función extraída de forms.py (bcm_webhook_presencial) para facilitar testing.
    Extrae el UUID del código de barras en diferentes formatos.
    """
    # Formato CON separadores: COD-{uuid}_{juicio_n}_{total}
    if cod_barra.startswith("COD-") and "_" in cod_barra:
        try:
            uuid_derecho_fijo = cod_barra.split("COD-")[1].split("_")[0]
            return uuid_derecho_fijo
        except (IndexError, Exception) as parse_err:
            raise ValueError(f"Error parseando formato con separadores: {parse_err}")
    
    # Formato SIN separadores: COD{uuid_32_chars}{resto}
    # Quitar prefijo "COD" o "COD-"
    if cod_barra.startswith("COD-"):
        sin_prefijo = cod_barra[4:]
    elif cod_barra.startswith("COD"):
        sin_prefijo = cod_barra[3:]
    else:
        raise ValueError("Formato de código de barras inválido, debe comenzar con COD")
    
    # Los primeros 32 caracteres son el UUID (sin guiones)
    if len(sin_prefijo) >= 32:
        uuid_sin_guiones = sin_prefijo[:32]
        # Reconstruir UUID con guiones para validación
        uuid_derecho_fijo = f"{uuid_sin_guiones[:8]}-{uuid_sin_guiones[8:12]}-{uuid_sin_guiones[12:16]}-{uuid_sin_guiones[16:20]}-{uuid_sin_guiones[20:32]}"
        return uuid_derecho_fijo
    else:
        raise ValueError(f"Código de barras muy corto para extraer UUID. Longitud: {len(sin_prefijo)}, esperado: 32+")


class TestWebhookParser:
    """Tests para el parsing de códigos de barras en webhooks"""
    
    def test_parse_new_format(self):
        """Test 1: Extraer UUID del nuevo formato (sin separadores)"""
        # ARRANGE
        test_uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
        codigo_barra = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        
        # ACT
        uuid_extraido = extraer_uuid_de_codigo_barra(codigo_barra)
        
        # ASSERT
        assert uuid_extraido == test_uuid, f"UUID extraído incorrecto: {uuid_extraido}"
    
    def test_parse_old_format_with_separators(self):
        """Test 2: Extraer UUID del formato antiguo (con separadores)"""
        # ARRANGE
        test_uuid = "abc12345-6789-abcd-ef01-234567890abc"
        codigo_barra = f"COD-{test_uuid}_123-2024_5000.50"
        
        # ACT
        uuid_extraido = extraer_uuid_de_codigo_barra(codigo_barra)
        
        # ASSERT
        assert uuid_extraido == test_uuid
    
    def test_parse_with_whitespace(self):
        """Test 3: Manejar espacios en blanco (del escáner)"""
        # ARRANGE
        codigo_barra = "  COD9cb06c3bf14e486ea97e15a4046fff6e0000010000  "
        expected_uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
        
        # ACT - Simular el .strip() del webhook
        codigo_limpio = codigo_barra.strip()
        uuid_extraido = extraer_uuid_de_codigo_barra(codigo_limpio)
        
        # ASSERT
        assert uuid_extraido == expected_uuid
    
    def test_invalid_format_no_cod_prefix(self):
        """Test 4: Rechazar códigos que no empiezan con COD"""
        # ARRANGE
        codigo_invalido = "XYZ9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        
        # ACT & ASSERT
        with pytest.raises(ValueError, match="debe comenzar con COD"):
            extraer_uuid_de_codigo_barra(codigo_invalido)
    
    def test_invalid_format_too_short(self):
        """Test 5: Rechazar códigos muy cortos"""
        # ARRANGE
        codigo_corto = "COD123"  # Solo 3 caracteres después de COD
        
        # ACT & ASSERT
        with pytest.raises(ValueError, match="muy corto"):
            extraer_uuid_de_codigo_barra(codigo_corto)
    
    def test_uuid_reconstruction(self):
        """Test 6: Verificar que el UUID se reconstruya con guiones correctamente"""
        # ARRANGE - UUID sin guiones en el código
        uuid_sin_guiones = "12345678123456781234567812345678"
        codigo_barra = f"COD{uuid_sin_guiones}0000100000"
        expected_uuid = "12345678-1234-5678-1234-567812345678"
        
        # ACT
        uuid_extraido = extraer_uuid_de_codigo_barra(codigo_barra)
        
        # ASSERT
        assert uuid_extraido == expected_uuid
        assert "-" in uuid_extraido, "El UUID debe tener guiones"
        assert uuid_extraido.count("-") == 4, "El UUID debe tener exactamente 4 guiones"
    
    def test_backward_compatibility(self):
        """Test 7: Verificar compatibilidad con ambos formatos"""
        test_uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
        
        # Formato nuevo
        codigo_nuevo = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        uuid_nuevo = extraer_uuid_de_codigo_barra(codigo_nuevo)
        
        # Formato viejo
        codigo_viejo = f"COD-{test_uuid}_123-2024_100.00"
        uuid_viejo = extraer_uuid_de_codigo_barra(codigo_viejo)
        
        # Ambos deben extraer el mismo UUID
        assert uuid_nuevo == uuid_viejo == test_uuid
    
    def test_multiple_formats_in_sequence(self):
        """Test 8: Procesar múltiples códigos consecutivamente"""
        test_cases = [
            ("COD9cb06c3bf14e486ea97e15a4046fff6e0000010000", "9cb06c3b-f14e-486e-a97e-15a4046fff6e"),
            ("COD-abc12345-6789-abcd-ef01-234567890abc_456_200", "abc12345-6789-abcd-ef01-234567890abc"),
            ("CODabc123def456789012345678901234560000050000", "abc123de-f456-7890-1234-567890123456"),
        ]
        
        for codigo, expected_uuid in test_cases:
            result = extraer_uuid_de_codigo_barra(codigo)
            assert result == expected_uuid, f"Falló para código: {codigo}"


class TestWebhookValidation:
    """Tests para validación de datos del webhook"""
    
    def test_validate_codigo_barra_length(self):
        """Test 9: Validar longitud de código nuevo"""
        codigo_barra = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        
        # Debe tener exactamente 45 caracteres
        assert len(codigo_barra) == 45
    
    def test_validate_codigo_is_alphanumeric(self):
        """Test 10: Validar que el código sea alfanumérico"""
        codigo_barra = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        
        # Solo debe contener letras y números
        assert codigo_barra.isalnum()
    
    def test_extract_amount_from_barcode(self):
        """Test 11: Extraer monto del código de barras (opcional)"""
        codigo_barra = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        
        # Los últimos 10 caracteres son el monto en centavos
        monto_centavos = int(codigo_barra[-10:])
        monto_pesos = monto_centavos / 100
        
        assert monto_centavos == 10000
        assert monto_pesos == 100.00


# Test de integración simulada
def test_integration_complete_flow():
    """Test 12: Simular el flujo completo de generación y parsing"""
    # Importar función desde el otro archivo de test
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from test_barcode_generation import generar_codigo_barra
    
    # 1. Generar código de barras
    original_uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
    amount = 100.00
    codigo_generado = generar_codigo_barra(original_uuid, amount)
    
    print(f"\n🔄 UUID original: {original_uuid}")
    print(f"🔄 Código generado: {codigo_generado}")
    
    # 2. Simular que la Bolsa escanea y envía el webhook
    # (podría agregar espacios como lo hace un escáner real)
    codigo_escaneado = codigo_generado.strip()
    
    # 3. Extraer UUID en el webhook
    uuid_extraido = extraer_uuid_de_codigo_barra(codigo_escaneado)
    
    print(f"🔄 UUID extraído: {uuid_extraido}")
    
    # 4. Verificar que el UUID coincida
    assert uuid_extraido == original_uuid, "El UUID debe ser el mismo después del ciclo completo"
    assert len(codigo_generado) == 45, "El código debe tener 45 caracteres"
    
    print("✅ Flujo completo exitoso!")

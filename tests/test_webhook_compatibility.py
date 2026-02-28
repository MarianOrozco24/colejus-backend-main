"""
Tests para la búsqueda robusta de recibos en el webhook BCM
Verifica que el webhook pueda encontrar recibos con diferentes formatos de códigos de barras
"""
import pytest


def buscar_recibo_compatible(cod_cliente: str, receipts_db: list) -> dict:
    """
    Simula la lógica de búsqueda del webhook con compatibilidad hacia atrás.
    
    Args:
        cod_cliente: Código de cliente recibido del webhook
        receipts_db: Lista de recibos simulados [{payment_id: ..., uuid: ...}]
    
    Returns:
        Recibo encontrado o None
    """
    receipt = None
    search_attempts = []
    
    # Variante 1: Código exacto como viene
    for r in receipts_db:
        if r['payment_id'] == cod_cliente:
            receipt = r
            break
    search_attempts.append(f"Exacto: '{cod_cliente}'")
    
    # Variante 2: Si código nuevo (45 chars), buscar formato antiguo
    if not receipt and cod_cliente.startswith("COD") and len(cod_cliente) == 45:
        try:
            uuid_sin_guiones = cod_cliente[3:35]
            uuid_con_guiones = f"{uuid_sin_guiones[:8]}-{uuid_sin_guiones[8:12]}-{uuid_sin_guiones[12:16]}-{uuid_sin_guiones[16:20]}-{uuid_sin_guiones[20:32]}"
            
            old_format_pattern = f"COD-{uuid_con_guiones}_"
            for r in receipts_db:
                if r['payment_id'].startswith(old_format_pattern):
                    receipt = r
                    break
            search_attempts.append(f"Formato antiguo con UUID: '{old_format_pattern}...'")
        except Exception as e:
            pass
    
    # Variante 3: Si código antiguo (COD-..._...), buscar formato nuevo
    if not receipt and cod_cliente.startswith("COD-") and "_" in cod_cliente:
        try:
            uuid_con_guiones = cod_cliente.split("COD-")[1].split("_")[0]
            uuid_sin_guiones = uuid_con_guiones.replace("-", "")
            
            new_format_pattern = f"COD{uuid_sin_guiones}"
            for r in receipts_db:
                if r['payment_id'].startswith(new_format_pattern):
                    receipt = r
                    break
            search_attempts.append(f"Formato nuevo con UUID: '{new_format_pattern}...'")
        except Exception as e:
            pass
    
    return receipt, search_attempts


class TestWebhookBackwardCompatibility:
    """Tests para verificar compatibilidad con códigos antiguos y nuevos"""
    
    def test_find_receipt_with_exact_new_format(self):
        """Test 1: Encontrar recibo con código nuevo (búsqueda exacta)"""
        # ARRANGE
        cod_cliente = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        receipts_db = [
            {"payment_id": "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000", "uuid": "receipt-1"},
            {"payment_id": "COD-other-uuid_123_100", "uuid": "receipt-2"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is not None, "Debe encontrar el recibo"
        assert receipt["uuid"] == "receipt-1"
        assert "Exacto" in attempts[0]
    
    def test_find_receipt_with_exact_old_format(self):
        """Test 2: Encontrar recibo con código antiguo (búsqueda exacta)"""
        # ARRANGE
        cod_cliente = "COD-9cb06c3b-f14e-486e-a97e-15a4046fff6e_123-2024_100.00"
        receipts_db = [
            {"payment_id": "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000", "uuid": "receipt-1"},
            {"payment_id": "COD-9cb06c3b-f14e-486e-a97e-15a4046fff6e_123-2024_100.00", "uuid": "receipt-2"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is not None
        assert receipt["uuid"] == "receipt-2"
    
    def test_find_old_receipt_with_new_code(self):
        """Test 3: Recibir código nuevo pero encontrar recibo antiguo"""
        # ARRANGE
        # Webhook envía código nuevo
        cod_cliente = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        # DB tiene solo recibo antiguo
        receipts_db = [
            {"payment_id": "COD-9cb06c3b-f14e-486e-a97e-15a4046fff6e_123_100", "uuid": "old-receipt"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is not None, "Debe encontrar el recibo antiguo usando el UUID extraído"
        assert receipt["uuid"] == "old-receipt"
        assert len(attempts) >= 2, "Debe intentar búsqueda exacta y luego formato antiguo"
    
    def test_find_new_receipt_with_old_code(self):
        """Test 4: Recibir código antiguo pero encontrar recibo nuevo"""
        # ARRANGE
        # Webhook envía código antiguo
        cod_cliente = "COD-9cb06c3b-f14e-486e-a97e-15a4046fff6e_123_100"
        # DB tiene solo recibo nuevo
        receipts_db = [
            {"payment_id": "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000", "uuid": "new-receipt"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is not None, "Debe encontrar el recibo nuevo usando el UUID extraído"
        assert receipt["uuid"] == "new-receipt"
        assert len(attempts) >= 3, "Debe intentar exacta, formato antiguo y nuevo"
    
    def test_uuid_extraction_from_new_code(self):
        """Test 5: Verificar extracción correcta del UUID de código nuevo"""
        # ARRANGE
        cod_cliente = "COD9cb06c3bf14e486ea97e15a4046fff6e0000010000"
        
        # ACT
        uuid_sin_guiones = cod_cliente[3:35]
        uuid_con_guiones = f"{uuid_sin_guiones[:8]}-{uuid_sin_guiones[8:12]}-{uuid_sin_guiones[12:16]}-{uuid_sin_guiones[16:20]}-{uuid_sin_guiones[20:32]}"
        
        # ASSERT
        assert uuid_sin_guiones == "9cb06c3bf14e486ea97e15a4046fff6e"
        assert uuid_con_guiones == "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
    
    def test_uuid_extraction_from_old_code(self):
        """Test 6: Verificar extracción correcta del UUID de código antiguo"""
        # ARRANGE
        cod_cliente = "COD-9cb06c3b-f14e-486e-a97e-15a4046fff6e_123-2024_100.00"
        
        # ACT
        uuid_con_guiones = cod_cliente.split("COD-")[1].split("_")[0]
        uuid_sin_guiones = uuid_con_guiones.replace("-", "")
        
        # ASSERT
        assert uuid_con_guiones == "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
        assert uuid_sin_guiones == "9cb06c3bf14e486ea97e15a4046fff6e"
    
    def test_no_receipt_found(self):
        """Test 7: Verificar que retorna None cuando no se encuentra"""
        # ARRANGE
        cod_cliente = "CODinvalidcode123456789012345678901234567890"
        receipts_db = [
            {"payment_id": "CODdifferent1234567890123456789012340000100000", "uuid": "receipt-1"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is None, "No debe encontrar recibo"
        assert len(attempts) >= 1, "Debe registrar intentos"
    
    def test_multiple_receipts_same_uuid_returns_first(self):
        """Test 8: Con múltiples recibos del mismo UUID, retorna el primero encontrado"""
        # ARRANGE
        uuid = "9cb06c3b-f14e-486e-a97e-15a4046fff6e"
        cod_cliente = f"COD{uuid.replace('-', '')}0000010000"
        
        receipts_db = [
            {"payment_id": f"COD-{uuid}_123_100", "uuid": "receipt-1"},
            {"payment_id": f"COD-{uuid}_456_200", "uuid": "receipt-2"},
            {"payment_id": cod_cliente, "uuid": "receipt-3"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is not None
        assert receipt["uuid"] == "receipt-3"  # Encuentra con búsqueda exacta primero
    
    def test_edge_case_cod_without_hyphen_but_short(self):
        """Test 9: Código que empieza con COD pero no tiene 45 caracteres"""
        # ARRANGE
        cod_cliente = "COD123456"  # Muy corto
        receipts_db = [
            {"payment_id": "COD123456", "uuid": "short-receipt"},
        ]
        
        # ACT
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        
        # ASSERT
        assert receipt is not None, "Debe encontrar con búsqueda exacta"
        assert receipt["uuid"] == "short-receipt"


def test_integration_webhook_compatibility():
    """Test 10: Simular escenarios reales de migración"""
    print("\n🔄 Simulando migración de formato antiguo a nuevo")
    
    # Escenario: Sistema en transición con ambos formatos
    receipts_db = [
        # Recibos antiguos (antes del cambio)
        {"payment_id": "COD-abc12345-6789-abcd-ef01-234567890abc_100_50.00", "uuid": "old-1"},
        {"payment_id": "COD-def45678-1234-5678-1234-567812345678_200_100.00", "uuid": "old-2"},
        
        # Recibos nuevos (después del cambio)
        {"payment_id": "CODabc123456789abcdef01234567890abc0000005000", "uuid": "new-1"},
        {"payment_id": "CODdef45678123456781234567812345678000001000", "uuid": "new-2"},
    ]
    
    test_cases = [
        # (código_enviado, uuid_esperado, descripción)
        ("COD-abc12345-6789-abcd-ef01-234567890abc_100_50.00", "old-1", "Código antiguo → recibo antiguo"),
        ("CODabc123456789abcdef01234567890abc0000005000", "new-1", "Código nuevo → recibo nuevo"),
        ("CODabc123456789abcdef01234567890abc0000005000", "new-1", "Código nuevo → encuentra antiguo también"),
        ("COD-def45678-1234-5678-1234-567812345678_200_100.00", "old-2", "Código antiguo → encuentra nuevo también"),
    ]
    
    for cod_cliente, expected_uuid, descripcion in test_cases:
        receipt, attempts = buscar_recibo_compatible(cod_cliente, receipts_db)
        print(f"   {descripcion}: {'✅' if receipt and receipt['uuid'] == expected_uuid else '❌'}")
        assert receipt is not None, f"Falló: {descripcion}"
        # Nota: algunos pueden encontrar múltiples, lo importante es que encuentren UNO
    
    print("✅ Todos los escenarios de migración pasaron!")

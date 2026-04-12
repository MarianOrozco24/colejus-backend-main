import requests
import time

BASE_URL = "http://localhost:5000/api"

def test_rate_limit():
    print("Iniciando prueba de Rate Limit (peticiones seguidas)...")
    success_count = 0
    blocked_count = 0
    
    # Intentamos hacer 350 peticiones rápidas
    for i in range(350):
        try:
            # Usamos un endpoint simple como /api/news
            response = requests.get(f"{BASE_URL}/news")
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                blocked_count += 1
                if blocked_count == 1:
                    print(f"Petición {i+1}: Bloqueado por Rate Limit (429)")
        except Exception as e:
            print(f"Error: {e}")
            break
            
    print(f"\nResultados:")
    print(f"Peticiones exitosas: {success_count}")
    print(f"Peticiones bloqueadas: {blocked_count}")
    
    if blocked_count > 0:
        print("✅ Prueba Superada: El Rate Limit está funcionando.")
    else:
        print("❌ Prueba Fallida: No se bloqueó ninguna petición.")

if __name__ == "__main__":
    test_rate_limit()

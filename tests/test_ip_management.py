import requests
import time

BASE_URL = "http://localhost:5000/api"

def test_ip_management():
    print("Iniciando prueba de Gestión de IPs...")
    
    # 1. Verificar rastreo (la IP debería aparecer en la lista después de unas peticiones)
    requests.get(f"{BASE_URL}/news")
    requests.get(f"{BASE_URL}/news")
    
    response = requests.get(f"{BASE_URL}/dev/ips")
    ips = response.json()
    my_ip = next((item for item in ips if item['requests_minute'] >= 1), None)
    
    if my_ip:
        print(f"✅ Rastreo funcionando. IP detectada: {my_ip['ip']}, Reqs/Min: {my_ip['requests_minute']}")
    else:
        print("❌ Error: IP no detectada en el rastreo.")
        return

    # 2. Probar Bloqueo
    print(f"Probando bloqueo para IP: {my_ip['ip']}...")
    blocking_resp = requests.post(f"{BASE_URL}/dev/ips/block", json={'ip': my_ip['ip']})
    print(f"Respuesta de bloqueo: {blocking_resp.json()}")
    
    # Intentar acceder a un recurso protegido
    blocked_request = requests.get(f"{BASE_URL}/news")
    if blocked_request.status_code == 403:
        print("✅ Bloqueo funcionando: Recibido 403 Forbidden.")
    else:
        print(f"❌ Error: Se esperaba 403 pero se obtuvo {blocked_request.status_code}")

    # 3. Probar Desbloqueo
    print(f"Probando desbloqueo para IP: {my_ip['ip']}...")
    unblocking_resp = requests.post(f"{BASE_URL}/dev/ips/unblock", json={'ip': my_ip['ip']})
    print(f"Respuesta de desbloqueo: {unblocking_resp.json()}")
    
    retry_request = requests.get(f"{BASE_URL}/news")
    if retry_request.status_code == 200:
        print("✅ Desbloqueo funcionando: Recibido 200 OK.")
    else:
        print(f"❌ Error: Se esperaba 200 pero se obtuvo {retry_request.status_code}")

if __name__ == "__main__":
    test_ip_management()

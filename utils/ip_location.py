import os
import requests
import logging

logger = logging.getLogger(__name__)

def get_ip_location(ip_address):
    """
    Obtiene la geolocalización (País y Ciudad) para una dirección IP usando la API de ipinfo.io.
    """
    # Si la IP es localhost, devolver valores por defecto
    if ip_address in ['127.0.0.1', '::1', 'localhost']:
        return {
            "pais": "Desconocido",
            "ciudad": "Desconocido",
            "continente": "Desconocido",
            "proveedor": "Desconocido",
            "dominio_proveedor": "Desconocido"
        }

    token = os.getenv("IPINFO_TOKEN")
    if not token:
        logger.warning("IPINFO_TOKEN no está configurado en las variables de entorno.")
        return {
            "pais": "Desconocido",
            "ciudad": "Desconocido",
            "continente": "Desconocido",
            "proveedor": "Desconocido",
            "dominio_proveedor": "Desconocido"
        }

    try:
        url = f"https://ipinfo.io/{ip_address}/json?token={token}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        country = data.get("country", "Desconocido")
        # Try to get city, but fallback if not present
        city = data.get("city", "Desconocido")
        
        # New fields that might be returned in an enriched response
        # Original: "como_nombre" -> as_name; "como dominio" -> as_domain; "continente" -> continent
        proveedor = data.get("as_name", data.get("org", "Desconocido"))
        dominio_proveedor = data.get("as_domain", "Desconocido")
        continente = data.get("continent", "Desconocido")
        
        return {
            "pais": country,
            "ciudad": city,
            "continente": continente,
            "proveedor": proveedor,
            "dominio_proveedor": dominio_proveedor
        }
    except requests.RequestException as e:
        logger.error(f"Error al obtener la ubicación de la IP {ip_address}: {e}")
        return {
            "pais": "Desconocido",
            "ciudad": "Desconocido",
            "continente": "Desconocido",
            "proveedor": "Desconocido",
            "dominio_proveedor": "Desconocido"
        }

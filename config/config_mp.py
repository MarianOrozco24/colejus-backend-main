import mercadopago
import os
import dotenv

dotenv.load_dotenv()

# Global variable to store the initialized SDK
sdk = None

def init_mp():
    global sdk
    # Get the access token from environment variables
    access_token = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
    
    print("\nMP Initialization Debug:")
    print("------------------------")
    print(f"Using token: {access_token}")
    try:
        print(access_token)
        # if not access_token:
        #     raise ValueError("Token missin")
    except Exception as error:
        print("Error de token", error)
        

    if not access_token == "APP_USR-1340807008525417-021217-c686ad23efbc7f7eda571f0fc4198393-2253798535":
        print("Warning: Token mismatch with expected production token")

    # Check if the access token is available
    if not access_token:
        raise ValueError("Mercado Pago access token is missing. Set MERCADO_PAGO_ACCESS_TOKEN in your environment.")

    # Initialize the Mercado Pago SDK
    sdk = mercadopago.SDK(access_token)

def get_mp_sdk():
    if sdk is None:
        raise ValueError("Mercado Pago SDK has not been initialized. Call init_mp() first.")
    return sdk
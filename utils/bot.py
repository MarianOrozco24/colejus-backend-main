import os, requests, dotenv
dotenv.load_dotenv()

def enviar_alerta(mensaje):

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    if frontend_url.startswith("http://localhost"):
        return None
    
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = [6636063550, 5519837040]
    for id in chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": id, "text": mensaje})

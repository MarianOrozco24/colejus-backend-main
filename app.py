from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from config.config import init_db, db, init_jwt, init_cors
from config.config_mp import init_mp
from routes import init_app
from utils.bot import enviar_alerta

app = Flask(__name__)
# CORS(app, supports_credentials=True)

# Cargar variables de entorno
load_dotenv(override=True)


init_mp()
init_db(app)
init_jwt(app)
init_cors(app) # En caso de entrar en modo desarrollador comentar y volver al comando basico de cors


# Crea las tablas en la base de datos
with app.app_context():
    db.create_all()

# Inicializar y registrar todos los blueprints
init_app(app)

if __name__ == '__main__':
    # enviar_alerta("🤖 Monitoreando colejus")
    app.run(debug=True)  # Para desarrollo modificar a host=0.0.0.0 y port=5000
    
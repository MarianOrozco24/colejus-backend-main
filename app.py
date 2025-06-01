from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from config.config import init_db, db, init_jwt, init_cors
from config.config_mp import init_mp
from routes import init_app

app = Flask(__name__)
# CORS(app, supports_credentials=True)

# Cargar variables de entorno
load_dotenv(override=True)

# 
init_mp()
init_db(app)
init_jwt(app)
## -----------------
# Descomentar para produccion. El motivo de este comentario es para poder realizar testeos con ngrok en lo que 
# respecta a los modulos de pago con MP

# init_cors(app) 
## -----------------


# Crea las tablas en la base de datos
with app.app_context():
    db.create_all()

# Inicializar y registrar todos los blueprints
init_app(app)

if __name__ == '__main__':
    app.run(debug=True, host= "0.0.0.0", port=5000)  # Modificar cuando vayamos a mandar a produccion
    
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from config.config import init_db, db, init_jwt, init_cors
from config.config_mp import init_mp
from routes import init_app
from utils.bot import enviar_alerta
from config.config_mail import init_mail, mail
from utils.logging_config import setup_logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Solucionar IP reales a traves del proxy de produccion
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configuración de Rate Limit
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["300 per minute"],
    storage_uri="memory://",
)
# CORS(app, supports_credentials=True)

# Cargar variables de entorno
load_dotenv(override=True)


init_mp()
setup_logging(app)
init_db(app)
init_jwt(app)
init_cors(app) # En caso de entrar en modo desarrollador comentar y volver al comando basico de cors
init_mail(app) # Inicializo la configuración de mail

from flask import request, abort
from models.ip_manager import IPRegistry
from datetime import datetime, timedelta
from utils.ip_manager_cache import ip_manager_cache

@app.before_request
def check_ip_block():
    # Ignorar peticiones de ping/dev stats si se desea, o rastrear todo
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    if ip_manager_cache.check_blocked(client_ip):
        abort(403, description="Tu IP ha sido bloqueada por el administrador.")

@app.after_request
def track_ip_stats(response):
    # No rastrear peticiones estáticas
    if not request.endpoint or 'static' in request.endpoint:
        return response

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip:
        client_ip = client_ip.split(',')[0].strip()
        
    if not client_ip:
        return response
        
    try:
        ip_manager_cache.track_request(client_ip)
    except Exception as e:
        app.logger.error(f"Error tracking IP stats in cache: {e}")
    
    return response

# Crea las tablas en la base de datos
with app.app_context():
    db.create_all()

# Inicializar y registrar todos los blueprints
init_app(app)
ip_manager_cache.init_app(app)

if __name__ == '__main__':
    # enviar_alerta("🤖 Monitoreando colejus")
    app.run(debug=True)  # Para desarrollo modificar a host=0.0.0.0 y port=5000
    
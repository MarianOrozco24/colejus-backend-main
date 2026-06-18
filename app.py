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

import os
from flask import request, abort, send_from_directory
from models.ip_manager import IPRegistry
from datetime import datetime, timedelta
from utils.ip_manager_cache import ip_manager_cache

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    uploads_dir = os.path.join(app.root_path, 'uploads')
    return send_from_directory(uploads_dir, filename)

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
    import models
    db.create_all()
    from models.profile import ProfileModel
    from models.access import AccessModel
    from models.room import RoomModel
    import uuid
    import json

    # 1. Seed default accesses (permissions)
    default_accesses = {
        'view_news': 'Ver sección de noticias',
        'manage_news': 'Publicar, editar y eliminar noticias',
        'view_trainings': 'Ver sección de capacitaciones',
        'manage_trainings': 'Crear, editar y eliminar capacitaciones',
        'view_tags': 'Ver categorías de noticias/capacitaciones',
        'manage_tags': 'Crear, editar y eliminar categorías',
        'view_edicts': 'Ver sección de edictos',
        'manage_edicts': 'Crear, editar y eliminar edictos',
        'view_professionals': 'Ver directorio de profesionales',
        'manage_professionals': 'Crear, editar y eliminar profesionales',
        'view_rates': 'Ver sección de tasas',
        'manage_rates': 'Crear, editar y eliminar tasas',
        'view_receipts': 'Ver historial de recibos',
        'manage_receipts': 'Descargar y gestionar recibos',
        'view_revenue': 'Ver dashboard de ingresos',
        'manage_revenue': 'Gestionar datos del dashboard de ingresos',
        'view_lawyer_payments': 'Ver historial de pagos de membresías',
        'manage_lawyer_payments': 'Registrar pagos de membresías',
        'view_collection_admin': 'Ver administrador de cobros de membresías',
        'manage_collection_admin': 'Modificar valores y ver reportes de deudores',
        'view_integrantes': 'Ver sección nosotros/integrantes',
        'manage_integrantes': 'Crear, editar y eliminar integrantes',
        'book_rooms': 'Reservar salas de coworking',
        'view_rooms': 'Ver gestión de salas coworking',
        'manage_rooms': 'Crear, editar y eliminar salas de coworking'
    }

    db_accesses = {}
    try:
        db_accesses = {a.name: a for a in AccessModel.query.all()}
        for name, desc in default_accesses.items():
            if name not in db_accesses:
                new_acc = AccessModel(
                    uuid=str(uuid.uuid4()),
                    name=name,
                    description=desc
                )
                db.session.add(new_acc)
                db_accesses[name] = new_acc
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error seeding accesses: {e}")

    # 2. Seed profiles and map permissions
    try:
        # Seed lawyer profile if missing
        lawyer_profile = ProfileModel.query.filter_by(name='lawyer').first()
        if not lawyer_profile:
            lawyer_profile = ProfileModel(
                uuid=str(uuid.uuid4()),
                name='lawyer',
                description='Rol para Abogados Colegiados'
            )
            db.session.add(lawyer_profile)
            db.session.commit()
            
        # Give lawyer default accesses
        default_lawyer_accesses = [
            'view_news',
            'view_trainings',
            'view_tags',
            'view_professionals',
            'view_rates',
            'view_receipts',
            'view_integrantes',
            'view_lawyer_payments',
            'manage_lawyer_payments',
            'book_rooms'
        ]
        for name in default_lawyer_accesses:
            acc = db_accesses.get(name)
            if acc and acc not in lawyer_profile.accesses:
                lawyer_profile.accesses.append(acc)

        # Give Administrators all permissions by default
        admin_profiles = ProfileModel.query.filter(ProfileModel.name.in_(['Admin', 'Administrador'])).all()
        for ap in admin_profiles:
            for acc in db_accesses.values():
                if acc not in ap.accesses:
                    ap.accesses.append(acc)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error seeding lawyer profile accesses: {e}")

    # 3. Seed initial rooms
    try:
        if RoomModel.query.filter(RoomModel.deleted_at.is_(None)).count() == 0:
            initial_rooms = [
                RoomModel(
                    name='Sala de Reuniones Ejecutiva',
                    capacity='10 personas',
                    price=1500.0,
                    image='/meeting_room_exec.png',
                    description='Ideal para reuniones de directorio, negociaciones, conciliaciones o presentaciones corporativas. Ambiente climatizado y privado.',
                    amenities=json.dumps([
                        'Mesa de directorio para 10 pers.',
                        'Pantalla Smart TV 55"',
                        'Wi-Fi Simétrico de Alta Velocidad',
                        'Cámara para Videoconferencias'
                    ], ensure_ascii=False),
                    is_active=True
                ),
                RoomModel(
                    name='SUM / Auditorio Multiuso',
                    capacity='30 personas',
                    price=3000.0,
                    image='/auditorium_sum.png',
                    description='Perfecto para capacitaciones, charlas informativas, asambleas o talleres grupales. Mobiliario modular configurable.',
                    amenities=json.dumps([
                        'Capacidad de hasta 30 personas',
                        'Proyector HD & Pantalla Gigante',
                        'Sistema de Audio & Micrófonos',
                        'Wi-Fi de Alta Velocidad'
                    ], ensure_ascii=False),
                    is_active=True
                ),
                RoomModel(
                    name='Box de Enfoque Individual',
                    capacity='1 persona',
                    price=500.0,
                    image='/individual_box.png',
                    description='Espacio optimizado para el trabajo individual concentrado, videollamadas privadas o estudio. Aislado acústicamente.',
                    amenities=json.dumps([
                        'Escritorio Individual Amplio',
                        'Wi-Fi de Alta Velocidad',
                        'Ergonomía & Tomas de Carga Directa',
                        'Panel de Absorción Acústica'
                    ], ensure_ascii=False),
                    is_active=True
                )
            ]
            for room in initial_rooms:
                db.session.add(room)
            db.session.commit()
            app.logger.info("Seeded initial rooms.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error seeding initial rooms: {e}")

    # 4. Seed default system configurations
    try:
        from models.config import SystemConfigModel
        default_configs = {
            'disable_membership_validation': 'false'
        }
        for k, v in default_configs.items():
            conf = SystemConfigModel.query.filter_by(key=k).first()
            if not conf:
                new_conf = SystemConfigModel(key=k, value=v)
                db.session.add(new_conf)
        db.session.commit()
        app.logger.info("Seeded initial configurations.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error seeding configurations: {e}")

# Inicializar y registrar todos los blueprints
init_app(app)
ip_manager_cache.init_app(app)

if __name__ == '__main__':
    # enviar_alerta("🤖 Monitoreando colejus")
    app.run(debug=True)  # Para desarrollo modificar a host=0.0.0.0 y port=5000
    
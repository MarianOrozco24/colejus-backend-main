import os
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()

def init_db(app):
    username = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD')
    host = os.environ.get('MYSQL_HOST')
    database = os.environ.get('MYSQL_DATABASE')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{username}:{password}@{host}/{database}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True
    db.init_app(app)

def init_jwt(app):
    # Configurar la clave secreta para JWT desde el archivo .env
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    jwt.init_app(app)

def init_cors(app):
    CORS(app, resources={r"/api/*": {"origins": "*"}}, expose_headers=['Content-Disposition'])
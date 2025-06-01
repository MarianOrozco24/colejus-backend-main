from flask import Flask

from .users import users_bp
from .auth import auth_bp
from .profiles import profile_bp
from .accesses import access_bp
from .forms import forms_bp
from .news import news_bp
from .trainings import trainings_bp
from .tags import tags_bp
from .edicts import edicts_bp
from .professionals import professional_bp
from .rates import rate_bp
from .receipts import receipts_bp
from .integrantes import integrantes_bp

def init_app(app: Flask):
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(profile_bp, url_prefix='/api')
    app.register_blueprint(access_bp, url_prefix='/api')
    app.register_blueprint(forms_bp, url_prefix='/api')
    app.register_blueprint(news_bp, url_prefix='/api')
    app.register_blueprint(trainings_bp, url_prefix='/api')
    app.register_blueprint(tags_bp, url_prefix='/api')
    app.register_blueprint(edicts_bp, url_prefix='/api')
    app.register_blueprint(professional_bp, url_prefix='/api')
    app.register_blueprint(rate_bp, url_prefix='/api')
    app.register_blueprint(receipts_bp, url_prefix='/api')
    app.register_blueprint(integrantes_bp, url_prefix='/api')
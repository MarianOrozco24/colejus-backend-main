from flask_mail import Mail
import os

mail = Mail()

def init_mail(app):
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.donweb.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = (
        os.getenv('MAIL_DEFAULT_SENDER_NAME', 'Colejus'),
        os.getenv('MAIL_DEFAULT_SENDER_EMAIL', os.getenv('MAIL_USERNAME'))
    )

    mail.init_app(app)

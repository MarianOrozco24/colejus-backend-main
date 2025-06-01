from config.config import db

# Tabla intermedia perfiles_usuarios
profiles_users = db.Table('profiles_users',
    db.Column('user_uuid', db.String(36), db.ForeignKey('users.uuid'), primary_key=True),
    db.Column('profile_uuid', db.String(36), db.ForeignKey('profiles.uuid'), primary_key=True)
)
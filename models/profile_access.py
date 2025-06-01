from config.config import db

# Tabla intermedia perfiles_accesos
profiles_accesses = db.Table('profiles_accesses',
    db.Column('profile_uuid', db.String(36), db.ForeignKey('profiles.uuid'), primary_key=True),
    db.Column('access_uuid', db.String(36), db.ForeignKey('accesses.uuid'), primary_key=True)
)
from config.config import db

# Tabla intermedia perfiles_usuarios
trainings_tags = db.Table('trainings_tags',
    db.Column('training_uuid', db.String(36), db.ForeignKey('trainings.uuid'), primary_key=True),
    db.Column('tag_uuid', db.String(36), db.ForeignKey('tags.uuid'), primary_key=True)
)
import uuid
from datetime import datetime
from config.config import db

class IntegranteModel(db.Model):
    __tablename__ = 'integrantes'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(128), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    cargo = db.Column(db.String(128), nullable=False)  # Ej: 'Presidente', 'Comisión de Género'
    categoria = db.Column(db.String(64), nullable=False)  # Ej: 'directorio', 'comision', 'tribunal_etica'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            "uuid": str(self.uuid),
            "nombre": self.nombre,
            "telefono": self.telefono,
            "cargo": self.cargo,
            "categoria": self.categoria,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
import uuid, json
from datetime import datetime
from config.config import db
from sqlalchemy.orm import backref
from utils.validate_date import validate_date
from utils.validate_fields import validate_fields

class DerechoFijoModel(db.Model):
    __tablename__ = 'derecho_fijo'
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lugar = db.Column(db.String(80), nullable=True)  
    fecha = db.Column(db.DateTime, nullable=True)
    fecha_inicio = db.Column(db.DateTime, nullable=True)
    tasa_justicia = db.Column(db.String(80), nullable=True)
    juicio_n = db.Column(db.String(80), nullable=True)
    derecho_fijo_5pc = db.Column(db.String(80), nullable=True)
    caratula = db.Column(db.String(255), nullable=True)
    parte = db.Column(db.String(255), nullable=True)
    juzgado = db.Column(db.String(255), nullable=True)
    total_depositado = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return '<DerechoFijo %r>' % self.uuid

    def to_json(self):
        profiles = [profile.to_json() for profile in self.profiles]
        return {
            'uuid': self.uuid,
            'lugar': self.lugar,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'tasa_justicia': self.tasa_justicia,
            'juicio_n': self.juicio_n,
            'derecho_fijo_5pc': self.derecho_fijo_5pc,
            'caratula': self.caratula,
            'parte': self.parte,
            'juzgado': self.juzgado,
            'total_depositado': self.total_depositado,
            "email": self.email,
            'created': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def from_json(json_dict):
        required_fields = [
            'lugar', 'fecha', 'fecha_inicio', 'tasa_justicia', 'juicio_n',
            'derecho_fijo_5pc', 'caratula', 'parte', 'juzgado', 'total_depositado'
        ]
        
        # Check for missing fields
        validate_fields(json_dict, required_fields)

        # Create an instance of DerechoFijoModel
        derecho_fijo = DerechoFijoModel()
        derecho_fijo.uuid = json_dict.get('uuid', str(uuid.uuid4()))

        # Assign values and validate dates
        derecho_fijo.lugar = json_dict['lugar']
        derecho_fijo.fecha = validate_date(json_dict['fecha'])  # Validate and convert
        derecho_fijo.fecha_inicio = validate_date(json_dict['fecha_inicio'])  # Validate and convert
        derecho_fijo.tasa_justicia = json_dict['tasa_justicia']
        derecho_fijo.juicio_n = json_dict['juicio_n']
        derecho_fijo.derecho_fijo_5pc = json_dict['derecho_fijo_5pc']
        derecho_fijo.caratula = json_dict['caratula']
        derecho_fijo.parte = json_dict['parte']
        derecho_fijo.juzgado = json_dict['juzgado']
        derecho_fijo.email = json_dict['email']
        derecho_fijo.total_depositado = json_dict['total_depositado']
        
        return derecho_fijo
from config.config import db
from datetime import datetime

class IPRegistry(db.Model):
    __tablename__ = 'ip_registry'
    
    ip = db.Column(db.String(45), primary_key=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    requests_minute = db.Column(db.Integer, default=0)
    requests_month = db.Column(db.Integer, default=0)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # Track the last reset times for internal logic
    last_minute_reset = db.Column(db.DateTime, default=datetime.utcnow)
    last_month_reset = db.Column(db.DateTime, default=datetime.utcnow)

    # Geolocation data
    pais = db.Column(db.String(100), default="Desconocido")
    ciudad = db.Column(db.String(100), default="Desconocido")
    continente = db.Column(db.String(100), default="Desconocido")
    proveedor = db.Column(db.String(150), default="Desconocido")
    dominio_proveedor = db.Column(db.String(150), default="Desconocido")

    def to_dict(self):
        return {
            'ip': self.ip,
            'last_seen': self.last_seen.isoformat(),
            'requests_minute': self.requests_minute,
            'requests_month': self.requests_month,
            'is_blocked': self.is_blocked,
            'pais': self.pais,
            'ciudad': self.ciudad,
            'continente': self.continente,
            'proveedor': self.proveedor,
            'dominio_proveedor': self.dominio_proveedor
        }

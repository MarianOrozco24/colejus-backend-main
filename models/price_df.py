import uuid
from datetime import datetime
from config.config import db
from flask import abort

class PriceDerechoFijo(db.Model):
    __tablename__ = 'derecho_fijo_price'

    id_table = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    value = db.Column(db.Float, nullable=False)

    def to_json(self):
        return {
            "id_table": self.id_table,
            "fecha": self.fecha.strftime("%Y-%m-%d %H:%M:%S"),
            "value": self.value
        }

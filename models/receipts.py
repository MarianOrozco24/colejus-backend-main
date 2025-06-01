import uuid
from datetime import datetime
from config.config import db

class ReceiptModel(db.Model):
    __tablename__ = 'receipts'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    uuid_derecho_fijo = db.Column(db.String(36), nullable=False)

    
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    caratula = db.Column(db.String(255), nullable=True)
    total_depositado = db.Column(db.Float, nullable=False)
    tasa_justicia = db.Column(db.Float, nullable=True)
    juicio_n = db.Column(db.String(100), nullable=True)
    
    payment_id = db.Column(db.String(100), nullable=True)  # ID de Mercado Pago
    fecha_pago = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(50), default="Pendiente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Receipt {self.receipt_number}>"

    @staticmethod
    def from_json(json_data):
        return ReceiptModel(
            receipt_number=json_data['receipt_number'],
            fecha_inicio=json_data.get('fecha_inicio'),
            fecha_vencimiento=json_data.get('fecha_vencimiento'),
            caratula=json_data.get('caratula'),
            total_depositado=json_data['total_depositado'],
            tasa_justicia=json_data.get('tasa_justicia'),
            juicio_n=json_data.get('juicio_n'),
            payment_id=json_data.get('payment_id'),
            fecha_pago=json_data.get('fecha_pago'),
            status=json_data.get('status', 'Pendiente')
        )

    def to_json(self):
        return {
            'uuid': self.uuid,
            'receipt_number': self.receipt_number,
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%d') if self.fecha_inicio else None,
            'fecha_vencimiento': self.fecha_vencimiento.strftime('%Y-%m-%d') if self.fecha_vencimiento else None,
            'caratula': self.caratula,
            'total_depositado': self.total_depositado,
            'tasa_justicia': self.tasa_justicia,
            'juicio_n': self.juicio_n,
            'payment_id': self.payment_id,
            'fecha_pago': self.fecha_pago.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_pago else None,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

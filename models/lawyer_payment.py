import uuid
from datetime import datetime
from config.config import db

class LawyerPaymentModel(db.Model):
    __tablename__ = 'lawyer_payments'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    uuid_user = db.Column(db.String(36), db.ForeignKey('users.uuid'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    value = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('UserModel', backref=db.backref('lawyer_payments', lazy=True))

    def to_json(self):
        return {
            'uuid': self.uuid,
            'uuid_user': self.uuid_user,
            'description': self.description,
            'value': self.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': {
                'name': self.user.name if self.user else None,
                'email': self.user.email if self.user else None
            }
        }

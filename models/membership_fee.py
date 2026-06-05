import uuid
from datetime import datetime
from config.config import db

class MembershipFeeModel(db.Model):
    __tablename__ = 'membership_fees'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    value = db.Column(db.Float, nullable=False)
    effective_date = db.Column(db.Date, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            'uuid': self.uuid,
            'value': self.value,
            'effective_date': self.effective_date.strftime('%Y-%m-%d') if self.effective_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

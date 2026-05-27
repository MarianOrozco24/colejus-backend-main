from config.config import db
from datetime import datetime

class BookingModel(db.Model):
    __tablename__ = 'bookings'
    __table_args__ = (
        db.UniqueConstraint('room_id', 'booking_date', 'time_slot', name='uq_room_date_slot'),
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(10), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(255), nullable=False)
    user_phone = db.Column(db.String(50), nullable=False)
    user_tuition = db.Column(db.String(50), nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    idempotency_key = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'booking_date': self.booking_date.isoformat() if self.booking_date else None,
            'time_slot': self.time_slot,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'user_phone': self.user_phone,
            'user_tuition': self.user_tuition,
            'purpose': self.purpose,
            'idempotency_key': self.idempotency_key,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

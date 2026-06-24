from config.config import db
from datetime import datetime
import json

class RoomModel(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    amenities = db.Column(db.Text, nullable=True)  # Almacenado como JSON String
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False, default='coworking')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def get_amenities(self):
        if not self.amenities:
            return []
        try:
            return json.loads(self.amenities)
        except Exception:
            return []

    def set_amenities(self, amenities_list):
        if not amenities_list:
            self.amenities = json.dumps([])
        else:
            self.amenities = json.dumps(amenities_list, ensure_ascii=False)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'price': self.price,
            'image': self.image,
            'description': self.description,
            'amenities': self.get_amenities(),
            'is_active': self.is_active,
            'room_type': self.room_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

import uuid
from datetime import datetime
from config.config import db

class ProfessionalModel(db.Model):
    __tablename__ = 'professionals'
    
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(64), nullable=False) 
    email = db.Column(db.String(128), nullable=False)
    address = db.Column(db.String(128), nullable=True)
    tuition = db.Column(db.String(10))
    phone = db.Column(db.String(36), nullable=True)
    location = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Professional {self.name}>"

    @staticmethod
    def from_json(json_data):
        return ProfessionalModel(
            name=json_data['name'],
            title=json_data.get('title'),  
            email=json_data.get('email'),
            tuition=json_data.get('tuition'),
            address=json_data.get('address'),  
            phone=json_data.get('phone'),
            location=json_data.get('location'),
        )

    def to_json(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'title': self.title,  
            'email': self.email,
            'address': self.address, 
            'tuition': self.tuition,
            'phone': self.phone,
            'location': self.location,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        
    def to_public_json(self):
        return {
            'name': self.name,
            'title': self.title, 
            'location': self.location,
            'phone': self.phone,
            'address': self.address,
            'tuition': self.tuition.replace(".", "") or 'Sin matricula',
        }

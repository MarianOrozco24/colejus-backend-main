import uuid
from datetime import datetime
from config.config import db

class ProfileModel(db.Model):
    __tablename__ = 'profiles'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.String(255))
    code = db.Column(db.String(9), unique=True)
    accesses = db.relationship('AccessModel', secondary='profiles_accesses', backref=db.backref('profiles', lazy='dynamic'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return '<Profile %r>' % self.uuid

    def to_json(self):
        accesses = [access.to_json() for access in self.accesses]
        return {
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'accesses': accesses,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
        
    def to_json_no_accesses(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    @staticmethod
    def from_json(json_dict):
        return ProfileModel(
            name=json_dict['name'],
            description=json_dict.get('description')
        )
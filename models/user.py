from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
from config.config import db
from sqlalchemy.orm import backref

class UserModel(db.Model):
    __tablename__ = 'users'
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(80), unique=False)  
    password = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    auth_token = db.Column(db.String(500), nullable=True)
    token_expiration_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    profiles = db.relationship('ProfileModel', secondary='profiles_users', lazy='subquery', backref=backref('users', lazy=True))
    
    def __repr__(self):
        return '<User %r>' % self.uuid

    def to_json(self):
        profiles = [profile.to_json() for profile in self.profiles]
        return {
            'uuid': self.uuid,
            'name': self.name,
            'email': self.email,
            'auth_token': self.auth_token,
            'token_expiration_date': self.token_expiration_date.isoformat() if self.token_expiration_date else None,
            'profiles': profiles,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
        
    def to_json_login(self):
        profiles = [
            {
                'profile_name': profile.name,
                'accesses': [access.name for access in profile.accesses]
            }
            for profile in self.profiles
        ]
        return {
            'uuid': self.uuid,
            'name': self.name,
            'email': self.email,
            'auth_token': self.auth_token,
            'profiles': profiles,
        }

        
    def to_json_list(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'email': self.email
        }

    @staticmethod
    def from_json(json_dict):
        user = UserModel()
        user.uuid = json_dict.get('uuid', str(uuid.uuid4()))

        user.name = json_dict['name']
        user.password = generate_password_hash(json_dict['password'])
        user.email = json_dict['email']
            
        return user
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
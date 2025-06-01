import uuid
from datetime import datetime
from config.config import db

class TagModel(db.Model):
    __tablename__ = 'tags'
    
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    color = db.Column(db.String(15), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<News {self.name}>"

    @staticmethod
    def from_json(json_data):
        return TagModel(
            name=json_data['name'],
            color=json_data['color'],
        )

    def to_json(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at
        }
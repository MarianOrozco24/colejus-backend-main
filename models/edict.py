import uuid
from datetime import datetime
from config.config import db

class EdictModel(db.Model):
    __tablename__ = 'edicts'
    
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.Text, nullable=False)
    subtitle = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)  # Rich-text content from Quill
    is_active = db.Column(db.Boolean, default=True)
    scheduled_date = db.Column(db.Date, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<News {self.title}>"

    @staticmethod
    def from_json(json_data):
        return EdictModel(
            title=json_data['title'],
            subtitle=json_data.get('subtitle'),
            date=json_data.get('date'),
            content=json_data.get('content'),
             scheduled_date=json_data.get('scheduled_date') 
        )

    def to_json(self):
        return {
            'uuid': self.uuid,
            'title': self.title,
            'subtitle': self.subtitle,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'content': self.content,
            'scheduled_date': self.scheduled_date.strftime('%Y-%m-%d') if self.scheduled_date else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
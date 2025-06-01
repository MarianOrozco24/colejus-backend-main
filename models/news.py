import uuid
from datetime import datetime
from config.config import db
from .news_tags import news_tags
from sqlalchemy.dialects.mysql import LONGTEXT

class NewsModel(db.Model):
    __tablename__ = 'news'
    
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    reading_duration = db.Column(db.Integer, nullable=True)  # Store in minutes
    tags = db.Column(db.Text, nullable=True)  # Use JSON string or comma-separated tags
    content = db.Column(LONGTEXT, nullable=False)  # Rich-text content from Quill
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    tags = db.relationship(
        'TagModel', 
        secondary=news_tags,
        lazy='subquery',
        backref=db.backref('news', lazy=True)
    )

    def __repr__(self):
        return f"<News {self.title}>"

    @staticmethod
    def from_json(json_data):
        return NewsModel(
            title=json_data['title'],
            subtitle=json_data.get('subtitle'),
            date=json_data.get('date'),
            reading_duration=json_data.get('reading_duration'),
            tags=json_data.get('tags'),
            content=json_data.get('content'),
        )

    def to_json(self):
        return {
            'uuid': self.uuid,
            'title': self.title,
            'subtitle': self.subtitle,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'reading_duration': self.reading_duration,
            'tags': [tag.to_json() for tag in self.tags],
            'content': self.content,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
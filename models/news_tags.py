from config.config import db

news_tags = db.Table('news_tags',
    db.Column('news_uuid', db.String(36), db.ForeignKey('news.uuid'), primary_key=True),
    db.Column('tag_uuid', db.String(36), db.ForeignKey('tags.uuid'), primary_key=True)
)
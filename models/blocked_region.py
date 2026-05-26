from config.config import db
from datetime import datetime

class BlockedRegion(db.Model):
    __tablename__ = 'blocked_regions'
    
    id = db.Column(db.Integer, primary_key=True)
    region_type = db.Column(db.String(50), nullable=False) # 'country' or 'continent'
    region_name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'region_type': self.region_type,
            'region_name': self.region_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

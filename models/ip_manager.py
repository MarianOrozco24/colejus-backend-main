from config.config import db
from datetime import datetime

class IPRegistry(db.Model):
    __tablename__ = 'ip_registry'
    
    ip = db.Column(db.String(45), primary_key=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    requests_minute = db.Column(db.Integer, default=0)
    requests_month = db.Column(db.Integer, default=0)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # Track the last reset times for internal logic
    last_minute_reset = db.Column(db.DateTime, default=datetime.utcnow)
    last_month_reset = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'ip': self.ip,
            'last_seen': self.last_seen.isoformat(),
            'requests_minute': self.requests_minute,
            'requests_month': self.requests_month,
            'is_blocked': self.is_blocked
        }

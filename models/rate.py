import uuid
from datetime import datetime
from config.config import db
from flask import abort
from enum import Enum, unique

@unique
class RateType(Enum):
    """
    Enum to categorize different types of rates.
    
    This allows you to specify additional context or classification 
    for rates beyond their numeric value and date range.
    """
    ACTIVABNA = 'activabna'
    PASIVABNA = 'pasivabna'
    UVA = 'uva'

class RateModel(db.Model):
    __tablename__ = 'rates'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rate = db.Column(db.Numeric(10, 4), nullable=False)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Add the enum column
    rate_type = db.Column(db.Enum(RateType), nullable=False, default=RateType.ACTIVABNA)

    def __repr__(self):
        return '<Rate %r>' % self.uuid

    def to_json(self):
        return {
            'uuid': self.uuid,
            'rate': float(self.rate),  # Convert Decimal to float for JSON serialization
            'rate_type': self.rate_type.value if self.rate_type else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    @staticmethod
    def from_json(json_dict):
        try:
            # Validate required fields
            if not all(key in json_dict for key in ['rate', 'start_date']):
                abort(400, description="Rate and start date are required.")

            # Process rate
            rate = round(float(json_dict['rate']), 4)
            if rate <= 0:
                abort(400, description="Rate must be a positive number.")
            
            # Process dates
            start_date = json_dict['start_date']
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            end_date = json_dict.get('end_date')
            if end_date and isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Handle rate type
            rate_type = RateType.ACTIVABNA
            if 'rate_type' in json_dict:
                try:
                    rate_type = RateType(str(json_dict['rate_type']))
                except ValueError:
                    abort(400, description=f"Invalid rate type. Must be one of {[t.value for t in RateType]}")
                    
            return RateModel(
                rate=rate,
                start_date=start_date,
                end_date=end_date,
                rate_type=rate_type
            )
        except ValueError as e:
            abort(400, description=str(e))
import uuid
from datetime import datetime

from config.config import db
from models.membership_constants import STATUSES_CAN_BOOK_MEETING


class LawyerMembershipStatusModel(db.Model):
    """Estado normalizado de membresía por matrícula (fuente canónica para reservas)."""

    __tablename__ = 'lawyer_membership_status'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tuition_normalized = db.Column(db.String(20), nullable=False, unique=True, index=True)
    tuition_display = db.Column(db.String(32), nullable=True)

    uuid_professional = db.Column(
        db.String(36),
        db.ForeignKey('professionals.uuid'),
        nullable=True,
        index=True,
    )
    uuid_user = db.Column(
        db.String(36),
        db.ForeignKey('users.uuid'),
        nullable=True,
        index=True,
    )

    last_name = db.Column(db.String(128), nullable=True)
    first_name = db.Column(db.String(128), nullable=True)
    branch = db.Column(db.String(64), nullable=True)

    status = db.Column(db.String(32), nullable=False, index=True)
    first_unpaid_month = db.Column(db.Date, nullable=True)
    blocked_reason = db.Column(db.String(64), nullable=True)
    raw_quota_text = db.Column(db.Text, nullable=True)
    observation = db.Column(db.Text, nullable=True)
    parse_notes = db.Column(db.String(255), nullable=True)

    last_import_uuid = db.Column(
        db.String(36),
        db.ForeignKey('membership_sheet_imports.uuid'),
        nullable=True,
    )
    source_row_number = db.Column(db.Integer, nullable=True)

    synced_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    professional = db.relationship('ProfessionalModel', foreign_keys=[uuid_professional])
    user = db.relationship('UserModel', foreign_keys=[uuid_user])

    def can_book_meeting_room(self):
        return self.status in STATUSES_CAN_BOOK_MEETING

    def to_json(self):
        return {
            'uuid': self.uuid,
            'tuition_normalized': self.tuition_normalized,
            'tuition_display': self.tuition_display,
            'uuid_professional': self.uuid_professional,
            'uuid_user': self.uuid_user,
            'last_name': self.last_name,
            'first_name': self.first_name,
            'branch': self.branch,
            'status': self.status,
            'first_unpaid_month': (
                self.first_unpaid_month.strftime('%Y-%m-%d') if self.first_unpaid_month else None
            ),
            'blocked_reason': self.blocked_reason,
            'raw_quota_text': self.raw_quota_text,
            'observation': self.observation,
            'parse_notes': self.parse_notes,
            'can_book_meeting_room': self.can_book_meeting_room(),
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

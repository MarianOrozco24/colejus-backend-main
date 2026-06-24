import uuid
import json
from datetime import datetime

from config.config import db


class MembershipSheetImportModel(db.Model):
    """Registro de cada sincronización desde el Excel/Sheets (fuente cruda)."""

    __tablename__ = 'membership_sheet_imports'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = db.Column(db.String(32), nullable=False)
    source_identifier = db.Column(db.String(512), nullable=True)
    sheet_name = db.Column(db.String(128), nullable=True)

    status = db.Column(db.String(32), nullable=False, default='pending')
    rows_total = db.Column(db.Integer, nullable=False, default=0)
    rows_raw_saved = db.Column(db.Integer, nullable=False, default=0)
    rows_normalized = db.Column(db.Integer, nullable=False, default=0)
    rows_skipped = db.Column(db.Integer, nullable=False, default=0)
    rows_ambiguous = db.Column(db.Integer, nullable=False, default=0)
    rows_blocked = db.Column(db.Integer, nullable=False, default=0)
    users_provisioned = db.Column(db.Integer, nullable=False, default=0)

    report_json = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_by_uuid = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    raw_rows = db.relationship(
        'MembershipSheetRowRawModel',
        backref='import_record',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def set_report(self, report_dict):
        self.report_json = json.dumps(report_dict, ensure_ascii=False)

    def get_report(self):
        if not self.report_json:
            return {}
        try:
            return json.loads(self.report_json)
        except json.JSONDecodeError:
            return {}

    def to_json(self):
        return {
            'uuid': self.uuid,
            'source_type': self.source_type,
            'source_identifier': self.source_identifier,
            'sheet_name': self.sheet_name,
            'status': self.status,
            'rows_total': self.rows_total,
            'rows_raw_saved': self.rows_raw_saved,
            'rows_normalized': self.rows_normalized,
            'rows_skipped': self.rows_skipped,
            'rows_ambiguous': self.rows_ambiguous,
            'rows_blocked': self.rows_blocked,
            'users_provisioned': self.users_provisioned,
            'report': self.get_report(),
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

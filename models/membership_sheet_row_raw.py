import uuid
import json
from datetime import datetime

from config.config import db


class MembershipSheetRowRawModel(db.Model):
    """Fila cruda tal como viene del Excel/Sheets (auditoría y reprocesamiento)."""

    __tablename__ = 'membership_sheet_rows_raw'

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    import_uuid = db.Column(
        db.String(36),
        db.ForeignKey('membership_sheet_imports.uuid'),
        nullable=False,
        index=True,
    )
    membership_status_uuid = db.Column(
        db.String(36),
        db.ForeignKey('lawyer_membership_status.uuid'),
        nullable=True,
        index=True,
    )

    row_number = db.Column(db.Integer, nullable=False)
    col_index = db.Column(db.String(32), nullable=True)
    col_apellido = db.Column(db.String(255), nullable=True)
    col_nombre = db.Column(db.String(255), nullable=True)
    col_mat = db.Column(db.String(64), nullable=True)
    col_cuota_adeudada = db.Column(db.String(512), nullable=True)
    col_sede = db.Column(db.String(128), nullable=True)
    col_observacion = db.Column(db.Text, nullable=True)
    full_row_json = db.Column(db.Text, nullable=True)

    parse_status = db.Column(db.String(32), nullable=False, default='saved')
    parse_notes = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_full_row(self, cells):
        self.full_row_json = json.dumps(cells, ensure_ascii=False)

    def get_full_row(self):
        if not self.full_row_json:
            return []
        try:
            return json.loads(self.full_row_json)
        except json.JSONDecodeError:
            return []

    def to_json(self):
        return {
            'uuid': self.uuid,
            'import_uuid': self.import_uuid,
            'membership_status_uuid': self.membership_status_uuid,
            'row_number': self.row_number,
            'col_index': self.col_index,
            'col_apellido': self.col_apellido,
            'col_nombre': self.col_nombre,
            'col_mat': self.col_mat,
            'col_cuota_adeudada': self.col_cuota_adeudada,
            'col_sede': self.col_sede,
            'col_observacion': self.col_observacion,
            'full_row': self.get_full_row(),
            'parse_status': self.parse_status,
            'parse_notes': self.parse_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

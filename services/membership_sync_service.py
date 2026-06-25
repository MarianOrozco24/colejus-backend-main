"""
Servicio de sincronización: Excel/Sheets (crudo) → BD normalizada.

Flujo:
1. Descargar/leer CSV
2. Guardar filas crudas (auditoría)
3. Normalizar matrícula + estado de cuota
4. Upsert en lawyer_membership_status
5. Opcionalmente provisionar usuarios abogados
"""

import csv
import io
import os
import uuid
from datetime import datetime
from typing import List, Optional

import requests
from werkzeug.security import generate_password_hash

from config.config import db
from models import (
    UserModel,
    ProfileModel,
    ProfessionalModel,
    MembershipSheetImportModel,
    MembershipSheetRowRawModel,
    LawyerMembershipStatusModel,
)
from models.membership_constants import (
    IMPORT_STATUS_PROCESSING,
    IMPORT_STATUS_COMPLETED,
    IMPORT_STATUS_FAILED,
    SOURCE_TYPE_GOOGLE_SHEETS_CSV,
    SOURCE_TYPE_FILE_UPLOAD,
    DEFAULT_SHEET_NAME,
    MEMBERSHIP_STATUS_AMBIGUOUS,
    MEMBERSHIP_STATUS_BLOCKED,
)
from utils.membership_sheet_parser import (
    find_header_row,
    get_row_cell,
    parse_quota_adeudada,
    title_case_name,
)
from utils.tuition_utils import (
    normalize_tuition,
    tuition_display_from_raw,
    link_membership_status_uuids,
    find_professional_by_tuition,
)


DEFAULT_MEMBERSHIP_SHEET_URL = (
    'https://docs.google.com/spreadsheets/d/'
    '1Gwwy0nOJ5dDpOkUJH7Urig4j7LtHT-34L76B8B-ZXr4/export'
    '?format=csv&gid=191760753'
)


def _read_csv_rows(content: str) -> List[List[str]]:
    if content.startswith('\ufeff'):
        content = content[1:]
    reader = csv.reader(io.StringIO(content))
    return [row for row in reader]


def _fetch_csv_from_url(url: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    # Google Sheets exporta UTF-8; errors='replace' evita fallos con caracteres raros
    return response.content.decode('utf-8', errors='replace')


class MembershipSyncService:
    def __init__(self, reference_date=None):
        self.reference_date = reference_date

    def sync_from_csv_content(
        self,
        csv_content: str,
        *,
        source_type=SOURCE_TYPE_FILE_UPLOAD,
        source_identifier=None,
        sheet_name=DEFAULT_SHEET_NAME,
        created_by_uuid=None,
        provision_users=False,
    ) -> MembershipSheetImportModel:
        import_record = MembershipSheetImportModel(
            uuid=str(uuid.uuid4()),
            source_type=source_type,
            source_identifier=source_identifier,
            sheet_name=sheet_name,
            status=IMPORT_STATUS_PROCESSING,
            started_at=datetime.utcnow(),
            created_by_uuid=created_by_uuid,
        )
        db.session.add(import_record)
        db.session.commit()

        report = {
            'ambiguous_rows': [],
            'skipped_rows': [],
            'blocked_rows': [],
            'status_changes': [],
        }

        try:
            rows = _read_csv_rows(csv_content)
            import_record.rows_total = max(len(rows) - 1, 0)

            header_idx, column_map = find_header_row(rows)
            if header_idx < 0:
                raise ValueError('No se encontró fila de encabezado con columnas MAT y CUOTA ADEUDADA.')

            data_rows = rows[header_idx + 1:]
            normalized_count = 0
            skipped_count = 0
            ambiguous_count = 0
            blocked_count = 0

            # Cargar todos los profesionales activos en memoria para lookup O(1)
            all_professionals = ProfessionalModel.query.filter(ProfessionalModel.deleted_at == None).all()
            prof_by_tuition = {}
            for prof in all_professionals:
                if prof.tuition:
                    key = prof.tuition.replace(' ', '').replace('.', '')
                    if key not in prof_by_tuition:
                        prof_by_tuition[key] = prof

            # Cargar todos los estados de cuota existentes en memoria para lookup O(1)
            all_existing_statuses = LawyerMembershipStatusModel.query.all()
            statuses_by_tuition = {s.tuition_normalized: s for s in all_existing_statuses}

            processed_tuitions_in_run = set()

            for offset, row in enumerate(data_rows):
                row_number = header_idx + offset + 2
                if not any(str(cell).strip() for cell in row):
                    continue

                raw_row = MembershipSheetRowRawModel(
                    uuid=str(uuid.uuid4()),
                    import_uuid=import_record.uuid,
                    row_number=row_number,
                    col_index=get_row_cell(row, 'index', column_map),
                    col_apellido=get_row_cell(row, 'apellido', column_map),
                    col_nombre=get_row_cell(row, 'nombre', column_map),
                    col_mat=get_row_cell(row, 'mat', column_map),
                    col_cuota_adeudada=get_row_cell(row, 'cuota', column_map),
                    col_sede=get_row_cell(row, 'sede', column_map),
                    col_observacion=get_row_cell(row, 'observacion', column_map),
                )
                raw_row.set_full_row(row)
                db.session.add(raw_row)
                import_record.rows_raw_saved += 1

                tuition_norm = normalize_tuition(raw_row.col_mat)
                if not tuition_norm:
                    raw_row.parse_status = 'skipped'
                    raw_row.parse_notes = 'invalid_or_missing_matricula'
                    skipped_count += 1
                    report['skipped_rows'].append({
                        'row_number': row_number,
                        'raw_mat': raw_row.col_mat,
                        'reason': 'invalid_or_missing_matricula',
                    })
                    continue

                if tuition_norm in processed_tuitions_in_run:
                    raw_row.parse_status = 'skipped'
                    raw_row.parse_notes = 'duplicate_matricula'
                    skipped_count += 1
                    report['skipped_rows'].append({
                        'row_number': row_number,
                        'raw_mat': raw_row.col_mat,
                        'reason': f'Matrícula duplicada ({tuition_norm}): ya procesada en otra fila',
                    })
                    continue

                processed_tuitions_in_run.add(tuition_norm)

                parsed = parse_quota_adeudada(
                    raw_row.col_cuota_adeudada,
                    reference_date=self.reference_date,
                )

                existing = statuses_by_tuition.get(tuition_norm)

                if existing and existing.status != parsed['status']:
                    report['status_changes'].append({
                        'tuition': tuition_norm,
                        'from': existing.status,
                        'to': parsed['status'],
                    })

                if parsed['status'] == MEMBERSHIP_STATUS_AMBIGUOUS:
                    raw_row.parse_status = 'ambiguous'
                    raw_row.parse_notes = parsed['parse_notes']
                    ambiguous_count += 1
                    report['ambiguous_rows'].append({
                        'row_number': row_number,
                        'tuition': tuition_norm,
                        'raw_quota': raw_row.col_cuota_adeudada,
                        'notes': parsed['parse_notes'],
                    })
                elif parsed['status'] == MEMBERSHIP_STATUS_BLOCKED:
                    raw_row.parse_status = 'blocked'
                    raw_row.parse_notes = parsed['parse_notes']
                    blocked_count += 1
                    report['blocked_rows'].append({
                        'row_number': row_number,
                        'tuition': tuition_norm,
                        'reason': parsed['blocked_reason'],
                    })
                else:
                    raw_row.parse_status = 'parsed'

                status_record = existing or LawyerMembershipStatusModel(
                    uuid=str(uuid.uuid4()),
                    tuition_normalized=tuition_norm,
                )

                status_record.tuition_display = tuition_display_from_raw(raw_row.col_mat)
                status_record.last_name = title_case_name(raw_row.col_apellido)
                status_record.first_name = title_case_name(raw_row.col_nombre)
                status_record.branch = get_row_cell(row, 'sede', column_map)
                status_record.status = parsed['status']
                status_record.first_unpaid_month = parsed['first_unpaid_month']
                status_record.blocked_reason = parsed['blocked_reason']
                status_record.raw_quota_text = raw_row.col_cuota_adeudada
                status_record.observation = raw_row.col_observacion
                status_record.parse_notes = parsed['parse_notes']
                status_record.last_import_uuid = import_record.uuid
                status_record.source_row_number = row_number
                status_record.synced_at = datetime.utcnow()
                
                # Inlined link_membership_status_uuids to use memory lookup
                professional = prof_by_tuition.get(tuition_norm)
                if professional:
                    status_record.uuid_professional = professional.uuid
                    status_record.uuid_user = professional.uuid_user

                raw_row.membership_status_uuid = status_record.uuid

                db.session.add(status_record)
                normalized_count += 1

            users_provisioned = 0
            if provision_users:
                users_provisioned = self._provision_lawyer_users(import_record.uuid)

            import_record.rows_normalized = normalized_count
            import_record.rows_skipped = skipped_count
            import_record.rows_ambiguous = ambiguous_count
            import_record.rows_blocked = blocked_count
            import_record.users_provisioned = users_provisioned
            import_record.status = IMPORT_STATUS_COMPLETED
            import_record.completed_at = datetime.utcnow()
            import_record.set_report(report)
            db.session.commit()
            return import_record

        except Exception as exc:
            db.session.rollback()
            import_record.status = IMPORT_STATUS_FAILED
            import_record.error_message = str(exc)
            import_record.completed_at = datetime.utcnow()
            import_record.set_report(report)
            db.session.commit()
            raise

    def sync_from_url(
        self,
        url: Optional[str] = None,
        *,
        created_by_uuid=None,
        provision_users=False,
    ) -> MembershipSheetImportModel:
        sheet_url = url or os.getenv('MEMBERSHIP_SHEET_CSV_URL', DEFAULT_MEMBERSHIP_SHEET_URL)
        csv_content = _fetch_csv_from_url(sheet_url)
        return self.sync_from_csv_content(
            csv_content,
            source_type=SOURCE_TYPE_GOOGLE_SHEETS_CSV,
            source_identifier=sheet_url,
            created_by_uuid=created_by_uuid,
            provision_users=provision_users,
        )

    def _provision_lawyer_users(self, import_uuid: str) -> int:
        default_password = os.getenv('LAWYER_DEFAULT_PASSWORD', 'Colejus2026')
        lawyer_profile = ProfileModel.query.filter_by(name='lawyer', deleted_at=None).first()
        if not lawyer_profile:
            return 0

        statuses = LawyerMembershipStatusModel.query.filter_by(last_import_uuid=import_uuid).all()
        
        # Pre-cargar usuarios activos
        all_users = UserModel.query.filter_by(deleted_at=None).all()
        users_by_email = {u.email.lower(): u for u in all_users if u.email}

        # Pre-cargar profesionales activos
        all_professionals = ProfessionalModel.query.filter(ProfessionalModel.deleted_at == None).all()
        prof_by_tuition = {}
        for p in all_professionals:
            if p.tuition:
                key = p.tuition.replace(' ', '').replace('.', '')
                if key not in prof_by_tuition:
                    prof_by_tuition[key] = p

        provisioned = 0

        # First pass: create all missing users and add lawyer profiles
        for status_record in statuses:
            if status_record.status == MEMBERSHIP_STATUS_AMBIGUOUS:
                continue

            tuition = status_record.tuition_normalized
            display_name = ' '.join(
                filter(None, [status_record.first_name, status_record.last_name])
            ).strip() or f'Matrícula {tuition}'

            # Buscar usuario por email (matrícula normalizada o formato display)
            user = users_by_email.get(tuition.lower())
            if not user and status_record.tuition_display:
                user = users_by_email.get(status_record.tuition_display.lower())

            if not user:
                user = UserModel()
                user.uuid = str(uuid.uuid4())
                user.email = tuition
                user.name = display_name
                user.password = generate_password_hash(default_password)
                user.must_change_password = True
                user.profiles = [lawyer_profile]
                db.session.add(user)
                users_by_email[tuition.lower()] = user
                provisioned += 1
            elif lawyer_profile not in user.profiles:
                user.profiles.append(lawyer_profile)

        # Flush to database so all user uuids are created and exist in the users table
        db.session.flush()

        # Second pass: link status records and professionals to the users
        for status_record in statuses:
            if status_record.status == MEMBERSHIP_STATUS_AMBIGUOUS:
                continue

            tuition = status_record.tuition_normalized
            user = users_by_email.get(tuition.lower())
            if not user and status_record.tuition_display:
                user = users_by_email.get(status_record.tuition_display.lower())

            if user:
                status_record.uuid_user = user.uuid
                professional = prof_by_tuition.get(tuition)
                if professional:
                    if not professional.uuid_user:
                        professional.uuid_user = user.uuid
                    status_record.uuid_professional = professional.uuid
                    db.session.add(professional)
                db.session.add(status_record)

        db.session.commit()
        return provisioned


def get_user_tuition_normalized(user) -> Optional[str]:
    """Obtiene la matrícula normalizada de un usuario."""
    from models import ProfessionalModel

    professional = ProfessionalModel.query.filter_by(
        uuid_user=user.uuid,
        deleted_at=None,
    ).first()
    if professional and professional.tuition:
        tuition = normalize_tuition(professional.tuition)
        if tuition:
            return tuition

    tuition = normalize_tuition(user.email)
    if tuition:
        return tuition

    return None


def get_membership_status_for_user(user) -> Optional[LawyerMembershipStatusModel]:
    record = LawyerMembershipStatusModel.query.filter_by(uuid_user=user.uuid).first()
    if record:
        return record

    professional = ProfessionalModel.query.filter_by(
        uuid_user=user.uuid,
        deleted_at=None,
    ).first()
    if professional:
        record = LawyerMembershipStatusModel.query.filter_by(
            uuid_professional=professional.uuid
        ).first()
        if record:
            return record

    tuition = get_user_tuition_normalized(user)
    if not tuition:
        return None
    return LawyerMembershipStatusModel.query.filter_by(tuition_normalized=tuition).first()


def can_user_book_meeting_room(user) -> bool:
    from models.config import SystemConfigModel

    try:
        bypass_record = SystemConfigModel.query.get('disable_membership_validation')
        if bypass_record and bypass_record.value == 'true':
            return True
    except Exception:
        pass

    if not user:
        return False

    is_lawyer = False
    is_admin_or_dev = False
    for profile in user.profiles:
        name_lower = profile.name.lower()
        if name_lower == 'lawyer':
            is_lawyer = True
        elif name_lower in ['admin', 'dev', 'administrador']:
            is_admin_or_dev = True

    if not is_lawyer or is_admin_or_dev:
        return True

    status_record = get_membership_status_for_user(user)
    if not status_record:
        return False

    return status_record.can_book_meeting_room()

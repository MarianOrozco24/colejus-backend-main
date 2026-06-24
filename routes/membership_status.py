from flask import Blueprint, request, jsonify

from utils.decorators import token_required
from services.membership_sync_service import (
    MembershipSyncService,
    get_membership_status_for_user,
    get_user_tuition_normalized,
    can_user_book_meeting_room,
)
from models import (
    MembershipSheetImportModel,
    LawyerMembershipStatusModel,
)
from models.membership_constants import (
    MEMBERSHIP_STATUS_AMBIGUOUS,
    MEMBERSHIP_STATUS_BLOCKED,
    MEMBERSHIP_STATUS_IN_DEBT,
)

membership_bp = Blueprint('membership', __name__)


def _is_dev_or_admin(user):
    for profile in user.profiles:
        if profile.name.lower() in ['dev', 'admin', 'administrador']:
            return True
    return False


@membership_bp.route('/membership/sync', methods=['POST'])
@token_required
def sync_membership():
    user = request.user
    if not _is_dev_or_admin(user):
        has_manage = any(
            access.name == 'manage_membership_sync'
            for profile in user.profiles
            for access in profile.accesses
        )
        if not has_manage:
            return jsonify({'error': 'Access denied'}), 403

    data = request.json or {}
    provision_users = bool(data.get('provision_users', False))

    try:
        service = MembershipSyncService()
        if data.get('csv_content'):
            import_record = service.sync_from_csv_content(
                data['csv_content'],
                source_identifier=data.get('source_identifier', 'api_upload'),
                created_by_uuid=user.uuid,
                provision_users=provision_users,
            )
        else:
            import_record = service.sync_from_url(
                url=data.get('source_url'),
                created_by_uuid=user.uuid,
                provision_users=provision_users,
            )

        return jsonify({
            'message': 'Sincronización completada.',
            'import': import_record.to_json(),
        }), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@membership_bp.route('/membership/sync/history', methods=['GET'])
@token_required
def sync_history():
    user = request.user
    if not _is_dev_or_admin(user):
        has_view = any(
            access.name == 'view_membership_sync'
            for profile in user.profiles
            for access in profile.accesses
        )
        if not has_view:
            return jsonify({'error': 'Access denied'}), 403

    imports = (
        MembershipSheetImportModel.query
        .order_by(MembershipSheetImportModel.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([record.to_json() for record in imports]), 200


@membership_bp.route('/membership/validate', methods=['GET'])
@token_required
def validate_membership():
    user = request.user
    tuition = get_user_tuition_normalized(user)
    status_record = get_membership_status_for_user(user)

    if not tuition:
        return jsonify({
            'status': 'not_found',
            'paid': False,
            'can_book_meeting_room': False,
            'tuition': None,
            'message': 'No se encontró matrícula asociada al usuario. Consulte con secretaría.',
        }), 200

    if not status_record:
        return jsonify({
            'status': 'not_in_sheet',
            'paid': False,
            'can_book_meeting_room': False,
            'tuition': tuition,
            'message': 'Su matrícula no figura en el listado de cuotas. Consulte con secretaría.',
        }), 200

    can_book = status_record.can_book_meeting_room()
    messages = {
        MEMBERSHIP_STATUS_IN_DEBT: (
            'Para reservar la sala de reuniones debe estar al día con la cuota del colegio. '
            'Acérquese a secretaría para regularizar su situación.'
        ),
        MEMBERSHIP_STATUS_BLOCKED: (
            'Su matrícula no está habilitada para reservas. Consulte con secretaría.'
        ),
        MEMBERSHIP_STATUS_AMBIGUOUS: (
            'No pudimos verificar su estado de cuota. Consulte con secretaría.'
        ),
    }

    response = {
        'status': status_record.status,
        'paid': can_book,
        'can_book_meeting_room': can_book,
        'tuition': tuition,
        'membership': status_record.to_json(),
        'message': messages.get(status_record.status) if not can_book else None,
    }
    return jsonify(response), 200


@membership_bp.route('/membership/status', methods=['GET'])
@token_required
def list_membership_status():
    user = request.user
    if not _is_dev_or_admin(user):
        has_view = any(
            access.name == 'view_membership_sync'
            for profile in user.profiles
            for access in profile.accesses
        )
        if not has_view:
            return jsonify({'error': 'Access denied'}), 403

    status_filter = request.args.get('status')
    query = LawyerMembershipStatusModel.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    records = query.order_by(LawyerMembershipStatusModel.tuition_normalized).limit(500).all()
    return jsonify([record.to_json() for record in records]), 200


@membership_bp.route('/membership/status/<tuition>', methods=['GET'])
@token_required
def get_membership_by_tuition(tuition):
    user = request.user
    if not _is_dev_or_admin(user):
        has_view = any(
            access.name == 'view_membership_sync'
            for profile in user.profiles
            for access in profile.accesses
        )
        if not has_view:
            return jsonify({'error': 'Access denied'}), 403

    from utils.tuition_utils import normalize_tuition
    tuition_norm = normalize_tuition(tuition)
    if not tuition_norm:
        return jsonify({'error': 'Matrícula inválida'}), 400

    record = LawyerMembershipStatusModel.query.filter_by(tuition_normalized=tuition_norm).first()
    if not record:
        return jsonify({'error': 'Matrícula no encontrada'}), 404

    return jsonify(record.to_json()), 200

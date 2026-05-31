from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from utils.decorators import token_required, access_required
from config.config import db
from models import LawyerPaymentModel, UserModel, MembershipFeeModel
from datetime import datetime, date

lawyer_payments_bp = Blueprint('lawyer_payments', __name__)

def get_months_range(start_date, end_date):
    months = []
    current = date(start_date.year, start_date.month, 1)
    target = date(end_date.year, end_date.month, 1)
    while current <= target:
        months.append(date(current.year, current.month, 1))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months

@lawyer_payments_bp.route('/lawyer_payments', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_lawyer_payments')
def create_payment():
    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    # User can specify uuid_user explicitly, or default to current user
    uuid_user = data.get('uuid_user')
    if not uuid_user:
        uuid_user = request.user.uuid

    description = data.get('description', 'Membresía')
    value = data.get('value')

    if value is None:
        return jsonify({'error': 'Missing field: value'}), 400

    try:
        value = float(value)
    except ValueError:
        return jsonify({'error': 'value must be a number'}), 400

    # Verify user exists
    user = UserModel.query.filter_by(uuid=uuid_user, deleted_at=None).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Custom date parsing if sent by frontend
    created_at_val = data.get('created_at')
    parsed_date = None
    if created_at_val:
        try:
            if len(created_at_val) == 7: # YYYY-MM
                parsed_date = datetime.strptime(created_at_val + "-01", "%Y-%m-%d")
            else: # YYYY-MM-DD
                parsed_date = datetime.strptime(created_at_val, "%Y-%m-%d")
        except Exception:
            try:
                parsed_date = datetime.fromisoformat(created_at_val.replace('Z', '+00:00'))
            except Exception:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM o YYYY-MM-DD'}), 400

    try:
        payment = LawyerPaymentModel(
            uuid_user=uuid_user,
            description=description,
            value=value
        )
        if parsed_date:
            payment.created_at = parsed_date
            
        db.session.add(payment)
        db.session.commit()
        return jsonify(payment.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@lawyer_payments_bp.route('/lawyer_payments', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_lawyer_payments')
def get_payments():
    try:
        # Check if the user is an admin/dev
        is_admin = False
        for profile in request.user.profiles:
            if profile.name.lower() in ['dev', 'admin']:
                is_admin = True
                break

        if is_admin:
            # Admins can view all payments or filter by uuid_user
            uuid_user = request.args.get('uuid_user')
            if uuid_user:
                payments = LawyerPaymentModel.query.filter_by(uuid_user=uuid_user).order_by(LawyerPaymentModel.created_at.desc()).all()
            else:
                payments = LawyerPaymentModel.query.order_by(LawyerPaymentModel.created_at.desc()).all()
        else:
            # Non-admins can only see their own payments
            payments = LawyerPaymentModel.query.filter_by(uuid_user=request.user.uuid).order_by(LawyerPaymentModel.created_at.desc()).all()

        return jsonify([p.to_json() for p in payments]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@lawyer_payments_bp.route('/membership_fees', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_collection_admin')
def set_membership_fee():

    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    value = data.get('value')
    if value is None:
        return jsonify({'error': 'value is required'}), 400
    try:
        value = float(value)
    except ValueError:
        return jsonify({'error': 'value must be a number'}), 400

    # Parse effective date and round to first day of the month
    try:
        dt = datetime.strptime(data.get('effective_date', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Default to first day of current month
        dt = date(datetime.utcnow().year, datetime.utcnow().month, 1)

    effective_date = date(dt.year, dt.month, 1)

    try:
        fee = MembershipFeeModel.query.filter_by(effective_date=effective_date).first()
        if fee:
            fee.value = value
        else:
            fee = MembershipFeeModel(effective_date=effective_date, value=value)
            db.session.add(fee)
        
        db.session.commit()
        return jsonify(fee.to_json()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@lawyer_payments_bp.route('/membership_fees', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_lawyer_payments')
def get_membership_fees():
    try:
        fees = MembershipFeeModel.query.order_by(MembershipFeeModel.effective_date.desc()).all()
        return jsonify([f.to_json() for f in fees]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@lawyer_payments_bp.route('/lawyer_payments/validate', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_lawyer_payments')
def validate_payment():
    try:
        uuid_user = request.args.get('uuid_user')
        
        is_admin = False
        for profile in request.user.profiles:
            if profile.name.lower() in ['dev', 'admin']:
                is_admin = True
                break

        if not is_admin or not uuid_user:
            uuid_user = request.user.uuid

        user = UserModel.query.filter_by(uuid=uuid_user, deleted_at=None).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        start_date = user.created_at.date() if user.created_at else datetime.utcnow().date()
        end_date = datetime.utcnow().date()

        months = get_months_range(start_date, end_date)

        total_owed = 0.0
        months_owed = 0
        for m in months:
            fee_record = MembershipFeeModel.query.filter(
                MembershipFeeModel.effective_date <= m
            ).order_by(MembershipFeeModel.effective_date.desc()).first()
            
            fee_val = fee_record.value if fee_record else 0.0
            total_owed += fee_val
            
            # If the cumulative paid up to now is less than cumulative owed up to this month
            # it means this month (and future months) is owed.
            # But wait, total_paid is the overall sum, so if total_paid is less than the total
            # owed up to month 'm', then that month 'm' is unpaid.
            # E.g. March (10k), April (20k), May (30k). If total_paid is 15k, then:
            # March: 15k >= 10k -> paid.
            # April: 15k < 20k -> unpaid (+1 month_owed)
            # May: 15k < 30k -> unpaid (+1 month_owed)
            # Total unpaid months = 2.
            # Note: total_paid is already queried, but we query it on line 201, let's query it before.

        total_paid = db.session.query(db.func.sum(LawyerPaymentModel.value)).filter(
            LawyerPaymentModel.uuid_user == user.uuid,
            LawyerPaymentModel.description.in_(['Membresía', 'Membresia'])
        ).scalar() or 0.0

        # Now compute months_owed
        cumulative_owed = 0.0
        for m in months:
            fee_record = MembershipFeeModel.query.filter(
                MembershipFeeModel.effective_date <= m
            ).order_by(MembershipFeeModel.effective_date.desc()).first()
            fee_val = fee_record.value if fee_record else 0.0
            cumulative_owed += fee_val
            if total_paid < cumulative_owed:
                months_owed += 1

        balance = total_paid - total_owed
        paid = (total_paid >= total_owed)

        response_data = {
            'status': 'ok' if paid else 'unpaid',
            'paid': paid,
            'balance': balance,
            'total_paid': total_paid,
            'total_owed': total_owed,
            'months_owed': months_owed,
            'user': {
                'uuid': user.uuid,
                'name': user.name,
                'email': user.email
            }
        }

        if paid:
            return jsonify(response_data), 200
        else:
            response_data['message'] = 'El abogado no ha abonado la membresía del mes en curso.'
            return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


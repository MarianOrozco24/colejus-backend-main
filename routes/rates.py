from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import RateModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required

rate_bp = Blueprint('rate_bp', __name__)

@rate_bp.route('/rates', methods=['POST'])
# @jwt_required()
# @token_required 
# @access_required('manage_rates')
def create_rate():
   data = request.json
   print(data)
   try:
       # Convert date strings to datetime objects
       start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
       
       # Handle optional end date
       end_date = None
       if data.get('end_date'):
           end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
       
       # Add parsed dates to data
       data['start_date'] = start_date
       data['end_date'] = end_date
       
       # Create and save new rate
       new_rate = RateModel.from_json(data)
       db.session.add(new_rate)
       db.session.commit()
       
       return jsonify({
           'message': 'Rate created successfully', 
           'uuid': new_rate.uuid
       }), 201
   
   except ValueError as e:
       return jsonify({'message': f'Invalid date format: {str(e)}'}), 400
   except Exception as e:
       db.session.rollback()
       return jsonify({'message': str(e)}), 400

@rate_bp.route('/rates', methods=['GET'])
# @jwt_required()
# @token_required 
# @access_required('view_rates')
def get_all_rates():
    rates = RateModel.query.filter(RateModel.deleted_at == None).all()
    rates_data = [rate.to_json() for rate in rates]
    return jsonify(rates_data), 200

@rate_bp.route('/rates/<uuid>', methods=['GET'])
# @jwt_required()
# @token_required 
# @access_required('view_rates')
def get_rate(uuid):
    rate = RateModel.query.filter_by(uuid=uuid, deleted_at=None).first()
    if rate:
        return jsonify(rate.to_json()), 200
    return jsonify({'message': 'Rate not found'}), 404

@rate_bp.route('/rates/<uuid>', methods=['PUT'])
# @jwt_required()
# @token_required 
# @access_required('manage_rates')
def update_rate(uuid):
    rate = RateModel.query.filter_by(uuid=uuid, deleted_at=None).first()
    if not rate:
        return jsonify({'message': 'Rate not found'}), 404

    data = request.json
    start_date = rate.start_date
    end_date = rate.end_date

    if 'start_date' in data:
        try:
            start_date = datetime.fromisoformat(data['start_date'])
        except ValueError:
            return jsonify({'message': 'Invalid start_date format'}), 400

    if 'end_date' in data:
        try:
            end_date = datetime.fromisoformat(data['end_date']) if data['end_date'] else None
        except ValueError:
            return jsonify({'message': 'Invalid end_date format'}), 400

    # Validate date range
    is_valid, error_message = RateModel.validate_date_range(start_date, end_date, exclude_uuid=uuid)
    if not is_valid:
        return jsonify({'message': error_message}), 400

    # Only update after validation passes
    if 'rate' in data:
        try:
            new_rate = round(float(data['rate']), 4)
            if new_rate <= 0:
                return jsonify({'message': 'Rate must be a positive number'}), 400
            rate.rate = new_rate
        except ValueError:
            return jsonify({'message': 'Invalid rate format'}), 400

    rate.start_date = start_date
    rate.end_date = end_date
    
    db.session.commit()
    return jsonify({'message': 'Rate updated successfully'}), 200

@rate_bp.route('/rates/<uuid>', methods=['DELETE'])
# @jwt_required()
# @token_required 
# @access_required('manage_rates')
def delete_rate(uuid):
    rate = RateModel.query.filter_by(uuid=uuid, deleted_at=None).first()
    if not rate:
        return jsonify({'message': 'Rate not found'}), 404

    # Don't allow deletion if it would create a gap
    if not rate.end_date:  # If this is the current active rate
        return jsonify({'message': 'Cannot delete the currently active rate'}), 400

    rate.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Rate deleted successfully'}), 200
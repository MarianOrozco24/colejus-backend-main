from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models.professional import ProfessionalModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

professional_bp = Blueprint('professional_bp', __name__)

import json

@professional_bp.route('/professionals', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_professionals')
def create_professional():
    try:
        data = request.json
        print("Received Data:", json.dumps(data, indent=4))  # Depuración

        required_fields = ['name', 'title', 'tuition', 'email', 'location']
        if not all(field in data for field in required_fields):
            return {'error': 'Name, title, tuition, email, location are required.'}, 400
        
        # Asegurar que 'address' y 'phone' están en el JSON recibido
        if 'address' not in data:
            return {'error': 'Address is required.'}, 400
        if 'phone' not in data:
            return {'error': 'Phone is required.'}, 400

        new_professional = ProfessionalModel.from_json(data)
        db.session.add(new_professional)
        db.session.commit()
        
        return jsonify({
            'message': 'Professional created successfully',
            'uuid': new_professional.uuid,
            'professional': new_professional.to_json()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@professional_bp.route('/professionals', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_professionals')
def get_all_professionals():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        query = ProfessionalModel.query.filter_by(deleted_at=None)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (ProfessionalModel.name.ilike(search_term)) |
                (ProfessionalModel.email.ilike(search_term)) |
                (ProfessionalModel.title.ilike(search_term))
            )
            
        pagination = query.order_by(ProfessionalModel.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        professionals = pagination.items
        
        return jsonify({
            'professionals': [prof.to_json() for prof in professionals],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@professional_bp.route('/public/professionals', methods=['GET'])
def get_public_professionals():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        letter = request.args.get('letter', '')
        locations = request.args.get('locations', '').split(',') if request.args.get('locations') else []
        
        query = ProfessionalModel.query.filter_by(deleted_at=None)
        
        # Apply letter filter if provided
        if letter:
            query = query.filter(ProfessionalModel.name.ilike(f'{letter}%'))
        
        # Apply location filter if provided
        if locations and locations[0]:  # Check if locations is not empty
            location_conditions = []
            for location in locations:
                if location.lower() == 'sanrafael':
                    location_conditions.append(ProfessionalModel.location.ilike('%San Rafael%'))
                elif location.lower() == 'alvear':
                    location_conditions.append(ProfessionalModel.location.ilike('%Alvear%'))
                elif location.lower() == 'malargue':
                    location_conditions.append(ProfessionalModel.location.ilike('%Malargüe%'))
            
            if location_conditions:
                query = query.filter(or_(*location_conditions))
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (ProfessionalModel.name.ilike(search_term)) |
                (ProfessionalModel.email.ilike(search_term)) |
                (ProfessionalModel.title.ilike(search_term))
            )
            
        pagination = query.order_by(ProfessionalModel.name.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        professionals = pagination.items
        
        return jsonify({
            'professionals': [prof.to_public_json() for prof in professionals],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@professional_bp.route('/professionals/<uuid>', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_professionals')
def get_professional(uuid):
    try:
        professional = ProfessionalModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        
        if not professional:
            return jsonify({'error': 'Professional not found'}), 404
            
        return jsonify(professional.to_json()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@professional_bp.route('/professionals/<uuid>', methods=['PUT'])
@jwt_required()
@token_required
@access_required('manage_professionals')
def update_professional(uuid):
    try:
        professional = ProfessionalModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        
        if not professional:
            return jsonify({'error': 'Professional not found'}), 404
            
        data = request.json
        if not data:
            return jsonify({'error': 'No update data provided'}), 400

        # Update fields if they exist in the request
        if 'name' in data:
            professional.name = data['name']
        if 'title' in data:
            professional.title = data['title']
        if 'tuition' in data:
            professional.tuition = data['tuition']
        if 'email' in data:
            professional.email = data['email']
        if 'location' in data:
            professional.location = data['location']
        if 'phone' in data:
            professional.phone = data['phone']
        if 'address' in data:
            professional.address = data['address']        
            
        professional.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Professional updated successfully',
            'professional': professional.to_json()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date format for tuition. Use YYYY-MM-DD'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@professional_bp.route('/professionals/<uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_professionals')
def delete_professional(uuid):
    try:
        professional = ProfessionalModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        
        if not professional:
            return jsonify({'error': 'Professional not found'}), 404
            
        professional.deleted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Professional deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
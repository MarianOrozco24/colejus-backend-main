from flask import Blueprint, request, jsonify
from config.config import db
from models.room import RoomModel
from utils.decorators import token_required, access_required
from datetime import datetime

rooms_bp = Blueprint('rooms', __name__)

@rooms_bp.route('/rooms', methods=['GET'])
def get_active_rooms():
    """Public/Private: returns all active rooms for booking."""
    try:
        rooms = RoomModel.query.filter(RoomModel.deleted_at.is_(None), RoomModel.is_active == True).order_by(RoomModel.id).all()
        return jsonify([r.to_json() for r in rooms]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms/all', methods=['GET'])
@token_required
@access_required('view_rooms')
def get_all_rooms():
    """Backoffice: returns all rooms (active and inactive)."""
    try:
        rooms = RoomModel.query.filter(RoomModel.deleted_at.is_(None)).order_by(RoomModel.id).all()
        return jsonify([r.to_json() for r in rooms]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms', methods=['POST'])
@token_required
@access_required('manage_rooms')
def create_room():
    """Create a new room."""
    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    required = ['name', 'capacity']
    missing = [f for f in required if f not in data or not str(data[f]).strip()]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    try:
        capacity_val = int(str(data['capacity']).strip())
        if capacity_val <= 0:
            return jsonify({'error': 'Capacity must be a positive integer'}), 400
    except ValueError:
        return jsonify({'error': 'Capacity must be a valid integer'}), 400

    try:
        room = RoomModel(
            name=data['name'].strip(),
            capacity=capacity_val,
            price=float(data.get('price', 0.0) or 0.0),
            image=data.get('image', '').strip() or None,
            description=data.get('description', '').strip() or None,
            is_active=data.get('is_active', True)
        )
        amenities = data.get('amenities')
        if amenities and isinstance(amenities, list):
            room.set_amenities(amenities)

        db.session.add(room)
        db.session.commit()
        return jsonify(room.to_json()), 201
    except ValueError:
        return jsonify({'error': 'Price must be a valid number'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms/<int:room_id>', methods=['PUT'])
@token_required
@access_required('manage_rooms')
def update_room(room_id):
    """Update an existing room."""
    room = RoomModel.query.filter(RoomModel.deleted_at.is_(None), RoomModel.id == room_id).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    try:
        if 'name' in data:
            room.name = data['name'].strip()
        if 'capacity' in data:
            try:
                capacity_val = int(str(data['capacity']).strip())
                if capacity_val <= 0:
                    return jsonify({'error': 'Capacity must be a positive integer'}), 400
                room.capacity = capacity_val
            except ValueError:
                return jsonify({'error': 'Capacity must be a valid integer'}), 400
        if 'price' in data:
            room.price = float(data['price']) if data['price'] else 0.0
        if 'image' in data:
            room.image = data['image'].strip() or None
        if 'description' in data:
            room.description = data['description'].strip() or None
        if 'amenities' in data:
            room.set_amenities(data['amenities'])
        if 'is_active' in data:
            room.is_active = bool(data['is_active'])

        db.session.commit()
        return jsonify(room.to_json()), 200
    except ValueError:
        return jsonify({'error': 'Price must be a valid number'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms/<int:room_id>', methods=['DELETE'])
@token_required
@access_required('manage_rooms')
def delete_room(room_id):
    """Soft-delete a room."""
    room = RoomModel.query.filter(RoomModel.deleted_at.is_(None), RoomModel.id == room_id).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    try:
        room.deleted_at = datetime.utcnow()
        room.is_active = False
        db.session.commit()
        return jsonify({'message': 'Room deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

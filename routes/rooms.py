from flask import Blueprint, request, jsonify
from config.config import db
from models.room import RoomModel
from utils.decorators import token_required, access_required
from datetime import datetime
import os
import uuid

rooms_bp = Blueprint('rooms', __name__)

@rooms_bp.route('/rooms', methods=['GET'])
def get_active_rooms():
    """Public/Private: returns active rooms filtered by room_type."""
    room_type = request.args.get('room_type')
    
    # Check if authorization token is provided
    token = request.headers.get('Authorization')
    user = None
    if token:
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request()
            email = get_jwt_identity()
            from models import UserModel
            user = UserModel.query.filter_by(email=email).first()
        except Exception:
            pass

    # If room_type is meeting, verify 'book_meeting_rooms' permission
    if room_type == 'meeting':
        if not user:
            return jsonify({'message': 'Authorization token required for meeting rooms'}), 401
        
        has_access = False
        for profile in user.profiles:
            if profile.name.lower() == 'dev':
                has_access = True
                break
            for access in profile.accesses:
                if access.name == 'book_meeting_rooms':
                    has_access = True
                    break
            if has_access:
                break
        if not has_access:
            return jsonify({'message': 'Access denied for meeting rooms'}), 403
            
        try:
            rooms = RoomModel.query.filter(
                RoomModel.deleted_at.is_(None),
                RoomModel.is_active == True,
                RoomModel.room_type == 'meeting'
            ).order_by(RoomModel.id).all()
            return jsonify([r.to_json() for r in rooms]), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Default to coworking if not specified (maintaining public access to coworking listings)
    target_type = room_type if room_type in ['coworking', 'meeting'] else 'coworking'
    try:
        rooms = RoomModel.query.filter(
            RoomModel.deleted_at.is_(None),
            RoomModel.is_active == True,
            RoomModel.room_type == target_type
        ).order_by(RoomModel.id).all()
        return jsonify([r.to_json() for r in rooms]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms/all', methods=['GET'])
@token_required
def get_all_rooms():
    """Backoffice: returns all rooms of a type (active and inactive)."""
    room_type = request.args.get('room_type', 'coworking').strip().lower()
    
    required_permission = 'view_rooms' if room_type == 'coworking' else 'view_meeting_rooms'
    has_access = False
    for profile in request.user.profiles:
        if profile.name.lower() == 'dev':
            has_access = True
            break
        for access in profile.accesses:
            if access.name == required_permission:
                has_access = True
                break
        if has_access:
            break
            
    if not has_access:
        return jsonify({'message': 'Access denied'}), 403

    try:
        rooms = RoomModel.query.filter(
            RoomModel.deleted_at.is_(None),
            RoomModel.room_type == room_type
        ).order_by(RoomModel.id).all()
        return jsonify([r.to_json() for r in rooms]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms', methods=['POST'])
@token_required
def create_room():
    """Create a new room."""
    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    required = ['name', 'capacity']
    missing = [f for f in required if f not in data or not str(data[f]).strip()]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    room_type = data.get('room_type', 'coworking').strip().lower()
    if room_type not in ['coworking', 'meeting']:
        return jsonify({'error': 'Invalid room type'}), 400

    required_permission = 'manage_rooms' if room_type == 'coworking' else 'manage_meeting_rooms'
    has_access = False
    for profile in request.user.profiles:
        if profile.name.lower() == 'dev':
            has_access = True
            break
        for access in profile.accesses:
            if access.name == required_permission:
                has_access = True
                break
        if has_access:
            break
            
    if not has_access:
        return jsonify({'message': 'Access denied'}), 403

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
            is_active=data.get('is_active', True),
            room_type=room_type
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
def update_room(room_id):
    """Update an existing room."""
    room = RoomModel.query.filter(RoomModel.deleted_at.is_(None), RoomModel.id == room_id).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    required_permission = 'manage_rooms' if room.room_type == 'coworking' else 'manage_meeting_rooms'
    has_access = False
    for profile in request.user.profiles:
        if profile.name.lower() == 'dev':
            has_access = True
            break
        for access in profile.accesses:
            if access.name == required_permission:
                has_access = True
                break
        if has_access:
            break
            
    if not has_access:
        return jsonify({'message': 'Access denied'}), 403

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
        if 'room_type' in data:
            room_type_val = data['room_type'].strip().lower()
            if room_type_val in ['coworking', 'meeting']:
                room.room_type = room_type_val

        db.session.commit()
        return jsonify(room.to_json()), 200
    except ValueError:
        return jsonify({'error': 'Price must be a valid number'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms/<int:room_id>', methods=['DELETE'])
@token_required
def delete_room(room_id):
    """Soft-delete a room."""
    room = RoomModel.query.filter(RoomModel.deleted_at.is_(None), RoomModel.id == room_id).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    required_permission = 'manage_rooms' if room.room_type == 'coworking' else 'manage_meeting_rooms'
    has_access = False
    for profile in request.user.profiles:
        if profile.name.lower() == 'dev':
            has_access = True
            break
        for access in profile.accesses:
            if access.name == required_permission:
                has_access = True
                break
        if has_access:
            break
            
    if not has_access:
        return jsonify({'message': 'Access denied'}), 403

    try:
        room.deleted_at = datetime.utcnow()
        room.is_active = False
        db.session.commit()
        return jsonify({'message': 'Room deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/rooms/upload-image', methods=['POST'])
@token_required
def upload_room_image():
    """Upload an image for a coworking or meeting room."""
    has_access = False
    for profile in request.user.profiles:
        if profile.name.lower() == 'dev':
            has_access = True
            break
        for access in profile.accesses:
            if access.name in ['manage_rooms', 'manage_meeting_rooms']:
                has_access = True
                break
        if has_access:
            break
            
    if not has_access:
        return jsonify({'message': 'Access denied'}), 403

    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext or ext[1:] not in allowed_extensions:
        return jsonify({'error': 'Allowed file types are: png, jpg, jpeg, gif, webp'}), 400

    try:
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_folder = os.path.join(backend_root, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        image_url = f"/static/uploads/{filename}"
        return jsonify({'image_url': image_url}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to save image: {str(e)}'}), 500

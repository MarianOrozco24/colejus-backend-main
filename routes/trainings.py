from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import TrainingModel, TagModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from sqlalchemy import desc

trainings_bp = Blueprint('trainings_bp', __name__)

@trainings_bp.route('/trainings', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_trainings')
def create_training():
    """Create a new training entry with tags."""
    data = request.json
    try:
        # Get tags from request and find them in DB
        tag_uuids = [tag.get('uuid') for tag in data.get('tags', [])]
        tags = TagModel.query.filter(
            TagModel.uuid.in_(tag_uuids), 
            TagModel.deleted_at == None
        ).all()

        # Create the training
        new_training = TrainingModel(
            title=data.get('title'),
            subtitle=data.get('subtitle'),
            date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.utcnow(),
            reading_duration=data.get('reading_duration'),
            content=data.get('content'),
            is_active=data.get('is_active', True),
            tags=tags
        )
        db.session.add(new_training)
        db.session.commit()
        return jsonify({'message': 'Training created successfully', 'uuid': new_training.uuid}), 201
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@trainings_bp.route('/trainings', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_trainings')
def get_all_trainings():
    """Get all trainings with pagination, ordering, and tags."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        tag_filter = request.args.get('tag', None)  # Optional tag filter

        query = TrainingModel.query.filter_by(deleted_at=None).order_by(desc(TrainingModel.created_at))

        # Apply tag filter if provided
        if tag_filter:
            query = query.join(TrainingModel.tags).filter(TagModel.name.ilike(f'%{tag_filter}%'))

        # Pagination
        paginated_trainings = query.paginate(page=page, per_page=per_page, error_out=False)

        # Prepare the response
        response = {
            "trainings": [training.to_json() for training in paginated_trainings.items],
            "total": paginated_trainings.total,
            "pages": paginated_trainings.pages,
            "current_page": paginated_trainings.page
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@trainings_bp.route('/trainings/<uuid>', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_trainings')
def get_training(uuid):
    """Get a single training entry by UUID with tags."""
    try:
        training = TrainingModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not training:
            return jsonify({'message': 'Training not found'}), 404
        return jsonify(training.to_json()), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@trainings_bp.route('/trainings/<uuid>', methods=['PUT'])
@jwt_required()
@token_required
@access_required('manage_trainings')
def update_training(uuid):
    """Update a training entry with tags."""
    data = request.json
    try:
        training = TrainingModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not training:
            return jsonify({'message': 'Training not found'}), 404

        # Update fields
        training.title = data.get('title', training.title)
        training.subtitle = data.get('subtitle', training.subtitle)
        training.date = datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else training.date
        training.reading_duration = data.get('reading_duration', training.reading_duration)
        training.content = data.get('content', training.content)
        training.is_active = data.get('is_active', training.is_active)

        # Update tags
        tag_uuids = [tag.get('uuid') for tag in data.get('tags', [])]
        new_tags = TagModel.query.filter(
            TagModel.uuid.in_(tag_uuids), 
            TagModel.deleted_at == None
        ).all()
        training.tags = new_tags

        db.session.commit()
        return jsonify({'message': 'Training updated successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@trainings_bp.route('/trainings/<uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_trainings')
def delete_training(uuid):
    """Soft delete a training entry."""
    try:
        training = TrainingModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not training:
            return jsonify({'message': 'Training not found'}), 404
        
        training.deleted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Training deleted successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@trainings_bp.route('/trainings/<uuid>/toggle', methods=['PATCH'])
@jwt_required()
@token_required
@access_required('manage_trainings')
def toggle_training_status(uuid):
    """Toggle the is_active status of a training entry."""
    try:
        training = TrainingModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not training:
            return jsonify({'message': 'Training not found'}), 404
        
        training.is_active = not training.is_active
        db.session.commit()
        
        return jsonify({
            'message': 'Training status updated successfully',
            'is_active': training.is_active
        }), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500
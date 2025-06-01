from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import TagModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from sqlalchemy import desc

# Blueprint for tags
tags_bp = Blueprint('tags_bp', __name__)

@tags_bp.route('/tags', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_tags')
def create_tag():
    """Create a new tag."""
    data = request.json
    try:
        new_tag = TagModel(
            name=data.get('name'),
            color=data.get('color')
        )
        db.session.add(new_tag)
        db.session.commit()
        return jsonify(new_tag.to_json()), 201
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/tags', methods=['GET'])
def get_all_tags():
    """Get all tags with pagination and ordering by latest."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = TagModel.query.filter_by(deleted_at=None).order_by(desc(TagModel.created_at))

        # Pagination
        paginated_tags = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Prepare the response
        response = {
            "tags": [tag.to_json() for tag in paginated_tags.items],
            "total": paginated_tags.total,
            "pages": paginated_tags.pages,
            "current_page": paginated_tags.page
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500
    
@tags_bp.route('/tags/get', methods=['POST'])
def get_all_tags_with_name():
    """Get all tags with pagination, ordering by latest, and optional search parameter."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        body = request.get_json() or {}
        search_param = body.get('parameter', '').strip()

        query = TagModel.query.filter_by(deleted_at=None)
        
        if search_param:
            query = query.filter(TagModel.name.ilike(f'%{search_param}%'))
        
        query = query.order_by(desc(TagModel.created_at))

        paginated_tags = query.paginate(page=page, per_page=per_page, error_out=False)
        
        response = {
            "tags": [tag.to_json() for tag in paginated_tags.items],
            "total": paginated_tags.total,
            "pages": paginated_tags.pages,
            "current_page": paginated_tags.page
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/tags/<uuid>', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_tags')
def get_tag(uuid):
    """Get a single tag by UUID."""
    try:
        tag = TagModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not tag:
            return jsonify({'message': 'Tag not found'}), 404
        return jsonify(tag.to_json()), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/tags/<uuid>', methods=['PUT'])
@jwt_required()
@token_required
@access_required('manage_tags')
def update_tag(uuid):
    """Update a tag."""
    data = request.json
    try:
        tag = TagModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not tag:
            return jsonify({'message': 'Tag not found'}), 404

        tag.name = data.get('name', tag.name)
        tag.color = data.get('color', tag.color)
        db.session.commit()

        return jsonify({'message': 'Tag updated successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/tags/<uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_tags')
def delete_tag(uuid):
    """Soft delete a tag."""
    try:
        tag = TagModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not tag:
            return jsonify({'message': 'Tag not found'}), 404

        tag.deleted_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Tag deleted successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500
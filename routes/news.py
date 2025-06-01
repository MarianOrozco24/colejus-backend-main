from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import NewsModel, TagModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from sqlalchemy import desc

news_bp = Blueprint('news_bp', __name__)

@news_bp.route('/news', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_news')
def create_news():
    """Create a new news entry."""
    data = request.json
    try:
        # Get tags from request and find them in DB
        tag_uuids = [tag.get('uuid') for tag in data.get('tags', [])]
        tags = TagModel.query.filter(
            TagModel.uuid.in_(tag_uuids), 
            TagModel.deleted_at == None
        ).all()

        new_news = NewsModel(
            title=data.get('title'),
            subtitle=data.get('subtitle'),
            date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.utcnow(),
            reading_duration=data.get('reading_duration'),
            content=data.get('content'),
            is_active=data.get('is_active', True),
            tags=tags
        )
        db.session.add(new_news)
        db.session.commit()
        return jsonify({'message': 'News created successfully', 'uuid': new_news.uuid}), 201
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@news_bp.route('/news', methods=['GET'])
def get_all_news():
    """Get all news with pagination and ordering by latest."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        tag_filter = request.args.get('tag', None)  # Optional tag filter

        query = NewsModel.query.filter_by(deleted_at=None).order_by(desc(NewsModel.created_at))

        if tag_filter:
            query = query.join(NewsModel.tags).filter(TagModel.name.ilike(f'%{tag_filter}%'))

        # Pagination
        paginated_news = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Prepare the response
        response = {
            "news": [news.to_json() for news in paginated_news.items],
            "total": paginated_news.total,
            "pages": paginated_news.pages,
            "current_page": paginated_news.page
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@news_bp.route('/news/<uuid>', methods=['GET'])
def get_news(uuid):
    """Get a single news entry by UUID."""
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news:
            return jsonify({'message': 'News not found'}), 404
        return jsonify(news.to_json()), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@news_bp.route('/news/<uuid>', methods=['PUT'])
@jwt_required()
@token_required
@access_required('manage_news')
def update_news(uuid):
    """Update a news entry."""
    data = request.json
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news:
            return jsonify({'message': 'News not found'}), 404
        
        news.title = data.get('title', news.title)
        news.subtitle = data.get('subtitle', news.subtitle)
        news.date = datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else news.date
        news.reading_duration = data.get('reading_duration', news.reading_duration)
        news.content = data.get('content', news.content)
        news.is_active = data.get('is_active', news.is_active)
        
        tag_uuids = [tag.get('uuid') for tag in data.get('tags', [])]
        new_tags = TagModel.query.filter(
            TagModel.uuid.in_(tag_uuids), 
            TagModel.deleted_at == None
        ).all()
        news.tags = new_tags 
        
        db.session.commit()
        return jsonify({'message': 'News updated successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@news_bp.route('/news/<uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_news')
def delete_news(uuid):
    """Soft delete a news entry."""
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news:
            return jsonify({'message': 'News not found'}), 404
        
        news.deleted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'News deleted successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@news_bp.route('/news/<uuid>/toggle', methods=['PATCH'])
@jwt_required()
@token_required
@access_required('manage_news')
def toggle_news_status(uuid):
    """Toggle the is_active status of a news entry."""
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news:
            return jsonify({'message': 'News not found'}), 404
        
        news.is_active = not news.is_active
        db.session.commit()
        
        return jsonify({
            'message': 'News status updated successfully',
            'is_active': news.is_active
        }), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500
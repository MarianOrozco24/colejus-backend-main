import os
import uuid as uuid_lib
import json
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
    try:
        # Check if the request is JSON or multipart/form-data
        if request.is_json:
            data = request.json
            title = data.get('title')
            subtitle = data.get('subtitle')
            date_val = datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.utcnow()
            reading_duration = data.get('reading_duration')
            content = data.get('content')
            is_active = data.get('is_active', True)
            
            tag_uuids = []
            tags_input = data.get('tags', [])
            if isinstance(tags_input, list):
                tag_uuids = [tag.get('uuid') for tag in tags_input if isinstance(tag, dict) and tag.get('uuid')]
            elif isinstance(tags_input, str):
                try:
                    loaded_tags = json.loads(tags_input)
                    tag_uuids = [tag.get('uuid') for tag in loaded_tags if isinstance(tag, dict) and tag.get('uuid')]
                except Exception:
                    pass
            
            image_path_val = data.get('image_path')
        else:
            # multipart/form-data
            title = request.form.get('title')
            subtitle = request.form.get('subtitle')
            date_str = request.form.get('date')
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.utcnow()
            
            reading_dur_str = request.form.get('reading_duration')
            reading_duration = int(reading_dur_str) if reading_dur_str else None
            
            content = request.form.get('content')
            
            is_active_str = request.form.get('is_active', 'true')
            is_active = is_active_str.lower() in ('true', '1')
            
            tag_uuids = []
            tags_str = request.form.get('tags')
            if tags_str:
                try:
                    loaded_tags = json.loads(tags_str)
                    if isinstance(loaded_tags, list):
                        tag_uuids = [tag.get('uuid') for tag in loaded_tags if isinstance(tag, dict) and tag.get('uuid')]
                except Exception:
                    tag_uuids = [t.strip() for t in tags_str.split(',') if t.strip()]
            
            image_path_val = None

        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                ext = os.path.splitext(file.filename)[1].lower()
                if not ext or ext[1:] not in allowed_extensions:
                    return jsonify({'error': 'Allowed file types are: png, jpg, jpeg, gif, webp'}), 400
                
                backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                upload_folder = os.path.join(backend_root, 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                filename = f"{uuid_lib.uuid4().hex}{ext}"
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                image_path_val = f"/uploads/{filename}"

        # Get tags from DB
        tags = []
        if tag_uuids:
            tags = TagModel.query.filter(
                TagModel.uuid.in_(tag_uuids), 
                TagModel.deleted_at == None
            ).all()

        new_news = NewsModel(
            title=title,
            subtitle=subtitle,
            date=date_val,
            reading_duration=reading_duration,
            content=content,
            is_active=is_active,
            image_path=image_path_val,
            tags=tags
        )
        db.session.add(new_news)
        db.session.commit()
        return jsonify({
            'message': 'News created successfully',
            'uuid': new_news.uuid,
            'news': new_news.to_json()
        }), 201
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

        active_only = request.args.get('active_only', 'false').lower() in ('true', '1')

        query = NewsModel.query.filter_by(deleted_at=None).order_by(desc(NewsModel.created_at))

        if active_only:
            query = query.filter(NewsModel.is_active.is_(True))

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
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news:
            return jsonify({'message': 'News not found'}), 404
        
        # Check if the request is JSON or multipart/form-data
        if request.is_json:
            data = request.json
            news.title = data.get('title', news.title)
            news.subtitle = data.get('subtitle', news.subtitle)
            if 'date' in data and data['date']:
                news.date = datetime.strptime(data['date'], '%Y-%m-%d')
            news.reading_duration = data.get('reading_duration', news.reading_duration)
            news.content = data.get('content', news.content)
            if 'is_active' in data:
                news.is_active = data['is_active']
            if 'image_path' in data:
                # Optionally allow clearing the image path via JSON
                news.image_path = data['image_path']
            
            tags_input = data.get('tags')
        else:
            # multipart/form-data
            if 'title' in request.form:
                news.title = request.form.get('title')
            if 'subtitle' in request.form:
                news.subtitle = request.form.get('subtitle')
            if 'date' in request.form and request.form.get('date'):
                news.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            if 'reading_duration' in request.form:
                reading_dur_str = request.form.get('reading_duration')
                news.reading_duration = int(reading_dur_str) if reading_dur_str else news.reading_duration
            if 'content' in request.form:
                news.content = request.form.get('content')
            if 'is_active' in request.form:
                is_active_str = request.form.get('is_active')
                news.is_active = is_active_str.lower() in ('true', '1')
            if 'image_path' in request.form:
                news.image_path = request.form.get('image_path') or None

            tags_input = request.form.get('tags')

        # Handle tag update if provided
        if tags_input is not None:
            tag_uuids = []
            if isinstance(tags_input, list):
                tag_uuids = [tag.get('uuid') for tag in tags_input if isinstance(tag, dict) and tag.get('uuid')]
            elif isinstance(tags_input, str):
                try:
                    loaded_tags = json.loads(tags_input)
                    if isinstance(loaded_tags, list):
                        tag_uuids = [tag.get('uuid') for tag in loaded_tags if isinstance(tag, dict) and tag.get('uuid')]
                    else:
                        tag_uuids = [t.strip() for t in tags_input.split(',') if t.strip()]
                except Exception:
                    tag_uuids = [t.strip() for t in tags_input.split(',') if t.strip()]
            
            new_tags = TagModel.query.filter(
                TagModel.uuid.in_(tag_uuids), 
                TagModel.deleted_at == None
            ).all()
            news.tags = new_tags

        # Handle image file upload update
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                ext = os.path.splitext(file.filename)[1].lower()
                if not ext or ext[1:] not in allowed_extensions:
                    return jsonify({'error': 'Allowed file types are: png, jpg, jpeg, gif, webp'}), 400
                
                backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                upload_folder = os.path.join(backend_root, 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                filename = f"{uuid_lib.uuid4().hex}{ext}"
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # Delete old file if exists
                if news.image_path and news.image_path.startswith('/uploads/'):
                    old_filename = news.image_path.split('/')[-1]
                    old_filepath = os.path.join(upload_folder, old_filename)
                    if os.path.exists(old_filepath):
                        try:
                            os.remove(old_filepath)
                        except Exception as e:
                            print(f"Error removing old image: {e}")
                
                news.image_path = f"/uploads/{filename}"
        
        db.session.commit()
        return jsonify({
            'message': 'News updated successfully',
            'news': news.to_json()
        }), 200
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
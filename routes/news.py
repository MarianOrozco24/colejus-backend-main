import os
import uuid as uuid_lib
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import NewsModel, TagModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from sqlalchemy import desc, asc, func

news_bp = Blueprint('news_bp', __name__)

MAX_FEATURED_NEWS = 8


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 'yes')


def _count_featured_active(exclude_uuid=None):
    query = NewsModel.query.filter_by(
        deleted_at=None, is_featured=True, is_active=True
    )
    if exclude_uuid:
        query = query.filter(NewsModel.uuid != exclude_uuid)
    return query.count()


def _next_featured_order():
    max_order = db.session.query(func.max(NewsModel.featured_order)).filter(
        NewsModel.deleted_at.is_(None),
        NewsModel.is_featured.is_(True),
        NewsModel.is_active.is_(True),
    ).scalar()
    return (max_order or 0) + 1


def _validate_featured_assignment(is_featured, is_active, exclude_uuid=None):
    if not is_featured:
        return None
    if not is_active:
        return 'Solo las noticias publicadas pueden marcarse como destacadas.'
    if _count_featured_active(exclude_uuid=exclude_uuid) >= MAX_FEATURED_NEWS:
        return (
            f'Ya hay {MAX_FEATURED_NEWS} noticias destacadas. '
            'Quitá una antes de agregar otra.'
        )
    return None


def _apply_featured_fields(news, is_featured, featured_order=None, exclude_uuid=None):
    """Apply featured flags with validation. Returns error message or None."""
    target_active = news.is_active

    if is_featured is not None:
        error = _validate_featured_assignment(is_featured, target_active, exclude_uuid=exclude_uuid)
        if error:
            return error
        news.is_featured = is_featured
        if is_featured:
            if featured_order is not None:
                news.featured_order = featured_order
            elif news.featured_order is None:
                news.featured_order = _next_featured_order()
        else:
            news.featured_order = None
    elif featured_order is not None and news.is_featured:
        news.featured_order = featured_order

    return None


def _parse_featured_from_payload(data, form_mode=False):
    if form_mode:
        is_featured_raw = request.form.get('is_featured')
        featured_order_raw = request.form.get('featured_order')
    else:
        is_featured_raw = data.get('is_featured') if data else None
        featured_order_raw = data.get('featured_order') if data else None

    is_featured = None
    if is_featured_raw is not None:
        is_featured = _parse_bool(is_featured_raw)

    featured_order = None
    if featured_order_raw is not None and str(featured_order_raw).strip() != '':
        featured_order = int(featured_order_raw)

    return is_featured, featured_order


def _save_uploaded_image(file):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext or ext[1:] not in allowed_extensions:
        return None, 'Allowed file types are: png, jpg, jpeg, gif, webp'

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_folder = os.path.join(backend_root, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"{uuid_lib.uuid4().hex}{ext}"
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    return f"/uploads/{filename}", None


@news_bp.route('/news', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_news')
def create_news():
    """Create a new news entry."""
    try:
        if request.is_json:
            data = request.json
            title = data.get('title')
            subtitle = data.get('subtitle')
            date_val = datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.utcnow()
            reading_duration = data.get('reading_duration')
            content = data.get('content')
            is_active = data.get('is_active', True)
            is_featured, featured_order = _parse_featured_from_payload(data)

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
            title = request.form.get('title')
            subtitle = request.form.get('subtitle')
            date_str = request.form.get('date')
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.utcnow()

            reading_dur_str = request.form.get('reading_duration')
            reading_duration = int(reading_dur_str) if reading_dur_str else None

            content = request.form.get('content')
            is_active = _parse_bool(request.form.get('is_active', 'true'), default=True)
            is_featured, featured_order = _parse_featured_from_payload(None, form_mode=True)

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

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_path_val, upload_error = _save_uploaded_image(file)
                if upload_error:
                    return jsonify({'error': upload_error}), 400

        tags = []
        if tag_uuids:
            tags = TagModel.query.filter(
                TagModel.uuid.in_(tag_uuids),
                TagModel.deleted_at == None
            ).all()

        if is_featured:
            error = _validate_featured_assignment(is_featured, is_active)
            if error:
                return jsonify({'error': error}), 400

        new_news = NewsModel(
            title=title,
            subtitle=subtitle,
            date=date_val,
            reading_duration=reading_duration,
            content=content,
            is_active=is_active,
            is_featured=bool(is_featured),
            featured_order=featured_order if is_featured else None,
            image_path=image_path_val,
            tags=tags
        )

        if new_news.is_featured and new_news.featured_order is None:
            new_news.featured_order = _next_featured_order()

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
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        tag_filter = request.args.get('tag', None)

        active_only = request.args.get('active_only', 'false').lower() in ('true', '1')
        featured_only = request.args.get('featured_only', 'false').lower() in ('true', '1')
        exclude_featured = request.args.get('exclude_featured', 'false').lower() in ('true', '1')

        query = NewsModel.query.filter_by(deleted_at=None)

        if featured_only:
            query = query.filter(
                NewsModel.is_featured.is_(True),
                NewsModel.is_active.is_(True),
            ).order_by(
                asc(NewsModel.featured_order),
                desc(NewsModel.created_at),
            )
        else:
            query = query.order_by(desc(NewsModel.created_at))
            if active_only:
                query = query.filter(NewsModel.is_active.is_(True))
            if exclude_featured:
                query = query.filter(NewsModel.is_featured.is_(False))

        if tag_filter:
            query = query.join(NewsModel.tags).filter(TagModel.name.ilike(f'%{tag_filter}%'))

        paginated_news = query.paginate(page=page, per_page=per_page, error_out=False)

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

        is_featured_input = None
        featured_order_input = None

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
                if not news.is_active:
                    news.is_featured = False
                    news.featured_order = None
            if 'image_path' in data:
                news.image_path = data['image_path']

            is_featured_input, featured_order_input = _parse_featured_from_payload(data)
            tags_input = data.get('tags')
        else:
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
                news.is_active = _parse_bool(request.form.get('is_active'))
                if not news.is_active:
                    news.is_featured = False
                    news.featured_order = None
            if 'image_path' in request.form:
                news.image_path = request.form.get('image_path') or None

            is_featured_input, featured_order_input = _parse_featured_from_payload(None, form_mode=True)
            tags_input = request.form.get('tags')

        if is_featured_input is not None or featured_order_input is not None:
            error = _apply_featured_fields(
                news,
                is_featured_input,
                featured_order_input,
                exclude_uuid=uuid,
            )
            if error:
                return jsonify({'error': error}), 400

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

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                new_path, upload_error = _save_uploaded_image(file)
                if upload_error:
                    return jsonify({'error': upload_error}), 400

                if news.image_path and news.image_path.startswith('/uploads/'):
                    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    upload_folder = os.path.join(backend_root, 'uploads')
                    old_filename = news.image_path.split('/')[-1]
                    old_filepath = os.path.join(upload_folder, old_filename)
                    if os.path.exists(old_filepath):
                        try:
                            os.remove(old_filepath)
                        except Exception as e:
                            print(f"Error removing old image: {e}")

                news.image_path = new_path

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
        if not news.is_active:
            news.is_featured = False
            news.featured_order = None

        db.session.commit()

        return jsonify({
            'message': 'News status updated successfully',
            'is_active': news.is_active,
            'is_featured': news.is_featured,
        }), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@news_bp.route('/news/<uuid>/toggle-featured', methods=['PATCH'])
@jwt_required()
@token_required
@access_required('manage_news')
def toggle_news_featured(uuid):
    """Toggle the is_featured status of a news entry."""
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news:
            return jsonify({'message': 'News not found'}), 404

        new_featured = not news.is_featured

        if new_featured:
            error = _validate_featured_assignment(True, news.is_active, exclude_uuid=uuid)
            if error:
                return jsonify({'error': error}), 400
            news.is_featured = True
            news.featured_order = _next_featured_order()
        else:
            news.is_featured = False
            news.featured_order = None

        db.session.commit()

        return jsonify({
            'message': 'Featured status updated successfully',
            'is_featured': news.is_featured,
            'featured_order': news.featured_order,
        }), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500


@news_bp.route('/news/<uuid>/featured-order', methods=['PATCH'])
@jwt_required()
@token_required
@access_required('manage_news')
def reorder_featured_news(uuid):
    """Move a featured news item up or down in display order."""
    try:
        news = NewsModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not news or not news.is_featured:
            return jsonify({'message': 'Featured news not found'}), 404

        data = request.json or {}
        direction = data.get('direction')

        featured_list = NewsModel.query.filter_by(
            deleted_at=None, is_featured=True, is_active=True
        ).order_by(
            asc(NewsModel.featured_order),
            desc(NewsModel.created_at),
        ).all()

        index = next((i for i, item in enumerate(featured_list) if item.uuid == uuid), None)
        if index is None:
            return jsonify({'message': 'Featured news not found'}), 404

        if direction == 'up' and index > 0:
            swap_with = featured_list[index - 1]
        elif direction == 'down' and index < len(featured_list) - 1:
            swap_with = featured_list[index + 1]
        else:
            return jsonify({'message': 'Cannot move in that direction'}), 400

        current_order = news.featured_order
        news.featured_order = swap_with.featured_order
        swap_with.featured_order = current_order

        db.session.commit()

        return jsonify({'message': 'Featured order updated successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

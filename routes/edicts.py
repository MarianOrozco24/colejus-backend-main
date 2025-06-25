from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import EdictModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from sqlalchemy import desc
import os


edicts_bp = Blueprint('edicts_bp', __name__)

@edicts_bp.route('/edicts', methods=['POST'])
# @jwt_required()
# @token_required
# @access_required('manage_edicts')
def create_edict():
    """Create a new edict entry with tags."""
    data = request.json
    # Parsear fecha de publicación programada o usar fecha actual si no viene
    scheduled_date = datetime.strptime(data.get('scheduled_date'), '%Y-%m-%d').date() if data.get('scheduled_date') else datetime.utcnow().date()

    try:
        # Crear el edicto
        new_edict = EdictModel(
            title=data.get('title'),
            subtitle=data.get('subtitle'),
            date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.utcnow(),
            content=data.get('content'),
        
            is_active=data.get('is_active', True),
            scheduled_date=scheduled_date 
        )
        db.session.add(new_edict)
        db.session.commit()

        # Obtener la URL del frontend de la variable de entorno o fallback a request.host_url
        frontend_base_url = os.getenv('FRONTEND_URL', request.host_url.rstrip('/'))

        # Generar la URL pública con la estructura del frontend
        public_url = f"{frontend_base_url}/edictos/{new_edict.uuid}"

        return jsonify({'message': 'Edicto creado exitosamente', 'uuid': new_edict.uuid, 'public_url': public_url}), 201

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

from datetime import datetime
from sqlalchemy import desc, or_

@edicts_bp.route('/edicts', methods=['GET'])
def get_all_edicts():
    """Get all edicts with optional scheduling filter, search and pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '') # Obtenemos los datos del filtro de busqueda
        include_scheduled = request.args.get('include_scheduled', 'false').lower() == 'true'

        search_term = request.args.get('search', '', type=str).strip()
        initial_date = request.args.get('initial_date', type=str)
        final_date = request.args.get('final_date', type=str)

        query = EdictModel.query.filter(EdictModel.deleted_at == None)

        if search: # Condicion de busqueda
            search_term = f"%{search}%"
            query = EdictModel.query.filter(
                EdictModel.title.ilike(search_term)
            )

        # ✅ Filtrar edictos programados si no se incluye el flag
        if not include_scheduled:
            today = datetime.utcnow().date()
            query = query.filter(
                or_(
                    EdictModel.scheduled_date == None,
                    EdictModel.scheduled_date <= today
                )
            )

        # 🔍 Filtro de búsqueda en título o contenido
        if search_term:
            like_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    EdictModel.title.ilike(like_pattern),
                    EdictModel.content.ilike(like_pattern)
                )
            )

        # 📅 Filtro por fechas de creación (created_at)
        if initial_date:
            try:
                initial = datetime.strptime(initial_date, "%Y-%m-%d")
                query = query.filter(EdictModel.created_at >= initial)
            except ValueError:
                pass

        if final_date:
            try:
                final = datetime.strptime(final_date, "%Y-%m-%d")
                final = final.replace(hour=23, minute=59, second=59)  # 👈 importante
                query = query.filter(EdictModel.created_at <= final)
            except ValueError:
                pass


        # Orden y paginación
        query = query.order_by(desc(EdictModel.created_at))
        paginated_edicts = query.paginate(page=page, per_page=per_page, error_out=False)

        response = {
            "edicts": [edict.to_json() for edict in paginated_edicts.items],
            "total": paginated_edicts.total,
            "pages": paginated_edicts.pages,
            "current_page": paginated_edicts.page
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@edicts_bp.route('/edicts/<uuid>', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_edicts')
def get_edict(uuid):
    """Get a single edict entry by UUID with tags."""
    try:
        edict = EdictModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not edict:
            return jsonify({'message': 'edict not found'}), 404
        return jsonify(edict.to_json()), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@edicts_bp.route('/public/edicts/<uuid>', methods=['GET'])
def get_public_edict(uuid):
    """Get a single public edict entry by UUID."""
    try:
        edict = EdictModel.query.filter_by(
            uuid=uuid, 
            deleted_at=None,
            is_active=True  # Only show active edicts
        ).first()
        
        if not edict:
            return jsonify({'message': 'Edicto no encontrado'}), 404
            
        return jsonify(edict.to_json()), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@edicts_bp.route('/edicts/<uuid>', methods=['PUT'])
@jwt_required()
@token_required
@access_required('manage_edicts')
def update_edict(uuid):
    """Update a edict entry with tags."""
    data = request.json
    try:
        edict = EdictModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not edict:
            return jsonify({'message': 'edict not found'}), 404

        # Update fields
        edict.title = data.get('title', edict.title)
        edict.subtitle = data.get('subtitle', edict.subtitle)
        edict.date = datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else edict.date
        edict.scheduled_date = datetime.strptime(data.get('scheduled_date'), '%Y-%m-%d') if data.get('scheduled_date') else None
        edict.content = data.get('content', edict.content)
        edict.is_active = data.get('is_active', edict.is_active)

        db.session.commit()
        return jsonify({'message': 'edict updated successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500

@edicts_bp.route('/edicts/<uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_edicts')
def delete_edict(uuid):
    """Soft delete a edict entry."""
    try:
        edict = EdictModel.query.filter_by(uuid=uuid, deleted_at=None).first()
        if not edict:
            return jsonify({'message': 'edict not found'}), 404
        
        edict.deleted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'edict deleted successfully'}), 200
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'error': str(e)}), 500
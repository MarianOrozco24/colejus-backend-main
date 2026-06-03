from flask import Blueprint, Response, jsonify, request
import psutil
import time
from datetime import datetime
from utils.logging_config import get_log_stream, get_recent_logs
from models.ip_manager import IPRegistry
from models import UserModel, ProfileModel, ProfessionalModel
from config.config import db
import os
from flask import current_app
from werkzeug.security import generate_password_hash
from models.access import AccessModel
from sqlalchemy.orm import subqueryload
from flask_jwt_extended import jwt_required
from utils.decorators import token_required, access_required

dev_bp = Blueprint('dev', __name__)

@dev_bp.route('/dev/logs')
@jwt_required()
@token_required
@access_required('manage_dev')
def stream_logs():
    return Response(get_log_stream(), mimetype='text/event-stream')

@dev_bp.route('/dev/logs/recent')
@jwt_required()
@token_required
@access_required('manage_dev')
def get_recent_logs_api():
    return jsonify(get_recent_logs())

@dev_bp.route('/dev/stats')
@jwt_required()
@token_required
@access_required('manage_dev')
def get_stats():
    stats = {
        'cpu_usage': psutil.cpu_percent(interval=None),
        'memory_usage': psutil.virtual_memory().percent,
        'timestamp': time.time()
    }
    return jsonify(stats)

from utils.ip_manager_cache import ip_manager_cache

@dev_bp.route('/dev/ips', methods=['GET'])
@jwt_required()
@token_required
@access_required('manage_dev')
def list_ips():
    # Retrieve from cache to get the most up-to-date stats without hitting DB
    ips = []
    for info in ip_manager_cache.ip_cache.values():
        rec = dict(info['record'])
        if isinstance(rec['last_seen'], datetime):
            rec['last_seen'] = rec['last_seen'].isoformat()
        if 'last_minute_reset' in rec: del rec['last_minute_reset']
        if 'last_month_reset' in rec: del rec['last_month_reset']
        ips.append(rec)
    # Sort by last_seen
    ips.sort(key=lambda x: x['last_seen'], reverse=True)
    return jsonify(ips)

@dev_bp.route('/dev/ips/block', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_dev')
def block_ip():
    data = request.get_json()
    ip_to_block = data.get('ip')
    if not ip_to_block:
        return jsonify({'error': 'IP is required'}), 400
    
    ip_manager_cache.block_ip(ip_to_block)
    return jsonify({'message': f'IP {ip_to_block} blocked successfully'})

@dev_bp.route('/dev/ips/unblock', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_dev')
def unblock_ip():
    data = request.get_json()
    ip_to_unblock = data.get('ip')
    if not ip_to_unblock:
        return jsonify({'error': 'IP is required'}), 400
    
    ip_manager_cache.unblock_ip(ip_to_unblock)
    return jsonify({'message': f'IP {ip_to_unblock} unblocked successfully'})

@dev_bp.route('/dev/regions/blocked', methods=['GET'])
@jwt_required()
@token_required
@access_required('manage_dev')
def list_blocked_regions():
    from models.blocked_region import BlockedRegion
    regions = BlockedRegion.query.all()
    return jsonify([r.to_dict() for r in regions])

@dev_bp.route('/dev/regions/block', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_dev')
def block_region():
    data = request.get_json()
    region_type = data.get('region_type') # 'country' or 'continent'
    region_name = data.get('region_name')
    if not region_type or not region_name:
        return jsonify({'error': 'region_type and region_name required'}), 400
        
    from models.blocked_region import BlockedRegion
    r = BlockedRegion.query.filter_by(region_name=region_name).first()
    if not r:
        r = BlockedRegion(region_type=region_type, region_name=region_name)
        db.session.add(r)
        db.session.commit()
        # update cache
        ip_manager_cache.blocked_regions[region_type].add(region_name)
        
    return jsonify({'message': f'Region {region_name} blocked successfully'})

@dev_bp.route('/dev/regions/unblock', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_dev')
def unblock_region():
    data = request.get_json()
    region_name = data.get('region_name')
    region_type = data.get('region_type')
    
    from models.blocked_region import BlockedRegion
    r = BlockedRegion.query.filter_by(region_name=region_name).first()
    if r:
        db.session.delete(r)
        db.session.commit()
        if region_name in ip_manager_cache.blocked_regions[r.region_type]:
            ip_manager_cache.blocked_regions[r.region_type].remove(region_name)
            
    return jsonify({'message': f'Region {region_name} unblocked successfully'})

@dev_bp.route('/dev/logs/history', methods=['GET'])
@jwt_required()
@token_required
@access_required('manage_dev')
def list_logs():
    log_dir = os.path.join(current_app.root_path, 'logs')
    if not os.path.exists(log_dir):
        return jsonify([])
    
    files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    # Ordenar por fecha (asumiendo formato app.log.YYYY-MM-DD.log)
    files.sort(reverse=True)
    return jsonify(files)

@dev_bp.route('/dev/logs/view/<filename>', methods=['GET'])
@jwt_required()
@token_required
@access_required('manage_dev')
def view_log(filename):
    log_dir = os.path.join(current_app.root_path, 'logs')
    file_path = os.path.join(log_dir, filename)
    
    # Seguridad básica para evitar path traversal
    if not os.path.exists(file_path) or '..' in filename:
        return jsonify({'error': 'Log file not found'}), 404
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dev_bp.route('/dev/users', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_users')
def list_users():
    users = UserModel.query.options(subqueryload(UserModel.profiles).subqueryload(ProfileModel.accesses)).all()
    return jsonify([user.to_json() for user in users])

@dev_bp.route('/dev/users/block', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_users')
def toggle_user_block():
    data = request.json
    user_uuid = data.get('uuid')
    user = UserModel.query.get(user_uuid)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.deleted_at:
        user.deleted_at = None
        message = "User unblocked/restored"
    else:
        user.deleted_at = datetime.utcnow()
        message = "User blocked/deleted"
        
    db.session.commit()
    return jsonify({'message': message, 'is_blocked': user.deleted_at is not None})

@dev_bp.route('/dev/users/create', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_users')
def create_user_dev():
    data = request.json
    try:
        new_user = UserModel(
            name=data['name'],
            email=data['email'],
            password=generate_password_hash(data['password'])
        )
        
        profile_uuids = data.get('profiles', [])
        if profile_uuids:
            profiles = ProfileModel.query.filter(ProfileModel.uuid.in_(profile_uuids)).all()
            new_user.profiles = profiles
            
        db.session.add(new_user)
        
        # Check and associate professional if tuition/matricula is provided
        tuition = data.get('tuition') or data.get('matricula')
        if tuition:
            professional = ProfessionalModel.query.filter_by(tuition=str(tuition), deleted_at=None).first()
            if professional:
                if professional.uuid_user and professional.uuid_user != new_user.uuid:
                    return jsonify({'error': 'Este perfil profesional ya está vinculado a otro usuario.'}), 400
                professional.uuid_user = new_user.uuid
                db.session.add(professional)

        db.session.commit()
        return jsonify(new_user.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/profiles', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_user_profiles')
def list_profiles_dev():
    profiles = ProfileModel.query.options(subqueryload(ProfileModel.accesses)).all() # Fetch all including deleted for management
    return jsonify([p.to_json() for p in profiles])

@dev_bp.route('/dev/accesses', methods=['GET'])
@jwt_required()
@token_required
@access_required('view_accesses')
def list_accesses_dev():
    accesses = AccessModel.query.all()
    return jsonify([a.to_json() for a in accesses])

@dev_bp.route('/dev/profiles/create', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_profiles')
def create_profile_dev():
    data = request.json
    try:
        new_profile = ProfileModel(
            name=data['name'],
            description=data.get('description', '')
        )
        accesses_uuids = data.get('accesses', [])
        if accesses_uuids:
            accs = AccessModel.query.filter(AccessModel.uuid.in_(accesses_uuids)).all()
            new_profile.accesses = accs
            
        db.session.add(new_profile)
        db.session.commit()
        return jsonify(new_profile.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/profiles/edit', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_profiles')
def edit_profile_dev():
    data = request.json
    profile_uuid = data.get('uuid')
    
    profile = ProfileModel.query.get(profile_uuid)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
        
    try:
        if 'name' in data and data['name']:
            profile.name = data['name']
        if 'description' in data:
            profile.description = data['description']
            
        accesses_uuids = data.get('accesses')
        if accesses_uuids is not None:
            accs = AccessModel.query.filter(AccessModel.uuid.in_(accesses_uuids)).all()
            profile.accesses = accs
            
        db.session.commit()
        return jsonify(profile.to_json()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/profiles/block', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_profiles')
def toggle_profile_block():
    data = request.json
    profile_uuid = data.get('uuid')
    profile = ProfileModel.query.get(profile_uuid)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    if profile.deleted_at:
        profile.deleted_at = None
        message = "Profile unblocked/restored"
    else:
        profile.deleted_at = datetime.utcnow()
        message = "Profile blocked/deleted"
        
    db.session.commit()
    return jsonify({'message': message, 'is_blocked': profile.deleted_at is not None})

@dev_bp.route('/dev/users/edit', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_users')
def edit_user_dev():
    data = request.json
    user_uuid = data.get('uuid')
    
    user = UserModel.query.get(user_uuid)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    try:
        if 'name' in data and data['name']:
            user.name = data['name']
        if 'email' in data and data['email']:
            user.email = data['email']
        if data.get('password'):
            user.password = generate_password_hash(data['password'])
            
        profile_uuids = data.get('profiles')
        if profile_uuids is not None:
            profiles = ProfileModel.query.filter(ProfileModel.uuid.in_(profile_uuids)).all()
            user.profiles = profiles
            
        db.session.commit()
        return jsonify(user.to_json()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/users/<string:uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_users')
def delete_user_dev(uuid):
    user = UserModel.query.get(uuid)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    try:
        # Unlink from ProfessionalModel
        professionals = ProfessionalModel.query.filter_by(uuid_user=uuid).all()
        for prof in professionals:
            prof.uuid_user = None
            db.session.add(prof)
            
        # Delete related LawyerPaymentModel records
        from models.lawyer_payment import LawyerPaymentModel
        LawyerPaymentModel.query.filter_by(uuid_user=uuid).delete()
        
        # Clear profiles relationship to clean up association table
        user.profiles = []
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/profiles/<string:uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_profiles')
def delete_profile_dev(uuid):
    profile = ProfileModel.query.get(uuid)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
        
    try:
        profile.users = []
        profile.accesses = []
        db.session.delete(profile)
        db.session.commit()
        return jsonify({'message': 'Profile deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/accesses/<string:uuid>', methods=['DELETE'])
@jwt_required()
@token_required
@access_required('manage_profiles')
def delete_access_dev(uuid):
    access = AccessModel.query.get(uuid)
    if not access:
        return jsonify({'error': 'Access not found'}), 404
        
    try:
        # Delete association rows in profiles_accesses
        from models.profile_access import profiles_accesses
        db.session.execute(profiles_accesses.delete().where(profiles_accesses.c.access_uuid == uuid))
        
        # Delete the access
        db.session.delete(access)
        db.session.commit()
        return jsonify({'message': 'Permission deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/accesses/create', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_profiles')
def create_access_dev():
    data = request.json
    try:
        new_access = AccessModel.from_json(data)
        db.session.add(new_access)
        db.session.commit()
        return jsonify(new_access.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/config', methods=['GET'])
@jwt_required()
@token_required
@access_required('manage_dev')
def get_configs():
    from models.config import SystemConfigModel
    configs = SystemConfigModel.query.all()
    return jsonify({c.key: c.value for c in configs}), 200

@dev_bp.route('/dev/config', methods=['POST'])
@jwt_required()
@token_required
@access_required('manage_dev')
def update_config():
    data = request.json
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'error': 'key and value are required'}), 400
    
    key = data['key']
    value = str(data['value'])
    
    from models.config import SystemConfigModel
    config = SystemConfigModel.query.get(key)
    if not config:
        config = SystemConfigModel(key=key, value=value)
        db.session.add(config)
    else:
        config.value = value
        
    try:
        db.session.commit()
        return jsonify(config.to_json()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



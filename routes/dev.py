from flask import Blueprint, Response, jsonify, request
import psutil
import time
from datetime import datetime
from utils.logging_config import get_log_stream, get_recent_logs
from models.ip_manager import IPRegistry
from models import UserModel, ProfileModel
from config.config import db
import os
from flask import current_app
from werkzeug.security import generate_password_hash
from models.access import AccessModel

dev_bp = Blueprint('dev', __name__)

@dev_bp.route('/dev/logs')
def stream_logs():
    return Response(get_log_stream(), mimetype='text/event-stream')

@dev_bp.route('/dev/logs/recent')
def get_recent_logs_api():
    return jsonify(get_recent_logs())

@dev_bp.route('/dev/stats')
def get_stats():
    stats = {
        'cpu_usage': psutil.cpu_percent(interval=None),
        'memory_usage': psutil.virtual_memory().percent,
        'timestamp': time.time()
    }
    return jsonify(stats)

@dev_bp.route('/dev/ips', methods=['GET'])
def list_ips():
    ips = IPRegistry.query.order_by(IPRegistry.last_seen.desc()).all()
    return jsonify([ip.to_dict() for ip in ips])

@dev_bp.route('/dev/ips/block', methods=['POST'])
def block_ip():
    data = request.get_json()
    ip_to_block = data.get('ip')
    if not ip_to_block:
        return jsonify({'error': 'IP is required'}), 400
    
    ip_record = IPRegistry.query.filter_by(ip=ip_to_block).first()
    if not ip_record:
        ip_record = IPRegistry(ip=ip_to_block)
        db.session.add(ip_record)
    
    ip_record.is_blocked = True
    db.session.commit()
    return jsonify({'message': f'IP {ip_to_block} blocked successfully'})

@dev_bp.route('/dev/ips/unblock', methods=['POST'])
def unblock_ip():
    data = request.get_json()
    ip_to_unblock = data.get('ip')
    if not ip_to_unblock:
        return jsonify({'error': 'IP is required'}), 400
    
    ip_record = IPRegistry.query.filter_by(ip=ip_to_unblock).first()
    if ip_record:
        ip_record.is_blocked = False
        db.session.commit()
    return jsonify({'message': f'IP {ip_to_unblock} unblocked successfully'})

@dev_bp.route('/dev/logs/history', methods=['GET'])
def list_logs():
    log_dir = os.path.join(current_app.root_path, 'logs')
    if not os.path.exists(log_dir):
        return jsonify([])
    
    files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    # Ordenar por fecha (asumiendo formato app.log.YYYY-MM-DD.log)
    files.sort(reverse=True)
    return jsonify(files)

@dev_bp.route('/dev/logs/view/<filename>', methods=['GET'])
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
def list_users():
    users = UserModel.query.all()
    return jsonify([user.to_json() for user in users])

@dev_bp.route('/dev/users/block', methods=['POST'])
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
        db.session.commit()
        return jsonify(new_user.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@dev_bp.route('/dev/profiles', methods=['GET'])
def list_profiles_dev():
    profiles = ProfileModel.query.all() # Fetch all including deleted for management
    return jsonify([p.to_json() for p in profiles])

@dev_bp.route('/dev/accesses', methods=['GET'])
def list_accesses_dev():
    accesses = AccessModel.query.all()
    return jsonify([a.to_json() for a in accesses])

@dev_bp.route('/dev/profiles/create', methods=['POST'])
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

from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import ProfileModel, AccessModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required

profile_bp = Blueprint('profile_bp', __name__)

@profile_bp.route('/profiles', methods=['POST'])
# @jwt_required()
# @token_required 
# @access_required('manage_profiles')
def create_profile():
    data = request.json
    new_profile = ProfileModel.from_json(data)
    db.session.add(new_profile)
    
    db.session.flush()
    
    accesses_uuids = set(data.get('uuid_accesses', []))
    accesses = AccessModel.query.filter(
        AccessModel.uuid.in_(accesses_uuids),
        AccessModel.deleted_at == None
    ).all()

    if accesses:
        added_accesses = set()

        view_access_uuids = [access.uuid for access in accesses if access.name.startswith('view_')]
        view_accesses = AccessModel.query.filter(
            AccessModel.uuid.in_(view_access_uuids),
            AccessModel.deleted_at == None
        ).all()
        
        for access in view_accesses:
            if access.uuid not in added_accesses:
                new_profile.accesses.append(access)
                added_accesses.add(access.uuid)

        manage_access_uuids = [access.uuid for access in accesses if access.name.startswith('manage_')]
        manage_accesses = AccessModel.query.filter(
            AccessModel.uuid.in_(manage_access_uuids),
            AccessModel.deleted_at == None
        ).all()

        if manage_accesses:
            for manage_access in manage_accesses:
                view_access_name = f"view_{manage_access.name.split('_')[1]}"
                view_access = AccessModel.query.filter(
                    AccessModel.name == view_access_name,
                    AccessModel.deleted_at == None
                ).first()

                if view_access:
                    if view_access.uuid not in added_accesses:
                        new_profile.accesses.append(view_access)
                        added_accesses.add(view_access.uuid)
                    if manage_access.uuid not in added_accesses:
                        new_profile.accesses.append(manage_access)
                        added_accesses.add(manage_access.uuid)
                else:
                    if manage_access.uuid not in added_accesses:
                        new_profile.accesses.append(manage_access)
                        added_accesses.add(manage_access.uuid)
    
    db.session.commit()

    return jsonify({
        'message': 'Profile created successfully',
        'uuid': new_profile.uuid
    }), 201

@profile_bp.route('/profiles/get', methods=['POST'])
@jwt_required()
@token_required 
@access_required('view_profiles')
def get_all_profiles():
    name = request.json.get('name')
    
    if name:
        profiles = ProfileModel.query.filter(ProfileModel.deleted_at == None, ProfileModel.name.ilike(f'%{name}%')).all()
    else:
        profiles = ProfileModel.query.filter(ProfileModel.deleted_at == None).all()
    
    profiles_data = [profile.to_json() for profile in profiles]
    return jsonify(profiles_data), 200

@profile_bp.route('/profiles/<uuid>', methods=['GET'])
@jwt_required()
@token_required 
@access_required('view_profiles')
def get_profile(uuid):
    profile = ProfileModel.query.filter_by(uuid=uuid, deleted_at=None).first()
    if profile:
        return jsonify(profile.to_json()), 200  # Usando to_json
    return jsonify({'message': 'Profile not found'}), 404

@profile_bp.route('/profiles/<uuid>', methods=['PUT'])
@jwt_required()
@token_required 
@access_required('manage_profiles')
def update_profile(uuid):
    profile = ProfileModel.query.filter_by(uuid=uuid, deleted_at=None).first()
    if profile:
        data = request.json
        profile.name = data.get('name', profile.name).lower()
        profile.description = data.get('description', profile.description)
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    return jsonify({'message': 'Profile not found'}), 404

@profile_bp.route('/profiles/<uuid>', methods=['DELETE'])
@jwt_required()
@token_required 
@access_required('manage_profiles')
def delete_profile(uuid):
    profile = ProfileModel.query.filter_by(uuid=uuid, deleted_at=None).first()
    if profile:
        profile.deleted_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Profile deleted successfully'}), 200
    return jsonify({'message': 'Profile not found'}), 404

@profile_bp.route('/profiles/<uuid_profile>/set_accesses', methods=['POST'])
@jwt_required()
@token_required 
@access_required('assign_accesses')
def set_accesses(uuid_profile):
    data = request.json
    profile = ProfileModel.query.filter_by(uuid=uuid_profile, deleted_at=None).first()
    if not profile:
        return jsonify({'message': 'Profile not found'}), 404

    profile.name = data.get('name', profile.name)
    profile.description = data.get('description', profile.description)
    accesses_uuids = data.get('uuid_accesses', [])
    accesses = AccessModel.query.filter(AccessModel.uuid.in_(accesses_uuids), AccessModel.deleted_at == None).all()
    if accesses:
        profile.accesses = accesses
        db.session.commit()
        # return jsonify({'message': 'Accesses assigned successfully'}), 200
        return jsonify(profile.to_json()), 200
    else:
        return jsonify({'message': 'No valid accesses found to assign'}), 400

@profile_bp.route('/profiles/<uuid_profile>/accesses', methods=['GET'])
@jwt_required()
@token_required 
@access_required('view_profile_accesses')
def get_profile_accesses(uuid_profile):
    profile = ProfileModel.query.filter_by(uuid=uuid_profile, deleted_at=None).first()
    if profile:
        accesses_data = [access.to_json() for access in profile.accesses]
        return jsonify(accesses_data), 200
    return jsonify({'message': 'Profile not found'}), 404
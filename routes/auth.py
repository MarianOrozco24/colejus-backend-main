from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models import UserModel, ProfileModel
from config.config import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from utils.decorators import token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
@jwt_required()
@token_required
def create_user():
    data = request.json
    required_fields = ['password', 'name', 'email', 'profiles']
    if not all(field in data for field in required_fields):
        return {'error': 'Email, password, name are required.'}, 400

    profiles_uuids = data.get('profiles', [])
    if not profiles_uuids:
        return {'error': 'No profile UUIDs provided. At least one profile UUID is required.'}, 400

    try:
        user = UserModel.from_json(data)
        profiles = ProfileModel.query.filter(ProfileModel.uuid.in_(profiles_uuids), ProfileModel.deleted_at == None).all()
        user.profiles = profiles
        db.session.add(user)
        db.session.commit()
        return {'user_uuid': user.uuid}, 201
    except Exception as e:
        db.session.rollback()
        print(e)
        return {'error': str(e)}, 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return {'error': 'email and password are required'}, 400

    try:
        user = UserModel.query.filter_by(email=email, deleted_at=None).first()

        if user is None or not user.check_password(password):
            return {'error': 'Invalid email or password'}, 401
        expires = timedelta(days=1)
        additional_claims = {"timestamp": datetime.utcnow().timestamp()}
        access_token = create_access_token(identity=email, expires_delta=expires, additional_claims=additional_claims)
            
        token_expiration_date = datetime.utcnow() + expires
        user.token_expiration_date = token_expiration_date
        user.auth_token = access_token

        db.session.add(user)
        db.session.commit()
            
        return user.to_json_login(), 200
    except Exception as e:
        print(f"Exception: {e}")
        return {'error': str(e)}, 500

@auth_bp.route('/change_password', methods=['POST'])
@jwt_required()
@token_required 
def change_password():
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return {'error': 'Current password and new password are required.'}, 400

    try:
        email = get_jwt_identity()
        user = UserModel.query.filter_by(email=email).first()
        print(email)
        if not user or not user.check_password(current_password):
            return {'error': 'Current password is incorrect.'}, 401

        user.password = generate_password_hash(new_password)
        db.session.commit()
        return {'message': 'Password updated successfully.'}, 200
    except Exception as e:
        print(e)
        db.session.rollback()
        return {'error': str(e)}, 500
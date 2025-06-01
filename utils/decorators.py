from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from models import UserModel
from datetime import datetime, timezone


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            email = get_jwt_identity()

            claims = get_jwt()
            expiration = claims['exp']

            if datetime.fromtimestamp(expiration, timezone.utc) < datetime.now(timezone.utc):
                return jsonify({'message': 'Token has expired'}), 401
            
            user = UserModel.query.filter_by(email=email).first()
            if not user:
                return jsonify({'message': 'User not found'}), 404
            
            request.user = user

        except Exception as e:
            return jsonify({'message': 'Token is invalid', 'error': str(e)}), 401

        return f(*args, **kwargs)
    return decorated_function

def access_required(access_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(request, 'user', None)
            if user is None:
                return jsonify({'message': 'User not set, token required'}), 401
            
            has_access = False
            for profile in user.profiles:
                for access in profile.accesses:
                    if access.name == access_name:
                        has_access = True
                        break
                if has_access:
                    break
            
            if not has_access:
                return jsonify({'message': 'Access denied'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
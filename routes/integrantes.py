from flask import Blueprint, request, jsonify
from models import IntegranteModel
from config.config import db
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
import uuid

integrantes_bp = Blueprint('integrantes_bp', __name__)

# Obtener todos los integrantes
@integrantes_bp.route('/integrantes', methods=['GET'])
# @jwt_required()
# @token_required
def get_all_integrantes():
    try:
        integrantes = IntegranteModel.query.order_by(IntegranteModel.created_at.desc()).all()
        return jsonify([i.to_json() for i in integrantes]), 200
    except Exception as e:
        print("❌ Error al obtener integrantes:", e)
        return jsonify({"error": str(e)}), 500

# Crear un nuevo integrante
@integrantes_bp.route('/integrantes', methods=['POST'])
# @jwt_required()
# @token_required
def create_integrante():
    try:
        data = request.json
        nuevo_integrante = IntegranteModel(
            uuid=str(uuid.uuid4()),
            nombre=data['nombre'],
            telefono=data.get('telefono'),
            cargo=data['cargo'],
            categoria=data['categoria']
        )
        db.session.add(nuevo_integrante)
        db.session.commit()
        return jsonify(nuevo_integrante.to_json()), 201
    except Exception as e:
        db.session.rollback()
        print("❌ Error al crear integrante:", e)
        return jsonify({"error": str(e)}), 500

# Eliminar un integrante
@integrantes_bp.route('/integrantes/<string:uuid>', methods=['DELETE'])
# @jwt_required()
# @token_required
def delete_integrante(uuid):
    try:
        integrante = IntegranteModel.query.get(uuid)
        if not integrante:
            return jsonify({"error": "Integrante no encontrado"}), 404

        db.session.delete(integrante)
        db.session.commit()
        return jsonify({"message": "Integrante eliminado"}), 200
    except Exception as e:
        db.session.rollback()
        print("❌ Error al eliminar integrante:", e)
        return jsonify({"error": str(e)}), 500
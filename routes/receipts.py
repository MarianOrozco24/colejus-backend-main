from datetime import datetime
from flask import Blueprint, request, jsonify
from config.config import db
from models import ReceiptModel
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required

receipts_bp = Blueprint('receipts_bp', __name__)

@receipts_bp.route('/forms/receipts', methods=['GET'])
@jwt_required()
@token_required
def get_all_receipts():
    try:
        search = request.args.get('search', '') # Obtenemos los datos del filtro de busqueda

        receipts = ReceiptModel.query.filter_by(status='Pagado').order_by(ReceiptModel.fecha_pago.desc()).all()
        # receipts = ReceiptModel.query.order_by(ReceiptModel.fecha_pago.desc()).all() ## Original || trae todos los recibos in discriminar si estan pagados o no

        # Condicional de busqueda 
        if search: # En caso de que haya informacion en el filtro realizamos un filtro distinto
            search_term = f"%{search}%"
            receipts = ReceiptModel.query.filter(
                ReceiptModel.caratula.ilike(search_term) |
                ReceiptModel.total_depositado.ilike(search_term) |
                ReceiptModel.fecha_pago.ilike(search_term)) # filtramos los datos por el filtro que indique el usuario

        results = []
        for r in receipts:
            results.append({
                "uuid": r.uuid,
                "receipt_number": r.receipt_number,
                "fecha_inicio": r.fecha_inicio.strftime("%Y-%m-%d") if r.fecha_inicio else None,
                "fecha_vencimiento": r.fecha_vencimiento.strftime("%Y-%m-%d") if r.fecha_vencimiento else None,
                "caratula": r.caratula or "",
                "total_depositado": float(r.total_depositado or 0),
                "tasa_justicia": float(r.tasa_justicia or 0),
                "juicio_n": r.juicio_n or "",
                "payment_id": r.payment_id,
                "fecha_pago": r.fecha_pago.strftime("%Y-%m-%d %H:%M") if r.fecha_pago else None,
                "status": r.status
            })

        return jsonify(results), 200

    except Exception as e:
        print("❌ Error al obtener recibos:", e)
        return jsonify({"error": str(e)}), 500

from flask import Blueprint, request, jsonify
from datetime import datetime
from config.config import db
from models.booking import BookingModel
from sqlalchemy.exc import IntegrityError

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/bookings/occupied', methods=['GET'])
def get_occupied_slots():
    room_id = request.args.get('room_id')
    date_str = request.args.get('date')

    if not room_id or not date_str:
        return jsonify({'error': 'room_id and date parameters are required.'}), 400

    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    try:
        bookings = BookingModel.query.filter_by(room_id=room_id, booking_date=booking_date).all()
        occupied = [b.time_slot for b in bookings]
        return jsonify(occupied), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/bookings', methods=['POST'])
def create_booking():
    data = request.json
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    required_fields = ['room_id', 'booking_date', 'time_slots', 'user_name', 'user_email', 'user_phone', 'user_tuition', 'idempotency_key']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

    room_id = data['room_id']
    date_str = data['booking_date']
    time_slots = data['time_slots']
    user_name = data['user_name']
    user_email = data['user_email']
    user_phone = data['user_phone']
    user_tuition = data['user_tuition']
    purpose = data.get('purpose', '')
    idempotency_key = data['idempotency_key']

    if not isinstance(time_slots, list) or not time_slots:
        return jsonify({'error': 'time_slots must be a non-empty list of strings'}), 400

    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # IDEMPOTENCIA: Verificar si ya existen reservas asociadas a esta key de cliente
    try:
        existing_bookings = BookingModel.query.filter(
            BookingModel.idempotency_key.like(f"{idempotency_key}_%")
        ).all()
        if existing_bookings:
            # Si existen, devolverlas como respuesta exitosa (idempotente)
            return jsonify({
                'message': 'Booking processed successfully (idempotent)',
                'bookings': [b.to_json() for b in existing_bookings]
            }), 200
    except Exception as e:
        pass

    try:
        # ATOMICIDAD: Comprobar que todos los slots solicitados estén disponibles
        conflicting_bookings = BookingModel.query.filter(
            BookingModel.room_id == room_id,
            BookingModel.booking_date == booking_date,
            BookingModel.time_slot.in_(time_slots)
        ).all()

        if conflicting_bookings:
            conflicts = [b.time_slot for b in conflicting_bookings]
            return jsonify({
                'error': 'One or more selected slots are already booked.',
                'conflicts': conflicts
            }), 409

        # Crear registros (uno por slot) asociando el idempotency_key modificado
        created_records = []
        for slot in time_slots:
            new_booking = BookingModel(
                room_id=room_id,
                booking_date=booking_date,
                time_slot=slot,
                user_name=user_name,
                user_email=user_email,
                user_phone=user_phone,
                user_tuition=user_tuition,
                purpose=purpose,
                idempotency_key=f"{idempotency_key}_{slot}"
            )
            db.session.add(new_booking)
            created_records.append(new_booking)

        db.session.commit()
        return jsonify({
            'message': 'Booking created successfully',
            'bookings': [b.to_json() for b in created_records]
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        # En caso de colisión de clave única por concurrencia extrema
        return jsonify({'error': 'Double-booking conflict or duplicate submission. Please try again.'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

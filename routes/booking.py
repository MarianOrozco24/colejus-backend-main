from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from config.config import db
from models.booking import BookingModel
from models.room import RoomModel
from models import UserModel, ProfileModel
from sqlalchemy.exc import IntegrityError
from utils.decorators import token_required, access_required

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/bookings/occupied', methods=['GET'])
@token_required
@access_required('book_rooms')
def get_occupied_slots():
    room_id = request.args.get('room_id')
    date_str = request.args.get('date')
    
    try:
        attendees = int(request.args.get('attendees', 1))
        if attendees <= 0:
            attendees = 1
    except ValueError:
        attendees = 1

    if not room_id or not date_str:
        return jsonify({'error': 'room_id and date parameters are required.'}), 400

    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    try:
        room = RoomModel.query.filter_by(id=room_id, deleted_at=None).first()
        if not room:
            return jsonify({'error': 'Room not found.'}), 404

        bookings = BookingModel.query.filter_by(room_id=room_id, booking_date=booking_date).all()
        
        # Calculate sum of attendees per slot
        slot_attendees = {}
        for b in bookings:
            slot_attendees[b.time_slot] = slot_attendees.get(b.time_slot, 0) + (b.attendees or 1)
            
        occupied = [slot for slot, total in slot_attendees.items() if total + attendees > room.capacity]
        return jsonify(occupied), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/bookings', methods=['POST'])
@token_required
@access_required('book_rooms')
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
    
    try:
        attendees = int(data.get('attendees', 1))
        if attendees <= 0:
            return jsonify({'error': 'Attendees count must be a positive integer.'}), 400
    except ValueError:
        return jsonify({'error': 'Attendees count must be a valid integer.'}), 400

    if not isinstance(time_slots, list) or not time_slots:
        return jsonify({'error': 'time_slots must be a non-empty list of strings'}), 400

    if len(time_slots) > 3:
        return jsonify({'error': 'El límite máximo de reserva es de 3 horas por turno.'}), 400

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
        room = RoomModel.query.filter_by(id=room_id, deleted_at=None).first()
        if not room:
            return jsonify({'error': 'Room not found.'}), 404

        if attendees > room.capacity:
            return jsonify({'error': f'Attendees count ({attendees}) exceeds maximum capacity of the room ({room.capacity}).'}), 400

        # ATOMICIDAD: Comprobar que todos los slots solicitados tengan capacidad disponible
        conflicts = []
        for slot in time_slots:
            existing_bookings = BookingModel.query.filter(
                BookingModel.room_id == room_id,
                BookingModel.booking_date == booking_date,
                BookingModel.time_slot == slot
            ).all()
            current_sum = sum(b.attendees or 1 for b in existing_bookings)
            if current_sum + attendees > room.capacity:
                conflicts.append(slot)

        if conflicts:
            return jsonify({
                'error': 'One or more selected slots do not have enough remaining capacity.',
                'conflicts': conflicts
            }), 409

        # Crear registros (uno por slot) asociando el idempotency_key modificado
        created_records = []
        companions_list = data.get('companions', [])
        import json
        companions_json = json.dumps(companions_list, ensure_ascii=False) if companions_list else None

        booker_uuid = request.user.uuid if hasattr(request, 'user') and request.user else None

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
                attendees=1,  # Fila principal representa al titular (1 asistente)
                companions=companions_json,
                idempotency_key=f"{idempotency_key}_{slot}",
                created_by_uuid=None
            )
            db.session.add(new_booking)
            created_records.append(new_booking)

            for idx, companion in enumerate(companions_list):
                comp_email = companion.get('email', '')
                comp_name = companion.get('name', '')

                # Buscar info del colega si está registrado
                comp_user = UserModel.query.filter_by(email=comp_email, deleted_at=None).first() if comp_email else None
                comp_tuition = ''
                comp_phone = ''
                if comp_user:
                    from models.professional import ProfessionalModel
                    comp_prof = ProfessionalModel.query.filter_by(uuid_user=comp_user.uuid, deleted_at=None).first()
                    if comp_prof:
                        comp_tuition = comp_prof.tuition or ''
                        comp_phone = comp_prof.phone or ''

                comp_id_str = comp_email if comp_email else f"idx_{idx}"
                comp_booking = BookingModel(
                    room_id=room_id,
                    booking_date=booking_date,
                    time_slot=slot,
                    user_name=comp_name,
                    user_email=comp_email,
                    user_phone=comp_phone,
                    user_tuition=comp_tuition,
                    purpose=purpose,
                    attendees=1,  # Fila del acompañante representa 1 asistente
                    companions=None,
                    idempotency_key=f"{idempotency_key}_{slot}_comp_{comp_id_str}",
                    created_by_uuid=booker_uuid
                )
                db.session.add(comp_booking)
                created_records.append(comp_booking)

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


@booking_bp.route('/bookings/stats', methods=['GET'])
@token_required
@access_required('view_rooms')
def get_booking_stats():
    room_id = request.args.get('room_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # 1. Determine Room ID (default to first active room if none provided)
    if not room_id or room_id == 'undefined' or room_id == 'null' or room_id == '':
        try:
            first_room = RoomModel.query.filter_by(deleted_at=None).order_by(RoomModel.id.asc()).first()
            if not first_room:
                return jsonify({
                    'avg_bookings_per_day': 0.0,
                    'total_bookings': 0,
                    'room_capacity': 0,
                    'top_users': [],
                    'intervals_heatmap': [],
                    'days_heatmap': []
                }), 200
            room_id = first_room.id
        except Exception as e:
            return jsonify({'error': f'Failed to retrieve default room: {str(e)}'}), 500

    try:
        room_id_int = int(room_id)
    except ValueError:
        return jsonify({'error': 'Invalid room_id format.'}), 400

    try:
        room = RoomModel.query.filter_by(id=room_id_int, deleted_at=None).first()
        if not room:
            return jsonify({'error': 'Room not found.'}), 404

        # 2. Parse Date Range
        today = datetime.utcnow().date()
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD.'}), 400
        else:
            start_date = today - timedelta(days=30)

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD.'}), 400
        else:
            end_date = today

        if start_date > end_date:
            return jsonify({'error': 'start_date cannot be greater than end_date.'}), 400

        # 3. Query bookings
        bookings = BookingModel.query.filter(
            BookingModel.room_id == str(room.id),
            BookingModel.booking_date >= start_date,
            BookingModel.booking_date <= end_date
        ).all()

        total_bookings = len(bookings)

        # 4. Calculate Average Daily Booking Count
        days_in_range = (end_date - start_date).days + 1
        avg_bookings_per_day = round(total_bookings / days_in_range, 2) if days_in_range > 0 else 0.0

        # 5. Calculate Top Users
        user_counts = {}
        for b in bookings:
            email = b.user_email.strip().lower() if b.user_email else "unknown"
            if email not in user_counts:
                user_counts[email] = {
                    'email': email,
                    'name': b.user_name or "Usuario Anónimo",
                    'count': 0
                }
            user_counts[email]['count'] += 1

        top_users = []
        for email, info in user_counts.items():
            percentage = round((info['count'] / total_bookings) * 100, 1) if total_bookings > 0 else 0.0
            top_users.append({
                'email': info['email'],
                'name': info['name'],
                'count': info['count'],
                'percentage': percentage
            })
        top_users.sort(key=lambda x: x['count'], reverse=True)
        top_users = top_users[:5]

        # 6. Intervals Heatmap (Weekday 0-6 vs Time Slots 08:00-19:00)
        slots_list = [f"{h:02d}:00" for h in range(8, 20)]
        intervals_grid = {w: {slot: 0 for slot in slots_list} for w in range(7)}

        for b in bookings:
            w = b.booking_date.weekday()  # Monday is 0, Sunday is 6
            slot = b.time_slot
            if slot in intervals_grid[w]:
                intervals_grid[w][slot] += 1

        intervals_heatmap = []
        for w in range(7):
            for slot in slots_list:
                intervals_heatmap.append({
                    'weekday': w,
                    'slot': slot,
                    'count': intervals_grid[w][slot]
                })

        # 7. Days Heatmap (Calendar Days count in range)
        day_counts = {}
        curr = start_date
        while curr <= end_date:
            day_counts[curr.isoformat()] = 0
            curr += timedelta(days=1)

        for b in bookings:
            dt_str = b.booking_date.isoformat()
            if dt_str in day_counts:
                day_counts[dt_str] += 1

        days_heatmap = [{'date': d, 'count': c} for d, c in sorted(day_counts.items())]

        return jsonify({
            'avg_bookings_per_day': avg_bookings_per_day,
            'total_bookings': total_bookings,
            'room_capacity': room.capacity,
            'top_users': top_users,
            'intervals_heatmap': intervals_heatmap,
            'days_heatmap': days_heatmap
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booking_bp.route('/bookings/lawyers', methods=['GET'])
@token_required
@access_required('book_rooms')
def get_lawyers_list():
    search_query = request.args.get('name', '').strip()
    try:
        # Join users with profiles and filter by name = 'lawyer'
        query = UserModel.query.join(UserModel.profiles).filter(
            ProfileModel.name == 'lawyer',
            UserModel.deleted_at.is_(None)
        )
        if search_query:
            query = query.filter(UserModel.name.ilike(f"%{search_query}%"))
            
        lawyers = query.order_by(UserModel.name.asc()).all()
        return jsonify([
            {
                'uuid': u.uuid,
                'name': u.name,
                'email': u.email
            } for u in lawyers
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booking_bp.route('/bookings/my-bookings', methods=['GET'])
@token_required
@access_required('book_rooms')
def get_my_bookings():
    date_str = request.args.get('date')
    user_email = request.user.email
    
    try:
        query = BookingModel.query.filter(db.func.lower(BookingModel.user_email) == user_email.lower())
        
        if date_str:
            try:
                booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.filter(BookingModel.booking_date == booking_date)
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
        else:
            today = datetime.utcnow().date()
            query = query.filter(BookingModel.booking_date >= today)
            
        bookings = query.order_by(BookingModel.booking_date.asc(), BookingModel.time_slot.asc()).all()
        
        # Get room names
        room_ids = {b.room_id for b in bookings if b.room_id}
        room_map = {}
        if room_ids:
            rooms = RoomModel.query.filter(RoomModel.id.in_(list(room_ids))).all()
            room_map = {str(r.id): r.name for r in rooms}
            
        result = []
        for b in bookings:
            data = b.to_json()
            data['room_name'] = room_map.get(str(b.room_id), 'Sala de Coworking')
            result.append(data)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booking_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
@token_required
@access_required('book_rooms')
def delete_booking(booking_id):
    user_email = request.user.email
    user_uuid = request.user.uuid if hasattr(request.user, 'uuid') else None
    
    # Check if the user is an admin or dev
    is_admin = False
    for profile in request.user.profiles:
        if profile.name.lower() in ['admin', 'administrador', 'dev']:
            is_admin = True
            break
            
    try:
        booking = BookingModel.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found.'}), 404
            
        # Extract the base prefix of the booking's idempotency_key
        # For example, if key is '1-2026-06-04-12345-9876_08:00', the base prefix is '1-2026-06-04-12345-9876'
        base_key = booking.idempotency_key.split('_')[0]
        
        # Query all rows in this booking group
        group_bookings = BookingModel.query.filter(BookingModel.idempotency_key.like(f"{base_key}%")).all()
        
        if not group_bookings:
            return jsonify({'error': 'Booking group not found.'}), 404
            
        # Check if user is authorized to delete this group
        authorized = is_admin
        if not authorized:
            for gb in group_bookings:
                if gb.user_email.lower() == user_email.lower() or (gb.created_by_uuid and gb.created_by_uuid == user_uuid):
                    authorized = True
                    break
                    
        if not authorized:
            return jsonify({'error': 'You are not authorized to cancel this booking.'}), 403
            
        # Delete all bookings in the group
        for gb in group_bookings:
            db.session.delete(gb)
            
        db.session.commit()
        return jsonify({'message': 'Booking cancelled successfully.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




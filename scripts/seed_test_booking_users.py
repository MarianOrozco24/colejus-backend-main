"""
Crea 2 usuarios de prueba para validar reservas de sala de reuniones.

Uso:
  python scripts/seed_test_booking_users.py
  python scripts/seed_test_booking_users.py --remove
"""

import argparse
import os
import sys
import uuid
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from app import app, db
from models import UserModel, ProfileModel, LawyerMembershipStatusModel
from models.membership_constants import (
    MEMBERSHIP_STATUS_UP_TO_DATE,
    MEMBERSHIP_STATUS_IN_DEBT,
)

TEST_USERS = [
    {
        'tuition': '88801',
        'name': 'Prueba Al Dia',
        'first_name': 'Prueba',
        'last_name': 'Al Dia',
        'status': MEMBERSHIP_STATUS_UP_TO_DATE,
        'first_unpaid_month': date(2026, 8, 1),
        'raw_quota_text': 'Agosto 2026',
        'password': 'Colejus2026',
    },
    {
        'tuition': '88802',
        'name': 'Prueba Deudor',
        'first_name': 'Prueba',
        'last_name': 'Deudor',
        'status': MEMBERSHIP_STATUS_IN_DEBT,
        'first_unpaid_month': date(2026, 4, 1),
        'raw_quota_text': 'Abril 2026',
        'password': 'Colejus2026',
    },
]


def remove_test_users():
    with app.app_context():
        for item in TEST_USERS:
            tuition = item['tuition']
            LawyerMembershipStatusModel.query.filter_by(tuition_normalized=tuition).delete()
            user = UserModel.query.filter_by(email=tuition, deleted_at=None).first()
            if user:
                user.deleted_at = datetime.utcnow()
        db.session.commit()
        print('Usuarios de prueba eliminados (soft-delete).')


def seed_test_users():
    with app.app_context():
        lawyer_profile = ProfileModel.query.filter_by(name='lawyer', deleted_at=None).first()
        if not lawyer_profile:
            print('Error: no existe perfil lawyer.')
            return

        default_password = os.getenv('LAWYER_DEFAULT_PASSWORD', 'Colejus2026')

        print('\n=== Usuarios de prueba para reservas ===\n')

        for item in TEST_USERS:
            tuition = item['tuition']

            status = LawyerMembershipStatusModel.query.filter_by(tuition_normalized=tuition).first()
            if not status:
                status = LawyerMembershipStatusModel(
                    uuid=str(uuid.uuid4()),
                    tuition_normalized=tuition,
                )
            status.tuition_display = tuition
            status.first_name = item['first_name']
            status.last_name = item['last_name']
            status.branch = 'San Rafael (TEST)'
            status.status = item['status']
            status.first_unpaid_month = item['first_unpaid_month']
            status.raw_quota_text = item['raw_quota_text']
            status.parse_notes = 'seed_test_booking_users'
            status.observation = 'Usuario de prueba — eliminar después'
            status.synced_at = datetime.utcnow()
            db.session.add(status)

            user = UserModel.query.filter_by(email=tuition, deleted_at=None).first()
            if not user:
                user = UserModel.query.filter_by(email=tuition).first()
                if user and user.deleted_at:
                    user.deleted_at = None

            if not user:
                user = UserModel()
                user.uuid = str(uuid.uuid4())
                user.email = tuition

            user.name = item['name']
            user.password = generate_password_hash(item['password'] or default_password)
            user.must_change_password = False
            if lawyer_profile not in user.profiles:
                user.profiles = list(user.profiles or []) + [lawyer_profile]
            db.session.add(user)

            status.uuid_user = user.uuid
            db.session.add(status)

            can_book = 'SI puede reservar' if status.can_book_meeting_room() else 'NO puede reservar'
            print(f"Matricula: {tuition}")
            print(f"  Nombre:    {item['name']}")
            print(f"  Password:  {item['password'] or default_password}")
            print(f"  Estado:    {item['status']} -> {can_book}")
            print(f"  Cuota:     {item['raw_quota_text']}")
            print()

        db.session.commit()
        print('Listo. Proba login con matricula + contrasena, luego Reservar Sala > Reuniones.\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remove', action='store_true', help='Eliminar usuarios de prueba')
    args = parser.parse_args()

    if args.remove:
        remove_test_users()
    else:
        seed_test_users()


if __name__ == '__main__':
    main()

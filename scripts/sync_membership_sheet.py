"""
Sincroniza el listado de cuotas desde Google Sheets hacia la base de datos.

Uso:
  python scripts/sync_membership_sheet.py
  python scripts/sync_membership_sheet.py --provision-users
  python scripts/sync_membership_sheet.py --file ruta/al/export.csv
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from services.membership_sync_service import MembershipSyncService


def main():
    parser = argparse.ArgumentParser(description='Sincronizar cuotas desde Excel/Sheets')
    parser.add_argument('--file', help='Ruta a CSV exportado manualmente')
    parser.add_argument('--url', help='URL de export CSV de Google Sheets')
    parser.add_argument('--provision-users', action='store_true', help='Crear usuarios abogados')
    args = parser.parse_args()

    with app.app_context():
        service = MembershipSyncService()
        if args.file:
            with open(args.file, 'r', encoding='utf-8-sig') as handle:
                csv_content = handle.read()
            import_record = service.sync_from_csv_content(
                csv_content,
                source_identifier=args.file,
                provision_users=args.provision_users,
            )
        else:
            import_record = service.sync_from_url(
                url=args.url,
                provision_users=args.provision_users,
            )

        print('Sincronización completada.')
        print(import_record.to_json())


if __name__ == '__main__':
    main()

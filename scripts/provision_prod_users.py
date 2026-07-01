"""
Utility script to run membership synchronization and lawyer user provisioning.
Can be executed locally targeting the production database.
"""

import sys
import os
import argparse
import uuid
from datetime import datetime

# Setup sys.path to resolve imports from parent directory
scripts_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(scripts_dir)
sys.path.insert(0, backend_dir)

# Command-line arguments parser
parser = argparse.ArgumentParser(description="Aprovisionar usuarios de abogados en la base de datos.")
parser.add_argument(
    "--mode",
    choices=["sync-and-provision", "provision-only"],
    default="sync-and-provision",
    help="Modo de ejecucion: sync-and-provision (sincroniza cuotas y crea usuarios) o provision-only (crea usuarios para registros existentes sin usuario).",
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Simular las acciones sin aplicar cambios permanentes en la base de datos.",
)
parser.add_argument(
    "--env-file",
    help="Ruta a un archivo .env personalizado (por ejemplo, para credenciales de produccion).",
)
parser.add_argument(
    "--db-host",
    help="Host de la base de datos (sobrescribe MYSQL_HOST).",
)
parser.add_argument(
    "--db-port",
    help="Puerto de la base de datos (se anexa a MYSQL_HOST como host:port).",
)
parser.add_argument(
    "--db-user",
    help="Usuario de la base de datos (sobrescribe MYSQL_USER).",
)
parser.add_argument(
    "--db-password",
    help="Contrasena de la base de datos (sobrescribe MYSQL_PASSWORD).",
)
parser.add_argument(
    "--db-name",
    help="Nombre de la base de datos (sobrescribe MYSQL_DATABASE).",
)
parser.add_argument(
    "--csv-file",
    help="Ruta a un archivo CSV local para sincronizar (solo para modo sync-and-provision).",
)
parser.add_argument(
    "--url",
    help="URL de exportacion CSV de Google Sheets a utilizar (solo para modo sync-and-provision).",
)
args = parser.parse_args()

# Load env variables
import dotenv
original_load_dotenv = dotenv.load_dotenv

def custom_load_dotenv(*args_ld, **kwargs_ld):
    kwargs_ld["override"] = False
    return original_load_dotenv(*args_ld, **kwargs_ld)

# Patch load_dotenv to prevent app.py from overwriting our overrides
dotenv.load_dotenv = custom_load_dotenv

# Load the env file
if args.env_file:
    print(f"Cargando variables de entorno desde: {args.env_file}")
    original_load_dotenv(args.env_file, override=True)
else:
    # Load the default project .env file
    default_env = os.path.join(backend_dir, ".env")
    if os.path.exists(default_env):
        print(f"Cargando variables de entorno por defecto desde: {default_env}")
        original_load_dotenv(default_env, override=True)

# Apply individual CLI overrides
db_host = args.db_host or os.environ.get("MYSQL_HOST")
db_port = args.db_port

if db_host:
    if db_port:
        if ":" in db_host:
            db_host = db_host.split(":")[0]
        os.environ["MYSQL_HOST"] = f"{db_host}:{db_port}"
    else:
        os.environ["MYSQL_HOST"] = db_host
elif db_port:
    current_host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    if ":" in current_host:
        current_host = current_host.split(":")[0]
    os.environ["MYSQL_HOST"] = f"{current_host}:{db_port}"

if args.db_user:
    os.environ["MYSQL_USER"] = args.db_user
if args.db_password:
    os.environ["MYSQL_PASSWORD"] = args.db_password
if args.db_name:
    os.environ["MYSQL_DATABASE"] = args.db_name

# Now import the Flask application context and models
from app import app, db
from models import (
    UserModel,
    ProfileModel,
    ProfessionalModel,
    LawyerMembershipStatusModel,
)
from models.membership_constants import (
    MEMBERSHIP_STATUS_AMBIGUOUS,
)
from services.membership_sync_service import MembershipSyncService
from werkzeug.security import generate_password_hash

def print_pending_changes():
    """Print objects that are in the database session pending to be committed."""
    new_users = [o for o in db.session.new if isinstance(o, UserModel)]
    new_statuses = [o for o in db.session.new if isinstance(o, LawyerMembershipStatusModel)]
    dirty_statuses = [o for o in db.session.dirty if isinstance(o, LawyerMembershipStatusModel)]
    
    print("\n--- RESUMEN DE CAMBIOS ---")
    if new_users:
        print(f"\n[Nuevos Usuarios a Crear: {len(new_users)}]")
        for u in new_users:
            print(f" - {u.name} (Email/Matricula: {u.email})")
            
    if new_statuses:
        print(f"\n[Nuevos Estados de Matricula a Agregar: {len(new_statuses)}]")
        for s in new_statuses:
            print(f" - {s.first_name} {s.last_name} (Matricula: {s.tuition_normalized}, Estado: {s.status})")
            
    if dirty_statuses:
        print(f"\n[Estados de Matricula a Modificar: {len(dirty_statuses)}]")
        for s in dirty_statuses:
            print(f" - {s.first_name} {s.last_name} (Matricula: {s.tuition_normalized}, Nuevo Estado: {s.status})")

    if not (new_users or new_statuses or dirty_statuses):
        print("No hay cambios pendientes de guardar en la base de datos.")

def run_sync_and_provision():
    service = MembershipSyncService()
    
    # If dry-run, we patch db.session.commit to bypass actual commits
    if args.dry_run:
        original_commit = db.session.commit
        def mocked_commit():
            db.session.flush()
        db.session.commit = mocked_commit
        print("[MODO SIMULACION] Se ejecutaran las operaciones de lectura y parseo pero no se guardaran cambios.")

    try:
        if args.csv_file:
            print(f"Iniciando sincronizacion desde archivo local: {args.csv_file}")
            with open(args.csv_file, "r", encoding="utf-8-sig") as handle:
                csv_content = handle.read()
            import_record = service.sync_from_csv_content(
                csv_content,
                source_identifier=args.csv_file,
                provision_users=True,
            )
        else:
            print("Iniciando sincronizacion desde URL de Google Sheets...")
            import_record = service.sync_from_url(
                url=args.url,
                provision_users=True,
            )

        if args.dry_run:
            print("\n--- RESUMEN DE LA SIMULACION ---")
            print(f"Usuarios a aprovisionar: {import_record.users_provisioned}")
            print(f"Filas a normalizar: {import_record.rows_normalized}")
            print(f"Filas omitidas: {import_record.rows_skipped}")
            print(f"Filas ambiguas: {import_record.rows_ambiguous}")
            print(f"Filas bloqueadas: {import_record.rows_blocked}")
            db.session.rollback()
            print("\n[MODO SIMULACION] Operaciones revertidas correctamente.")
        else:
            print("\nSincronizacion y aprovisionamiento completado con exito.")
            print(f"Usuarios aprovisionados: {import_record.users_provisioned}")
            print(f"Filas normalizadas: {import_record.rows_normalized}")

    except Exception as exc:
        if args.dry_run:
            db.session.rollback()
        print(f"Error durante la sincronizacion: {exc}")
        sys.exit(1)

def run_provision_only():
    default_password = os.getenv("LAWYER_DEFAULT_PASSWORD", "Colejus2026")
    
    # Check if lawyer profile exists
    lawyer_profile = ProfileModel.query.filter_by(name="lawyer", deleted_at=None).first()
    if not lawyer_profile:
        print("Error: No se encontro el perfil 'lawyer' en la base de datos.")
        sys.exit(1)

    # Find status records that have no associated user and are not ambiguous
    statuses = LawyerMembershipStatusModel.query.filter(
        (LawyerMembershipStatusModel.uuid_user == None) &
        (LawyerMembershipStatusModel.status != MEMBERSHIP_STATUS_AMBIGUOUS)
    ).all()

    if not statuses:
        print("No se encontraron registros de matricula que requieran aprovisionamiento de usuario.")
        return

    print(f"Se encontraron {len(statuses)} registros de matricula sin usuario asociado.")

    # Preload users
    all_users = UserModel.query.filter_by(deleted_at=None).all()
    users_by_email = {u.email.lower(): u for u in all_users if u.email}

    # Preload professionals
    all_professionals = ProfessionalModel.query.filter(ProfessionalModel.deleted_at == None).all()
    prof_by_tuition = {}
    for p in all_professionals:
        if p.tuition:
            key = p.tuition.replace(" ", "").replace(".", "")
            if key not in prof_by_tuition:
                prof_by_tuition[key] = p

    provisioned_count = 0
    updated_profiles_count = 0

    # First pass: create all missing users and add lawyer profiles
    for status_record in statuses:
        tuition = status_record.tuition_normalized
        display_name = " ".join(
            filter(None, [status_record.first_name, status_record.last_name])
        ).strip() or f"Matricula {tuition}"

        # Find user by email
        user = users_by_email.get(tuition.lower())
        if not user and status_record.tuition_display:
            user = users_by_email.get(status_record.tuition_display.lower())

        if not user:
            print(f"[NUEVO USUARIO] Se creara el usuario {display_name} con email/matricula: {tuition}")
            if not args.dry_run:
                user = UserModel()
                user.uuid = str(uuid.uuid4())
                user.email = tuition
                user.name = display_name
                user.password = generate_password_hash(default_password)
                user.must_change_password = True
                user.profiles = [lawyer_profile]
                db.session.add(user)
                users_by_email[tuition.lower()] = user
            provisioned_count += 1
        else:
            if lawyer_profile not in user.profiles:
                print(f"[ACTUALIZAR ROL] Se agregara el rol de abogado al usuario existente {user.name} ({user.email})")
                if not args.dry_run:
                    user.profiles.append(lawyer_profile)
                updated_profiles_count += 1

    # Flush to database so all user uuids are created and exist in the users table
    if not args.dry_run:
        db.session.flush()

    # Second pass: link status records and professionals to the users
    for status_record in statuses:
        tuition = status_record.tuition_normalized
        user = users_by_email.get(tuition.lower())
        if not user and status_record.tuition_display:
            user = users_by_email.get(status_record.tuition_display.lower())

        if user:
            if not args.dry_run:
                status_record.uuid_user = user.uuid
                professional = prof_by_tuition.get(tuition)
                if professional:
                    if not professional.uuid_user:
                        professional.uuid_user = user.uuid
                    status_record.uuid_professional = professional.uuid
                    db.session.add(professional)
                db.session.add(status_record)

    if args.dry_run:
        print(f"\n[MODO SIMULACION] Fin de la simulacion. Se hubieran creado {provisioned_count} usuarios y actualizado {updated_profiles_count} roles.")
    else:
        try:
            db.session.commit()
            print(f"\nAprovisionamiento finalizado con exito. Creados: {provisioned_count}, Actualizados: {updated_profiles_count}.")
        except Exception as exc:
            db.session.rollback()
            print(f"Error al guardar cambios: {exc}")
            sys.exit(1)

def main():
    print(f"Iniciando ejecucion de provision de usuarios en modo: {args.mode} (Dry-run: {args.dry_run})")
    
    with app.app_context():
        # Verify db connection works
        try:
            db.session.execute(db.text("SELECT 1"))
            print("Conexion con la base de datos establecida correctamente.")
        except Exception as exc:
            print(f"Error de conexion a la base de datos: {exc}")
            sys.exit(1)

        if args.mode == "sync-and-provision":
            run_sync_and_provision()
        elif args.mode == "provision-only":
            run_provision_only()

if __name__ == "__main__":
    main()

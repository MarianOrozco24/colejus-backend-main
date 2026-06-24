"""add membership sheet tables and must_change_password

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if 'membership_sheet_imports' not in existing_tables:
        op.create_table(
            'membership_sheet_imports',
            sa.Column('uuid', sa.String(length=36), nullable=False),
            sa.Column('source_type', sa.String(length=32), nullable=False),
            sa.Column('source_identifier', sa.String(length=512), nullable=True),
            sa.Column('sheet_name', sa.String(length=128), nullable=True),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('rows_total', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rows_raw_saved', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rows_normalized', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rows_skipped', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rows_ambiguous', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rows_blocked', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('users_provisioned', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('report_json', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('uuid'),
        )

    if 'membership_sheet_rows_raw' not in existing_tables:
        op.create_table(
            'membership_sheet_rows_raw',
            sa.Column('uuid', sa.String(length=36), nullable=False),
            sa.Column('import_uuid', sa.String(length=36), nullable=False),
            sa.Column('row_number', sa.Integer(), nullable=False),
            sa.Column('col_index', sa.String(length=32), nullable=True),
            sa.Column('col_apellido', sa.String(length=255), nullable=True),
            sa.Column('col_nombre', sa.String(length=255), nullable=True),
            sa.Column('col_mat', sa.String(length=64), nullable=True),
            sa.Column('col_cuota_adeudada', sa.String(length=512), nullable=True),
            sa.Column('col_sede', sa.String(length=128), nullable=True),
            sa.Column('col_observacion', sa.Text(), nullable=True),
            sa.Column('full_row_json', sa.Text(), nullable=True),
            sa.Column('parse_status', sa.String(length=32), nullable=False),
            sa.Column('parse_notes', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['import_uuid'], ['membership_sheet_imports.uuid']),
            sa.PrimaryKeyConstraint('uuid'),
        )
        op.create_index(
            'ix_membership_sheet_rows_raw_import_uuid',
            'membership_sheet_rows_raw',
            ['import_uuid'],
            unique=False,
        )

    if 'lawyer_membership_status' not in existing_tables:
        op.create_table(
            'lawyer_membership_status',
            sa.Column('uuid', sa.String(length=36), nullable=False),
            sa.Column('tuition_normalized', sa.String(length=20), nullable=False),
            sa.Column('tuition_display', sa.String(length=32), nullable=True),
            sa.Column('last_name', sa.String(length=128), nullable=True),
            sa.Column('first_name', sa.String(length=128), nullable=True),
            sa.Column('branch', sa.String(length=64), nullable=True),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('first_unpaid_month', sa.Date(), nullable=True),
            sa.Column('blocked_reason', sa.String(length=64), nullable=True),
            sa.Column('raw_quota_text', sa.Text(), nullable=True),
            sa.Column('observation', sa.Text(), nullable=True),
            sa.Column('parse_notes', sa.String(length=255), nullable=True),
            sa.Column('last_import_uuid', sa.String(length=36), nullable=True),
            sa.Column('source_row_number', sa.Integer(), nullable=True),
            sa.Column('synced_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['last_import_uuid'], ['membership_sheet_imports.uuid']),
            sa.PrimaryKeyConstraint('uuid'),
            sa.UniqueConstraint('tuition_normalized'),
        )
        op.create_index(
            'ix_lawyer_membership_status_tuition',
            'lawyer_membership_status',
            ['tuition_normalized'],
            unique=False,
        )
        op.create_index(
            'ix_lawyer_membership_status_status',
            'lawyer_membership_status',
            ['status'],
            unique=False,
        )

    user_columns = [c['name'] for c in insp.get_columns('users')]
    if 'must_change_password' not in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    'must_change_password',
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    user_columns = [c['name'] for c in insp.get_columns('users')]
    if 'must_change_password' in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_column('must_change_password')

    if 'lawyer_membership_status' in existing_tables:
        op.drop_table('lawyer_membership_status')
    if 'membership_sheet_rows_raw' in existing_tables:
        op.drop_table('membership_sheet_rows_raw')
    if 'membership_sheet_imports' in existing_tables:
        op.drop_table('membership_sheet_imports')

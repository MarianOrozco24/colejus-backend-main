"""add uuid foreign keys to membership tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-22 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    status_columns = [c['name'] for c in insp.get_columns('lawyer_membership_status')]
    with op.batch_alter_table('lawyer_membership_status', schema=None) as batch_op:
        if 'uuid_professional' not in status_columns:
            batch_op.add_column(sa.Column('uuid_professional', sa.String(length=36), nullable=True))
        if 'uuid_user' not in status_columns:
            batch_op.add_column(sa.Column('uuid_user', sa.String(length=36), nullable=True))

    existing_indexes = {idx['name'] for idx in insp.get_indexes('lawyer_membership_status')}
    if 'ix_lawyer_membership_status_uuid_professional' not in existing_indexes:
        op.create_index(
            'ix_lawyer_membership_status_uuid_professional',
            'lawyer_membership_status',
            ['uuid_professional'],
            unique=False,
        )
    if 'ix_lawyer_membership_status_uuid_user' not in existing_indexes:
        op.create_index(
            'ix_lawyer_membership_status_uuid_user',
            'lawyer_membership_status',
            ['uuid_user'],
            unique=False,
        )

    raw_columns = [c['name'] for c in insp.get_columns('membership_sheet_rows_raw')]
    with op.batch_alter_table('membership_sheet_rows_raw', schema=None) as batch_op:
        if 'membership_status_uuid' not in raw_columns:
            batch_op.add_column(sa.Column('membership_status_uuid', sa.String(length=36), nullable=True))

    raw_indexes = {idx['name'] for idx in insp.get_indexes('membership_sheet_rows_raw')}
    if 'ix_membership_sheet_rows_raw_status_uuid' not in raw_indexes:
        op.create_index(
            'ix_membership_sheet_rows_raw_status_uuid',
            'membership_sheet_rows_raw',
            ['membership_status_uuid'],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    raw_indexes = {idx['name'] for idx in insp.get_indexes('membership_sheet_rows_raw')}
    if 'ix_membership_sheet_rows_raw_status_uuid' in raw_indexes:
        op.drop_index('ix_membership_sheet_rows_raw_status_uuid', table_name='membership_sheet_rows_raw')

    raw_columns = [c['name'] for c in insp.get_columns('membership_sheet_rows_raw')]
    with op.batch_alter_table('membership_sheet_rows_raw', schema=None) as batch_op:
        if 'membership_status_uuid' in raw_columns:
            batch_op.drop_column('membership_status_uuid')

    status_indexes = {idx['name'] for idx in insp.get_indexes('lawyer_membership_status')}
    if 'ix_lawyer_membership_status_uuid_user' in status_indexes:
        op.drop_index('ix_lawyer_membership_status_uuid_user', table_name='lawyer_membership_status')
    if 'ix_lawyer_membership_status_uuid_professional' in status_indexes:
        op.drop_index('ix_lawyer_membership_status_uuid_professional', table_name='lawyer_membership_status')

    status_columns = [c['name'] for c in insp.get_columns('lawyer_membership_status')]
    with op.batch_alter_table('lawyer_membership_status', schema=None) as batch_op:
        if 'uuid_user' in status_columns:
            batch_op.drop_column('uuid_user')
        if 'uuid_professional' in status_columns:
            batch_op.drop_column('uuid_professional')

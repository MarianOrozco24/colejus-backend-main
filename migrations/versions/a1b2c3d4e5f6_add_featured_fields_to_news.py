"""add featured fields to news

Revision ID: a1b2c3d4e5f6
Revises: ca9134007da2
Create Date: 2026-06-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'ca9134007da2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    news_columns = [c['name'] for c in insp.get_columns('news')]

    with op.batch_alter_table('news', schema=None) as batch_op:
        if 'is_featured' not in news_columns:
            batch_op.add_column(
                sa.Column('is_featured', sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if 'featured_order' not in news_columns:
            batch_op.add_column(sa.Column('featured_order', sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    news_columns = [c['name'] for c in insp.get_columns('news')]

    with op.batch_alter_table('news', schema=None) as batch_op:
        if 'featured_order' in news_columns:
            batch_op.drop_column('featured_order')
        if 'is_featured' in news_columns:
            batch_op.drop_column('is_featured')

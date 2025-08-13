"""Merge migration branches

Revision ID: af71fdf08f97
Revises: 85acb9c2b7f6, 9804239e9f10
Create Date: 2025-08-13 14:28:45.547696

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af71fdf08f97'
down_revision = ('85acb9c2b7f6', '9804239e9f10')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

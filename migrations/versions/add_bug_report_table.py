"""Add BugReport table for automatic error reporting

Revision ID: add_bug_report_table
Revises: fea43f00c057
Create Date: 2024-01-17 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_bug_report_table'
down_revision = 'fea43f00c057'
branch_labels = None
depends_on = None


def upgrade():
    # Create bug_report table
    op.create_table('bug_report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('error_type', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_role', sa.String(length=50), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('request_data', sa.Text(), nullable=True),
        sa.Column('browser_info', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['teacher_staff.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_bug_report_status', 'bug_report', ['status'])
    op.create_index('idx_bug_report_severity', 'bug_report', ['severity'])
    op.create_index('idx_bug_report_created_at', 'bug_report', ['created_at'])
    op.create_index('idx_bug_report_user_id', 'bug_report', ['user_id'])
    op.create_index('idx_bug_report_assigned_to', 'bug_report', ['assigned_to'])
    op.create_index('idx_bug_report_error_type', 'bug_report', ['error_type'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_bug_report_error_type', table_name='bug_report')
    op.drop_index('idx_bug_report_assigned_to', table_name='bug_report')
    op.drop_index('idx_bug_report_user_id', table_name='bug_report')
    op.drop_index('idx_bug_report_created_at', table_name='bug_report')
    op.drop_index('idx_bug_report_severity', table_name='bug_report')
    op.drop_index('idx_bug_report_status', table_name='bug_report')
    
    # Drop table
    op.drop_table('bug_report')

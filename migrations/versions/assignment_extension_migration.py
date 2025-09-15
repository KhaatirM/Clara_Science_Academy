"""Add AssignmentExtension table

Revision ID: assignment_extension_001
Revises: fea43f00c057
Create Date: 2025-09-15 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'assignment_extension_001'
down_revision = 'fea43f00c057'
branch_labels = None
depends_on = None


def upgrade():
    # Create assignment_extension table
    op.create_table('assignment_extension',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('extended_due_date', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('granted_by', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignment.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['student.id'], ),
        sa.ForeignKeyConstraint(['granted_by'], ['teacher_staff.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_assignment_extension_assignment_id', 'assignment_extension', ['assignment_id'])
    op.create_index('idx_assignment_extension_student_id', 'assignment_extension', ['student_id'])
    op.create_index('idx_assignment_extension_active', 'assignment_extension', ['is_active'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_assignment_extension_active', table_name='assignment_extension')
    op.drop_index('idx_assignment_extension_student_id', table_name='assignment_extension')
    op.drop_index('idx_assignment_extension_assignment_id', table_name='assignment_extension')
    
    # Drop table
    op.drop_table('assignment_extension')

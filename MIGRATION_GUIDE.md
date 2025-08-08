# Flask-Migrate Database Migration Guide

This guide explains how to use Flask-Migrate for database migrations in the Clara Science App.

## Overview

Flask-Migrate is now integrated into the application to handle database schema changes in a safe and controlled manner. This replaces the manual `create_db.py` approach for production environments.

## Setup (Already Completed)

1. **Flask-Migrate Added**: Added to `requirements.txt`
2. **Application Integration**: Updated `app.py` to initialize Flask-Migrate
3. **Migration Repository**: Initialized with `flask db init`
4. **Initial Migration**: Created to capture current database schema

## Migration Workflow

### Making Database Changes

1. **Modify Models**: Edit `models.py` to add/remove/modify fields or tables
2. **Generate Migration**: Run `python -m flask db migrate -m "Description of changes"`
3. **Review Migration**: Check the generated migration file in `migrations/versions/`
4. **Apply Migration**: Run `python -m flask db upgrade`

### Example Workflow

```bash
# 1. Make changes to models.py (e.g., add a new field)
# 2. Generate migration
python -m flask db migrate -m "Add email field to Student model"

# 3. Apply the migration
python -m flask db upgrade
```

## Available Commands

### `python -m flask db migrate -m "Message"`
- Compares current models to database state
- Generates a migration script in `migrations/versions/`
- Use descriptive messages for the migration

### `python -m flask db upgrade`
- Applies pending migrations to the database
- Updates the database schema
- Safe to run multiple times

### `python -m flask db downgrade`
- Reverts the last migration
- Useful for testing or fixing issues
- Be careful with data loss

### `python -m flask db current`
- Shows the current migration version
- Useful for checking migration status

### `python -m flask db history`
- Shows migration history
- Displays all applied migrations

### `python -m flask db stamp head`
- Marks database as up-to-date without running migrations
- Useful when restoring from backup

## Migration Files

- **Location**: `migrations/versions/`
- **Format**: `{revision_id}_{description}.py`
- **Purpose**: Contains the SQL commands to update the database

### Example Migration File
```python
"""Add is_active field to SystemConfig

Revision ID: 4cd99ccb2794
Revises: 60815f645d4b
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add the new column
    op.add_column('system_config', sa.Column('is_active', sa.Boolean(), nullable=True))

def downgrade():
    # Remove the column if needed
    op.drop_column('system_config', 'is_active')
```

## Best Practices

### 1. Always Test Migrations
- Test migrations on a copy of production data
- Verify data integrity after migrations
- Test both upgrade and downgrade paths

### 2. Use Descriptive Messages
```bash
# Good
python -m flask db migrate -m "Add user profile fields"

# Bad
python -m flask db migrate -m "fix"
```

### 3. Review Generated Migrations
- Check the generated migration file before applying
- Ensure it captures your intended changes
- Modify if necessary (rare but sometimes needed)

### 4. Backup Before Major Changes
```bash
# Backup current database
cp instance/app.db instance/app_backup_$(date +%Y%m%d_%H%M%S).db
```

### 5. Handle Data Migrations
For complex changes involving data transformation:

```python
def upgrade():
    # Add new column
    op.add_column('user', sa.Column('new_field', sa.String(50), nullable=True))
    
    # Data migration
    connection = op.get_bind()
    connection.execute("UPDATE user SET new_field = 'default_value'")
    
    # Make column not nullable
    op.alter_column('user', 'new_field', nullable=False)
```

## Production Deployment

### Local Development
```bash
# Apply all pending migrations
python -m flask db upgrade
```

### Production Server (Render)
```bash
# The same command works on production
python -m flask db upgrade
```

## Troubleshooting

### Migration Conflicts
If you get conflicts between migrations:
1. Check the migration history: `python -m flask db history`
2. Identify the conflicting migration
3. Consider using `python -m flask db stamp head` to mark current state
4. Generate a new migration from current state

### Database Out of Sync
If the database is out of sync with migrations:
```bash
# Mark as up-to-date (if database is correct)
python -m flask db stamp head

# Or reset and recreate
rm -rf migrations/
python -m flask db init
python -m flask db migrate -m "Initial migration"
python -m flask db upgrade
```

### Reverting Changes
```bash
# Revert last migration
python -m flask db downgrade

# Revert to specific migration
python -m flask db downgrade <revision_id>
```

## Migration vs create_db.py

| Feature | Flask-Migrate | create_db.py |
|---------|---------------|--------------|
| **Incremental Changes** | ✅ Yes | ❌ No |
| **Data Preservation** | ✅ Yes | ❌ No |
| **Rollback Support** | ✅ Yes | ❌ No |
| **Production Safe** | ✅ Yes | ❌ No |
| **Version Control** | ✅ Yes | ❌ No |
| **Team Collaboration** | ✅ Yes | ❌ No |

## When to Use create_db.py

- **Local Development**: Quick database reset
- **Testing**: Fresh database for tests
- **Development Only**: Never use in production

## Migration Commands Summary

```bash
# Initialize migration repository (one-time setup)
python -m flask db init

# Generate migration for model changes
python -m flask db migrate -m "Description"

# Apply pending migrations
python -m flask db upgrade

# Revert last migration
python -m flask db downgrade

# Check current migration version
python -m flask db current

# View migration history
python -m flask db history

# Mark database as up-to-date
python -m flask db stamp head
```

## Important Notes

1. **Never delete migration files** that have been applied to production
2. **Always backup** before major migrations
3. **Test migrations** on development data first
4. **Use descriptive messages** for migrations
5. **Review generated migrations** before applying

## Getting Help

If you encounter issues with migrations:
1. Check the migration history: `python -m flask db history`
2. Verify database state: `python -m flask db current`
3. Review the migration files in `migrations/versions/`
4. Consider resetting if necessary (development only)

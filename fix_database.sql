-- SQL script to fix the missing academic_period_id column in the assignment table
-- Run this on your PostgreSQL database (Render) to fix the error

-- First, check if the column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'academic_period_id'
    ) THEN
        -- Add the missing column
        ALTER TABLE assignment ADD COLUMN academic_period_id INTEGER;
        
        -- Add foreign key constraint
        ALTER TABLE assignment 
        ADD CONSTRAINT fk_assignment_academic_period 
        FOREIGN KEY (academic_period_id) REFERENCES academic_period(id);
        
        RAISE NOTICE 'Added academic_period_id column and foreign key constraint';
    ELSE
        RAISE NOTICE 'academic_period_id column already exists';
    END IF;
END $$;

-- Check if semester column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'semester'
    ) THEN
        ALTER TABLE assignment ADD COLUMN semester VARCHAR(10);
        RAISE NOTICE 'Added semester column';
    ELSE
        RAISE NOTICE 'semester column already exists';
    END IF;
END $$;

-- Check if is_locked column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'is_locked'
    ) THEN
        ALTER TABLE assignment ADD COLUMN is_locked BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_locked column';
    ELSE
        RAISE NOTICE 'is_locked column already exists';
    END IF;
END $$;

-- Check if created_at column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'created_at'
    ) THEN
        ALTER TABLE assignment ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added created_at column';
    ELSE
        RAISE NOTICE 'created_at column already exists';
    END IF;
END $$;

-- Verify the current table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'assignment'
ORDER BY ordinal_position;

-- Show any foreign key constraints
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'assignment';

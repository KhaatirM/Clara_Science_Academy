-- Fix missing assignment table columns in production PostgreSQL database
-- Run this script on your Render PostgreSQL database

-- Check current columns
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'assignment' 
AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes')
ORDER BY column_name;

-- Add missing columns if they don't exist
DO $$ 
BEGIN
    -- Add allow_save_and_continue column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'allow_save_and_continue'
    ) THEN
        ALTER TABLE assignment ADD COLUMN allow_save_and_continue BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added allow_save_and_continue column';
    ELSE
        RAISE NOTICE 'allow_save_and_continue column already exists';
    END IF;

    -- Add max_save_attempts column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'max_save_attempts'
    ) THEN
        ALTER TABLE assignment ADD COLUMN max_save_attempts INTEGER DEFAULT 3;
        RAISE NOTICE 'Added max_save_attempts column';
    ELSE
        RAISE NOTICE 'max_save_attempts column already exists';
    END IF;

    -- Add save_timeout_minutes column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assignment' 
        AND column_name = 'save_timeout_minutes'
    ) THEN
        ALTER TABLE assignment ADD COLUMN save_timeout_minutes INTEGER DEFAULT 30;
        RAISE NOTICE 'Added save_timeout_minutes column';
    ELSE
        RAISE NOTICE 'save_timeout_minutes column already exists';
    END IF;
END $$;

-- Verify the columns were added
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'assignment' 
AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes')
ORDER BY column_name;

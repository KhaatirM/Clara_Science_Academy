-- Add assignment_type field to Assignment table
-- Run this in Render's PostgreSQL database console

-- Check if column already exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'assignment' 
AND column_name = 'assignment_type';

-- Add the assignment_type column
ALTER TABLE assignment 
ADD COLUMN assignment_type VARCHAR(20) DEFAULT 'pdf' NOT NULL;

-- Update existing assignments to have 'pdf' as default type
UPDATE assignment 
SET assignment_type = 'pdf' 
WHERE assignment_type IS NULL;

-- Verify the column was added
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns 
WHERE table_name = 'assignment' 
AND column_name = 'assignment_type';

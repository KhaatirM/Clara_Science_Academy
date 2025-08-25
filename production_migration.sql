-- Production Database Migration Script
-- Add missing columns to teacher_staff table

-- Add middle_initial column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS middle_initial VARCHAR(1);

-- Add date of birth column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS dob VARCHAR(20);

-- Add social security number column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS staff_ssn VARCHAR(20);

-- Add assigned role column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS assigned_role VARCHAR(100);

-- Add subject column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS subject VARCHAR(200);

-- Add employment type column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS employment_type VARCHAR(20);

-- Add grades taught column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS grades_taught TEXT;

-- Add resume filename column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS resume_filename VARCHAR(255);

-- Add other document filename column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS other_document_filename VARCHAR(255);

-- Add image column
ALTER TABLE teacher_staff ADD COLUMN IF NOT EXISTS image VARCHAR(255);

-- Verify the changes
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'teacher_staff' 
ORDER BY ordinal_position;

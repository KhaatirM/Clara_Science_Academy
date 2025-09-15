-- AssignmentExtension Table Creation Script
-- Run this in Render's PostgreSQL database console

-- Check if table already exists
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'assignment_extension'
);

-- Create the assignment_extension table
CREATE TABLE IF NOT EXISTS assignment_extension (
    id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    extended_due_date TIMESTAMP NOT NULL,
    reason TEXT,
    granted_by INTEGER NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (assignment_id) REFERENCES assignment (id),
    FOREIGN KEY (student_id) REFERENCES student (id),
    FOREIGN KEY (granted_by) REFERENCES teacher_staff (id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_assignment_extension_assignment_id ON assignment_extension (assignment_id);
CREATE INDEX IF NOT EXISTS idx_assignment_extension_student_id ON assignment_extension (student_id);
CREATE INDEX IF NOT EXISTS idx_assignment_extension_active ON assignment_extension (is_active);

-- Verify the table was created
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'assignment_extension';

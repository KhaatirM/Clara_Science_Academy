from app import create_app, db
from models import User, Student, TeacherStaff
from werkzeug.security import generate_password_hash
from datetime import datetime

def add_test_users():
    app = create_app()
    
    with app.app_context():
        # Clear existing data (optional - comment out if you want to keep existing data)
        print("Clearing existing users...")
        User.query.delete()
        Student.query.delete()
        TeacherStaff.query.delete()
        db.session.commit()
        
        # 1. Director
        print("Adding Director...")
        director_staff = TeacherStaff(
            first_name='Dr. Maria',
            last_name='Rodriguez',
            email='maria.rodriguez@school.edu',
            staff_id='DIR001',
            assigned_role='Director',
            position='School Director'
        )
        db.session.add(director_staff)
        db.session.flush()
        
        director_user = User(
            username='director',
            password_hash=generate_password_hash('password123'),
            role='Director',
            teacher_staff_id=director_staff.id
        )
        db.session.add(director_user)
        db.session.flush()
        
        # 2. School Administrator
        print("Adding School Administrator...")
        admin_staff = TeacherStaff(
            first_name='James',
            last_name='Wilson',
            email='james.wilson@school.edu',
            staff_id='ADM001',
            assigned_role='School Administrator',
            position='School Administrator'
        )
        db.session.add(admin_staff)
        db.session.flush()
        
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('password123'),
            role='School Administrator',
            teacher_staff_id=admin_staff.id
        )
        db.session.add(admin_user)
        db.session.flush()
        
        # 3. Teacher
        print("Adding Teacher...")
        teacher_staff = TeacherStaff(
            first_name='Sarah',
            last_name='Johnson',
            email='sarah.johnson@school.edu',
            staff_id='TCH001',
            assigned_role='Teacher',
            position='Math Teacher',
            subject='Mathematics'
        )
        db.session.add(teacher_staff)
        db.session.flush()
        
        teacher_user = User(
            username='teacher',
            password_hash=generate_password_hash('password123'),
            role='Teacher',
            teacher_staff_id=teacher_staff.id
        )
        db.session.add(teacher_user)
        db.session.flush()
        
        # 4. Student with full parent and emergency contact information
        print("Adding Student...")
        student = Student(
            first_name='Alex',
            last_name='Smith',
            dob='05/15/2010',
            grade_level=8,
            address='123 Main St, Austin, TX 78701',
            
            # Parent 1 information
            parent1_first_name='Michael',
            parent1_last_name='Smith',
            parent1_email='michael.smith@email.com',
            parent1_phone='(512) 555-0101',
            parent1_relationship='Father',
            
            # Parent 2 information
            parent2_first_name='Jennifer',
            parent2_last_name='Smith',
            parent2_email='jennifer.smith@email.com',
            parent2_phone='(512) 555-0102',
            parent2_relationship='Mother',
            
            # Emergency contact
            emergency_first_name='Robert',
            emergency_last_name='Johnson',
            emergency_email='robert.johnson@email.com',
            emergency_phone='(512) 555-0103',
            emergency_relationship='Grandparent',
            
            # Address fields
            street='123 Main St',
            apt_unit='Apt 4B',
            city='Austin',
            state='Texas',
            zip_code='78701'
        )
        # Generate Student ID
        student.student_id = student.generate_student_id()
        db.session.add(student)
        db.session.flush()
        
        student_user = User(
            username='student',
            password_hash=generate_password_hash('password123'),
            role='Student',
            student_id=student.id
        )
        db.session.add(student_user)
        db.session.flush()
        
        # 5. Tech
        print("Adding Tech...")
        tech_staff = TeacherStaff(
            first_name='David',
            last_name='Chen',
            email='david.chen@school.edu',
            staff_id='TEC001',
            assigned_role='Tech',
            position='IT Support Specialist'
        )
        db.session.add(tech_staff)
        db.session.flush()
        
        tech_user = User(
            username='tech',
            password_hash=generate_password_hash('password123'),
            role='Tech',
            teacher_staff_id=tech_staff.id
        )
        db.session.add(tech_user)
        
        # Commit all changes
        db.session.commit()
        
        print("\n=== Test Users Added Successfully ===")
        print("All users have password: 'password123'")
        print("\nLogin Credentials:")
        print("=" * 50)
        print("1. DIRECTOR")
        print("   Username: director")
        print("   Password: password123")
        print("   Staff ID: DIR001")
        print("   Name: Dr. Maria Rodriguez")
        print()
        print("2. SCHOOL ADMINISTRATOR")
        print("   Username: admin")
        print("   Password: password123")
        print("   Staff ID: ADM001")
        print("   Name: James Wilson")
        print()
        print("3. TEACHER")
        print("   Username: teacher")
        print("   Password: password123")
        print("   Staff ID: TCH001")
        print("   Name: Sarah Johnson (Math Teacher)")
        print()
        print("4. STUDENT")
        print("   Username: student")
        print("   Password: password123")
        print(f"   Student ID: {student.student_id}")
        print("   Name: Alex Smith (Grade 8)")
        print("   - Parent 1: Michael Smith (Father)")
        print("   - Parent 2: Jennifer Smith (Mother)")
        print("   - Emergency Contact: Robert Johnson (Grandparent)")
        print()
        print("5. TECH (ID NOT REQUIRED)")
        print("   Username: tech")
        print("   Password: password123")
        print("   Staff ID: TEC001 (optional)")
        print("   Name: David Chen (IT Support)")
        print()
        print("=" * 50)
        print("IMPORTANT: Tech users can login with just username + password")
        print("All other users need username + password + ID number")
        print("\nYou can now test the enhanced security login!")

if __name__ == '__main__':
    add_test_users() 
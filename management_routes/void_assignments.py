"""
Assignment voiding functionality for administrators.
Allows voiding assignments for all students or specific students.
"""

from flask import Blueprint, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Assignment, Grade, GroupAssignment, GroupGrade, Student
from datetime import datetime

bp = Blueprint('void_assignments', __name__)

@bp.route('/void-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def void_assignment_for_students(assignment_id):
    """
    Void an assignment for all students or specific students.
    Can void individual or group assignments.
    """
    try:
        assignment_type = request.form.get('assignment_type', 'individual')  # 'individual' or 'group'
        student_ids = request.form.getlist('student_ids')  # Empty list = void for all
        reason = request.form.get('reason', 'Voided by administrator')
        void_all = request.form.get('void_all', 'false').lower() == 'true'
        
        voided_count = 0
        
        if assignment_type == 'group':
            # Handle group assignment voiding
            group_assignment = GroupAssignment.query.get_or_404(assignment_id)
            
            if void_all or not student_ids:
                # Void for all students in groups
                group_grades = GroupGrade.query.filter_by(
                    group_assignment_id=assignment_id,
                    is_voided=False
                ).all()
                
                for grade in group_grades:
                    grade.is_voided = True
                    grade.voided_by = current_user.id
                    grade.voided_at = datetime.utcnow()
                    grade.voided_reason = reason
                    voided_count += 1
                
                message = f'Voided group assignment "{group_assignment.title}" for all students ({voided_count} grades)'
            else:
                # Void for specific students
                for student_id in student_ids:
                    # Find student's group for this assignment
                    from models import StudentGroupMember, GroupSubmission
                    member = StudentGroupMember.query.filter_by(student_id=int(student_id)).first()
                    
                    if member:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_group_id=member.student_group_id,
                            is_voided=False
                        ).first()
                        
                        if group_grade:
                            group_grade.is_voided = True
                            group_grade.voided_by = current_user.id
                            group_grade.voided_at = datetime.utcnow()
                            group_grade.voided_reason = reason
                            voided_count += 1
                
                message = f'Voided group assignment "{group_assignment.title}" for {voided_count} student(s)'
        
        else:
            # Handle individual assignment voiding
            assignment = Assignment.query.get_or_404(assignment_id)
            
            if void_all or not student_ids:
                # Void for all students
                grades = Grade.query.filter_by(
                    assignment_id=assignment_id,
                    is_voided=False
                ).all()
                
                for grade in grades:
                    grade.is_voided = True
                    grade.voided_by = current_user.id
                    grade.voided_at = datetime.utcnow()
                    grade.voided_reason = reason
                    voided_count += 1
                
                message = f'Voided assignment "{assignment.title}" for all students ({voided_count} grades)'
            else:
                # Void for specific students
                for student_id in student_ids:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=int(student_id),
                        is_voided=False
                    ).first()
                    
                    if grade:
                        grade.is_voided = True
                        grade.voided_by = current_user.id
                        grade.voided_at = datetime.utcnow()
                        grade.voided_reason = reason
                        voided_count += 1
                
                message = f'Voided assignment "{assignment.title}" for {voided_count} student(s)'
        
        db.session.commit()
        
        # Update quarter grades for affected students (force recalculation)
        from utils.quarter_grade_calculator import update_quarter_grade
        if assignment_type == 'individual':
            assignment_obj = Assignment.query.get(assignment_id)
            quarter = assignment_obj.quarter
            school_year_id = assignment_obj.school_year_id
            class_id = assignment_obj.class_id
        else:
            assignment_obj = GroupAssignment.query.get(assignment_id)
            quarter = assignment_obj.quarter
            school_year_id = assignment_obj.school_year_id
            class_id = assignment_obj.class_id
        
        # Refresh quarter grades for affected students
        students_to_update = student_ids if student_ids else [g.student_id for g in Grade.query.filter_by(assignment_id=assignment_id).all()]
        for sid in students_to_update:
            try:
                update_quarter_grade(
                    student_id=int(sid),
                    class_id=class_id,
                    school_year_id=school_year_id,
                    quarter=quarter,
                    force=True  # Force immediate recalculation
                )
            except Exception as e:
                current_app.logger.warning(f"Could not update quarter grade for student {sid}: {e}")
        
        flash(message, 'success')
        return jsonify({'success': True, 'message': message, 'voided_count': voided_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/unvoid-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def unvoid_assignment_for_students(assignment_id):
    """
    Un-void an assignment (restore grades).
    """
    try:
        assignment_type = request.form.get('assignment_type', 'individual')
        student_ids = request.form.getlist('student_ids')
        unvoid_all = request.form.get('unvoid_all', 'false').lower() == 'true'
        
        unvoided_count = 0
        
        if assignment_type == 'group':
            group_assignment = GroupAssignment.query.get_or_404(assignment_id)
            
            if unvoid_all or not student_ids:
                group_grades = GroupGrade.query.filter_by(
                    group_assignment_id=assignment_id,
                    is_voided=True
                ).all()
                
                for grade in group_grades:
                    grade.is_voided = False
                    grade.voided_by = None
                    grade.voided_at = None
                    grade.voided_reason = None
                    unvoided_count += 1
                
                message = f'Restored group assignment "{group_assignment.title}" for all students'
            else:
                for student_id in student_ids:
                    from models import StudentGroupMember
                    member = StudentGroupMember.query.filter_by(student_id=int(student_id)).first()
                    
                    if member:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_group_id=member.student_group_id,
                            is_voided=True
                        ).first()
                        
                        if group_grade:
                            group_grade.is_voided = False
                            group_grade.voided_by = None
                            group_grade.voided_at = None
                            group_grade.voided_reason = None
                            unvoided_count += 1
                
                message = f'Restored group assignment "{group_assignment.title}" for {unvoided_count} student(s)'
        else:
            assignment = Assignment.query.get_or_404(assignment_id)
            
            if unvoid_all or not student_ids:
                grades = Grade.query.filter_by(
                    assignment_id=assignment_id,
                    is_voided=True
                ).all()
                
                for grade in grades:
                    grade.is_voided = False
                    grade.voided_by = None
                    grade.voided_at = None
                    grade.voided_reason = None
                    unvoided_count += 1
                
                message = f'Restored assignment "{assignment.title}" for all students'
            else:
                for student_id in student_ids:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=int(student_id),
                        is_voided=True
                    ).first()
                    
                    if grade:
                        grade.is_voided = False
                        grade.voided_by = None
                        grade.voided_at = None
                        grade.voided_reason = None
                        unvoided_count += 1
                
                message = f'Restored assignment "{assignment.title}" for {unvoided_count} student(s)'
        
        db.session.commit()
        flash(message, 'success')
        return jsonify({'success': True, 'message': message, 'unvoided_count': unvoided_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500



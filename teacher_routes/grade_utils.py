"""
Utility functions for grade calculations including:
- Grade scales (with +/- support)
- Late penalty calculations
- Extra credit handling
- Grade statistics
"""

import json
from datetime import datetime, timedelta
from models import Assignment, Grade, Submission


def get_default_grade_scale():
    """Get the default grade scale."""
    return {
        "A": 90,
        "B": 80,
        "C": 70,
        "D": 60,
        "F": 0,
        "use_plus_minus": True
    }


def parse_grade_scale(assignment):
    """Parse grade scale from assignment, return default if not set."""
    if assignment.grade_scale:
        try:
            scale = json.loads(assignment.grade_scale)
            # Ensure required keys exist
            for key in ["A", "B", "C", "D", "F"]:
                if key not in scale:
                    scale[key] = get_default_grade_scale()[key]
            if "use_plus_minus" not in scale:
                scale["use_plus_minus"] = True
            return scale
        except:
            pass
    return get_default_grade_scale()


def calculate_letter_grade(percentage, grade_scale=None):
    """
    Calculate letter grade from percentage using grade scale.
    
    Args:
        percentage: Grade percentage (0-100)
        grade_scale: Dictionary with grade thresholds, or None for default
    
    Returns:
        Letter grade string (e.g., "A", "A-", "B+", "B", "B-", etc.)
    """
    if grade_scale is None:
        grade_scale = get_default_grade_scale()
    
    use_plus_minus = grade_scale.get("use_plus_minus", True)
    a_threshold = grade_scale.get("A", 90)
    b_threshold = grade_scale.get("B", 80)
    c_threshold = grade_scale.get("C", 70)
    d_threshold = grade_scale.get("D", 60)
    
    if percentage >= a_threshold:
        if use_plus_minus:
            if percentage >= a_threshold + 3:
                return "A"
            elif percentage >= a_threshold:
                return "A-"
        return "A"
    elif percentage >= b_threshold:
        if use_plus_minus:
            if percentage >= b_threshold + 3:
                return "B+"
            elif percentage >= b_threshold:
                return "B"
            else:
                return "B-"
        return "B"
    elif percentage >= c_threshold:
        if use_plus_minus:
            if percentage >= c_threshold + 3:
                return "C+"
            elif percentage >= c_threshold:
                return "C"
            else:
                return "C-"
        return "C"
    elif percentage >= d_threshold:
        if use_plus_minus:
            if percentage >= d_threshold + 3:
                return "D+"
            elif percentage >= d_threshold:
                return "D"
            else:
                return "D-"
        return "D"
    else:
        return "F"


def calculate_late_penalty(assignment, submission_date, due_date):
    """
    Calculate late penalty points based on assignment settings.
    
    Args:
        assignment: Assignment object
        submission_date: DateTime when assignment was submitted
        due_date: DateTime when assignment was due
    
    Returns:
        Tuple of (penalty_points, days_late)
    """
    if not assignment.late_penalty_enabled or assignment.late_penalty_per_day == 0:
        return (0.0, 0)
    
    if submission_date <= due_date:
        return (0.0, 0)
    
    # Calculate days late
    days_late = (submission_date - due_date).days
    if days_late <= 0:
        return (0.0, 0)
    
    # Apply max days limit if set
    if assignment.late_penalty_max_days > 0:
        days_late = min(days_late, assignment.late_penalty_max_days)
    
    # Calculate penalty percentage
    penalty_percentage = days_late * assignment.late_penalty_per_day
    
    # Calculate penalty points (based on total_points)
    penalty_points = (penalty_percentage / 100.0) * assignment.total_points
    
    return (penalty_points, days_late)


def calculate_final_grade(points_earned, total_points, extra_credit_points=0.0, late_penalty_points=0.0):
    """
    Calculate final grade with extra credit and late penalty.
    
    Args:
        points_earned: Points student earned (before penalties)
        total_points: Total points for assignment
        extra_credit_points: Extra credit points earned
        late_penalty_points: Points deducted for late submission
    
    Returns:
        Dictionary with final_points, percentage, and max_possible
    """
    # Apply late penalty
    final_points = max(0, points_earned - late_penalty_points)
    
    # Add extra credit (can exceed total_points)
    final_points += extra_credit_points
    
    # Calculate percentage (based on total_points, not including extra credit)
    percentage = (final_points / total_points * 100) if total_points > 0 else 0
    
    # Max possible includes extra credit
    max_possible = total_points + extra_credit_points
    
    return {
        "points_earned": points_earned,
        "extra_credit_points": extra_credit_points,
        "late_penalty_points": late_penalty_points,
        "final_points": final_points,
        "total_points": total_points,
        "max_possible": max_possible,
        "percentage": round(percentage, 2)
    }


def calculate_assignment_statistics(assignment_id):
    """
    Calculate statistics for an assignment.
    
    Returns:
        Dictionary with average, median, mode, min, max, std_dev, grade_distribution
    """
    grades = Grade.query.filter_by(
        assignment_id=assignment_id,
        is_voided=False
    ).all()
    
    if not grades:
        return {
            "total_students": 0,
            "graded_students": 0,
            "average": 0,
            "median": 0,
            "mode": 0,
            "min": 0,
            "max": 0,
            "std_dev": 0,
            "grade_distribution": {}
        }
    
    percentages = []
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            percentage = grade_data.get('percentage', 0)
            if percentage > 0:
                percentages.append(percentage)
        except:
            continue
    
    if not percentages:
        return {
            "total_students": len(grades),
            "graded_students": 0,
            "average": 0,
            "median": 0,
            "mode": 0,
            "min": 0,
            "max": 0,
            "std_dev": 0,
            "grade_distribution": {}
        }
    
    percentages.sort()
    n = len(percentages)
    
    # Calculate statistics
    average = sum(percentages) / n
    median = percentages[n // 2] if n % 2 == 1 else (percentages[n // 2 - 1] + percentages[n // 2]) / 2
    min_grade = min(percentages)
    max_grade = max(percentages)
    
    # Calculate standard deviation
    variance = sum((x - average) ** 2 for x in percentages) / n
    std_dev = variance ** 0.5
    
    # Calculate mode (most common grade range)
    grade_ranges = {}
    for p in percentages:
        range_key = f"{(p // 10) * 10}-{(p // 10) * 10 + 9}"
        grade_ranges[range_key] = grade_ranges.get(range_key, 0) + 1
    mode_range = max(grade_ranges.items(), key=lambda x: x[1])[0] if grade_ranges else "0-9"
    
    # Grade distribution (A, B, C, D, F)
    distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for p in percentages:
        if p >= 90:
            distribution["A"] += 1
        elif p >= 80:
            distribution["B"] += 1
        elif p >= 70:
            distribution["C"] += 1
        elif p >= 60:
            distribution["D"] += 1
        else:
            distribution["F"] += 1
    
    return {
        "total_students": len(grades),
        "graded_students": n,
        "average": round(average, 2),
        "median": round(median, 2),
        "mode": mode_range,
        "min": round(min_grade, 2),
        "max": round(max_grade, 2),
        "std_dev": round(std_dev, 2),
        "grade_distribution": distribution
    }


"""Report cards API for the React management SPA."""



from __future__ import annotations



from flask import jsonify, request

from flask_login import current_user, login_required



from decorators import admin_required, permissions_required

from extensions import db

from management_routes.report_cards_spa_helpers import (

    delete_report_card_record,

    query_report_card_comment_prefill,

    query_report_card_detail,

    query_report_card_generate_form,

    query_report_cards_category,

    query_report_cards_hub,
    query_report_cards_search,
    query_pending_report_cards,
    query_student_classes_for_report_card,

    query_student_report_card_details,

    query_student_report_card_history,
    query_student_report_card_school_years,
    submit_report_card_generate,

)

from models import ReportCard

from utils.report_card_portal import (

    approve_report_card_for_parents,

    revoke_report_card_parent_access,

)

from utils.user_roles import canonical_role_label



from . import spa_api_blueprint





@spa_api_blueprint.route("/report-cards/hub")

@login_required

@permissions_required("report_cards:view", "report_cards:generate")

def report_cards_hub():

    return jsonify(query_report_cards_hub())





@spa_api_blueprint.route("/report-cards/categories/<category>")

@login_required

@permissions_required("report_cards:view", "report_cards:generate")

def report_cards_category(category: str):

    payload = query_report_cards_category(category)

    if payload is None:

        return jsonify({"error": "Invalid grade category."}), 404

    return jsonify(payload)





@spa_api_blueprint.route("/report-cards/pending")
@login_required
@permissions_required("report_cards:view", "report_cards:generate")
def report_cards_pending():
    return jsonify(query_pending_report_cards())


@spa_api_blueprint.route("/report-cards/search")
@login_required
@permissions_required("report_cards:view", "report_cards:generate")
def report_cards_search():
    params = {
        "page": request.args.get("page", type=int),
        "per_page": request.args.get("per_page", type=int),
        "school_year_id": request.args.get("school_year_id", type=int),
        "quarter": request.args.get("quarter", type=str),
        "student_id": request.args.get("student_id", type=int),
        "class_id": request.args.get("class_id", type=int),
        "q": request.args.get("q", type=str),
    }
    return jsonify(query_report_cards_search(params))


@spa_api_blueprint.route("/report-cards/generate-form")

@login_required

@permissions_required("report_cards:generate")

def report_cards_generate_form():

    student_id = request.args.get("student_id", type=int)

    category = (request.args.get("category") or "").strip()
    default_school_year_id = request.args.get("school_year_id", type=int)
    return jsonify(
        query_report_card_generate_form(
            student_id=student_id,
            category=category,
            default_school_year_id=default_school_year_id,
        )
    )





@spa_api_blueprint.route("/report-cards/generate", methods=["POST"])

@login_required

@permissions_required("report_cards:generate")

def report_cards_generate():

    payload = request.get_json(silent=True) or {}

    result = submit_report_card_generate(payload)

    status = 200 if result.get("success") else 400

    return jsonify(result), status





@spa_api_blueprint.route("/report-cards/comments")

@login_required

@permissions_required("report_cards:generate")

def report_cards_comments():

    student_id = request.args.get("student_id", type=int)

    school_year_id = request.args.get("school_year_id", type=int)

    class_ids = [int(x) for x in request.args.getlist("class_ids") if str(x).isdigit()]

    result = query_report_card_comment_prefill(student_id, school_year_id, class_ids)

    if not result.get("success"):

        return jsonify(result), 400

    return jsonify(result)





@spa_api_blueprint.route("/report-cards/students/<int:student_id>/details")

@login_required

@permissions_required("report_cards:generate")

def report_cards_student_details(student_id: int):

    payload = query_student_report_card_details(student_id)

    if payload is None:

        return jsonify({"error": "Student not found."}), 404

    return jsonify({"success": True, "student": payload})





@spa_api_blueprint.route("/report-cards/students/<int:student_id>/classes")

@login_required

@permissions_required("report_cards:generate")

def report_cards_student_classes(student_id: int):

    school_year_id = request.args.get("school_year_id", type=int)

    quarters = request.args.getlist("quarters")

    return jsonify(query_student_classes_for_report_card(student_id, school_year_id, quarters))





@spa_api_blueprint.route("/report-cards/students/<int:student_id>/school-years")
@login_required
@permissions_required("report_cards:view", "report_cards:generate")
def report_cards_student_school_years(student_id: int):
    payload = query_student_report_card_school_years(student_id)
    if payload is None:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(payload)


@spa_api_blueprint.route("/report-cards/students/<int:student_id>/history")

@login_required

@permissions_required("report_cards:view", "report_cards:generate")

def report_cards_student_history(student_id: int):

    payload = query_student_report_card_history(student_id)

    if payload is None:

        return jsonify({"error": "Student not found."}), 404

    return jsonify(payload)





@spa_api_blueprint.route("/report-cards/<int:report_card_id>/pdf")

@login_required

@permissions_required("report_cards:view", "report_cards:generate")

def report_cards_pdf(report_card_id: int):

    report_card = ReportCard.query.get_or_404(report_card_id)

    try:

        from management_routes.reports import build_report_card_pdf_response



        return build_report_card_pdf_response(report_card)

    except ImportError:

        return jsonify({"error": "PDF generation requires WeasyPrint."}), 500

    except Exception as exc:

        from werkzeug.exceptions import HTTPException



        if isinstance(exc, HTTPException):

            raise

        return jsonify({"error": f"Error generating PDF: {exc}"}), 500





@spa_api_blueprint.route("/report-cards/<int:report_card_id>", methods=["GET", "DELETE"])

@login_required

@permissions_required("report_cards:view", "report_cards:generate")

def report_cards_detail_or_delete(report_card_id: int):

    if request.method == "DELETE":

        result = delete_report_card_record(report_card_id)

        status = 200 if result.get("success") else 400

        return jsonify(result), status



    is_director = canonical_role_label(current_user.role) == "Director"

    payload = query_report_card_detail(report_card_id, is_director=is_director)

    if payload is None:

        return jsonify({"error": "Report card not found."}), 404

    return jsonify(payload)





@spa_api_blueprint.route("/report-cards/<int:report_card_id>/approve", methods=["POST"])

@login_required

@admin_required

def report_cards_approve(report_card_id: int):

    report_card = ReportCard.query.get_or_404(report_card_id)

    try:

        approve_report_card_for_parents(report_card, current_user.id)

        db.session.commit()

        return jsonify({"success": True, "message": "Report card approved for Family Portal."})

    except ValueError as exc:

        return jsonify({"success": False, "message": str(exc)}), 400

    except Exception as exc:

        db.session.rollback()

        return jsonify({"success": False, "message": f"Could not approve report card: {exc}"}), 500





@spa_api_blueprint.route("/report-cards/<int:report_card_id>/revoke", methods=["POST"])

@login_required

@admin_required

def report_cards_revoke(report_card_id: int):

    report_card = ReportCard.query.get_or_404(report_card_id)

    try:

        revoke_report_card_parent_access(report_card)

        db.session.commit()

        return jsonify({"success": True, "message": "Report card removed from Family Portal."})

    except Exception as exc:

        db.session.rollback()

        return jsonify({"success": False, "message": f"Could not revoke parent access: {exc}"}), 500


from flask import Blueprint, jsonify, request
from app.models import Student, db
from flask_jwt_extended import jwt_required, get_jwt

bp = Blueprint("student", __name__)


@bp.route("/students/<int:student_id>", methods=["DELETE"])
# 處理刪除學生
@jwt_required()
def delete_student(student_id):
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")

    # 檢查使用者是否為老師
    if user_type != "teacher":
        return jsonify({"message": "Access forbidden: Teachers only."}), 403

    try:
        # 檢查學生資料是否存在
        student = Student.query.get(student_id)

        if not student:
            return jsonify({"message": "Student not found."}), 404

        # 刪除學生
        db.session.delete(student)
        db.session.commit()

        return jsonify(
            {"message": f"Student with ID {student_id} has been deleted."}
        ), 200

    except Exception as e:
        bp.logger.error(f"Error deleting student: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while deleting the student"})


@bp.route("/students/<int:student_id>/group/<int:group_num>", methods=["PUT"])
# 處理小組變更
@jwt_required()
def change_student_group(student_id, group_num):
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")

    # 檢查使用者是否為老師
    if user_type != "teacher":
        return jsonify({"message": "Access forbidden: Teachers only."}), 403

    try:
        # 檢查學生資料是否存在
        student = Student.query.get(student_id)

        if not student:
            return jsonify({"message": "Student not found."}), 404

        # 修改學生小組
        student.group_number = group_num

        db.session.commit()

        return jsonify(
            {
                "message": f"The group of student with ID {student_id} has been changed to {group_num}."
            }
        ), 200

    except Exception as e:
        bp.logger.error(f"Error changing group of student: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while changing group of student"})


@bp.route("/listgroups/<int:course_id>", methods=["GET"])
# 處理查詢組別
@jwt_required()
def listgroups(course_id):
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")

    # 檢查使用者是否為老師
    if user_type != "teacher":
        return jsonify({"message": "Access forbidden: Teachers only."}), 403

    try:
        unique_groups = (
            db.session.query(Student.group_number)
            .distinct()
            .order_by(Student.group_number)
            .all()
        )

        group_numbers = [group[0] for group in unique_groups if group[0] != -1]

        return jsonify({"groups": group_numbers}), 200

    except Exception as e:
        bp.logger.error(f"Error fetching groups: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while fetching groups"})


@bp.route("/deletegroup/<int:course_id>", methods=["DELETE"])
# 處理查詢組別
@jwt_required()
def deletegroup(course_id):
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")
    group_number = request.form.get("group_number")
    # 檢查使用者是否為老師
    if user_type != "teacher":
        return jsonify({"message": "Access forbidden: Teachers only."}), 403

    try:
        students_to_update = Student.query.filter_by(
            group_number=group_number, course_id=course_id
        ).all()

        for student in students_to_update:
            student.group_number = -1
        db.session.commit()
        return jsonify({"message": f"Deleting group {group_number} sucessfully."})

    except Exception as e:
        bp.logger.error(f"Error deleting group: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while deleting group"})

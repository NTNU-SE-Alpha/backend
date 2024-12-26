from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from app.models import Course, Teacher, db, CourseSections
from datetime import datetime

bp = Blueprint("course", __name__)


@bp.route("/courses", methods=["GET"])
# 處理教師查詢課堂
@jwt_required()
def get_teacher_courses():
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")

    # 檢查使用者是否為老師
    if user_type != "teacher":
        return jsonify({"message": "Access forbidden: Teachers only."}), 403

    try:
        teacher = Teacher.query.get(user_id)
        if not teacher:
            return jsonify({"message": "Teacher not found."}), 404

        # 取得所有屬於該老師，且非封存的課程
        courses = Course.query.filter_by(teacher_id=teacher.id, archive=False).all()

        # 將資料轉為 dict
        courses_data = [course.to_dict() for course in courses]

        return jsonify({"courses": courses_data}), 200

    except Exception as e:
        bp.logger.error(f"Error retrieving courses for teacher ID {user_id}: {e}")
        return jsonify({"message": "An error occurred while retrieving courses."}), 500


@bp.route("/getCourseInfo/<int:course_id>")
# 取得課程資訊
def get_course(course_id):
    course = Course.query.get(course_id)
    if course:
        return course.to_dict()
    else:
        return jsonify({"error": "Course not found"}), 404

@bp.route("/getStudents/<int:course_id>")
def get_students(course_id):
    course = Course.query.get(course_id)
    if course:
        students = [
            {
                "id": student.id,
                "username": student.username,
                "name": student.name,
                "group": student.group_number,
            }
            for student in course.students
        ]
        return jsonify({"students": students}), 200


@bp.route("/toggle_favorite/<int:course_id>", methods=["PUT"])
@jwt_required()
def add_favorite(course_id):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400
    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
        course = Course.query.filter_by(id=course_id, teacher_id=user.id).first()
        if not course:
            return jsonify({"error": "Course not found or not owned by teacher"}), 404
        if course.is_favorite:
            course.is_favorite = False
        else:
            course.is_favorite = True
        db.session.commit()
        return jsonify({"success": "Course favorite toggled"}), 200


@bp.route("/favorites", methods=["GET"])
@jwt_required()
def get_favorites():
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400
    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
        favorites = Course.query.filter_by(teacher_id=user.id, is_favorite=True).all()
        favorite_list = []
        for course in favorites:
            c = get_course(course.id)
            favorite_list.append(c)
        return jsonify({"favorites": favorite_list}), 200


@bp.route("/courses/<int:course_id>", methods=["PUT"])
# 處理教師變更課程資料
@jwt_required()
def update_course_data():
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")

    # 檢查使用者是否為老師
    if user_type != "teacher":
        return jsonify({"message": "Access forbidden: Teachers only."}), 403

    # 檢查課程是否存在
    course = Course.query.get("course_id")
    if not course:
        return jsonify({"message": "Course not found."}), 404

    # 檢查該課程是否屬於該老師
    if course.teacher_id != user_id:
        return jsonify(
            {
                "message": "Access forbidden: Only the owner teacher can edit this course."
            }
        ), 403

    data = request.get_json()

    # 更新課程資訊
    if "name" in data:
        course.name = data["name"]
    if "teacher_id" in data:
        course.teacher_id = data["teacher_id"]
    if "weekday" in data:
        course.weekday = data["weekday"]
    if "semester" in data:
        course.semester = data["semester"]
    if "archive" in data:
        course.archive = data["archive"]
    if "image_id" in data:
        course.image_id = data["image_id"]
    if "is_favorite" in data:
        course.is_favorite = data["is_favorite"]

    try:
        db.session.commit()

        return jsonify({"message": "Course updated successfully"}), 200

    except Exception as e:
        bp.logger.error(f"Error updating course: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while updating the course"}), 500


@bp.route("/getSections/<int:course_id>", methods=["GET"])
@jwt_required()
# 取得每週課程資訊
def get_course_sections(course_id):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")

    course = Course.query.get(course_id)
    if course:
        if user_type == "student":
            # 檢查該學生是否為課程學生
            if course.is_student(user_id):
                sections = course.get_sections()
                sections_data = [section.to_dict() for section in sections]
                return jsonify({"sections": sections_data}), 200
            else:
                # Return a response if the student is not part of the course
                return jsonify({"error": "You are not a student of this course"}), 403
        elif user_type == "teacher":
            if course.teacher_id == user_id:
                sections = course.get_sections()
                sections_data = [section.to_dict() for section in sections]
                return jsonify({"sections": sections_data}), 200
            else:
                # Return a response if the student is not part of the course
                return jsonify({"error": "You are not a teacher of this course"}), 403
        else:
            return jsonify({"error": "Error"}), 403
    else:
        return jsonify({"error": "Course not found"}), 404


@bp.route("/deleteSection/<int:course_id>/<int:course_section_id>", methods=["DELETE"])
@jwt_required()
def delete_course_section(course_id, course_section_id):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    if user_type != "teacher":
        return jsonify({"error": "Access forbidden"}), 403

    if course.teacher_id != user_id:
        return jsonify({"error": "You are not a teacher of this course"}), 403

    course_section = CourseSections.query.filter_by(id=course_section_id, course_id=course_id).first()
    if not course_section:
        return jsonify({"error": "Course section not found"}), 404

    try:
        db.session.delete(course_section)
        db.session.commit()
        return jsonify({"message": "Course section deleted successfully"}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An error occurred while deleting the course section"}), 500

# Create a Course Section
@bp.route("/newSection/<int:course_id>", methods=["POST"])
def create_course_section(course_id):
    data = request.get_json()
    try:
        new_course_section = CourseSections(
            sequence=data['sequence'],
            name=data['name'],
            course_id=course_id,
            content=data.get('content'),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            publish_date=datetime.fromisoformat(data['publish_date'])
        )
        db.session.add(new_course_section)
        db.session.commit()
        return jsonify(new_course_section.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return  jsonify({"message": f"Error occured while creating new course section: {e}"}), 500
    
@bp.route("/editSection/<int:course_id>/<int:course_section_id>", methods=["PUT"])
def update_course_section(course_id, course_section_id):
    data = request.get_json()
    section = CourseSections.query.get(course_section_id)
    if not section:
        return jsonify({"message": "Course section not found."}), 404 
    try:
        if 'sequence' in data:
            section.sequence = data.get('sequence', section.sequence)
        if 'name' in data:
            section.name = data.get('name', section.name)
        if'content' in data:
            section.content = data.get('content', section.content)
        if 'start_date' in data:
            section.start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            section.end_date = datetime.fromisoformat(data['end_date'])
        if 'publish_date' in data:
            section.publish_date = datetime.fromisoformat(data['publish_date'])
        
        db.session.commit()
        return jsonify(section.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error while editing course seciton. {e}"}), 500 
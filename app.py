from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from models import db, Teacher, Student, Course
from config import Config
from marshmallow import ValidationError
from schemas import LoginSchema, UserDataUpdateSchema
from flask_migrate import Migrate


app = Flask(__name__)
app.config.from_object(Config)

migrate = Migrate(app, db)

db.init_app(app)
jwt = JWTManager(app)

@app.route("/login", methods=["POST"])
# 處理使用者登入
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Username and password are required."}), 400

    schema = LoginSchema()
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # 先檢查是否為老師
    user = Teacher.query.filter_by(username=validated_data["username"]).first()
    user_type = "teacher"

    if not user:
        # 如果不是老師，則檢查是否為學生
        user = Student.query.filter_by(username=validated_data["username"]).first()
        user_type = "student"

    # 如果不是老師也不是學生
    if not user:
        return jsonify({"message": "Invalid username or password."}), 401

    # 如果帳號或密碼錯誤
    if not user.check_password(validated_data["password"]):
        return jsonify({"message": "Invalid username or password."}), 401

    # 產生 JWT Token
    additional_claims = {"user_type": user_type, "user_id": user.id}
    access_token = create_access_token(
        identity=validated_data["username"], additional_claims=additional_claims
    )

    # 回傳使用者的資料
    if user_type == "teacher":
        user_info = {
            "id": user.id,
            "username": user.username,
            "name": user.name
        }
    else:
        user_info = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "course": user.course,
            "group": user.group_number,
        }

    return jsonify({"access_token": access_token, "user": user_info}), 200


@app.route("/user", methods=["GET"])
# 處理使用者資料獲取
@jwt_required()
def get_user_data():
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")

    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    # 根據 Claims 中的 user_type 來獲取資料
    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        user_info = {"id": user.id, 
            "username": user.username,
            "name": user.name
        }

    elif user_type == "student":
        user = Student.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        user_info = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "course": user.course,
            "group": user.group_number,
        }

    else:
        return jsonify({"message": "Invalid user type."}), 400

    return jsonify({"user": user_info}), 200


@app.route("/user", methods=["PUT"])
# 處理使用者資料變更
@jwt_required()
def update_user_data():
    # 從 JWT Token 中取得資料(claims)
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")

    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    data = request.get_json()
    schema = UserDataUpdateSchema()
    try:
        # 檢查使用者輸入的資料
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    try:
        # 如果是老師
        if user_type == "teacher":
            user = Teacher.query.get(user_id)
            if not user:
                return jsonify({"message": "User not found."}), 404

            # 檢查請求是否包含要更改的資料
            if "password" in validated_data:
                user.set_password(validated_data["password"])

            db.session.commit()

            user_info = {"id": user.id,
                "username": user.username,
                "name": user.name
            }
            
        # 如果是學生
        elif user_type == "student":
            user = Student.query.get(user_id)
            if not user:
                return jsonify({"message": "User not found."}), 404
            
            # 檢查請求是否包含要更改的資料
            if "password" in validated_data:
                user.set_password(validated_data["password"])

            db.session.commit()

            user_info = {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "course": user.course,
                "group": user.group_number,
            }

        else:
            return jsonify({"message": "Invalid user type."}), 400

        return jsonify({"user": user_info}), 200

    except Exception as e:
        print(f"Error updating user data: {e}")
        return jsonify({"message": "Internal server error."}), 500


@app.route("/students/<int:student_id>", methods=["DELETE"])
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
        app.logger.error(f"Error deleting student: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while deleting the student"})


@app.route("/courses", methods=["GET"])
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
        app.logger.error(f"Error retrieving courses for teacher ID {user_id}: {e}")
        return jsonify({"message": "An error occurred while retrieving courses."}), 500


if __name__ == "__main__":
    app.run(debug=True)

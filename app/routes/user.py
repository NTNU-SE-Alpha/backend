from flask import Blueprint, jsonify
from app.models import Teacher, Student, db
from flask_jwt_extended import jwt_required, get_jwt
from flask import Flask, jsonify, request
from app.schemas import UserDataUpdateSchema
from marshmallow import ValidationError

bp = Blueprint('user', __name__)
@bp.route("/user", methods=["GET"])
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

        user_info = {
            "id": user.id,
            "user_type": "teacher",
            "username": user.username,
            "name": user.name,
        }

    elif user_type == "student":
        user = Student.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        user_info = {
            "id": user.id,
            "user_type": "student",
            "username": user.username,
            "name": user.name,
            "course": user.course,
            "group": user.group_number,
        }

    else:
        return jsonify({"message": "Invalid user type."}), 400

    return jsonify({"user": user_info}), 200


@bp.route("/user", methods=["PUT"])
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

            if "old_password" not in validated_data:
                return jsonify({"message": "Please input your current password"}), 400

            if not user.check_password(validated_data["old_password"]):
                return jsonify({"message": "Old password is incorrect."}), 400

            # 檢查請求是否包含要更改的資料
            if "new_password" in validated_data:
                user.set_password(validated_data["new_password"])

            db.session.commit()

            user_info = {"id": user.id, "username": user.username, "name": user.name}

        # 如果是學生
        elif user_type == "student":
            user = Student.query.get(user_id)
            if not user:
                return jsonify({"message": "User not found."}), 404

            if "old_password" not in validated_data:
                return jsonify({"message": "Please input your current password"}), 400

            if not user.check_password(validated_data["old_password"]):
                return jsonify({"message": "Old password is incorrect."}), 400

            # 檢查請求是否包含要更改的資料
            if "new_password" in validated_data:
                user.set_password(validated_data["new_password"])

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


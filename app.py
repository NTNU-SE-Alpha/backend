import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, jwt_required
from flask_migrate import Migrate
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from marshmallow import ValidationError

from AI.teacher import AITeacher
from config import Config
from models import (
    Conversation,
    Course,
    Student,
    Teacher,
    TeacherFaiss,
    TeacherFiles,
    db,
)
from schemas import LoginSchema, UserDataUpdateSchema

ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
cors = CORS(app)
app.config.from_object(Config)

migrate = Migrate(app, db)

db.init_app(app)
jwt = JWTManager(app)

aiteacher = AITeacher(app.config['OPENAI_API_KEY'])


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
        user_info = {"id": user.id, "username": user.username, "name": user.name}
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

        user_info = {"id": user.id, "username": user.username, "name": user.name}

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

            user_info = {"id": user.id, "username": user.username, "name": user.name}

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


@app.route("/getCourseInfo/<int:course_id>")
# 取得課程資訊
def get_course(course_id):
    course = Course.query.get(course_id)
    if course:
        return course.to_dict()
    else:
        return {"error": "Course not found"}, 404


@app.route("/getSections/<int:course_id>")
# 取得每週課程資訊
def get_course_sections(course_id):
    course = Course.query.get(course_id)
    if course:
        # 檢查該學生是否為課程學生
        if course.is_student(course_id):
            sections = course.get_sections()
            sections_data = [section.to_dict() for section in sections]
            return jsonify({"sections": sections_data}), 200
    else:
        return {"error": "Course not found"}, 404


@app.route("/getStudents/<int:course_id>")
def get_students(course_id):
    course = Course.query.get(course_id)
    if course:
        students = [
            {"id": student.id, "username": student.username, "name": student.name}
            for student in course.students
        ]
        return jsonify({"students": students}), 200


# 檢查檔案類型是否允許
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# 儲存檔案
def save_file(file):
    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        return filename
    return None


# API: 上傳檔案處理
@app.route("/api/upload", methods=["POST"])
def upload_file():
    # 檢查是否有文件
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    # 檢查是否有文件選擇
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # 儲存檔案
    filename = save_file(file)
    if filename:
        return jsonify(
            {"message": "File uploaded successfully", "filename": filename}
        ), 200
    else:
        return jsonify({"error": "File type not allowed"}), 400


# API 回傳以及顯示上傳的檔案:
@app.route("/api/uploads/<filename>", methods=["GET"])
def get_uploaded_file(filename):
    # 確認檔案存在
    if os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], filename)):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    else:
        return jsonify({"error": "File not found"}), 404


@app.route("/start_conversation", methods=["GET"])
@jwt_required()
def start_conversation():
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    new_conversation = Conversation(teacher_id=user_id)
    db.session.add(new_conversation)
    db.session.commit()
    return jsonify({"uuid": new_conversation.uuid})


@app.route("/chat/<string:conversation_uuid>", methods=["POST"])
@jwt_required()
def chat(conversation_uuid):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    if not conversation_uuid:
        return jsonify({"message": "The UUID of conversation is required."}), 400

    conversation = Conversation.query.filter_by(uuid=conversation_uuid).first()

    if conversation is None:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    if conversation.teacher_id != user_id:
        return jsonify({"message": "Not authorized."}), 401

    data = request.json
    user_input = data.get("user_input", "").strip()

    if not user_input:
        return jsonify(
            {"message": "The UUID of conversation and the user input are required."}
        ), 400

    if "file_id" in data:
        file = TeacherFiles.query.filter_by(id=data["file_id"]).first()

        if file is None:
            return jsonify({"message": "file_id is invalid."}), 400

        file_content = aiteacher.extract_text_from_pdf(file.path)

        if not file_content:
            return jsonify({"message": "Unable to read file."}), 400

        faiss_file = TeacherFaiss.query.filter_by(file_id=data["file_id"]).first()

        if faiss_file is not None:
            index, sentences = aiteacher.load_faiss_index(data["file_id"])
            print(sentences)
            if index is None or sentences is None:
                faiss_index = TeacherFaiss.query.get(faiss_file.id)
                db.session.delete(faiss_index)
                db.session.commit()
                return jsonify({"message": "Unable to read faiss file"}), 400
        else:
            index, sentences = aiteacher.build_faiss_index(file_content, data["file_id"])

            if index is None or sentences is None:
                print("建立索引失敗，程式結束。")
                return

            faiss_index = TeacherFaiss(file_id=data["file_id"])
            db.session.add(faiss_index)
            db.session.commit()

        aiteacher.system_context = f"""您是一位AI教學助手。
以下是課程內容的摘要：{file_content[:1000]}...
請基於上述內容來回答問題。如果需要引入新的例子或故事，請確保與原始課程內容保持關聯。"""

        relevant_context = aiteacher.search_rag(user_input, index, sentences)

        context = "\n".join(relevant_context)

    else:
        aiteacher.system_context = ""
        context = ""

    conversation, conversation_history = aiteacher.load_conversation_history(
        conversation_uuid
    )
    if not conversation:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    if len(conversation_history) == 0:
        conversation.summary = aiteacher.summarize_text(user_input)
        db.session.commit()

    messages = [
        SystemMessage(content=aiteacher.system_context),
        SystemMessage(content=f"相關上下文：\n\n{context}"),
    ]

    for _, q, a, _ in conversation_history:
        messages.append(HumanMessage(content=q))
        messages.append(AIMessage(content=a))

    messages.append(HumanMessage(user_input))

    answer = aiteacher.generate_response(messages)
    conversation_history.append((user_input, answer))

    aiteacher.save_message(conversation.id, "user", user_input)
    aiteacher.save_message(conversation.id, "assistant", answer)

    return jsonify({"answer": answer})


@app.route("/history/<string:conversation_uuid>", methods=["GET"])
@jwt_required()
def get_history(conversation_uuid):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    if not conversation_uuid:
        return jsonify({"message": "The UUID of conversation is required."}), 400

    conversation = Conversation.query.filter_by(uuid=conversation_uuid).first()

    if conversation is None:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    if conversation.teacher_id != user_id:
        return jsonify({"message": "Not authorized."}), 401

    conversation, conversation_history = aiteacher.load_conversation_history(
        conversation_uuid
    )

    if not conversation:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    formatted_history = [
        {
            "id": id,
            "sender": sender,
            "message": msg,
            "sent_at": sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for id, sender, msg, sent_at in conversation_history
    ]
    return jsonify({"uuid": conversation_uuid, "history": formatted_history})


@app.route("/list_conversations", methods=["GET"])
@jwt_required()
def list_conversations():
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    conversations = Conversation.query.filter_by(teacher_id=user_id).all()

    conversation_list = [
        {
            "uuid": conversation.uuid,
            "summary": conversation.summary
            if conversation.summary
            else "No summary available",
            "created_at": conversation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for conversation in conversations
    ]

    return jsonify({"conversations": conversation_list})


if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    if not os.path.exists(aiteacher.save_dir):
        os.makedirs(aiteacher.save_dir)

    app.run(debug=True)

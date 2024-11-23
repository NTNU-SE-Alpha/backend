import hashlib
import io
import os

from AI.teacher import AITeacher
from config import Config
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, jwt_required
from flask_migrate import Migrate
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from marshmallow import ValidationError
from PIL import Image
from schemas import LoginSchema, RegisterSchema, UserDataUpdateSchema
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from models import (
    Conversation,
    Course,
    Student,
    StudentFiles,
    Teacher,
    TeacherFaiss,
    TeacherFiles,
    Course_sections,
    db,
)

ALLOWED_EXTENSIONS = {'pdf'}
OTHER_ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'doc', 'docx', 'txt'}

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
        students = [{'id': student.id, 'username': student.username, 'name': student.name} for student in course.students]
        return jsonify({'students': students}), 200

# function: checksum & 儲存資訊到資料庫
def generate_checksum(filepath):
    # 計算檔案的 SHA256 
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# 學生和教師的資訊分別存到 teacher_files 或 student_files (有更新 models.py)
def save_file_info(uploader_id, uploader_type, class_id, filename, filepath):
    checksum = generate_checksum(filepath)

    if uploader_type == "teacher":
        new_file = TeacherFiles(
            class_id=class_id,
            teacher=uploader_id,
            name=filename,
            path=filepath,
            checksum=checksum
        )
    elif uploader_type == "student":
        new_file = StudentFiles(
            class_id=class_id,
            student=uploader_id,
            name=filename,
            path=filepath,
            checksum=checksum
        )
    else:
        return False

    db.session.add(new_file)
    db.session.commit()
    return new_file.id

# API: 上傳檔案處理 (更新: 將資訊存入資料庫)
@app.route('/api/upload_pdf', methods=['POST'])
@jwt_required()
def upload_pdf():
    claims = get_jwt()
    uploader_id = claims.get("user_id")
    uploader_type = claims.get("user_type")
    course_id = request.form.get("course_id")

    if not course_id:
        return jsonify({'error': 'Course ID is required'}), 400

    # 檢查是否有文件
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    # 檢查是否有文件選擇
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # 檢查檔案是否為 PDF
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    # 儲存檔案
    filename, filepath = save_file(file, ALLOWED_EXTENSIONS)
    if filename:
        # 呼叫 generate_checksum()
        # checksum = generate_checksum(filepath)
        
        # 呼叫 save_file_info() 儲存資訊進資料庫中
        file_id = save_file_info(uploader_id, uploader_type, course_id, filename, filepath)
        if file_id:
            return jsonify({'message': 'PDF file uploaded successfully', 'filename': filename, 'file_id': file_id}), 200
        else:
            return jsonify({'error': 'Failed to save file info'}), 500
    else:
        return jsonify({"error": "File type not allowed"}), 400


# 新增其他檔案類型的上傳功能
@app.route('/api/upload_various_file', methods=['POST'])
@jwt_required()
def upload_various_file():
    claims = get_jwt()
    uploader_id = claims.get("user_id")
    uploader_type = claims.get("user_type")
    class_id = request.form.get("class_id")  # 修改這裡，從 course_id 改為 class_id

    if not class_id:
        return jsonify({'error': 'Class ID is required'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename, filepath = save_file(file, OTHER_ALLOWED_EXTENSIONS)
    if filename:
        # 儲存檔案資訊到資料庫
        if save_file_info(uploader_id, uploader_type, class_id, filename, filepath):
            return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 200
        else:
            return jsonify({'error': 'Failed to save file info'}), 500
    return jsonify({'error': 'File type not allowed'}), 400

# secure_filename:
def save_file(file, allowed_extensions):
    if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1
        file.save(file_path)
        return filename, file_path
    return None, None
    
# 下載檔案api : api/download/ 仍在 debug 中
@app.route('/api/download/<int:file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    # class_id = request.args.get("class_id")
    course_id = request.form.get("course_id")

    if not course_id:
        return jsonify({'error': 'Class ID is required'}), 400

    if user_type == "teacher":
        file_record = TeacherFiles.query.filter_by(id=file_id, class_id=course_id, teacher=user_id).first()
    elif user_type == "student":
        file_record = StudentFiles.query.filter_by(id=file_id, class_id=course_id, student=user_id).first()
    else:
        return jsonify({'error': 'Access forbidden'}), 403

    if not file_record or not os.path.exists(file_record.path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_record.path, as_attachment=True)

@app.route("/start_conversation", methods=["POST"])
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

    course_id = request.form.get("course_id")
    course_section=request.form.get("course_section")
    new_conversation = Conversation(teacher_id=user_id, course_id=course_id, course_section=course_section)
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
    conversation_list = []
    for conversation in conversations:
        course=Course.query.filter_by(id=conversation.course_id).first()
        course_section=Course_sections.query.filter_by(course=conversation.course_id, sequence=conversation.course_section).first()
        conversation_list.append(
            {
                "uuid": conversation.uuid,
                "course_name": course.name,
                "course_section": course_section.name,
                "summary": conversation.summary
                if conversation.summary
                else "No summary available",
                "created_at": conversation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return jsonify({"conversations": conversation_list})



@app.route('/register', methods=["POST"])
def register():
    data = request.get_json()

    # 檢查必要填寫的欄位
    if not data or "username" not in data or "password" not in data or "user_type" not in data:
        return jsonify({"message": "Username, password, and user_type are required."}), 400

    schema = RegisterSchema()
    try:
        validated_data = schema.load(data)

        # 檢查 username 是否重複
        teacher_check = Teacher.query.filter_by(username=validated_data["username"]).first()
        student_check = Student.query.filter_by(username=validated_data["username"]).first()

        if teacher_check or student_check:
            return jsonify({"message": "Username already exists."}), 400

        # 檢查密碼是否符合規範 (長度不小於6)
        if len(validated_data["password"]) < 6:
            return jsonify({"message": "Password must be at least 8 characters long."}), 400

        # 密碼加密
        hashed_password = generate_password_hash(validated_data["password"])

        # 儲存使用者至資料庫
        if data["user_type"] == "teacher":
            if validated_data['group']:
                return jsonify({"message": "only user_type is student have group."}), 400
            # 檢查是否有提供教師的名字
            if not validated_data.get("name"):
                return jsonify({"message": "Teacher name is required."}), 400
            
            # 檢查是否有提供有效的 course 名稱
            course_name = data.get("course")
            if not course_name:
                return jsonify({"message": "Course name is required for students."}), 400
            
            # 從 Course 表中找到對應的課程
            course = Course.query.filter_by(name=course_name).first()
            if not course:
                return jsonify({"message": "Course not found."}), 400

            # 創建教師帳戶並設置密碼
            new_user = Teacher(
                username=validated_data["username"],
                name=validated_data["name"],
                password_hash=hashed_password
            )

            # 若course先存在, 老師選課程時自動加入
            if "course" in validated_data:
                course_name = validated_data["course"]
                course = Course.query.filter_by(name=course_name).first()
                if course:
                    course.teacher_id = new_user.id

        elif data["user_type"] == "student":
            # 檢查是否有提供有效的 course 名稱
            course_name = data.get("course")
            if not course_name:
                return jsonify({"message": "Course name is required for students."}), 400

            # 從 Course 表中找到對應的課程
            course = Course.query.filter_by(name=course_name).first()
            if not course:
                return jsonify({"message": "Course not found."}), 400

            # 創建學生帳戶並設置密碼
            new_user = Student(
                username=validated_data["username"],
                name=validated_data.get("name"),  # 假設學生有名字這個欄位
                group_number=validated_data.get("group", 1),  # 默認組號為 1
                password_hash=hashed_password,
                course=course.id  # 設置為 Course 表的 id
            )
        else:
            return jsonify({"message": "Invalid user type."}), 400

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User registered successfully."}), 201

    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500

@app.route('/add_favorite/<int:course_id>')
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
        course.is_favorite = True
        db.session.commit()
        return jsonify({"success": "Course marked as favorite"}), 200

@app.route('/favorites', methods=['GET'])
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

@app.route('/courses/<int:course_id>', methods=["PUT"])
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
        return jsonify({"message": "Access forbidden: Only the owner teacher can edit this course."}), 403
    
    data = request.get_json()

    #更新課程資訊
    if 'name' in data:
        course.name = data['name']
    if 'teacher_id' in data:
        course.teacher_id = data['teacher_id']
    if 'weekday' in data:
        course.weekday = data['weekday']
    if 'semester' in data:
        course.semester = data['semester']
    if 'archive' in data:
        course.archive = data['archive']
    if 'image_id' in data:
        course.image_id = data['image_id']
    if 'is_favorite' in data:
        course.is_favorite = data['is_favorite']
    
    try:
        db.session.commit()
        
        return jsonify({"message": "Course updated successfully"}), 200
    
    except Exception as e:
        app.logger.error(f"Error updating course: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while updating the course"}), 500
    
    
if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    if not os.path.exists(aiteacher.save_dir):
        os.makedirs(aiteacher.save_dir)

    app.run(debug=True)
from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from models import db, Teacher, Student, Course, TeacherFiles, StudentFiles
from config import Config
from marshmallow import ValidationError
from schemas import LoginSchema, UserDataUpdateSchema
from flask_migrate import Migrate
from flask_cors import CORS
from werkzeug.utils import secure_filename


import os
import hashlib


ALLOWED_EXTENSIONS = {'pdf'}
OTHER_ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'doc', 'docx', 'txt'}


app = Flask(__name__)
cors = CORS(app)
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

@app.route('/getCourseInfo/<int:course_id>')
# 取得課程資訊
def get_course(course_id):
    course = Course.query.get(course_id)
    if course:
        return course.to_dict()
    else:
        return {'error': 'Course not found'}, 404
    

@app.route('/getSections/<int:course_id>')
# 取得每週課程資訊
def get_course_sections(course_id):
    course = Course.query.get(course_id)
    if course:
        # 檢查該學生是否為課程學生
        if course.is_student(course_id):
            sections = course.get_sections()
            sections_data = [section.to_dict() for section in sections]
            return jsonify({'sections':sections_data }), 200
    else:
        return {'error': 'Course not found'}, 404

@app.route('/getStudents/<int:course_id>')
def get_students(course_id):
    course = Course.query.get(course_id)
    if course:
        students = [{'id': student.id, 'username': student.username, 'name': student.name} for student in course.students]
        return jsonify({'students': students}), 200

# 檢查檔案類型是否允許
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 儲存檔案
def save_file(file):
    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


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
    return True

# API: 上傳檔案處理 (更新: 將資訊存入資料庫)
@app.route('/api/upload_pdf', methods=['POST'])
@jwt_required()
def upload_pdf():
    claims = get_jwt()
    uploader_id = claims.get("user_id")
    uploader_type = claims.get("user_type")
    course_id = request.args.get("course_id")

    if not course_id:
        return jsonify({'error': 'Course ID is required'}), 400

    # 檢查是否有文件
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # 檢查是否有文件選擇
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 檢查檔案是否為 PDF
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    # 儲存檔案
    filename, filepath = save_file(file, ALLOWED_EXTENSIONS)
    if filename:
        # 呼叫 generate_checksum()
        checksum = generate_checksum(filepath)
        
        # 呼叫 save_file_info() 儲存資訊進資料庫中
        if save_file_info(uploader_id, uploader_type, course_id, filename, filepath, checksum):
            return jsonify({'message': 'PDF file uploaded successfully', 'filename': filename}), 200
        else:
            return jsonify({'error': 'Failed to save file info'}), 500
    else:
        return jsonify({'error': 'File type not allowed'}), 400

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
@app.route('/api/download/<filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    # class_id = request.args.get("class_id")
    class_id = request.form.get("class_id")

    if not class_id:
        return jsonify({'error': 'Class ID is required'}), 400

    if user_type == "teacher":
        file_record = TeacherFiles.query.filter_by(name=filename, class_id=class_id, teacher=user_id).first()
    elif user_type == "student":
        file_record = StudentFiles.query.filter_by(name=filename, class_id=class_id, student=user_id).first()
    else:
        return jsonify({'error': 'Access forbidden'}), 403

    if not file_record or not os.path.exists(file_record.path):
        return jsonify({'error': 'File not found'}), 404

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# API 回傳以及顯示上傳的檔案:
@app.route('/api/uploads/<filename>', methods=['GET'])
def get_uploaded_file(filename):
    # 確認檔案存在
    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        # Not Found: 404
        return jsonify({'error': 'File not found'}), 404

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)

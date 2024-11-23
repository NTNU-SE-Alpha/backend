from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from models import db, Teacher, Student, Course, Assignments, AssignmentFiles, Submissions
from config import Config
from marshmallow import ValidationError
from schemas import LoginSchema, UserDataUpdateSchema, RegisterSchema
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime

from werkzeug.security import generate_password_hash

import os

ALLOWED_EXTENSIONS = {'pdf'}

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


# API: 上傳檔案處理
@app.route('/api/upload', methods=['POST'])
def upload_file():
    # 檢查是否有文件
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # 檢查是否有文件選擇
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 儲存檔案
    filename = save_file(file)
    if filename:
        return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 200
    else:
        return jsonify({'error': 'File type not allowed'}), 400

# API 回傳以及顯示上傳的檔案:
@app.route('/api/uploads/<filename>', methods=['GET'])
def get_uploaded_file(filename):
    # 確認檔案存在
    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        return jsonify({'error': 'File not found'}), 404

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
    
# 新增作業功能    
@app.route("/assignments", methods=["POST"])
@jwt_required()
def create_assignment():
    claims = get_jwt()
    # 僅限教師新增作業
    if claims["user_type"] != "teacher":
        return jsonify({"message": "Only teachers can create assignments."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid data."}), 400

    try:
        title = data["title"]
        description = data.get("description", "")
        due_date = data["due_date"]
        course_id = data["course_id"]
        files = data.get("files", [])  # 檔案清單
    except KeyError as e:
        return jsonify({"message": f"Missing required field: {str(e)}"}), 400

    if not title or not due_date or not course_id:
        return jsonify({"message": "Missing required fields."}), 400

    try:
        # 新增作業基本資料
        new_assignment = Assignments(
            course_id=course_id,
            title=title,
            description=description,
            due_date=due_date,
            created_date=datetime.now(),
            modified_date=datetime.now(),
        )

        # 新增檔案
        for file_url in files:
            assignment_file = AssignmentFiles(file_url=file_url)
            new_assignment.files.append(assignment_file)  # 透過 relationship 自動關聯

        db.session.add(new_assignment)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error creating assignment: {str(e)}"}), 500

    return jsonify({
        "message": "Assignment created successfully.",
        "assignment": {
            "id": new_assignment.assignment_id,
            "title": new_assignment.title,
            "description": new_assignment.description,
            "due_date": new_assignment.due_date,
            "created_date": new_assignment.created_date,
            "modified_date": new_assignment.modified_date,
            "files": [file.file_url for file in new_assignment.files],
        },
    }), 201

# delete 作業
@app.route("/assignments/<int:assignment_id>", methods=["DELETE"])
@jwt_required()
def delete_assignment(assignment_id):
    claims = get_jwt()
    if claims["user_type"] != "teacher":
        return jsonify({"message": "Only teachers can delete assignments."}), 403

    try:
        assignment = Assignments.query.get_or_404(assignment_id)
        db.session.delete(assignment)  # 自動刪除關聯的檔案
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error deleting assignment: {str(e)}"}), 500

    return jsonify({"message": "Assignment deleted successfully."}), 200


# 查詢作業
@app.route("/assignments/<int:course_id>", methods=["GET"])
@jwt_required()
def get_assignments(course_id):
    assignments = Assignments.query.filter_by(course_id=course_id).all()
    response = []
    for assignment in assignments:
        response.append({
            "id": assignment.assignment_id,
            "title": assignment.title,
            "description": assignment.description,
            "due_date": assignment.due_date,
            "created_date": assignment.created_date,
            "modified_date": assignment.modified_date,
            "files": [file.file_url for file in assignment.files]
        })
    return jsonify({"assignments": response}), 200


# 修改 assignment
@app.route("/assignments/<int:assignment_id>", methods=["PUT"])
@jwt_required()
def update_assignment(assignment_id):
    claims = get_jwt()
    if claims["user_type"] != "teacher":
        return jsonify({"message": "Only teachers can update assignments."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid data."}), 400

    try:
        assignment = Assignments.query.get_or_404(assignment_id)
        
        # 更新作業基本資訊
        assignment.title = data.get("title", assignment.title)
        assignment.description = data.get("description", assignment.description)
        assignment.due_date = data.get("due_date", assignment.due_date)
        assignment.modified_date = datetime.utcnow()

        # 更新檔案資料（如果有提供）
        new_files = data.get("files", [])
        if new_files:
            # 刪除舊檔案記錄
            AssignmentFiles.query.filter_by(assignment_id=assignment_id).delete()
            
            # 新增新檔案記錄
            for file_url in new_files:
                new_file = AssignmentFiles(
                    assignment_id=assignment_id,
                    file_url=file_url
                )
                db.session.add(new_file)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error updating assignment: {str(e)}"}), 500

    return jsonify({"message": "Assignment updated successfully."}), 200

# 首次評分
@app.route("/submissions/<int:submission_id>/grade", methods=["POST"])
@jwt_required()
def add_grade_submission(submission_id):
    claims = get_jwt()
    if claims["user_type"] != "teacher":
        return jsonify({"message": "Only teachers can add grades."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid data."}), 400

    try:
        score = data.get("score")
        feedback = data.get("feedback", "")

        if score is None or not isinstance(score, (int, float)):
            return jsonify({"message": "Score must be provided and should be a number."}), 400

        # 查找提交
        submission = Submissions.query.get_or_404(submission_id)

        # 確認是否已評分
        if submission.score is not None:
            return jsonify({"message": "Grade already exists. Use the update API to modify the grade."}), 400

        # 新增評分與評語
        submission.score = score
        submission.feedback = feedback
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error adding grade: {str(e)}"}), 500

    return jsonify({
        "message": "Submission graded successfully.",
        "submission": {
            "submission_id": submission.submission_id,
            "assignment_id": submission.assignment_id,
            "student_id": submission.student_id,
            "score": submission.score,
            "feedback": submission.feedback,
            "submitted_at": submission.submitted_at,
        },
    }), 201

# 修改評分
@app.route("/submissions/<int:submission_id>/grade", methods=["PUT"])
@jwt_required()
def update_grade_submission(submission_id):
    claims = get_jwt()
    if claims["user_type"] != "teacher":
        return jsonify({"message": "Only teachers can update grades."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid data."}), 400

    try:
        score = data.get("score")
        feedback = data.get("feedback", "")

        if score is None or not isinstance(score, (int, float)):
            return jsonify({"message": "Score must be provided and should be a number."}), 400

        # 查找提交
        submission = Submissions.query.get_or_404(submission_id)

        # 確認是否已評分
        if submission.score is None:
            return jsonify({"message": "Grade does not exist. Use the add API to create a grade."}), 400

        # 修改評分與評語
        submission.score = score
        submission.feedback = feedback
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error updating grade: {str(e)}"}), 500

    return jsonify({
        "message": "Submission grade updated successfully.",
        "submission": {
            "submission_id": submission.submission_id,
            "assignment_id": submission.assignment_id,
            "student_id": submission.student_id,
            "score": submission.score,
            "feedback": submission.feedback,
            "submitted_at": submission.submitted_at,
        },
    }), 200




if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
    


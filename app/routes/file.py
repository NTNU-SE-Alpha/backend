import os
import hashlib
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt
from app.models import TeacherFiles, StudentFiles, db



bp = Blueprint("file", __name__)


# function: checksum & 儲存資訊到資料庫
def generate_checksum(filepath):
    # 計算檔案的 SHA256
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# 學生和教師的資訊分別存到 teacher_files 或 student_files (有更新 models.py)
def save_file_info(uploader_id, uploader_type, course_id, filename, filepath):
    checksum = generate_checksum(filepath)

    if uploader_type == "teacher":
        new_file = TeacherFiles(
            course_id=course_id,
            teacher_id=uploader_id,
            name=filename,
            path=filepath,
            checksum=checksum,
        )
    elif uploader_type == "student":
        new_file = StudentFiles(
            course_id=course_id,
            student_id=uploader_id,
            name=filename,
            path=filepath,
            checksum=checksum,
        )
    else:
        return False

    db.session.add(new_file)
    db.session.commit()
    return new_file.id

# secure_filename:
def save_file(file, allowed_extensions):
    if (
        file
        and "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower() in allowed_extensions
    ):
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            counter += 1
        file.save(file_path)
        return filename, file_path
    return None, None


# API: 上傳檔案處理 (更新: 將資訊存入資料庫)
@bp.route("/api/upload_pdf", methods=["POST"])
@jwt_required()
def upload_pdf():
    claims = get_jwt()
    uploader_id = claims.get("user_id")
    uploader_type = claims.get("user_type")
    course_id = request.form.get("course_id")

    if not course_id:
        return jsonify({"error": "Course ID is required"}), 400

    # 檢查是否有文件
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    # 檢查是否有文件選擇
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # 檢查檔案是否為 PDF
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    # 儲存檔案
    filename, filepath = save_file(file, current_app.config['ALLOWED_EXTENSIONS'])
    if filename:
        # 呼叫 generate_checksum()
        # checksum = generate_checksum(filepath)

        # 呼叫 save_file_info() 儲存資訊進資料庫中
        file_id = save_file_info(
            uploader_id, uploader_type, course_id, filename, filepath
        )
        if file_id:
            return jsonify(
                {
                    "message": "PDF file uploaded successfully",
                    "filename": filename,
                    "file_id": file_id,
                }
            ), 200
        else:
            return jsonify({"error": "Failed to save file info"}), 500
    else:
        return jsonify({"error": "File type not allowed"}), 400


# 新增其他檔案類型的上傳功能
@bp.route("/api/upload_various_file", methods=["POST"])
@jwt_required()
def upload_various_file():
    claims = get_jwt()
    uploader_id = claims.get("user_id")
    uploader_type = claims.get("user_type")
    course_id = request.form.get("course_id")  # 修改這裡，從 course_id 改為 course_id

    if not course_id:
        return jsonify({"error": "Class ID is required"}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename, filepath = save_file(file, current_app.config['OTHER_ALLOWED_EXTENSIONS'])
    if filename:
        # 儲存檔案資訊到資料庫
        if save_file_info(uploader_id, uploader_type, course_id, filename, filepath):
            return jsonify(
                {"message": "File uploaded successfully", "filename": filename}
            ), 200
        else:
            return jsonify({"error": "Failed to save file info"}), 500
    return jsonify({"error": "File type not allowed"}), 400


# # 上傳小組討論錄音檔
# @bp.route("/api/upload_group_audio", methods=["POST"])
# @jwt_required()
# def upload_group_audio(course_id, group_num):
#     claims = get_jwt()
#     uploader_id = claims.get("user_id")
#     uploader_type = claims.get("user_type")
#     course_id = request.form.get("course_id")
#     gruop_num = request.form.get("gruop_num")
    
#     if not course_id:
#         return jsonify({"error": "Class ID is required"}), 400

#     if not gruop_num:
#         return jsonify({"error": "Group number is required"}), 400


    
#     if "file" not in request.files:
#         return jsonify({"error": "No file part"}), 400

#     file = request.files["file"]

#     if file.filename == "":
#         return jsonify({"error": "No selected file"}), 400


#     filename, filepath = save_file(file, current_app.config['OTHER_ALLOWED_EXTENSIONS'])
#     if filename:
#         # 儲存檔案資訊到資料庫
#         if save_file_info(uploader_id, uploader_type, course_id, filename, filepath):
#             return jsonify(
#                 {"message": "File uploaded successfully", "filename": filename}
#             ), 200
#         else:
#             return jsonify({"error": "Failed to save file info"}), 500
#     return jsonify({"error": "File type not allowed"}), 400




# 下載檔案api : api/download/ 仍在 debug 中
@bp.route("/api/download/<int:file_id>", methods=["GET"])
@jwt_required()
def download_file(file_id):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    course_id = request.form.get("course_id")

    if not course_id:
        return jsonify({"error": "Class ID is required"}), 400

    if user_type == "teacher":
        file_record = TeacherFiles.query.filter_by(
            id=file_id, course_id=course_id, teacher_id=user_id
        ).first()
    elif user_type == "student":
        file_record = StudentFiles.query.filter_by(
            id=file_id, course_id=course_id, student_id=user_id
        ).first()
    else:
        return jsonify({"error": "Access forbidden."}), 403

    print(current_app.root_path)
    file_path = os.path.join(current_app.root_path, "../",file_record.path)
    if not file_record or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True)

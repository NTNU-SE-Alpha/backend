from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    courses = db.relationship("Course", backref="teacher", lazy=True)

    def set_password(self, password):
        # 產生密碼的 hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # 檢查密碼
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    course = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    group_number = db.Column(db.Integer, nullable=False)

    def set_password(self, password):
        # 產生密碼的 hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # 檢查密碼
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    students = db.relationship("Student", backref=db.backref("courses", lazy=True))
    sections = db.relationship(
        "Course_sections", backref=db.backref("courses", lazy=True)
    )
    weekday = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    archive = db.Column(db.Boolean, default=False, nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image_data.id'))
    is_favorite = db.Column(db.Boolean, default=False)

    # 將資料轉為 dict
    def to_dict(self):
        teacher = Teacher.query.filter_by(id=self.teacher_id).first()
        return {
            "id": self.id,
            "name": self.name,
            "teacher_id": self.teacher_id,
            "teacher_username": teacher.username,
            "teacher_name": teacher.name,
            "weekday": self.weekday,
            "semester": self.semester,
            "archive": self.archive,
        }

    def get_sections(self):
        return (
            Course_sections.query.filter_by(course=self.id)
            .order_by(Course_sections.sequence)
            .all()
        )

    def is_student(self, user_id):
        return any(student.id == user_id for student in self.students)


class Course_sections(db.Model):
    __tablename__ = "course_sections"
    id = db.Column(db.Integer, primary_key=True)
    sequence = db.Column(db.Integer)
    name = db.Column(db.String(20), nullable=False, unique=True)
    course = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    publish_date = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "sequence": self.sequence,
            "name": self.name,
            "course_id": self.course,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "publish_date": self.publish_date.isoformat(),
        }

class ImageData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.LargeBinary, nullable=False)
    course = db.relationship('Courses', backref=db.backref('image', uselist=False))
    
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text, nullable=True)  # New field to store the summary


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversation.id"), nullable=False
    )
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'ai'
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship(
        "Conversation", backref=db.backref("messages", lazy=True)
    )

class TeacherFaiss(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("teacher_files.id"), nullable=False)

# Upload files: Teachers
class TeacherFiles(db.Model):
    __tablename__ = "teacher_files"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    checksum = db.Column(db.String(64), nullable=False)
    
# Upload files: Students
class StudentFiles(db.Model):
    __tablename__ = "student_files"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, nullable=False)
    student = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    checksum = db.Column(db.String(64), nullable=False)

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    attachments = db.relationship(
        "AnnouncementAttachment", backref="announcement", lazy=True
    )
    visibility = db.Column(
        db.String(20), nullable=False, default="all"
    )  # "all", "students", "teachers"
    start_date = db.Column(db.DateTime, nullable=False)  # visibility開始日期
    end_date = db.Column(db.DateTime, nullable=False)  # visibility結束日期
    publish_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 發布日期

    #  將資料轉為 dict
    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "title": self.title,
            "content": self.content,
            "attachments": [attachment.to_dict() for attachment in self.attachments],
            "visibility": self.visibility,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "publish_date": self.publish_date.isoformat(),
        }


class AnnouncementAttachment(db.Model):
    __tablename__ = "announcement_attachments"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)  # attachment name
    path = db.Column(db.String(255), nullable=False)  # attachment path
    checksum = db.Column(db.String(64), nullable=False)  # 校驗碼

    def to_dict(self):
        return {
            "id": self.id,
            "announcement_id": self.announcement_id,
            "name": self.name,
            "path": self.path,
            "checksum": self.checksum,
        }
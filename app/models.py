import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

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
        "CourseSections", backref=db.backref("courses", lazy=True)
    )
    weekday = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    archive = db.Column(db.Boolean, default=False, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)

    conversations = db.relationship(
        "TeacherAIConversations", backref="course", lazy=True
    )

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
            "is_favorite": self.is_favorite,
        }

    def get_sections(self):
        return (
            CourseSections.query.filter_by(course_id=self.id)
            .order_by(CourseSections.sequence)
            .all()
        )

    def is_student(self, user_id):
        return any(student.id == user_id for student in self.students)


class CourseSections(db.Model):
    __tablename__ = "course_sections"
    id = db.Column(db.Integer, primary_key=True)
    sequence = db.Column(db.Integer)
    name = db.Column(db.String(20), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    content = db.Column(db.String(2000), nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    publish_date = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "sequence": self.sequence,
            "name": self.name,
            "course_id": self.course_id,
            "content": self.content,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "publish_date": self.publish_date.isoformat(),
        }


class TeacherAIConversations(db.Model):
    __tablename__ = "teacher_ai_conversations"
    id = db.Column(db.Integer, primary_key=True)
    # uuid = db.Column(
    #     db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    # )
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    course_section = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    summary = db.Column(db.Text, nullable=True)


class TeacherAIMessages(db.Model):
    __tablename__ = "teacher_ai_messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("teacher_ai_conversations.id"), nullable=False
    )
    sender = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)

    conversation = db.relationship(
        "TeacherAIConversations", backref=db.backref("teacher_ai_messages", lazy=True)
    )


class StudentAIConversations(db.Model):
    __tablename__ = "student_ai_conversations"
    id = db.Column(db.Integer, primary_key=True)
    # uuid = db.Column(
    #     db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    # )
    # uuid = db.Column(db.String(36), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    course_section = db.Column(db.Integer, nullable=False)
    # student = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    # created_at = db.Column(db.DateTime, default=datetime.now())
    # summary = db.Column(db.Text, nullable=True)


class StudentAIMessages(db.Model):
    __tablename__ = "student_ai_messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("student_ai_conversations.id"), nullable=False
    )
    sender = db.Column(db.String(10), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)

    conversation = db.relationship(
        "StudentAIConversations", backref=db.backref("student_ai_messages", lazy=True)
    )


class TeacherAIFaisses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("teacher_files.id"), nullable=False)


# Upload files: Teachers
class TeacherFiles(db.Model):
    __tablename__ = "teacher_files"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    checksum = db.Column(db.String(64), nullable=False)


# Upload files: Students
class StudentFiles(db.Model):
    __tablename__ = "student_files"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    checksum = db.Column(db.String(64), nullable=False)


class StudentGroupMessage(db.Model):
    __tablename__ = "group_message"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    sender = db.Column(db.String(10), nullable=False)
    room = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)


class GroupAudioFiles(db.Model):
    __tablename__ = "group_audio_files"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    checksum = db.Column(db.String(64), nullable=False)


class StudentAIFeedbacks(db.Model):
    __tablename__ = "student_ai_feedbacks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("student_ai_conversations.id"), nullable=False
    )
    feedback = db.Column(db.String(600), nullable=False)

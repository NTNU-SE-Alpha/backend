from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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
    course = db.Column(db.Integer, nullable=False) 
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
    weekday = db.Column(db.String(20), nullable=False) 
    semester = db.Column(db.String(20), nullable=False)
    archive = db.Column(db.Boolean, default=False, nullable=False)

    # 將資料轉為 dict
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "teacher_id": self.teacher_id,
            "weekday": self.weekday,
            "semester": self.semester,
            "archive": self.archive,
        }

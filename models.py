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
    course = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
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
    students = db.relationship('Student', backref=db.backref('courses', lazy=True))
    sections = db.relationship('Course_sections', backref=db.backref('courses', lazy=True))
    weekday = db.Column(db.String(20), nullable=False) 
    semester = db.Column(db.String(20), nullable=False)
    archive = db.Column(db.Boolean, default=False, nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image_data.id'))

    # 將資料轉為 dict
    def to_dict(self):
        teacher = Teacher.query.filter_by(id = self.teacher_id).first()
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
        return Course_sections.query.filter_by(course=self.id).order_by(Course_sections.sequence).all()
    def is_student(self, user_id):
        return any(student.id == user_id for student in self.students)

class Course_sections(db.Model):
    __tablename__ = "course_sections"
    id = db.Column(db.Integer,primary_key=True)
    sequence = db.Column(db.Integer)
    name = db.Column(db.String(20), nullable=False, unique=True)
    course = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    publish_date = db.Column(db.DateTime, nullable=False)
    def to_dict(self):
        return {
            'id': self.id,
            'sequence': self.sequence,
            'name': self.name,
            'course_id': self.course,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'publish_date': self.publish_date.isoformat(),
        }

class ImageData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.LargeBinary, nullable=False)
    course = db.relationship('Courses', backref=db.backref('image', uselist=False))
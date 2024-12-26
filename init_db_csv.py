import csv
from datetime import datetime
from app import create_app, db
from app.models import Course, CourseSections, Student, Teacher, TeacherFiles


def read_csv(file_path):
    with open(file_path, mode="r", encoding="utf-8") as file:
        return list(csv.DictReader(file))

def init_db():
    app = create_app("development")
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database tables created.")

        teachers_data = read_csv("test_data/teachers.csv")
        courses_data = read_csv("test_data/courses.csv")
        students_data = read_csv("test_data/students.csv")
        sections_data = read_csv("test_data/sections.csv")
        teacher_files_data = read_csv("test_data/teacher_files.csv")

        teachers = []
        for row in teachers_data:
            teacher = Teacher(id=row["id"], username=row["username"], name=row["name"])
            teacher.set_password(row["password"])
            teachers.append(teacher)
        db.session.add_all(teachers)
        db.session.commit()

        courses = []
        for row in courses_data:
            course = Course(
                id=row["id"],
                name=row["name"],
                teacher_id=row["teacher_id"],
                weekday=row["weekday"],
                semester=row["semester"],
                archive=row["archive"] == "True",
                is_favorite=row["is_favorite"] == "True",
            )
            courses.append(course)
        db.session.add_all(courses)
        db.session.commit()

        students = []
        for row in students_data:
            student = Student(
                username=row["username"],
                name=row["name"],
                course=row["course"],
                group_number=int(row["group_number"]),
            )
            student.set_password(row["password"])
            students.append(student)
        db.session.add_all(students)
        db.session.commit()

        sections = []
        for row in sections_data:
            section = CourseSections(
                name=row["name"],
                sequence=int(row["sequence"]),
                course_id=row["course_id"],
                content=row["content"].replace("\\n", "\n"),
                start_date=datetime.strptime(row["start_date"], "%Y-%m-%d %H:%M:%S"),
                end_date=datetime.strptime(row["end_date"], "%Y-%m-%d %H:%M:%S"),
                publish_date=datetime.strptime(
                    row["publish_date"], "%Y-%m-%d %H:%M:%S"
                ),
            )
            sections.append(section)
        db.session.add_all(sections)
        db.session.commit()

        teacher_files = []
        for row in teacher_files_data:
            teacher_file = TeacherFiles(
                teacher_id=row["teacher_id"],
                course_id=row["course_id"],
                name=row["name"],
                path=row["path"],
                checksum=row["checksum"],
            )
            teacher_files.append(teacher_file)
        db.session.add_all(teacher_files)
        db.session.commit()

        print("Data from CSV files inserted into the database.")


if __name__ == "__main__":
    init_db()

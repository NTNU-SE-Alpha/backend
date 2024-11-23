from datetime import datetime

from app import app, db

from models import Course, Course_sections, Student, Teacher, TeacherFiles


def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database tables created.")

        teacher1 = Teacher(username="neokent", name="劑博聞")
        teacher1.set_password("securepassword1")

        teacher2 = Teacher(username="ytchang", name="張諭騰")
        teacher2.set_password("securepassword2")


        course1 = Course(
            name="軟體工程",
            teacher_id=1,
            weekday="Wed",
            semester="113-1",
            archive=False,
            is_favorite=False
        )

        course2 = Course(
            name="電子學", 
            teacher_id=2,
            weekday="Thur", 
            semester="113-1",
            archive=False,
            is_favorite=False
        )

        course3 = Course(
            name="程式設計(一)",
            teacher_id=1,
            weekday="Tue",
            semester="113-1",
            archive=False,
        )

        student1 = Student(
            username="41275006H", name="無待錚", course=1, group_number=1
        )
        student1.set_password("studentpass1")

        student2 = Student(
            username="41275023H", name="曾柏魚", course=2, group_number=2
        )
        student2.set_password("studentpass2")

        section1 = Course_sections(
            name="Week1",
            sequence=1,
            course=1,
            start_date=datetime(2024, 10, 1, 8, 0),
            end_date=datetime(2024, 10, 1, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )

        section2 = Course_sections(
            name="Week 2",
            sequence=2,
            course=1,
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )

        teachfile1 = TeacherFiles(
            teacher=1,
            class_id=1,
            name="teaching_resources",
            path="uploads/teaching_resources.pdf",
            checksum="0ad30feac1b9fd248d678798114fc5412b9dd6460e9b1e64280f67528d675771",
        )

        db.session.add_all(
            [
                teacher1,
                teacher2,
                student1,
                student2,
                course1,
                course2,
                course3,
                section1,
                section2,
            ]
        )

        db.session.commit()
        
        db.session.add(teachfile1)
        db.session.commit()
        print("Test data inserted into the database.")


if __name__ == "__main__":
    init_db()

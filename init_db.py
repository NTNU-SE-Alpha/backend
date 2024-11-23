from app import app, db
from models import Teacher, Student, Course, Course_sections, Assignments, AssignmentFiles
from datetime import datetime


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
        )

        course2 = Course(
            name="電子學", teacher_id=2, weekday="Thur", semester="113-1", archive=False
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
        
        # 新增作業資料
        assignment1 = Assignments(
            course_id=1,
            title="作業 1: 軟體開發流程",
            description="閱讀課本第 1-3 章，並撰寫報告。",
            due_date=datetime(2024, 10, 15, 23, 59),
            created_date=datetime.now(),
            modified_date=datetime.now(),
        )

        assignment2 = Assignments(
            course_id=2,
            title="作業 1: 電子元件設計",
            description="設計一個基本電路並提供模擬結果。",
            due_date=datetime(2024, 10, 20, 23, 59),
            created_date=datetime.now(),
            modified_date=datetime.now(),
        )

        # 新增作業附加檔案
        assignment_file1 = AssignmentFiles(
            assignment_id=1,
            file_url="uploads/Assignment1_Guidelines.pdf",
        )

        assignment_file2 = AssignmentFiles(
            assignment_id=2,
            file_url="uploads/Circuit_Design_Examples.zip",
        )
        
        #先生成id
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

        db.session.add_all(
            [
                assignment1,
                assignment2,
                assignment_file1,
                assignment_file2
            ]
        )

        db.session.commit()
        print("Test data inserted into the database.")


if __name__ == "__main__":
    init_db()

from datetime import datetime

from app import app, db

from models import Course, Course_sections, Student, Teacher, TeacherFiles


def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database tables created.")

        teacher1 = Teacher(id=1,username="neokent", name="劑博聞")
        teacher1.set_password("securepassword1")

        teacher2 = Teacher(id=2,username="ytchang", name="張諭騰")
        teacher2.set_password("securepassword2")
        
        teacher3 = Teacher(id=3,username="brucelin", name="林政紅")
        teacher3.set_password("securepassword3")

        teacher4 = Teacher(id=4,username="cklu", name="旅程凱")
        teacher4.set_password("securepassword4")

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
        course4 = Course(
            name="資訊安全",
            teacher_id=1,
            weekday="Mon",
            semester="113-1",
            archive=False,
        )
        course5 = Course(
            name="高等資安攻防演練",
            teacher_id=1,
            weekday="Fri",
            semester="113-1",
            archive=False,
        )
        course6 = Course(
            name="高等資安攻防演練",
            teacher_id=1,
            weekday="Fri",
            semester="113-1",
            archive=False,
        )
        course7 = Course(
            name="類比積體電路導論",
            teacher_id=2,
            weekday="Thu",
            semester="113-1",
            archive=False,
        )
        course8 = Course(
            name="電機專題製作",
            teacher_id=2,
            weekday="Fri",
            semester="113-1",
            archive=False,
        )
        course8 = Course(
            name="電機專題製作",
            teacher_id=2,
            weekday="Fri",
            semester="113-1",
            archive=False,
        )
        course9 = Course(
            name="數位系統",
            teacher_id=3,
            weekday="Mon",
            semester="113-1",
            archive=False,
        )
        course10 = Course(
            name="資料結構",
            teacher_id=3,
            weekday="Tue",
            semester="113-1",
            archive=False,
        )
        course11 = Course(
            name="計算機概論",
            teacher_id=4,
            weekday="Thu",
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
        
        student3 = Student(
            username="41275024H", name="章節", course=2, group_number=2
        )
        student3.set_password("studentpass3")

        student4 = Student(
            username="41275046H", name="彭尚折", course=3, group_number=1
        )
        student4.set_password("studentpass4")

        section1 = Course_sections(
            name="Week 1",
            sequence=1,
            course=2,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section2 = Course_sections(
            name="Week 2",
            sequence=2,
            course=2,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section3 = Course_sections(
            name="Week 1",
            sequence=1,
            course=3,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section4 = Course_sections(
            name="Week 2",
            sequence=2,
            course=3,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section5 = Course_sections(
            name="Week 1",
            sequence=1,
            course=4,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section6 = Course_sections(
            name="Week 2",
            sequence=2,
            course=4,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section7 = Course_sections(
            name="Week 1",
            sequence=1,
            course=5,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section8 = Course_sections(
            name="Week 2",
            sequence=2,
            course=5,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section9 = Course_sections(
            name="Week 1",
            sequence=1,
            course=6,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section10 = Course_sections(
            name="Week 2",
            sequence=2,
            course=6,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section11 = Course_sections(
            name="Week 1",
            sequence=1,
            course=7,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section12 = Course_sections(
            name="Week 2",
            sequence=2,
            course=7,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section13 = Course_sections(
            name="Week 1",
            sequence=1,
            course=8,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section14 = Course_sections(
            name="Week 2",
            sequence=2,
            course=8,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section15 = Course_sections(
            name="Week 1",
            sequence=1,
            course=9,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section16 = Course_sections(
            name="Week 2",
            sequence=2,
            course=9,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section17 = Course_sections(
            name="Week 1",
            sequence=1,
            course=10,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section18 = Course_sections(
            name="Week 2",
            sequence=2,
            course=10,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section19 = Course_sections(
            name="Week 1",
            sequence=1,
            course=11,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section20 = Course_sections(
            name="Week 2",
            sequence=2,
            course=11,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
        )

        section21 = Course_sections(
            name="Week 1",
            sequence=1,
            course=1,
            content="測試資料",
            start_date=datetime(2024, 10, 8, 8, 0),
            end_date=datetime(2024, 10, 8, 10, 0),
            publish_date=datetime(2024, 9, 30, 12, 0),
        )
        section22 = Course_sections(
            name="Week 2",
            sequence=2,
            course=1,
            content="測試資料",
            start_date=datetime(2024, 10, 15, 8, 0),
            end_date=datetime(2024, 10, 15, 10, 0),
            publish_date=datetime(2024, 10, 7, 12, 0),
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
                teacher3,
                teacher4,
            ]
        )
        db.session.commit()
        
        db.session.add_all([
                course1,
                course2,
                course3,
                course4,
                course5,
                course6,
                course7,
                course8,
                course9,
                course10,
                course11,
        ])
        db.session.commit()
        
        db.session.add_all([
                student1,
                student2,
                student3,
                student4, 
        ])
        db.session.commit()
        
        db.session.add_all([
                section1,
                section2,
                section3,
                section4,
                section5,
                section6,
                section7,
                section8,
                section9,
                section10,
                section11,
                section12,
                section13,
                section14,
                section15,
                section16,
                section17,
                section18,
                section19,
                section20,
                section21,
                section22, 
        ])
        db.session.commit()
        
        db.session.add(teachfile1)
        db.session.commit()
        
        print("Test data inserted into the database.")


if __name__ == "__main__":
    init_db()

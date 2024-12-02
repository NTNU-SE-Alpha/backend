from datetime import datetime,timedelta

from app import app, db

from models import Course, CourseSections, Student, Teacher, TeacherFiles


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
            weekday="Thu", 
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
        course7 = Course(
            name="類比積體電路導論",
            teacher_id=2,
            weekday="Thu",
            semester="113-1",
            archive=False,
            is_favorite=True,
        )
        course8 = Course(
            name="電機專題製作",
            teacher_id=2,
            weekday="Fri",
            semester="113-1",
            archive=False,
            is_favorite=True,
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
        student4.set_password(" ")

        sections = [
            CourseSections(
                name=f"Week {sequence}",
                sequence=sequence,
                course=course,
                content="""
## 課程目標
- 了解資料結構的基本概念與重要性。
- 探討資料結構在程式設計與問題解決中的應用。

---

## 課程大綱
1. **資料結構簡介**
   - 資料結構的定義與用途
   - 資料結構與演算法的關係
2. **時間與空間複雜度**
   - 大O符號簡介
   - 演算法效能分析
3. **基本資料結構概念**
   - 陣列（Array）
   - 鏈結串列（Linked List）

---

## 課程內容

### 1. 資料結構的定義
- 資料的組織、管理與儲存方式。
- 實例：如何在程式中有效率地存取與操作資料。

### 2. 時間與空間複雜度
- **時間複雜度**
  - 描述演算法執行時間隨輸入大小的變化。
  - 範例：迴圈的時間複雜度。
- **空間複雜度**
  - 描述演算法執行時所需的記憶體資源。

### 3. 陣列與鏈結串列
- **陣列**
  - 定義：固定大小的連續記憶體區塊。
  - 優缺點：快速存取，但插入與刪除成本高。
- **鏈結串列**
  - 定義：以節點（Node）連結的動態資料結構。
  - 優缺點：靈活性高，但存取成本高。

---

## 必讀教材與參考資料
- 教科書：《Data Structures and Algorithm Analysis in C》
- 參考網站：[GeeksforGeeks - Data Structures](https://www.geeksforgeeks.org/data-structures/)

---

## 作業與練習
1. **閱讀**教材中關於時間與空間複雜度的章節。
2. **練習**：
   - 使用陣列儲存並搜尋一組數字。
   - 用鏈結串列實作基本操作（新增、刪除）。

---

## 提問與討論
- [課程討論區](#)
- **問題範例**：
  - 陣列和鏈結串列適合用在什麼樣的應用場合？
  - 如何評估演算法的時間複雜度？

---

## 下週預告
- 堆疊（Stack）與佇列（Queue）的基本操作與應用。
                """,
                start_date=datetime(2024, 10, 8, 8, 0) + timedelta(weeks=sequence-1),
                end_date=datetime(2024, 10, 8, 10, 0) + timedelta(weeks=sequence-1),
                publish_date=datetime(2024, 9, 30, 12, 0) + timedelta(weeks=sequence-1),
            )
            for course in range(1, 11)
            for sequence in range(1, 6)
        ]
        
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
        
        db.session.add_all(sections)
        db.session.commit()
        
        db.session.add(teachfile1)
        db.session.commit()
        
        print("Test data inserted into the database.")


if __name__ == "__main__":
    init_db()

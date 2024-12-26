from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt
from app.models import (
    Teacher,
    Student,
    StudentAIConversations,
    TeacherFiles,
    TeacherAIConversations,
    TeacherAIFaisses,
    TeacherAIMessages,
    Course,
    CourseSections,
    StudentAIFeedbacks,
    db,
)
from app.services.ai_teacher import AITeacher
from app.services.ai_student import AIStudent
from datetime import datetime
import uuid
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage



bp = Blueprint("chat", __name__)

aiteacher = AITeacher(current_app.config["OPENAI_API_KEY"])
aistudent = AIStudent(current_app.config["OPENAI_API_KEY"])


@bp.route("/start_conversation", methods=["GET"])
@jwt_required()
def start_conversation():
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
    else:
        return jsonify({"message": "Access forbidden"}), 403
    # course_id = request.form.get("course_id")
    # course_section_id = request.form.get("course_section_id")
    # course_id = 1
    # course_section_id = 21

    # new_conversation = Conversation(
    #     teacher_id=user_id, course_id=course_id, course_section=course_section_id
    # )
    # db.session.add(new_conversation)
    # db.session.commit()
    return jsonify({"uuid": uuid.uuid4()})


def is_valid_uuid(uuid_to_test):
    try:
        uuid_obj = uuid.UUID(str(uuid_to_test))
        return True
    except ValueError:
        return False


@bp.route("/chat/<string:conversation_uuid>", methods=["POST"])
@jwt_required()
def chat(conversation_uuid):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
    else:
        return jsonify({"message": "Access forbidden"}), 403

    if not conversation_uuid:
        return jsonify({"message": "The UUID of conversation is required."}), 400

    conversation = TeacherAIConversations.query.filter_by(
        uuid=conversation_uuid
    ).first()

    if conversation is None:
        if is_valid_uuid(conversation_uuid):
            new_conversation = TeacherAIConversations(
                uuid=conversation_uuid,
                teacher_id=user_id,
                course_id=1,
                course_section=1,
            )
            db.session.add(new_conversation)
            db.session.commit()
        else:
            return jsonify({"message": "The UUID of conversation is invalid."}), 400

    elif conversation.teacher_id != user_id:
        return jsonify({"message": "Not authorized."}), 401

    data = request.json
    user_input = data.get("user_input", "").strip()

    if not user_input:
        return jsonify(
            {"message": "The UUID of conversation and the user input are required."}
        ), 400

    if "file_id" in data:
        file = TeacherFiles.query.filter_by(id=data["file_id"]).first()

        if file is None:
            return jsonify({"message": "file_id is invalid."}), 400

        file_content = aiteacher.extract_text_from_pdf(file.path)

        if not file_content:
            return jsonify({"message": "Unable to read file."}), 400

        faiss_file = TeacherAIFaisses.query.filter_by(file_id=data["file_id"]).first()

        if faiss_file is not None:
            index, sentences = aiteacher.load_faiss_index(data["file_id"])
            print(sentences)
            if index is None or sentences is None:
                faiss_index = TeacherAIFaisses.query.get(faiss_file.id)
                db.session.delete(faiss_index)
                db.session.commit()
                return jsonify({"message": "Unable to read faiss file"}), 400
        else:
            index, sentences = aiteacher.build_faiss_index(
                file_content, data["file_id"]
            )

            if index is None or sentences is None:
                print("建立索引失敗，程式結束。")
                return

            faiss_index = TeacherAIFaisses(file_id=data["file_id"])
            db.session.add(faiss_index)
            db.session.commit()

        aiteacher.system_context = """您是一位AI教學助手。
請基於上述內容來回答問題。如果需要引入新的例子或故事，請確保與原始課程內容保持關聯。"""

        relevant_context = aiteacher.search_rag(user_input, index, sentences)

        context = "\n".join(relevant_context)

    else:
        aiteacher.system_context = ""
        context = ""

    conversation, conversation_history = aiteacher.load_conversation_history(
        conversation_uuid
    )
    if not conversation:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    if len(conversation_history) == 0:
        conversation.summary = aiteacher.summarize_text(user_input)
        db.session.commit()

    messages = [
        SystemMessage(content=aiteacher.system_context),
        SystemMessage(content=f"相關上下文：\n\n{context}"),
    ]

    for _, q, a, _ in conversation_history:
        messages.append(HumanMessage(content=q))
        messages.append(AIMessage(content=a))

    messages.append(HumanMessage(user_input))

    answer = aiteacher.generate_response(messages)
    conversation_history.append((user_input, answer))

    aiteacher.save_message(conversation.id, "user", user_input)
    aiteacher.save_message(conversation.id, "assistant", answer)

    return jsonify({"answer": answer})


@bp.route("/student_chat/<int:course_id>/<int:course_section>", methods=["POST"])
@jwt_required()
def student_chat(course_id, course_section):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "student":
        user = Student.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
    else:
        return jsonify({"message": "Access forbidden."}), 403

    if not (course_id and course_section):
        return jsonify(
            {"message": "The course_id and course_section are required."}
        ), 400

    conversation = StudentAIConversations.query.filter_by(
        course_id=course_id, course_section=course_section
    ).first()

    if conversation is None:
        return jsonify({"message": "This course is not deployed."}), 404

    if user.course != course_id:
        return jsonify({"message": "Access forbidden."}), 403

    data = request.json
    user_input = data.get("user_input", "").strip()

    if not user_input:
        return jsonify({"message": "user input are required."}), 400

    aistudent.system_context = "您是一位AI教學助手，以下是先前教師和AI助手的對話紀錄，你需要根據這些對話紀錄，回應學生，記住，不要提到「以前的對話紀錄」，改為「根據老師」。現在開始我是學生。"

    conversation, conversation_history = aistudent.load_conversation_history(
        course_id,
        course_section,
        user.id,
    )

    if not conversation:
        return jsonify({"message": "This course is not deployed."}), 400

    messages = [
        SystemMessage(content=aistudent.system_context),
        # SystemMessage(content=f"相關上下文：\n\n{context}"),
    ]
    teacher_conversation_history = aistudent.load_teacher_conversation_history(
        course_id
    )

    for _, q, a, _ in teacher_conversation_history:
        messages.append(HumanMessage(content=q))
        messages.append(AIMessage(content=a))

    messages.append(HumanMessage("以上是教師的對話紀錄"))

    for _, q, a, _ in conversation_history:
        messages.append(HumanMessage(content=q))
        messages.append(AIMessage(content=a))

    messages.append(HumanMessage(user_input))

    answer = aistudent.generate_response(messages)
    conversation_history.append((user_input, answer))

    aistudent.save_message(conversation.id, user.id, "user", user_input)
    aistudent.save_message(conversation.id, user.id, "assistant", answer)

    return jsonify({"answer": answer})


@bp.route("/conversation/<string:conversation_uuid>", methods=["GET"])
@jwt_required()
def get_history(conversation_uuid):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    else:
        return jsonify({"message": "Access forbidden"}), 403

    if not conversation_uuid:
        return jsonify({"message": "The UUID of conversation is required."}), 400

    conversation = TeacherAIConversations.query.filter_by(
        uuid=conversation_uuid
    ).first()

    if conversation is None:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    if conversation.teacher_id != user_id:
        return jsonify({"message": "Not authorized."}), 401

    conversation, conversation_history = aiteacher.load_conversation_history(
        conversation_uuid
    )

    if not conversation:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    formatted_history = [
        {
            "id": id,
            "sender": sender,
            "message": msg,
            "sent_at": sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for id, sender, msg, sent_at in conversation_history
    ]
    return jsonify({"uuid": conversation_uuid, "history": formatted_history})


@bp.route("/conversation/<string:conversation_uuid>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conversation_uuid):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    if not conversation_uuid:
        return jsonify({"message": "The UUID of conversation is required."}), 400

    conversation = TeacherAIConversations.query.filter_by(
        uuid=conversation_uuid
    ).first()

    if conversation is None:
        return jsonify({"message": "The UUID of conversation is invalid."}), 400

    if conversation.teacher_id != user_id:
        return jsonify({"message": "Not authorized."}), 401

    try:
        messages = TeacherAIMessages.query.filter_by(
            conversation_id=conversation.id
        ).all()
        for message in messages:
            db.session.delete(message)
        db.session.commit()

        db.session.delete(conversation)
        db.session.commit()

        return jsonify(
            {"message": f"Conversation with UUID {conversation_uuid} has been deleted."}
        ), 200

    except Exception as e:
        bp.logger.error(f"Error deleting conversation: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while deleting the conversatoin"})


@bp.route("/list_conversations", methods=["GET"])
@jwt_required()
def list_conversations():
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

    conversations = TeacherAIConversations.query.filter_by(teacher_id=user_id).all()
    conversation_list = []
    for conversation in conversations:
        course = Course.query.filter_by(id=conversation.course_id).first()
        course_section = CourseSections.query.filter_by(
            id=conversation.course_section
        ).first()
        conversation_list.append(
            {
                "uuid": conversation.uuid,
                "course_name": course.name,
                "course_section": course_section.name,
                "summary": conversation.summary
                if conversation.summary
                else "No summary available",
                "created_at": conversation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return jsonify({"conversations": conversation_list})


@bp.route("/deploy_student_llm/<string:conversation_uuid>", methods=["GET"])
@jwt_required()
def deploy(conversation_uuid):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
    else:
        return jsonify({"message": "Access forbidden"}), 403

    if not conversation_uuid:
        return jsonify({"message": "The UUID of conversation is required."}), 400

    conversation = TeacherAIConversations.query.filter_by(
        uuid=conversation_uuid
    ).first()

    if conversation is None:
        if is_valid_uuid(conversation_uuid):
            new_conversation = TeacherAIConversations(
                uuid=conversation_uuid,
                teacher_id=user_id,
                course_id=1,
                course_section=1,
            )
            db.session.add(new_conversation)
            db.session.commit()
        else:
            return jsonify({"message": "The UUID of conversation is invalid."}), 400

    elif conversation.teacher_id != user_id:
        return jsonify({"message": "Not authorized."}), 401

    course_id = conversation.course_id
    course_section = conversation.course_section
    try:
        new_student_conversation = StudentAIConversations(
            course_id=course_id, course_section=course_section
        )
        db.session.add(new_student_conversation)
        db.session.commit()
        return jsonify({"message": "Deploy successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Deploy failed"}), 400

@bp.route("/generate_feedback", methods=["POST"])
@jwt_required()
def generate_feedback():
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    
    course_id = request.form.get('course_id')
    course_section_id = request.form.get('course_section_id')
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
    else:
        return jsonify({"message": "Access forbidden"}), 403

    if not course_id:
        return jsonify({"message": "The ID of course is required."}), 400
    
    if not course_section_id:
        return jsonify({"message": "The ID of course section is required."}), 400
    
    student_conversation = StudentAIConversations.query.filter_by(
        course_id = course_id,
        course_section = course_section_id
    ).first()
    
    if student_conversation is None:
        return jsonify({"message": "The course is not deployed."}), 404

    students = Student.query.filter_by(course=course_id).all()
    
    try:
        for student in students:
            conversation, conversation_history = aistudent.load_conversation_history(
                course_id,
                course_section_id,
                student.id
            )
            
            if not conversation:
                continue
            
            summary_prompt = "請總結以下對話的重點，幫助老師了解學生的學習狀況，如果對話是空白的，則回覆學生尚未進行對話：\n\n"
            for _, sender, a, _ in conversation_history:
                if sender == 'user':
                    summary_prompt += f"學生說: {a} "
                elif sender == 'assistant':
                    summary_prompt += f"AI 助教回: {a} \n\n"
                # summary_prompt += f"學生: {q}\nAI 助教: {a}\n\n"
            
            print(summary_prompt)
            
            llm_summary = ChatOpenAI(
                api_key=current_app.config["OPENAI_API_KEY"],
                max_tokens=1500,
                model_name="gpt-4"  # 確保使用正確的模型名稱
            )
            messages = [
                SystemMessage(content="您是一位 AI 助教，請根據以下對話歷史生成一個詳細的總結，幫助老師了解學生的學習狀況。"),
                HumanMessage(content=summary_prompt)
            ]
            
            response = llm_summary(messages)
            
            summary = response.content.strip()
            
            print("\n從 LLM 收到的回應:")
            print(summary)
            
            old_student_feedback = StudentAIFeedbacks.query.filter_by(
                user_id = student.id,
                conversation_id=student_conversation.id,
            ).first()
            
            if old_student_feedback is None:
                student_feedback = StudentAIFeedbacks(
                    user_id = student.id,
                    conversation_id=student_conversation.id,
                    feedback = summary
                )
                
                db.session.add(student_feedback)
                db.session.commit()
            else:
                old_student_feedback.feedback = summary
                db.session.commit()
                
        return jsonify({"message": "Feedback generated sucessfully."})
        
    except Exception as e:
        bp.logger.error(f"Error generating feedback: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while generating the feedback"})
    
@bp.route("/list_feedback/<int:course_id>/<int:course_section_id>", methods=["GET"])
@jwt_required()
def list_feedback(course_id, course_section_id):
    claims = get_jwt()
    user_type = claims.get("user_type")
    user_id = claims.get("user_id")
    
    if not user_type or not user_id:
        return jsonify({"message": "Invalid token."}), 400

    if user_type == "teacher":
        user = Teacher.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404
    else:
        return jsonify({"message": "Access forbidden"}), 403

    if not course_id:
        return jsonify({"message": "The ID of course is required."}), 400
    
    if not course_section_id:
        return jsonify({"message": "The ID of course section is required."}), 400
    
    student_conversation = StudentAIConversations.query.filter_by(
        course_id = course_id,
        course_section = course_section_id
    ).first()
    
    if student_conversation is None:
        return jsonify({"message": "The course is not deployed."}), 404

    students = Student.query.filter_by(course=course_id).all()
    
    try:
        feedback_list = []
        for student in students:
            student_feedback = StudentAIFeedbacks.query.filter_by(
                user_id = student.id,
                conversation_id=student_conversation.id,
            ).first()
            
            if student_feedback is None:
                return jsonify({"message": "Feedback for this course has not been generated yet."})
            
            feedback_list.append({
                "student_name": student.name,
                "student_id": student.id,
                "feedback": student_feedback.feedback, 
            })
            
        return jsonify(feedback_list),200 
        
    except Exception as e:
        bp.logger.error(f"Error fetching feedback: {e}")
        db.session.rollback()
        return jsonify({"message": "An error occurred while fetching the feedback"})
    
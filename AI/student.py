import json
import os
import pathlib
import re

import faiss
import fitz  # PyMuPDF
import numpy as np
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer

from models import (
    StudentAIConversations,
    TeacherAIConversations,
    StudentAIMessages,
    TeacherAIMessages,
    db,
)


class AIStudent:
    def __init__(self, open_api_key):
        current_dir = pathlib.Path(__file__).parent.absolute()
        self.save_dir = os.path.join(current_dir, "saved_data")

        # os.makedirs(self.save_dir, exist_ok=True)

        print(f"保存目錄路徑: {self.save_dir}")

        self.openai_api_key = open_api_key
        self.llm = ChatOpenAI(
            api_key=self.openai_api_key, max_tokens=4096, model_name="gpt-4o"
        )
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.system_context = None

    def load_teacher_conversation_history(self, course_id):
        conversations = TeacherAIConversations.query.filter_by(course_id=course_id).all()
        if not conversations:
            return []
        history = []
        for conversation in conversations:
            messages = (
                TeacherAIMessages.query.filter_by(conversation_id=conversation.id)
                .order_by(TeacherAIMessages.sent_at)
                .all()
            )
            for msg in messages:
                history.append((msg.id, msg.sender, msg.message, msg.sent_at))
            # history.append(
            #     (msg.id, msg.sender, msg.message, msg.sent_at) for msg in messages
            # )
        # history = [(msg.id, msg.sender, msg.message, msg.sent_at) for msg in messages]
        return history

    def load_conversation_history(self, course_id, course_section, student_id):
        conversation = StudentAIConversations.query.filter_by(
            course_id=course_id, course_section=course_section
        ).first()
        if not conversation:
            return None, []

        messages = (
            StudentAIMessages.query.filter_by(
                conversation_id=conversation.id, student_id=student_id
            )
            .order_by(StudentAIMessages.sent_at)
            .all()
        )
        history = [(msg.id, msg.sender, msg.message, msg.sent_at) for msg in messages]
        return conversation, history

    def save_message(self, conversation_id, user_id, sender, message):
        new_message = StudentAIMessages(
            conversation_id=conversation_id,
            student_id=user_id,
            sender=sender,
            message=message,
        )
        db.session.add(new_message)
        db.session.commit()

    def load_faiss_index(self, name="current"):
        """載入 FAISS 索引和對應的句子"""
        try:
            index_path = os.path.join(self.save_dir, f"{name}_index.faiss")
            index = faiss.read_index(index_path)

            sentences_path = os.path.join(self.save_dir, f"{name}_sentences.json")
            with open(sentences_path, "r", encoding="utf-8") as f:
                sentences = json.load(f)

            return index, sentences
        except Exception as e:
            print(f"載入 FAISS 索引時發生錯誤: {e}")
            return None, None

    def search_rag(self, query, index, sentences, top_k=10):
        try:
            query_embedding = self.model.encode([query])
            distances, indices = index.search(query_embedding, top_k)
            return [sentences[i] for i in indices[0]]
        except Exception as e:
            print(f"Error during RAG search: {e}")
            return []

    def generate_response(self, messages):
        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"Error generating response: {e}")
            return "抱歉，我無法處理您的請求。"

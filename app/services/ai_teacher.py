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

from app.models import (
    TeacherAIConversations,
    TeacherAIMessages,
    db,
)


class AITeacher:
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

    def summarize_text(self, text):
        messages = [
            SystemMessage(
                content="以下為教師傳給 AI 的問題，請用一段文字總結教師的問題，不要加上主詞"
            ),
            HumanMessage(content=text),
        ]

        try:
            summary = self.generate_response(messages)
            return summary
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "無法生成摘要。"

    def load_conversation_history(self, conversation_uuid):
        conversation = TeacherAIConversations.query.filter_by(uuid=conversation_uuid).first()
        if not conversation:
            return None, []

        messages = (
            TeacherAIMessages.query.filter_by(conversation_id=conversation.id)
            .order_by(TeacherAIMessages.sent_at)
            .all()
        )
        history = [(msg.id, msg.sender, msg.message, msg.sent_at) for msg in messages]
        return conversation, history

    def save_message(self, conversation_id, sender, message):
        new_message = TeacherAIMessages(
            conversation_id=conversation_id, sender=sender, message=message
        )
        db.session.add(new_message)
        db.session.commit()

    def extract_text_from_pdf(self, pdf_path):
        """從 PDF 提取文本"""
        try:
            pdf_absolute_path = os.path.abspath(pdf_path)
            print(f"PDF 文件路徑: {pdf_absolute_path}")  # 調試信息

            if not os.path.exists(pdf_absolute_path):
                print(f"PDF 文件不存在: {pdf_absolute_path}")
                return ""

            doc = fitz.open(pdf_absolute_path)
            text = ""
            for page in doc:
                text += page.get_text()

            print(f"提取的文本長度: {len(text)}")  # 調試信息
            return text

        except Exception as e:
            print(f"提取 PDF 文本時發生錯誤: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return ""

    def build_faiss_index(self, text, save_name=None):
        try:
            # 分割句子並移除空白行
            sentences = re.split('(?<=[。！？])', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            print(f"總句子數: {len(sentences)}")  # 調試信息

            if not sentences:
                print("警告：沒有找到有效的句子")
                return None, None

            # 生成嵌入向量
            print("開始生成嵌入向量...")  # 調試信息
            embeddings = self.model.encode(sentences)
            embeddings = embeddings.astype(np.float32)
            print(f"嵌入向量形狀: {embeddings.shape}")  # 調試信息

            # 建立索引
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings)
            print(f"索引中的向量數: {index.ntotal}")  # 調試信息

            # 如果提供了保存名稱，則保存索引
            if save_name:
                save_success = self.save_faiss_index(index, sentences, save_name)
                if save_success:
                    print("索引保存成功")
                else:
                    print("索引保存失敗")

            return index, sentences

        except Exception as e:
            print(f"建立 FAISS 索引時發生錯誤: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return None, None

    def save_faiss_index(self, index, sentences, name="current"):
        """保存 FAISS 索引和對應的句子"""
        try:
            index_path = os.path.join(self.save_dir, f"{name}_index.faiss")
            sentences_path = os.path.join(self.save_dir, f"{name}_sentences.json")

            # 保存 FAISS 索引
            faiss.write_index(index, index_path)
            print(f"FAISS 索引已保存到: {index_path}")  # 調試信息

            # 保存對應的句子
            with open(sentences_path, "w", encoding="utf-8") as f:
                json.dump(sentences, f, ensure_ascii=False, indent=2)
            print(f"句子數據已保存到: {sentences_path}")  # 調試信息

            # 驗證文件是否確實被創建
            if os.path.exists(index_path) and os.path.exists(sentences_path):
                file_size_index = os.path.getsize(index_path)
                file_size_sentences = os.path.getsize(sentences_path)
                print(f"索引文件大小: {file_size_index} bytes")  # 調試信息
                print(f"句子文件大小: {file_size_sentences} bytes")  # 調試信息
                return True
            else:
                print("文件保存失敗，文件不存在")  # 調試信息
                return False

        except Exception as e:
            print(f"保存 FAISS 索引時發生錯誤: {str(e)}")
            import traceback

            print(traceback.format_exc())  # 打印完整的錯誤堆疊
            return False

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

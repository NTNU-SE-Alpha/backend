import os
from urllib.parse import quote_plus
from dotenv import load_dotenv


# 載入 .env 檔
load_dotenv()


class Config:
        
    ALLOWED_EXTENSIONS = {"pdf"}
    OTHER_ALLOWED_EXTENSIONS = {
        "pdf",
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "webp",
        "doc",
        "docx",
        "txt",
    }

    
    SECRET_KEY = os.environ.get("SECRET_KEY")

    DB_HOST = str(os.environ.get("DB_HOST"))
    DB_USER = str(os.environ.get("DB_USER"))
    DB_PASSWORD = str(os.environ.get("DB_PASSWORD"))
    DB_NAME = str(os.environ.get("DB_NAME"))
    DB_PORT = int(os.environ.get("DB_PORT"))
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = False

    JSON_AS_ASCII = False
    JSONIFY_MIMETYPE = "application/json;charset=utf-8"

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

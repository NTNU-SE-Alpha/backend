from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from app.extensions import socketio

from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.models import db

app = Flask(__name__)

def create_app(environment="development"):
    if environment == "development":
        app.config.from_object(DevelopmentConfig)
    elif environment == "production":
        app.config.from_object(ProductionConfig)
    elif environment == "testing":
        app.config.from_object(TestingConfig)

    CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt = JWTManager(app)
    socketio.init_app(app)

    with app.app_context():
        from app.routes import ai_chat, auth, course, file, group_chat, user, student

        app.register_blueprint(auth.bp)
        app.register_blueprint(user.bp)
        app.register_blueprint(course.bp)
        app.register_blueprint(ai_chat.bp)
        app.register_blueprint(file.bp)
        app.register_blueprint(group_chat.bp)
        app.register_blueprint(student.bp)
        return app

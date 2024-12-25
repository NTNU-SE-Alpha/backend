import hashlib
import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from flask_socketio import join_room, send
from app.extensions import socketio

from app.models import (
    Course,
    Student,
    StudentGroupMessage,
    db,
)

bp = Blueprint("group_chat", __name__)


@bp.route("/group_chat_history", methods=["GET"])
@jwt_required()
def group_chat_history():
    claims = get_jwt()
    user_id = claims.get("user_id")
    user_type = claims.get("user_type")
    if user_type != "student":
        return jsonify({"message": "Access forbidden: Studnets only."}), 403
    user = Student.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    room = f"{user.course}-{user.group_number}"
    messages = (
        StudentGroupMessage.query.filter_by(room=room)
        .order_by(StudentGroupMessage.sent_at)
        .all()
    )

    formatted_history = [
        {
            "id": message.id,
            "student_id": message.student_id,
            "username": message.sender,
            "message": message.message,
            "sent_at": message.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for message in messages
    ]
    return jsonify(
        {
            "course": Course.query.filter_by(id=user.course).first().name,
            "group_number": user.group_number,
            "history": formatted_history,
        }
    )


@socketio.on("join_group_chat")
@jwt_required()
def handle_join(data):
    claims = get_jwt()
    user_id = claims.get("user_id")
    user_type = claims.get("user_type")
    if user_type != "student":
        return jsonify({"message": "Access forbidden: Studnets only."}), 403
    user = Student.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    room = f"{user.course}-{user.group_number}"

    join_room(room)


@socketio.on("message")
@jwt_required()
def handle_message(data):
    claims = get_jwt()
    user_id = claims.get("user_id")
    user_type = claims.get("user_type")
    if user_type != "student":
        return jsonify({"message": "Access forbidden: Studnets only."}), 403
    user = Student.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    room = f"{user.course}-{user.group_number}"

    message = StudentGroupMessage(
        student_id=user.id, sender=user.name, room=room, message=data
    )
    db.session.add(message)
    db.session.commit()

    send(
        {
            "student_id": user.id,
            "sender": user.name,
            "message": data,
            "sent_at": message.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
        room=room,
    )

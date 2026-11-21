from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room
from backend.database import db_session
from backend.models import UnderstandingResponse, Lecture

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")

@socketio.on("connect")
def handle_connect():
    # Client connected
    pass

@socketio.on("disconnect")
def handle_disconnect():
    # Client disconnected
    pass

@socketio.on("join_lecture")
def handle_join_lecture(data):
    """
    Client joins a lecture room to receive real-time updates:
    - QR refresh (every 10s)
    - Confusion tally updates
    - Question release notifications
    """
    lecture_id = data.get("lecture_id")
    if lecture_id:
        room = f"lecture_{lecture_id}"
        join_room(room)
        emit("joined_lecture", {"room": room, "status": "success"}, to=request.sid)

@socketio.on("leave_lecture")
def handle_leave_lecture(data):
    lecture_id = data.get("lecture_id")
    if lecture_id:
        room = f"lecture_{lecture_id}"
        leave_room(room)
        emit("left_lecture", {"room": room, "status": "success"}, to=request.sid)

@socketio.on("ping_server")
def handle_ping():
    emit("pong_server", {"message": "FLASHNOVA real-time engine active"})

def emit_qr_update(lecture_id: int, qr_data: dict):
    """
    Broadcasts newly refreshed QR token to the lecture room.
    """
    room = f"lecture_{lecture_id}"
    socketio.emit("qr_refreshed", qr_data, room=room)

def emit_confusion_update(lecture_id: int):
    """
    Broadcasts aggregated confusion counts to teacher in real-time.
    """
    db = db_session()
    try:
        records = db.query(UnderstandingResponse).filter_by(lecture_id=lecture_id).all()
        u = sum(1 for r in records if r.status == "UNDERSTAND")
        d = sum(1 for r in records if r.status == "DOUBT")
        du = sum(1 for r in records if r.status == "DONT_UNDERSTAND")
        room = f"lecture_{lecture_id}"
        socketio.emit("confusion_tally", {
            "lecture_id": lecture_id,
            "understand": u,
            "doubt": d,
            "dont_understand": du,
            "total": len(records)
        }, room=room)
    finally:
        db.close()

def emit_doubt_alert(lecture_id: int, doubt_data: dict):
    """
    Notifies teacher of a new voluntary doubt.
    """
    room = f"lecture_{lecture_id}"
    socketio.emit("new_voluntary_doubt", doubt_data, room=room)

def emit_attendance_update(lecture_id: int, masked_record: dict):
    """
    Broadcasts real-time attendance change to teacher screen.
    """
    room = f"lecture_{lecture_id}"
    socketio.emit("attendance_change", masked_record, room=room)

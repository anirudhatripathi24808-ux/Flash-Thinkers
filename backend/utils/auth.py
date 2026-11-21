import functools
from flask import request, session, jsonify, g
from backend.database import db_session
from backend.models import User

def get_current_user():
    """
    Retrieves the currently authenticated User object from Flask session or Authorization header.
    """
    user_id = session.get("user_id")
    
    # Also check Bearer / Custom Token header for cross-origin GitHub Pages clients
    auth_header = request.headers.get("Authorization")
    if not user_id and auth_header:
        # Expected format: "Bearer <user_id>" or "Token <user_id>"
        parts = auth_header.split()
        if len(parts) == 2 and parts[1].isdigit():
            user_id = int(parts[1])
            
    if not user_id:
        return None
        
    db = db_session()
    user = db.query(User).filter_by(id=user_id).first()
    return user

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "Authentication required."}), 401
        if user.role != "teacher":
            return jsonify({"success": False, "error": "Access denied. Teacher privilege required."}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "Authentication required."}), 401
        if user.role != "student":
            return jsonify({"success": False, "error": "Access denied. Student privilege required."}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated_function

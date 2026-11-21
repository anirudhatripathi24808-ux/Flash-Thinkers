import re
from flask import Blueprint, request, jsonify, session
from backend.database import db_session
from backend.models import User, StudentProfile, TeacherProfile, Subject, AuditEvent
from backend.utils.auth import get_current_user, login_required
from backend.config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/student/register", methods=["POST"])
def register_student():
    """
    One-time Student Registration:
    - Full Name
    - Enrollment Number (strictly 10 digits, numeric only)
    - Password and Confirm Password
    - Duplicate check
    - Demo flag identification
    """
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    enrollment_no = (data.get("enrollment_no") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    is_demo = bool(data.get("is_demo", False))
    
    if not name:
        return jsonify({"success": False, "error": "Full Name is required"}), 400
        
    # Strictly 10 digits validation
    if not re.fullmatch(r"^\d{10}$", enrollment_no):
        return jsonify({
            "success": False, 
            "error": "Enrollment number must be exactly 10 numeric digits with no letters, spaces, or special characters"
        }), 400
        
    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
        
    if password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match"}), 400
        
    db = db_session()
    try:
        # Check duplicate enrollment
        existing = db.query(StudentProfile).filter_by(enrollment_no=enrollment_no).first()
        if existing:
            return jsonify({"success": False, "error": f"Enrollment number {enrollment_no} is already registered"}), 409
            
        user = User(
            role="student",
            name=name,
            username=f"student_{enrollment_no}"
        )
        user.set_password(password)
        db.add(user)
        db.flush()
        
        profile = StudentProfile(
            user_id=user.id,
            enrollment_no=enrollment_no,
            is_demo=is_demo
        )
        db.add(profile)
        db.commit()
        
        # Setup session
        session["user_id"] = user.id
        session["role"] = "student"
        session["enrollment_no"] = enrollment_no
        
        return jsonify({
            "success": True,
            "message": "Student registration successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "role": "student",
                "enrollment_no": enrollment_no,
                "is_demo": is_demo
            },
            "token": str(user.id)
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Registration failed: {str(e)}"}), 500
    finally:
        db.close()

@auth_bp.route("/student/login", methods=["POST"])
def login_student():
    """
    Student Login:
    - Enrollment Number (10 digits)
    - Password
    """
    data = request.get_json() or {}
    enrollment_no = (data.get("enrollment_no") or "").strip()
    password = data.get("password") or ""
    
    if not enrollment_no or not password:
        return jsonify({"success": False, "error": "Enrollment number and password are required"}), 400
        
    db = db_session()
    try:
        profile = db.query(StudentProfile).filter_by(enrollment_no=enrollment_no).first()
        if not profile or not profile.user or not profile.user.check_password(password):
            return jsonify({"success": False, "error": "Invalid enrollment number or password"}), 401
            
        user = profile.user
        session["user_id"] = user.id
        session["role"] = "student"
        session["enrollment_no"] = enrollment_no
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "role": "student",
                "enrollment_no": profile.enrollment_no,
                "is_demo": profile.is_demo
            },
            "token": str(user.id)
        })
    finally:
        db.close()

@auth_bp.route("/teacher/register", methods=["POST"])
def register_teacher():
    """
    Teacher Registration:
    - Name
    - Username
    - Password & Confirm Password
    """
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    department = (data.get("department") or "Engineering").strip()
    
    if not name or not username:
        return jsonify({"success": False, "error": "Name and username are required"}), 400
        
    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
        
    if password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match"}), 400
        
    db = db_session()
    try:
        existing = db.query(User).filter_by(username=username).first()
        if existing:
            return jsonify({"success": False, "error": "Username already taken"}), 409
            
        user = User(
            role="teacher",
            name=name,
            username=username
        )
        user.set_password(password)
        db.add(user)
        db.flush()
        
        profile = TeacherProfile(
            user_id=user.id,
            department=department
        )
        db.add(profile)
        db.commit()
        
        session["user_id"] = user.id
        session["role"] = "teacher"
        
        return jsonify({
            "success": True,
            "message": "Teacher registered successfully",
            "user": user.to_dict(),
            "token": str(user.id)
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route("/teacher/login", methods=["POST"])
def login_teacher():
    """
    Teacher Login (Step 1):
    - Username
    - Password
    """
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required"}), 400
        
    db = db_session()
    try:
        user = db.query(User).filter_by(username=username, role="teacher").first()
        if not user or not user.check_password(password):
            return jsonify({"success": False, "error": "Invalid teacher username or password"}), 401
            
        session["user_id"] = user.id
        session["role"] = "teacher"
        
        return jsonify({
            "success": True,
            "message": "Credentials verified. Proceed to subject selection.",
            "user": user.to_dict(),
            "token": str(user.id)
        })
    finally:
        db.close()

@auth_bp.route("/teacher/subjects", methods=["GET"])
def get_available_subjects():
    """
    Returns the three supported subjects for teacher subject selection cards:
    1. Mathematics – MAT121
    2. Chemistry – CHM131
    3. Workshop – WSP111
    """
    db = db_session()
    try:
        subjects = db.query(Subject).all()
        return jsonify({
            "success": True,
            "subjects": [s.to_dict() for s in subjects]
        })
    finally:
        db.close()

@auth_bp.route("/teacher/verify-subject", methods=["POST"])
@login_required
def verify_subject_code():
    """
    Teacher Subject Verification (Step 2 & 3):
    - Subject Code selected (MAT121, CHM131, WSP111)
    - Access Code entered by teacher
    Validates against backend configured access codes.
    """
    user = get_current_user()
    if user.role != "teacher":
        return jsonify({"success": False, "error": "Only teachers can verify subjects"}), 403
        
    data = request.get_json() or {}
    subject_code = (data.get("subject_code") or "").strip().upper()
    access_code = (data.get("access_code") or "").strip()
    
    if not subject_code or not access_code:
        return jsonify({"success": False, "error": "Subject code and access code are required"}), 400
        
    db = db_session()
    try:
        subject = db.query(Subject).filter_by(code=subject_code).first()
        if not subject:
            return jsonify({"success": False, "error": f"Subject '{subject_code}' not found"}), 404
            
        if subject.access_code != access_code:
            return jsonify({"success": False, "error": f"Incorrect access code for {subject.name} ({subject.code})"}), 401
            
        # Store authorized subject in session
        session["authorized_subject_id"] = subject.id
        session["authorized_subject_code"] = subject.code
        
        return jsonify({
            "success": True,
            "message": f"Subject {subject.name} verified successfully",
            "subject": subject.to_dict()
        })
    finally:
        db.close()

@auth_bp.route("/me", methods=["GET"])
def get_me():
    """
    Returns current user info:
    - Student gets full enrollment number in their private profile
    - Teacher gets authorized subject info
    """
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "authenticated": False}), 200
        
    db = db_session()
    try:
        user_info = user.to_dict()
        user_info["authenticated"] = True
        
        if user.role == "student" and user.student_profile:
            user_info["enrollment_no"] = user.student_profile.enrollment_no
            user_info["is_demo"] = user.student_profile.is_demo
        elif user.role == "teacher":
            subj_id = session.get("authorized_subject_id")
            if subj_id:
                subj = db.query(Subject).filter_by(id=subj_id).first()
                user_info["authorized_subject"] = subj.to_dict() if subj else None
            else:
                user_info["authorized_subject"] = None
                
        return jsonify({"success": True, "user": user_info})
    finally:
        db.close()

@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

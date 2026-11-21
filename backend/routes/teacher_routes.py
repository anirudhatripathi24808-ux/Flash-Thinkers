import os
import uuid
import datetime
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from backend.database import db_session
from backend.models import (
    User, Subject, Classroom, ClassroomMembership, Lecture, QRToken,
    Attendance, PresenceVerification, UploadedFile, Question, QuestionOption,
    AnswerAttempt, UnderstandingResponse, Doubt, TeacherReply, AuditEvent, StudentProfile
)
from backend.utils.auth import get_current_user, teacher_required
from backend.utils.privacy import generate_masked_aliases, sanitize_teacher_record, mask_enrollment
from backend.utils.qr_crypto import generate_lecture_qr_token
from backend.config import Config

teacher_bp = Blueprint("teacher", __name__, url_prefix="/api/teacher")

def is_allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

# ----------------- Classroom Management -----------------

@teacher_bp.route("/classrooms", methods=["GET"])
@teacher_required
def get_teacher_classrooms():
    user = get_current_user()
    db = db_session()
    try:
        query = db.query(Classroom).filter_by(teacher_id=user.id)
        # Filter by authorized subject if set in session
        subj_id = session.get("authorized_subject_id")
        if subj_id:
            query = query.filter_by(subject_id=subj_id)
            
        classrooms = query.order_by(Classroom.created_at.desc()).all()
        result = []
        for c in classrooms:
            data = c.to_dict()
            data["student_count"] = db.query(ClassroomMembership).filter_by(classroom_id=c.id).count()
            # Check if has active lecture
            active_lec = db.query(Lecture).filter_by(classroom_id=c.id, is_active=True).first()
            data["active_lecture"] = active_lec.to_dict() if active_lec else None
            result.append(data)
        return jsonify({"success": True, "classrooms": result})
    finally:
        db.close()

@teacher_bp.route("/classrooms", methods=["POST"])
@teacher_required
def create_classroom():
    user = get_current_user()
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    subject_id = data.get("subject_id") or session.get("authorized_subject_id")
    allow_qr_auto_enroll = bool(data.get("allow_qr_auto_enroll", True))
    
    if not name or not subject_id:
        return jsonify({"success": False, "error": "Classroom name and subject are required"}), 400
        
    db = db_session()
    try:
        subj = db.query(Subject).filter_by(id=subject_id).first()
        if not subj:
            return jsonify({"success": False, "error": "Invalid subject selected"}), 404
            
        code = f"{subj.code}-{uuid.uuid4().hex[:6].upper()}"
        classroom = Classroom(
            name=name,
            code=code,
            subject_id=subj.id,
            teacher_id=user.id,
            allow_qr_auto_enroll=allow_qr_auto_enroll
        )
        db.add(classroom)
        db.commit()
        return jsonify({"success": True, "classroom": classroom.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@teacher_bp.route("/classrooms/<int:classroom_id>/toggle-auto-enroll", methods=["POST"])
@teacher_required
def toggle_auto_enroll(classroom_id: int):
    user = get_current_user()
    db = db_session()
    try:
        classroom = db.query(Classroom).filter_by(id=classroom_id, teacher_id=user.id).first()
        if not classroom:
            return jsonify({"success": False, "error": "Classroom not found"}), 404
            
        classroom.allow_qr_auto_enroll = not classroom.allow_qr_auto_enroll
        db.commit()
        return jsonify({
            "success": True, 
            "allow_qr_auto_enroll": classroom.allow_qr_auto_enroll,
            "message": f"QR Auto-Enrollment {'enabled' if classroom.allow_qr_auto_enroll else 'disabled'}"
        })
    finally:
        db.close()

# ----------------- Lecture & Dynamic QR -----------------

@teacher_bp.route("/lectures/start", methods=["POST"])
@teacher_required
def start_lecture():
    user = get_current_user()
    data = request.get_json() or {}
    classroom_id = data.get("classroom_id")
    topic = (data.get("topic") or "").strip()
    
    if not classroom_id or not topic:
        return jsonify({"success": False, "error": "Classroom and topic name are required"}), 400
        
    db = db_session()
    try:
        classroom = db.query(Classroom).filter_by(id=classroom_id, teacher_id=user.id).first()
        if not classroom:
            return jsonify({"success": False, "error": "Classroom not found or unauthorized"}), 404
            
        # End any currently active lecture for this classroom
        prev_active = db.query(Lecture).filter_by(classroom_id=classroom.id, is_active=True).all()
        now = datetime.datetime.utcnow()
        for p in prev_active:
            p.is_active = False
            p.ended_at = now
            
        lecture = Lecture(
            classroom_id=classroom.id,
            topic=topic,
            is_active=True,
            started_at=now
        )
        db.add(lecture)
        db.commit()
        
        # Serialize lecture dict
        lecture_data = lecture.to_dict()
        
        # Immediately generate first QR token using same db session
        qr_data = generate_lecture_qr_token(lecture.id, db=db)
        
        return jsonify({
            "success": True,
            "lecture": lecture_data,
            "qr": qr_data
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@teacher_bp.route("/lectures/<int:lecture_id>/stop", methods=["POST"])
@teacher_required
def stop_lecture(lecture_id: int):
    user = get_current_user()
    db = db_session()
    try:
        lecture = db.query(Lecture).join(Classroom).filter(
            Lecture.id == lecture_id,
            Classroom.teacher_id == user.id
        ).first()
        if not lecture:
            return jsonify({"success": False, "error": "Lecture not found"}), 404
            
        lecture.is_active = False
        lecture.ended_at = datetime.datetime.utcnow()
        db.commit()
        return jsonify({"success": True, "message": "Lecture ended successfully", "lecture": lecture.to_dict()})
    finally:
        db.close()

@teacher_bp.route("/lectures/<int:lecture_id>/qr", methods=["GET"])
@teacher_required
def get_dynamic_qr(lecture_id: int):
    """
    Refreshes dynamic QR token for active lecture (10s expiry).
    """
    user = get_current_user()
    db = db_session()
    try:
        lecture = db.query(Lecture).join(Classroom).filter(
            Lecture.id == lecture_id,
            Classroom.teacher_id == user.id,
            Lecture.is_active == True
        ).first()
        if not lecture:
            return jsonify({"success": False, "error": "Active lecture not found"}), 404
            
        qr_data = generate_lecture_qr_token(lecture.id, db=db)
        return jsonify(qr_data)
    finally:
        db.close()

# ----------------- File Management -----------------

@teacher_bp.route("/files", methods=["POST"])
@teacher_required
def upload_study_file():
    user = get_current_user()
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
        
    uploaded_file = request.files["file"]
    if uploaded_file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400
        
    classroom_id = request.form.get("classroom_id")
    lecture_id = request.form.get("lecture_id")
    title = (request.form.get("title") or uploaded_file.filename).strip()
    description = (request.form.get("description") or "").strip()
    
    if not classroom_id:
        return jsonify({"success": False, "error": "Classroom ID is required"}), 400
        
    if not is_allowed_file(uploaded_file.filename):
        return jsonify({
            "success": False, 
            "error": f"Invalid file format. Allowed: {', '.join(sorted(Config.ALLOWED_EXTENSIONS))}"
        }), 400
        
    orig_name = secure_filename(uploaded_file.filename)
    ext = orig_name.rsplit(".", 1)[1].lower() if "." in orig_name else "bin"
    stored_name = f"{uuid.uuid4().hex}_{orig_name}"
    save_path = os.path.join(Config.UPLOAD_FOLDER, stored_name)
    
    uploaded_file.save(save_path)
    file_size = os.path.getsize(save_path)
    
    db = db_session()
    try:
        file_obj = UploadedFile(
            classroom_id=int(classroom_id),
            lecture_id=int(lecture_id) if lecture_id else None,
            teacher_id=user.id,
            original_filename=orig_name,
            stored_filename=stored_name,
            file_type=ext.upper(),
            file_size=file_size,
            title=title,
            description=description,
            is_published=True
        )
        db.add(file_obj)
        db.commit()
        return jsonify({"success": True, "file": file_obj.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@teacher_bp.route("/files", methods=["GET"])
@teacher_required
def list_teacher_files():
    user = get_current_user()
    classroom_id = request.args.get("classroom_id")
    db = db_session()
    try:
        query = db.query(UploadedFile).filter_by(teacher_id=user.id)
        if classroom_id:
            query = query.filter_by(classroom_id=int(classroom_id))
        files = query.order_by(UploadedFile.uploaded_at.desc()).all()
        return jsonify({"success": True, "files": [f.to_dict() for f in files]})
    finally:
        db.close()

@teacher_bp.route("/files/<int:file_id>/toggle-publish", methods=["POST"])
@teacher_required
def toggle_file_publish(file_id: int):
    user = get_current_user()
    db = db_session()
    try:
        file_obj = db.query(UploadedFile).filter_by(id=file_id, teacher_id=user.id).first()
        if not file_obj:
            return jsonify({"success": False, "error": "File not found"}), 404
        file_obj.is_published = not file_obj.is_published
        db.commit()
        return jsonify({
            "success": True, 
            "is_published": file_obj.is_published,
            "message": f"File {'published' if file_obj.is_published else 'unpublished'}"
        })
    finally:
        db.close()

@teacher_bp.route("/files/<int:file_id>", methods=["DELETE"])
@teacher_required
def delete_file(file_id: int):
    user = get_current_user()
    db = db_session()
    try:
        file_obj = db.query(UploadedFile).filter_by(id=file_id, teacher_id=user.id).first()
        if not file_obj:
            return jsonify({"success": False, "error": "File not found"}), 404
            
        file_path = os.path.join(Config.UPLOAD_FOLDER, file_obj.stored_filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
                
        db.delete(file_obj)
        db.commit()
        return jsonify({"success": True, "message": "File deleted successfully"})
    finally:
        db.close()

# ----------------- Manual Question Management -----------------

@teacher_bp.route("/questions", methods=["POST"])
@teacher_required
def create_question():
    user = get_current_user()
    data = request.get_json() or {}
    classroom_id = data.get("classroom_id")
    lecture_id = data.get("lecture_id")
    question_text = (data.get("question_text") or "").strip()
    topic = (data.get("topic") or "General").strip()
    difficulty = (data.get("difficulty") or "Medium").strip()
    is_compulsory = bool(data.get("is_compulsory", True))
    correct_answer = (data.get("correct_answer") or "").strip().upper()
    status = (data.get("status") or "PUBLISHED").strip().upper()
    options_data = data.get("options") or {}  # Dict like {'A': '...', 'B': '...', 'C': '...', 'D': '...'}
    
    if not classroom_id or not question_text:
        return jsonify({"success": False, "error": "Classroom and question text are required"}), 400
        
    if correct_answer not in {"A", "B", "C", "D"}:
        return jsonify({"success": False, "error": "Correct answer must be A, B, C, or D"}), 400
        
    db = db_session()
    try:
        q = Question(
            classroom_id=int(classroom_id),
            lecture_id=int(lecture_id) if lecture_id else None,
            question_text=question_text,
            topic=topic,
            difficulty=difficulty,
            is_compulsory=is_compulsory,
            status=status,
            correct_answer=correct_answer,
            reveal_answer=False
        )
        db.add(q)
        db.flush()
        
        # Add 4 options
        for key in ["A", "B", "C", "D"]:
            opt_text = options_data.get(key) or options_data.get(key.lower()) or f"Option {key}"
            opt = QuestionOption(question_id=q.id, key=key, text=opt_text.strip())
            db.add(opt)
            
        db.commit()
        return jsonify({"success": True, "question": q.to_dict(include_correct=True)}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@teacher_bp.route("/questions", methods=["GET"])
@teacher_required
def list_questions():
    classroom_id = request.args.get("classroom_id")
    lecture_id = request.args.get("lecture_id")
    db = db_session()
    try:
        query = db.query(Question)
        if classroom_id:
            query = query.filter_by(classroom_id=int(classroom_id))
        if lecture_id:
            query = query.filter_by(lecture_id=int(lecture_id))
            
        questions = query.order_by(Question.created_at.desc()).all()
        return jsonify({"success": True, "questions": [q.to_dict(include_correct=True) for q in questions]})
    finally:
        db.close()

@teacher_bp.route("/questions/<int:question_id>/toggle-reveal", methods=["POST"])
@teacher_required
def toggle_reveal_answer(question_id: int):
    db = db_session()
    try:
        q = db.query(Question).filter_by(id=question_id).first()
        if not q:
            return jsonify({"success": False, "error": "Question not found"}), 404
        q.reveal_answer = not q.reveal_answer
        db.commit()
        return jsonify({
            "success": True, 
            "reveal_answer": q.reveal_answer,
            "message": f"Answer {'revealed to students' if q.reveal_answer else 'hidden from students'}"
        })
    finally:
        db.close()

@teacher_bp.route("/questions/<int:question_id>", methods=["DELETE"])
@teacher_required
def delete_question(question_id: int):
    db = db_session()
    try:
        q = db.query(Question).filter_by(id=question_id).first()
        if not q:
            return jsonify({"success": False, "error": "Question not found"}), 404
        db.delete(q)
        db.commit()
        return jsonify({"success": True, "message": "Question deleted successfully"})
    finally:
        db.close()

# ----------------- Voluntary Doubt Inbox -----------------

@teacher_bp.route("/doubts", methods=["GET"])
@teacher_required
def get_voluntary_doubts():
    """
    Teacher Voluntary Doubt Inbox:
    Shows explicitly consented doubt requests.
    Contains Student Full Name, Full Enrollment Number, written doubt, timestamp, status.
    """
    lecture_id = request.args.get("lecture_id")
    classroom_id = request.args.get("classroom_id")
    db = db_session()
    try:
        query = db.query(Doubt).join(Lecture).join(Classroom)
        user = get_current_user()
        query = query.filter(Classroom.teacher_id == user.id)
        
        if lecture_id:
            query = query.filter(Doubt.lecture_id == int(lecture_id))
        if classroom_id:
            query = query.filter(Lecture.classroom_id == int(classroom_id))
            
        doubts = query.order_by(Doubt.created_at.desc()).all()
        result = []
        for d in doubts:
            student_profile = db.query(StudentProfile).filter_by(user_id=d.student_id).first()
            replies = db.query(TeacherReply).filter_by(doubt_id=d.id).order_by(TeacherReply.created_at.asc()).all()
            result.append({
                "id": d.id,
                "lecture_id": d.lecture_id,
                "lecture_topic": d.lecture.topic if d.lecture else None,
                "classroom_name": d.lecture.classroom.name if d.lecture and d.lecture.classroom else None,
                "student_name": d.student.name if d.student else "Unknown",
                "student_enrollment_no": student_profile.enrollment_no if student_profile else "N/A",
                "topic": d.topic,
                "doubt_text": d.doubt_text,
                "is_consented": d.is_consented,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "replies": [{
                    "id": r.id,
                    "teacher_name": r.teacher.name if r.teacher else "Teacher",
                    "reply_text": r.reply_text,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in replies]
            })
        return jsonify({"success": True, "doubts": result})
    finally:
        db.close()

@teacher_bp.route("/doubts/<int:doubt_id>/reply", methods=["POST"])
@teacher_required
def reply_to_doubt(doubt_id: int):
    user = get_current_user()
    data = request.get_json() or {}
    reply_text = (data.get("reply_text") or "").strip()
    new_status = (data.get("status") or "Resolved").strip()
    
    if not reply_text:
        return jsonify({"success": False, "error": "Reply text cannot be empty"}), 400
        
    db = db_session()
    try:
        doubt = db.query(Doubt).filter_by(id=doubt_id).first()
        if not doubt:
            return jsonify({"success": False, "error": "Doubt not found"}), 404
            
        reply = TeacherReply(
            doubt_id=doubt.id,
            teacher_id=user.id,
            reply_text=reply_text
        )
        db.add(reply)
        doubt.status = new_status
        db.commit()
        return jsonify({"success": True, "message": "Reply sent successfully", "status": doubt.status})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

# ----------------- Presence Verification & Challenges -----------------

@teacher_bp.route("/lectures/<int:lecture_id>/verifications", methods=["GET"])
@teacher_required
def get_presence_verifications(lecture_id: int):
    """
    Returns presence verification records for lecture.
    Strictly MASKED: enrollment numbers are 1234******.
    NO student names or raw emails leak!
    """
    db = db_session()
    try:
        records = db.query(PresenceVerification).filter_by(lecture_id=lecture_id).all()
        # Collect enrollments for collision aliasing
        enrollments = []
        for r in records:
            sp = db.query(StudentProfile).filter_by(user_id=r.student_id).first()
            if sp:
                enrollments.append(sp.enrollment_no)
        masked_map = generate_masked_aliases(enrollments)
        
        result = []
        for r in records:
            sp = db.query(StudentProfile).filter_by(user_id=r.student_id).first()
            enr = sp.enrollment_no if sp else None
            result.append({
                "id": r.id,
                "student_masked_id": masked_map.get(enr, mask_enrollment(enr)),
                "status": r.status,
                "has_location": bool(r.latitude and r.longitude),
                "device_info": r.device_info or "Unknown Device",
                "verified_at": r.verified_at.isoformat() if r.verified_at else None
            })
        return jsonify({"success": True, "verifications": result})
    finally:
        db.close()

@teacher_bp.route("/verifications/<int:verification_id>/status", methods=["POST"])
@teacher_required
def update_verification_status(verification_id: int):
    data = request.get_json() or {}
    new_status = data.get("status")  # 'VERIFIED' or 'REJECTED'
    if new_status not in {"VERIFIED", "REJECTED"}:
        return jsonify({"success": False, "error": "Invalid status"}), 400
        
    db = db_session()
    try:
        pv = db.query(PresenceVerification).filter_by(id=verification_id).first()
        if not pv:
            return jsonify({"success": False, "error": "Verification record not found"}), 404
        pv.status = new_status
        
        # Trigger recalculation of attendance for this student and lecture
        recalculate_student_attendance(db, pv.lecture_id, pv.student_id)
        db.commit()
        return jsonify({"success": True, "status": pv.status, "message": f"Verification updated to {pv.status}"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

def recalculate_student_attendance(db, lecture_id: int, student_id: int):
    """
    Recalculates attendance according to Rule 17:
    Student is Present ONLY when:
    1. Valid QR scanned for lecture.
    2. Required presence verification is completed/approved (status == 'VERIFIED').
    3. Attempted every compulsory question assigned to that lecture.
    Missing even one compulsory question means In Progress.
    Pending verification means Pending Verification.
    No valid QR scan means Not Marked.
    """
    att = db.query(Attendance).filter_by(lecture_id=lecture_id, student_id=student_id).first()
    if not att or not att.qr_scanned_at:
        return "Not Marked"
        
    pv = db.query(PresenceVerification).filter_by(lecture_id=lecture_id, student_id=student_id).first()
    if pv and pv.status == "PENDING":
        att.status = "Pending Verification"
        return att.status
    elif pv and pv.status == "REJECTED":
        att.status = "Not Marked"
        return att.status
        
    # Check compulsory questions
    compulsory_qs = db.query(Question).filter_by(lecture_id=lecture_id, is_compulsory=True).all()
    if not compulsory_qs:
        # If no compulsory questions, QR + Verified is enough for Present
        att.status = "Present"
        return att.status
        
    attempted_q_ids = set(
        row[0] for row in db.query(AnswerAttempt.question_id).filter(
            AnswerAttempt.student_id == student_id,
            AnswerAttempt.question_id.in_([q.id for q in compulsory_qs])
        ).all()
    )
    
    all_attempted = all(q.id in attempted_q_ids for q in compulsory_qs)
    if all_attempted:
        att.status = "Present"
    else:
        att.status = "In Progress"
        
    att.updated_at = datetime.datetime.utcnow()
    return att.status

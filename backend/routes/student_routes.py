import os
import datetime
from flask import Blueprint, request, jsonify, send_file
from backend.database import db_session
from backend.models import (
    User, StudentProfile, Classroom, ClassroomMembership, Lecture, QRToken,
    Attendance, PresenceVerification, UploadedFile, Question, QuestionOption,
    AnswerAttempt, UnderstandingResponse, Doubt, TeacherReply, AuditEvent
)
from backend.utils.auth import get_current_user, student_required
from backend.utils.qr_crypto import validate_lecture_qr_token
from backend.routes.teacher_routes import recalculate_student_attendance
from backend.config import Config

student_bp = Blueprint("student", __name__, url_prefix="/api/student")

# ----------------- QR Scan & Entry -----------------

@student_bp.route("/scan-qr", methods=["POST"])
@student_required
def scan_qr_entry():
    """
    Handles QR entry for student:
    - Validates 10-second token
    - Auto-enrolls if enabled on classroom
    - Records presence verification
    - Records QR scan attendance
    - Recalculates attendance
    """
    user = get_current_user()
    data = request.get_json() or {}
    token_str = (data.get("token") or "").strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    device_info = data.get("device_info", "Browser Device")
    
    if not token_str:
        return jsonify({"success": False, "error": "QR token is required"}), 400
        
    db = db_session()
    try:
        # Validate token using same db session
        val_result = validate_lecture_qr_token(token_str, db=db)
        if not val_result.get("valid"):
            return jsonify({"success": False, "error": val_result.get("error")}), 400
            
        lecture_id = val_result["lecture_id"]
        classroom_id = val_result["classroom_id"]
        classroom = db.query(Classroom).filter_by(id=classroom_id).first()
        lecture = db.query(Lecture).filter_by(id=lecture_id).first()
        
        # Check membership
        membership = db.query(ClassroomMembership).filter_by(
            classroom_id=classroom_id, 
            student_id=user.id
        ).first()
        
        if not membership:
            if classroom.allow_qr_auto_enroll:
                # Auto-enroll student into classroom
                membership = ClassroomMembership(
                    classroom_id=classroom_id,
                    student_id=user.id,
                    enrolled_at=datetime.datetime.utcnow()
                )
                db.add(membership)
                db.flush()
            else:
                return jsonify({
                    "success": False, 
                    "error": "You are not enrolled in this classroom and auto-enrollment is disabled by the teacher."
                }), 403
                
        now = datetime.datetime.utcnow()
        
        # Record Presence Verification
        pv = db.query(PresenceVerification).filter_by(
            lecture_id=lecture_id, 
            student_id=user.id
        ).first()
        if not pv:
            pv = PresenceVerification(
                lecture_id=lecture_id,
                student_id=user.id,
                status="VERIFIED",
                latitude=float(latitude) if latitude is not None else None,
                longitude=float(longitude) if longitude is not None else None,
                device_info=str(device_info)[:255],
                verified_at=now
            )
            db.add(pv)
        else:
            if latitude is not None and longitude is not None:
                pv.latitude = float(latitude)
                pv.longitude = float(longitude)
            pv.verified_at = now
            
        # Record Attendance
        att = db.query(Attendance).filter_by(
            lecture_id=lecture_id, 
            student_id=user.id
        ).first()
        if not att:
            att = Attendance(
                lecture_id=lecture_id,
                student_id=user.id,
                status="In Progress",
                qr_scanned_at=now
            )
            db.add(att)
        elif not att.qr_scanned_at:
            att.qr_scanned_at = now
            
        db.flush()
        
        # Recalculate Attendance status (Present, In Progress, Pending Verification)
        final_status = recalculate_student_attendance(db, lecture_id, user.id)
        
        # Log Audit event
        audit = AuditEvent(
            event_type="QR_SCAN",
            user_id=user.id,
            details=f"Scanned QR for Lecture {lecture_id} ({lecture.topic})"
        )
        db.add(audit)
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Classroom entered successfully",
            "attendance_status": final_status,
            "lecture": lecture.to_dict(),
            "classroom": classroom.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

# ----------------- Student Dashboard Overview -----------------

@student_bp.route("/dashboard", methods=["GET"])
@student_required
def get_student_dashboard():
    user = get_current_user()
    db = db_session()
    try:
        # Find enrolled classrooms
        memberships = db.query(ClassroomMembership).filter_by(student_id=user.id).all()
        classrooms_data = []
        active_lecture = None
        
        for m in memberships:
            c = m.classroom
            c_dict = c.to_dict()
            # Check if has active lecture
            lec = db.query(Lecture).filter_by(classroom_id=c.id, is_active=True).first()
            if lec:
                c_dict["active_lecture"] = lec.to_dict()
                if not active_lecture:
                    # Fetch student's attendance for active lecture
                    att = db.query(Attendance).filter_by(lecture_id=lec.id, student_id=user.id).first()
                    active_lecture = lec.to_dict()
                    active_lecture["attendance_status"] = att.status if att else "Not Marked"
            else:
                c_dict["active_lecture"] = None
            classrooms_data.append(c_dict)
            
        profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
        
        return jsonify({
            "success": True,
            "student": {
                "name": user.name,
                "enrollment_no": profile.enrollment_no if profile else "N/A",
                "is_demo": profile.is_demo if profile else False
            },
            "classrooms": classrooms_data,
            "active_lecture": active_lecture
        })
    finally:
        db.close()

# ----------------- Understanding Feedback (3 Buttons) -----------------

@student_bp.route("/understanding", methods=["POST"])
@student_required
def submit_understanding():
    """
    Submits student understanding feedback:
    1. 'UNDERSTAND'
    2. 'DOUBT'
    3. 'DONT_UNDERSTAND'
    Anonymous by default. Identity is NEVER exposed to teachers through this endpoint.
    """
    user = get_current_user()
    data = request.get_json() or {}
    lecture_id = data.get("lecture_id")
    status = (data.get("status") or "").strip().upper()
    topic = (data.get("topic") or "General").strip()
    
    if not lecture_id or status not in {"UNDERSTAND", "DOUBT", "DONT_UNDERSTAND"}:
        return jsonify({"success": False, "error": "Invalid understanding status or missing lecture ID"}), 400
        
    db = db_session()
    try:
        # Check active lecture
        lecture = db.query(Lecture).filter_by(id=int(lecture_id)).first()
        if not lecture:
            return jsonify({"success": False, "error": "Lecture not found"}), 404
            
        # Record response (upsert for this student and lecture)
        resp = db.query(UnderstandingResponse).filter_by(
            lecture_id=lecture.id, 
            student_id=user.id
        ).first()
        
        if not resp:
            resp = UnderstandingResponse(
                lecture_id=lecture.id,
                student_id=user.id,
                status=status,
                topic=topic
            )
            db.add(resp)
        else:
            resp.status = status
            resp.topic = topic
            resp.created_at = datetime.datetime.utcnow()
            
        db.commit()
        return jsonify({
            "success": True,
            "message": "Feedback submitted anonymously",
            "status": status
        })
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

# ----------------- Volunteer To Ask A Doubt -----------------

@student_bp.route("/doubts/volunteer", methods=["POST"])
@student_required
def volunteer_ask_doubt():
    """
    Volunteer to Ask a Doubt:
    - Explicit consent dialog confirmed by student
    - Discloses Full Name and Enrollment Number only for this specific request
    - Records Audit Event
    """
    user = get_current_user()
    data = request.get_json() or {}
    lecture_id = data.get("lecture_id")
    topic = (data.get("topic") or "General").strip()
    doubt_text = (data.get("doubt_text") or "").strip()
    is_consented = bool(data.get("is_consented", False))
    
    if not lecture_id or not doubt_text:
        return jsonify({"success": False, "error": "Lecture ID and doubt text are required"}), 400
        
    if not is_consented:
        return jsonify({
            "success": False, 
            "error": "You must explicitly confirm identity disclosure before volunteering a doubt"
        }), 400
        
    db = db_session()
    try:
        doubt = Doubt(
            lecture_id=int(lecture_id),
            student_id=user.id,
            topic=topic,
            doubt_text=doubt_text,
            is_consented=True,
            status="Pending"
        )
        db.add(doubt)
        db.flush()
        
        # Log Audit Event for identity disclosure
        audit = AuditEvent(
            event_type="VOLUNTARY_IDENTITY_DISCLOSURE",
            user_id=user.id,
            details=f"Student {user.name} voluntarily submitted doubt #{doubt.id} with identity disclosure"
        )
        db.add(audit)
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Doubt sent to teacher inbox with voluntary identity authorization",
            "doubt_id": doubt.id
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@student_bp.route("/doubts", methods=["GET"])
@student_required
def get_my_doubts():
    """
    Returns student's own doubt history and teacher replies.
    """
    user = get_current_user()
    db = db_session()
    try:
        doubts = db.query(Doubt).filter_by(student_id=user.id).order_by(Doubt.created_at.desc()).all()
        result = []
        for d in doubts:
            replies = db.query(TeacherReply).filter_by(doubt_id=d.id).order_by(TeacherReply.created_at.asc()).all()
            result.append({
                "id": d.id,
                "lecture_id": d.lecture_id,
                "lecture_topic": d.lecture.topic if d.lecture else "Lecture",
                "topic": d.topic,
                "doubt_text": d.doubt_text,
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

# ----------------- Student Questions & Answers -----------------

@student_bp.route("/questions", methods=["GET"])
@student_required
def get_student_questions():
    """
    Returns published questions for student's classrooms/lectures.
    Can be answered later (not only during live lecture).
    Hides correct answers unless teacher enabled reveal_answer.
    """
    user = get_current_user()
    classroom_id = request.args.get("classroom_id")
    lecture_id = request.args.get("lecture_id")
    db = db_session()
    try:
        query = db.query(Question).filter(Question.status == "PUBLISHED")
        if classroom_id:
            query = query.filter_by(classroom_id=int(classroom_id))
        elif lecture_id:
            query = query.filter_by(lecture_id=int(lecture_id))
        else:
            # All enrolled classrooms
            memberships = db.query(ClassroomMembership.classroom_id).filter_by(student_id=user.id).all()
            c_ids = [m[0] for m in memberships]
            query = query.filter(Question.classroom_id.in_(c_ids))
            
        questions = query.order_by(Question.created_at.desc()).all()
        result = []
        for q in questions:
            q_dict = q.to_dict(include_correct=False)
            # Check if student attempted this question
            attempt = db.query(AnswerAttempt).filter_by(question_id=q.id, student_id=user.id).first()
            if attempt:
                q_dict["has_attempted"] = True
                q_dict["selected_option"] = attempt.selected_option
                q_dict["submitted_at"] = attempt.submitted_at.isoformat() if attempt.submitted_at else None
                # Reveal correctness only if teacher enabled reveal_answer
                if q.reveal_answer:
                    q_dict["is_correct"] = attempt.is_correct
                    q_dict["correct_answer"] = q.correct_answer
                else:
                    q_dict["is_correct"] = None
            else:
                q_dict["has_attempted"] = False
                q_dict["selected_option"] = None
                q_dict["is_correct"] = None
            result.append(q_dict)
            
        return jsonify({"success": True, "questions": result})
    finally:
        db.close()

@student_bp.route("/questions/<int:question_id>/submit", methods=["POST"])
@student_required
def submit_question_answer(question_id: int):
    """
    Submits answer for a question:
    - One attempt per student per question by default (prevent duplicate submission)
    - Validates submission on backend
    - Evaluates correctness
    - Recalculates attendance if question is compulsory for lecture
    """
    user = get_current_user()
    data = request.get_json() or {}
    selected_option = (data.get("selected_option") or "").strip().upper()
    
    if selected_option not in {"A", "B", "C", "D"}:
        return jsonify({"success": False, "error": "Selected option must be A, B, C, or D"}), 400
        
    db = db_session()
    try:
        q = db.query(Question).filter_by(id=question_id).first()
        if not q or q.status != "PUBLISHED":
            return jsonify({"success": False, "error": "Question is not available for submissions"}), 404
            
        # Prevent duplicate submissions
        existing = db.query(AnswerAttempt).filter_by(question_id=q.id, student_id=user.id).first()
        if existing:
            return jsonify({"success": False, "error": "You have already submitted an answer for this question"}), 409
            
        is_correct = (selected_option == q.correct_answer)
        attempt = AnswerAttempt(
            question_id=q.id,
            student_id=user.id,
            selected_option=selected_option,
            is_correct=is_correct,
            submitted_at=datetime.datetime.utcnow()
        )
        db.add(attempt)
        db.flush()
        
        # If question is linked to a lecture, recalculate student attendance
        new_attendance_status = None
        if q.lecture_id:
            new_attendance_status = recalculate_student_attendance(db, q.lecture_id, user.id)
            
        db.commit()
        
        response_data = {
            "success": True,
            "message": "Answer submitted successfully",
            "has_attempted": True,
            "selected_option": selected_option,
            "attendance_status": new_attendance_status
        }
        if q.reveal_answer:
            response_data["is_correct"] = is_correct
            response_data["correct_answer"] = q.correct_answer
            
        return jsonify(response_data), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

# ----------------- Study Materials Download -----------------

@student_bp.route("/files", methods=["GET"])
@student_required
def list_student_files():
    user = get_current_user()
    classroom_id = request.args.get("classroom_id")
    lecture_id = request.args.get("lecture_id")
    db = db_session()
    try:
        query = db.query(UploadedFile).filter_by(is_published=True)
        if classroom_id:
            query = query.filter_by(classroom_id=int(classroom_id))
        elif lecture_id:
            query = query.filter_by(lecture_id=int(lecture_id))
        else:
            memberships = db.query(ClassroomMembership.classroom_id).filter_by(student_id=user.id).all()
            c_ids = [m[0] for m in memberships]
            query = query.filter(UploadedFile.classroom_id.in_(c_ids))
            
        files = query.order_by(UploadedFile.uploaded_at.desc()).all()
        return jsonify({"success": True, "files": [f.to_dict() for f in files]})
    finally:
        db.close()

@student_bp.route("/files/<int:file_id>/download", methods=["GET"])
@student_required
def download_student_file(file_id: int):
    user = get_current_user()
    db = db_session()
    try:
        file_obj = db.query(UploadedFile).filter_by(id=file_id, is_published=True).first()
        if not file_obj:
            return jsonify({"success": False, "error": "File not found or unpublished"}), 404
            
        # Verify student is a member of the classroom
        membership = db.query(ClassroomMembership).filter_by(
            classroom_id=file_obj.classroom_id,
            student_id=user.id
        ).first()
        if not membership:
            return jsonify({"success": False, "error": "Access denied. Classroom membership required."}), 403
            
        file_path = os.path.join(Config.UPLOAD_FOLDER, file_obj.stored_filename)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "File does not exist on server storage"}), 404
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_obj.original_filename
        )
    finally:
        db.close()

# ----------------- Student Attendance History -----------------

@student_bp.route("/attendance", methods=["GET"])
@student_required
def get_my_attendance():
    """
    Returns student's personal attendance history across all lectures.
    """
    user = get_current_user()
    db = db_session()
    try:
        attendances = db.query(Attendance).filter_by(student_id=user.id).all()
        result = []
        for att in attendances:
            lec = att.lecture
            result.append({
                "lecture_id": att.lecture_id,
                "topic": lec.topic if lec else "Lecture",
                "classroom_name": lec.classroom.name if lec and lec.classroom else "Classroom",
                "status": att.status,
                "qr_scanned_at": att.qr_scanned_at.isoformat() if att.qr_scanned_at else None,
                "updated_at": att.updated_at.isoformat() if att.updated_at else None
            })
        return jsonify({"success": True, "attendance": result})
    finally:
        db.close()

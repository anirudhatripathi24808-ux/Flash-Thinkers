import csv
import io
import datetime
from flask import Blueprint, request, jsonify, Response, send_file
from backend.database import db_session
from backend.models import (
    User, StudentProfile, Classroom, ClassroomMembership, Lecture,
    Attendance, Question, QuestionOption, AnswerAttempt, UnderstandingResponse,
    Doubt, PresenceVerification
)
from backend.utils.auth import get_current_user, teacher_required
from backend.utils.privacy import generate_masked_aliases, mask_enrollment

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

@analytics_bp.route("/lecture/<int:lecture_id>", methods=["GET"])
@teacher_required
def get_lecture_analytics(lecture_id: int):
    """
    Comprehensive lecture analytics:
    - Confusion breakdown (Understand, Doubt, Don't Understand, Non-response)
    - Attendance summary (Present, In Progress, Pending Verification, Not Marked)
    - Question performance metrics
    - STRICT PRIVACY: Student names are NOT included. Enrollment numbers are masked: 1234******.
    """
    db = db_session()
    try:
        lecture = db.query(Lecture).filter_by(id=lecture_id).first()
        if not lecture:
            return jsonify({"success": False, "error": "Lecture not found"}), 404
            
        classroom = lecture.classroom
        enrolled_students = db.query(ClassroomMembership).filter_by(classroom_id=classroom.id).all()
        total_eligible = len(enrolled_students)
        
        # Collect all enrolled student IDs and map their masked enrollment numbers
        student_ids = [m.student_id for m in enrolled_students]
        profiles = db.query(StudentProfile).filter(StudentProfile.user_id.in_(student_ids)).all() if student_ids else []
        enr_list = [p.enrollment_no for p in profiles]
        masked_map = generate_masked_aliases(enr_list)
        user_to_masked = {p.user_id: masked_map.get(p.enrollment_no, mask_enrollment(p.enrollment_no)) for p in profiles}
        
        # 1. Understanding & Confusion Metrics
        understanding_records = db.query(UnderstandingResponse).filter_by(lecture_id=lecture.id).all()
        understand_count = sum(1 for r in understanding_records if r.status == "UNDERSTAND")
        doubt_count = sum(1 for r in understanding_records if r.status == "DOUBT")
        dont_understand_count = sum(1 for r in understanding_records if r.status == "DONT_UNDERSTAND")
        total_feedback = len(understanding_records)
        no_feedback_count = max(0, total_eligible - total_feedback)
        
        denominator = total_eligible if total_eligible > 0 else 1
        confusion_stats = {
            "total_eligible": total_eligible,
            "understand": {
                "count": understand_count,
                "percentage": round((understand_count / denominator) * 100, 1)
            },
            "doubt": {
                "count": doubt_count,
                "percentage": round((doubt_count / denominator) * 100, 1)
            },
            "dont_understand": {
                "count": dont_understand_count,
                "percentage": round((dont_understand_count / denominator) * 100, 1)
            },
            "no_response": {
                "count": no_feedback_count,
                "percentage": round((no_feedback_count / denominator) * 100, 1)
            }
        }
        
        # Topic-wise confusion distribution
        topic_confusion = {}
        for r in understanding_records:
            t = r.topic or "General"
            if t not in topic_confusion:
                topic_confusion[t] = {"understand": 0, "doubt": 0, "dont_understand": 0}
            if r.status == "UNDERSTAND":
                topic_confusion[t]["understand"] += 1
            elif r.status == "DOUBT":
                topic_confusion[t]["doubt"] += 1
            elif r.status == "DONT_UNDERSTAND":
                topic_confusion[t]["dont_understand"] += 1
                
        # 2. Attendance Metrics
        attendance_records = db.query(Attendance).filter_by(lecture_id=lecture.id).all()
        att_by_user = {a.student_id: a for a in attendance_records}
        
        present_count = 0
        in_progress_count = 0
        pending_verif_count = 0
        not_marked_count = 0
        attendance_list = []
        
        for sid in student_ids:
            a = att_by_user.get(sid)
            status = a.status if a else "Not Marked"
            if status == "Present":
                present_count += 1
            elif status == "In Progress":
                in_progress_count += 1
            elif status == "Pending Verification":
                pending_verif_count += 1
            else:
                not_marked_count += 1
                
            attendance_list.append({
                "masked_enrollment": user_to_masked.get(sid, "UNKNOWN"),
                "status": status,
                "qr_scanned_at": a.qr_scanned_at.isoformat() if (a and a.qr_scanned_at) else None
            })
            
        attendance_summary = {
            "total_eligible": total_eligible,
            "joined_count": len(attendance_records),
            "present_count": present_count,
            "in_progress_count": in_progress_count,
            "pending_verif_count": pending_verif_count,
            "not_marked_count": not_marked_count,
            "attendance_rate": round((present_count / denominator) * 100, 1),
            "records": attendance_list
        }
        
        # 3. Question Performance
        questions = db.query(Question).filter_by(lecture_id=lecture.id).all()
        question_stats = []
        
        for q in questions:
            attempts = db.query(AnswerAttempt).filter_by(question_id=q.id).all()
            answered_count = len(attempts)
            not_answered_count = max(0, total_eligible - answered_count)
            correct_count = sum(1 for a in attempts if a.is_correct)
            incorrect_count = sum(1 for a in attempts if not a.is_correct)
            
            q_denom = answered_count if answered_count > 0 else 1
            
            # Option counts
            opt_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            for a in attempts:
                if a.selected_option in opt_counts:
                    opt_counts[a.selected_option] += 1
                    
            masked_attempts = []
            for a in attempts:
                masked_attempts.append({
                    "masked_enrollment": user_to_masked.get(a.student_id, mask_enrollment(str(a.student_id))),
                    "selected_option": a.selected_option,
                    "is_correct": a.is_correct,
                    "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None
                })
                
            question_stats.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "topic": q.topic,
                "difficulty": q.difficulty,
                "is_compulsory": q.is_compulsory,
                "correct_answer": q.correct_answer,
                "total_eligible": total_eligible,
                "answered_count": answered_count,
                "not_answered_count": not_answered_count,
                "correct_count": correct_count,
                "incorrect_count": incorrect_count,
                "correct_percentage": round((correct_count / q_denom) * 100, 1),
                "incorrect_percentage": round((incorrect_count / q_denom) * 100, 1),
                "options_breakdown": {
                    opt: {
                        "count": opt_counts[opt],
                        "percentage": round((opt_counts[opt] / q_denom) * 100, 1)
                    } for opt in ["A", "B", "C", "D"]
                },
                "masked_attempts": masked_attempts
            })
            
        return jsonify({
            "success": True,
            "lecture": lecture.to_dict(),
            "confusion_stats": confusion_stats,
            "topic_confusion": topic_confusion,
            "attendance_summary": attendance_summary,
            "question_stats": question_stats
        })
    finally:
        db.close()

# ----------------- CSV Report Export -----------------

@analytics_bp.route("/lecture/<int:lecture_id>/export/csv", methods=["GET"])
@teacher_required
def export_lecture_csv(lecture_id: int):
    """
    Exports CSV lecture report.
    STRICT PRIVACY: Only masked enrollment numbers (1234******). No student names or emails!
    """
    db = db_session()
    try:
        lecture = db.query(Lecture).filter_by(id=lecture_id).first()
        if not lecture:
            return jsonify({"success": False, "error": "Lecture not found"}), 404
            
        classroom = lecture.classroom
        enrolled_students = db.query(ClassroomMembership).filter_by(classroom_id=classroom.id).all()
        student_ids = [m.student_id for m in enrolled_students]
        profiles = db.query(StudentProfile).filter(StudentProfile.user_id.in_(student_ids)).all() if student_ids else []
        enr_list = [p.enrollment_no for p in profiles]
        masked_map = generate_masked_aliases(enr_list)
        user_to_masked = {p.user_id: masked_map.get(p.enrollment_no, mask_enrollment(p.enrollment_no)) for p in profiles}
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header info
        writer.writerow(["FLASHNOVA - LECTURE POST-CLASS REPORT"])
        writer.writerow(["Topic", lecture.topic])
        writer.writerow(["Classroom", classroom.name])
        writer.writerow(["Subject", f"{classroom.subject.name} ({classroom.subject.code})"])
        writer.writerow(["Generated At", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
        writer.writerow([])
        
        # Attendance Section (Strictly Masked)
        writer.writerow(["--- ATTENDANCE RECORDS (PRIVACY PROTECTED) ---"])
        writer.writerow(["Masked Enrollment", "Attendance Status", "QR Scanned At"])
        
        attendances = db.query(Attendance).filter_by(lecture_id=lecture.id).all()
        att_dict = {a.student_id: a for a in attendances}
        for sid in student_ids:
            a = att_dict.get(sid)
            masked_enr = user_to_masked.get(sid, "UNKNOWN")
            status = a.status if a else "Not Marked"
            scanned_at = a.qr_scanned_at.strftime("%Y-%m-%d %H:%M:%S") if (a and a.qr_scanned_at) else "N/A"
            writer.writerow([masked_enr, status, scanned_at])
            
        writer.writerow([])
        # Questions Section
        writer.writerow(["--- QUESTION ATTEMPT RECORDS (PRIVACY PROTECTED) ---"])
        writer.writerow(["Question ID", "Topic", "Masked Enrollment", "Selected Option", "Result", "Submitted At"])
        
        questions = db.query(Question).filter_by(lecture_id=lecture.id).all()
        for q in questions:
            attempts = db.query(AnswerAttempt).filter_by(question_id=q.id).all()
            for att in attempts:
                masked_enr = user_to_masked.get(att.student_id, mask_enrollment(str(att.student_id)))
                res = "Correct" if att.is_correct else "Incorrect"
                sub_at = att.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if att.submitted_at else "N/A"
                writer.writerow([q.id, q.topic, masked_enr, att.selected_option, res, sub_at])
                
        output.seek(0)
        filename = f"FLASHNOVA_Report_{lecture.id}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        db.close()

# ----------------- PDF / Printable Report Export -----------------

@analytics_bp.route("/lecture/<int:lecture_id>/export/pdf", methods=["GET"])
@teacher_required
def export_lecture_pdf(lecture_id: int):
    """
    Generates PDF report using ReportLab or HTML-to-PDF.
    STRICT PRIVACY: Masks all enrollment numbers. Zero identity leakage.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    db = db_session()
    try:
        lecture = db.query(Lecture).filter_by(id=lecture_id).first()
        if not lecture:
            return jsonify({"success": False, "error": "Lecture not found"}), 404
            
        classroom = lecture.classroom
        enrolled_students = db.query(ClassroomMembership).filter_by(classroom_id=classroom.id).all()
        student_ids = [m.student_id for m in enrolled_students]
        profiles = db.query(StudentProfile).filter(StudentProfile.user_id.in_(student_ids)).all() if student_ids else []
        enr_list = [p.enrollment_no for p in profiles]
        masked_map = generate_masked_aliases(enr_list)
        user_to_masked = {p.user_id: masked_map.get(p.enrollment_no, mask_enrollment(p.enrollment_no)) for p in profiles}
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#06b6d4"),
            spaceAfter=10
        )
        subtitle_style = ParagraphStyle(
            "SubTitleStyle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=15
        )
        h2_style = ParagraphStyle(
            "H2Style",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        
        elements = []
        elements.append(Paragraph("FLASHNOVA – Lecture Analytics Report", title_style))
        elements.append(Paragraph(
            f"<b>Topic:</b> {lecture.topic} &nbsp;|&nbsp; <b>Classroom:</b> {classroom.name} &nbsp;|&nbsp; <b>Subject:</b> {classroom.subject.name} ({classroom.subject.code})<br/>"
            f"<b>Date:</b> {lecture.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if lecture.started_at else 'N/A'}",
            subtitle_style
        ))
        
        # Attendance Table
        elements.append(Paragraph("Attendance Records (Strictly Masked 1234******)", h2_style))
        attendances = db.query(Attendance).filter_by(lecture_id=lecture.id).all()
        att_dict = {a.student_id: a for a in attendances}
        
        att_data = [["Masked Enrollment", "Attendance Status", "QR Scanned At"]]
        for sid in student_ids:
            a = att_dict.get(sid)
            masked_enr = user_to_masked.get(sid, "UNKNOWN")
            status = a.status if a else "Not Marked"
            scanned_at = a.qr_scanned_at.strftime("%Y-%m-%d %H:%M:%S") if (a and a.qr_scanned_at) else "N/A"
            att_data.append([masked_enr, status, scanned_at])
            
        if len(att_data) == 1:
            att_data.append(["No enrolled students", "-", "-"])
            
        t1 = Table(att_data, colWidths=[200, 150, 190])
        t1.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#38bdf8")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elements.append(t1)
        elements.append(Spacer(1, 15))
        
        # Confusion Stats Table
        elements.append(Paragraph("Topic Confusion & Understanding Breakdown", h2_style))
        records = db.query(UnderstandingResponse).filter_by(lecture_id=lecture.id).all()
        u_count = sum(1 for r in records if r.status == "UNDERSTAND")
        d_count = sum(1 for r in records if r.status == "DOUBT")
        du_count = sum(1 for r in records if r.status == "DONT_UNDERSTAND")
        
        conf_data = [
            ["Response Category", "Count", "Percentage"],
            ["I UNDERSTAND", str(u_count), f"{round(u_count / max(1, len(records)) * 100, 1)}%"],
            ["I HAVE A DOUBT", str(d_count), f"{round(d_count / max(1, len(records)) * 100, 1)}%"],
            ["I DON'T UNDERSTAND", str(du_count), f"{round(du_count / max(1, len(records)) * 100, 1)}%"]
        ]
        t2 = Table(conf_data, colWidths=[240, 150, 150])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#a855f7")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elements.append(t2)
        
        doc.build(elements)
        pdf_buffer.seek(0)
        filename = f"FLASHNOVA_Report_{lecture.id}.pdf"
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    finally:
        db.close()

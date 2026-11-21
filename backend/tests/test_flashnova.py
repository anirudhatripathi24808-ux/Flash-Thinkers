import os
import unittest
import json
import io
import datetime
from backend.app import create_app
from backend.database import db_session, Base, engine
from backend.models import User, StudentProfile, TeacherProfile, Subject, Classroom, Lecture, QRToken, Attendance, Question, AnswerAttempt, UnderstandingResponse, Doubt, TeacherReply
from backend.utils.privacy import mask_enrollment, generate_masked_aliases

class FlashnovaTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure in-memory or test database
        cls.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-flashnova-secret"
        })
        cls.client = cls.app.test_client()

    def setUp(self):
        # Recreate schema for isolated test run
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        from backend.database import seed_subjects
        seed_subjects()

    def tearDown(self):
        db_session.remove()

    # 1. Enrollment Number Validation & Student Registration
    def test_student_registration_validation(self):
        # Valid 10-digit enrollment
        res = self.client.post("/api/auth/student/register", json={
            "name": "Alex Mercer",
            "enrollment_no": "1234567890",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["enrollment_no"], "1234567890")

        # Invalid enrollment: 9 digits
        res_short = self.client.post("/api/auth/student/register", json={
            "name": "Short Enr",
            "enrollment_no": "123456789",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.assertEqual(res_short.status_code, 400)

        # Invalid enrollment: 11 digits
        res_long = self.client.post("/api/auth/student/register", json={
            "name": "Long Enr",
            "enrollment_no": "12345678901",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.assertEqual(res_long.status_code, 400)

        # Invalid enrollment: contains letters
        res_alpha = self.client.post("/api/auth/student/register", json={
            "name": "Alpha Enr",
            "enrollment_no": "123456789A",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.assertEqual(res_alpha.status_code, 400)

        # Duplicate enrollment rejection
        res_dup = self.client.post("/api/auth/student/register", json={
            "name": "Duplicate Mercer",
            "enrollment_no": "1234567890",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.assertEqual(res_dup.status_code, 409)

    # 2. Teacher Registration, Subject Selection, and Verification Codes
    def test_teacher_flow_and_subject_verification(self):
        # Register Teacher
        res = self.client.post("/api/auth/teacher/register", json={
            "name": "Dr. Eleanor Vance",
            "username": "eleanor_vance",
            "department": "Engineering",
            "password": "teacherpass123",
            "confirm_password": "teacherpass123"
        })
        self.assertEqual(res.status_code, 201)

        # Teacher Login (Step 1)
        res_login = self.client.post("/api/auth/teacher/login", json={
            "username": "eleanor_vance",
            "password": "teacherpass123"
        })
        self.assertEqual(res_login.status_code, 200)

        # Verify subjects list
        res_subjs = self.client.get("/api/auth/teacher/subjects")
        self.assertEqual(res_subjs.status_code, 200)
        codes = [s["code"] for s in res_subjs.get_json()["subjects"]]
        self.assertIn("MAT121", codes)
        self.assertIn("CHM131", codes)
        self.assertIn("WSP111", codes)

        # Step 3: Reject incorrect subject code
        res_bad_code = self.client.post("/api/auth/teacher/verify-subject", json={
            "subject_code": "MAT121",
            "access_code": "WRONG_CODE"
        })
        self.assertEqual(res_bad_code.status_code, 401)

        # Step 3: Accept correct subject code
        res_good_code = self.client.post("/api/auth/teacher/verify-subject", json={
            "subject_code": "MAT121",
            "access_code": "MAT121"
        })
        self.assertEqual(res_good_code.status_code, 200)
        self.assertTrue(res_good_code.get_json()["success"])

    # 3. Classroom Creation, Lecture, and Dynamic 10s QR Cycle
    def test_dynamic_qr_and_auto_enrollment(self):
        # 1. Setup Teacher
        self.client.post("/api/auth/teacher/register", json={
            "name": "Prof. Smith",
            "username": "prof_smith",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.client.post("/api/auth/teacher/login", json={"username": "prof_smith", "password": "password123"})
        self.client.post("/api/auth/teacher/verify-subject", json={"subject_code": "MAT121", "access_code": "MAT121"})

        # 2. Create Classroom with Auto-Enrollment enabled
        res_c = self.client.post("/api/teacher/classrooms", json={
            "name": "Calculus 101 - Section A",
            "allow_qr_auto_enroll": True
        })
        self.assertEqual(res_c.status_code, 201)
        classroom_id = res_c.get_json()["classroom"]["id"]

        # 3. Start Lecture
        res_lec = self.client.post("/api/teacher/lectures/start", json={
            "classroom_id": classroom_id,
            "topic": "Differential Calculus"
        })
        self.assertEqual(res_lec.status_code, 201)
        lecture_data = res_lec.get_json()
        lecture_id = lecture_data["lecture"]["id"]
        qr_token = lecture_data["qr"]["token"]

        self.assertIsNotNone(qr_token)
        self.assertEqual(lecture_data["qr"]["expires_in"], 10)

        # 4. Register and Login Student
        student_client = self.app.test_client()
        student_client.post("/api/auth/student/register", json={
            "name": "Student Alpha",
            "enrollment_no": "2026101234",
            "password": "password123",
            "confirm_password": "password123"
        })

        # 5. Student scans valid QR -> Auto-enrolls & Enters Classroom
        res_scan = student_client.post("/api/student/scan-qr", json={
            "token": qr_token,
            "latitude": 37.7749,
            "longitude": -122.4194
        })
        self.assertEqual(res_scan.status_code, 200)
        self.assertTrue(res_scan.get_json()["success"])

        # 6. Test Expired QR rejection
        db = db_session()
        qr_obj = db.query(QRToken).filter_by(token=qr_token).first()
        qr_obj.expires_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
        db.commit()

        res_expired = student_client.post("/api/student/scan-qr", json={"token": qr_token})
        self.assertEqual(res_expired.status_code, 400)
        self.assertIn("expired", res_expired.get_json()["error"].lower())

    # 4. Question Creation, Submissions, and Attendance Calculation
    def test_question_answering_and_attendance_logic(self):
        # Setup Teacher & Classroom
        self.client.post("/api/auth/teacher/register", json={
            "name": "Prof. Chemistry",
            "username": "prof_chem",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.client.post("/api/auth/teacher/login", json={"username": "prof_chem", "password": "password123"})
        self.client.post("/api/auth/teacher/verify-subject", json={"subject_code": "CHM131", "access_code": "CHM131"})
        
        c_res = self.client.post("/api/teacher/classrooms", json={"name": "Organic Chem Batch", "allow_qr_auto_enroll": True})
        cid = c_res.get_json()["classroom"]["id"]
        
        lec_res = self.client.post("/api/teacher/lectures/start", json={"classroom_id": cid, "topic": "Hydrocarbons"})
        lid = lec_res.get_json()["lecture"]["id"]
        token = lec_res.get_json()["qr"]["token"]

        # Teacher adds a COMPULSORY Question
        q_res = self.client.post("/api/teacher/questions", json={
            "classroom_id": cid,
            "lecture_id": lid,
            "question_text": "What is the formula of Methane?",
            "topic": "Alkanes",
            "difficulty": "Easy",
            "is_compulsory": True,
            "correct_answer": "B",
            "options": {"A": "CO2", "B": "CH4", "C": "H2O", "D": "C2H6"}
        })
        self.assertEqual(q_res.status_code, 201)
        qid = q_res.get_json()["question"]["id"]

        # Setup Student
        s_client = self.app.test_client()
        s_client.post("/api/auth/student/register", json={
            "name": "Jane Doe",
            "enrollment_no": "2026555555",
            "password": "password123",
            "confirm_password": "password123"
        })

        # Step A: Student scans QR -> Should be 'In Progress' because compulsory question is not attempted yet
        scan_res = s_client.post("/api/student/scan-qr", json={"token": token})
        self.assertEqual(scan_res.status_code, 200)
        self.assertEqual(scan_res.get_json()["attendance_status"], "In Progress")

        # Step B: Student attempts question later with Option B (Correct)
        ans_res = s_client.post(f"/api/student/questions/{qid}/submit", json={"selected_option": "B"})
        self.assertEqual(ans_res.status_code, 201)
        # Attendance must now transition to 'Present' because compulsory question was attempted!
        self.assertEqual(ans_res.get_json()["attendance_status"], "Present")

        # Step C: Prevent duplicate attempt
        ans_dup = s_client.post(f"/api/student/questions/{qid}/submit", json={"selected_option": "A"})
        self.assertEqual(ans_dup.status_code, 409)

    # 5. Strict Student Privacy & Masked Enrollment (1234******)
    def test_strict_privacy_and_masking(self):
        # Register two students with similar prefix to test collision aliasing
        self.assertEqual(mask_enrollment("1234567890"), "1234******")
        
        # Test collision aliasing helper
        enrollments = ["1234567890", "1234999999", "9876543210"]
        masked_map = generate_masked_aliases(enrollments)
        self.assertEqual(masked_map["1234567890"], "1234****** (#1)")
        self.assertEqual(masked_map["1234999999"], "1234****** (#2)")
        self.assertEqual(masked_map["9876543210"], "9876******")

        # Setup Teacher and Student
        self.client.post("/api/auth/teacher/register", json={
            "name": "Prof. Workshop",
            "username": "prof_wsp",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.client.post("/api/auth/teacher/login", json={"username": "prof_wsp", "password": "password123"})
        self.client.post("/api/auth/teacher/verify-subject", json={"subject_code": "WSP111", "access_code": "WSP111"})

        c_res = self.client.post("/api/teacher/classrooms", json={"name": "Fitting Shop", "allow_qr_auto_enroll": True})
        cid = c_res.get_json()["classroom"]["id"]
        lec_res = self.client.post("/api/teacher/lectures/start", json={"classroom_id": cid, "topic": "Safety Tools"})
        lid = lec_res.get_json()["lecture"]["id"]
        token = lec_res.get_json()["qr"]["token"]

        s_client = self.app.test_client()
        s_client.post("/api/auth/student/register", json={
            "name": "Confidential Student",
            "enrollment_no": "1122334455",
            "password": "password123",
            "confirm_password": "password123"
        })
        s_client.post("/api/student/scan-qr", json={"token": token})

        # Request Teacher Analytics
        res_analytics = self.client.get(f"/api/analytics/lecture/{lid}")
        self.assertEqual(res_analytics.status_code, 200)
        data = res_analytics.get_json()

        # VERIFY: No student name in attendance records!
        rec = data["attendance_summary"]["records"][0]
        self.assertNotIn("name", rec)
        self.assertNotIn("student_name", rec)
        self.assertNotIn("user_id", rec)
        self.assertEqual(rec["masked_enrollment"], "1122******")

        # Test CSV export privacy
        res_csv = self.client.get(f"/api/analytics/lecture/{lid}/export/csv")
        self.assertEqual(res_csv.status_code, 200)
        csv_text = res_csv.data.decode("utf-8")
        self.assertNotIn("Confidential Student", csv_text)
        self.assertIn("1122******", csv_text)

        # Test PDF export privacy
        res_pdf = self.client.get(f"/api/analytics/lecture/{lid}/export/pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")

    # 6. Voluntary Doubt Feature with Explicit Consent
    def test_voluntary_doubt_consent_workflow(self):
        # Setup Teacher & Lecture
        self.client.post("/api/auth/teacher/register", json={
            "name": "Prof. Math",
            "username": "prof_math",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.client.post("/api/auth/teacher/login", json={"username": "prof_math", "password": "password123"})
        self.client.post("/api/auth/teacher/verify-subject", json={"subject_code": "MAT121", "access_code": "MAT121"})
        
        c_res = self.client.post("/api/teacher/classrooms", json={"name": "Linear Algebra", "allow_qr_auto_enroll": True})
        cid = c_res.get_json()["classroom"]["id"]
        lec_res = self.client.post("/api/teacher/lectures/start", json={"classroom_id": cid, "topic": "Eigenvectors"})
        lid = lec_res.get_json()["lecture"]["id"]
        token = lec_res.get_json()["qr"]["token"]

        # Student joins
        s_client = self.app.test_client()
        s_client.post("/api/auth/student/register", json={
            "name": "Brave Volunteer",
            "enrollment_no": "9988776655",
            "password": "password123",
            "confirm_password": "password123"
        })
        s_client.post("/api/student/scan-qr", json={"token": token})

        # Submit doubt without consent -> Rejected!
        res_no_consent = s_client.post("/api/student/doubts/volunteer", json={
            "lecture_id": lid,
            "topic": "Determinants",
            "doubt_text": "I need help with 3x3 matrices",
            "is_consented": False
        })
        self.assertEqual(res_no_consent.status_code, 400)

        # Submit doubt with explicit consent -> Accepted!
        res_consented = s_client.post("/api/student/doubts/volunteer", json={
            "lecture_id": lid,
            "topic": "Determinants",
            "doubt_text": "I need help with 3x3 matrices",
            "is_consented": True
        })
        self.assertEqual(res_consented.status_code, 201)
        doubt_id = res_consented.get_json()["doubt_id"]

        # Teacher checks Voluntary Doubt Inbox -> Sees full name and full enrollment number!
        res_inbox = self.client.get(f"/api/teacher/doubts?lecture_id={lid}")
        self.assertEqual(res_inbox.status_code, 200)
        doubts = res_inbox.get_json()["doubts"]
        self.assertEqual(len(doubts), 1)
        self.assertEqual(doubts[0]["student_name"], "Brave Volunteer")
        self.assertEqual(doubts[0]["student_enrollment_no"], "9988776655")

        # Teacher replies to doubt
        res_reply = self.client.post(f"/api/teacher/doubts/{doubt_id}/reply", json={
            "reply_text": "Remember det(AB) = det(A)det(B). Let's review at 4 PM.",
            "status": "Resolved"
        })
        self.assertEqual(res_reply.status_code, 200)

        # Student views reply in their doubt history
        res_student_doubts = s_client.get("/api/student/doubts")
        self.assertEqual(res_student_doubts.status_code, 200)
        s_doubts = res_student_doubts.get_json()["doubts"]
        self.assertEqual(s_doubts[0]["status"], "Resolved")
        self.assertEqual(s_doubts[0]["replies"][0]["reply_text"], "Remember det(AB) = det(A)det(B). Let's review at 4 PM.")

    # 7. Anonymous Understanding Feedback (Triple Buttons)
    def test_anonymous_understanding_feedback(self):
        # Teacher & Lecture Setup
        self.client.post("/api/auth/teacher/register", json={"name":"Prof","username":"p_test","password":"password123","confirm_password":"password123"})
        self.client.post("/api/auth/teacher/login", json={"username":"p_test","password":"password123"})
        self.client.post("/api/auth/teacher/verify-subject", json={"subject_code":"MAT121","access_code":"MAT121"})
        c_res = self.client.post("/api/teacher/classrooms", json={"name":"Feedback Class","allow_qr_auto_enroll":True})
        cid = c_res.get_json()["classroom"]["id"]
        l_res = self.client.post("/api/teacher/lectures/start", json={"classroom_id":cid,"topic":"Limits at Infinity"})
        lid = l_res.get_json()["lecture"]["id"]
        token = l_res.get_json()["qr"]["token"]

        # Student joins
        s_client = self.app.test_client()
        s_client.post("/api/auth/student/register", json={"name":"Feedback Student","enrollment_no":"3344556677","password":"password123","confirm_password":"password123"})
        s_client.post("/api/student/scan-qr", json={"token":token})

        # Student votes 'DOUBT'
        v_res = s_client.post("/api/student/understanding", json={
            "lecture_id": lid,
            "status": "DOUBT",
            "topic": "Limits"
        })
        self.assertEqual(v_res.status_code, 200)
        self.assertTrue(v_res.get_json()["success"])

        # Teacher verifies tally in analytics
        a_res = self.client.get(f"/api/analytics/lecture/{lid}")
        self.assertEqual(a_res.status_code, 200)
        conf_stats = a_res.get_json()["confusion_stats"]
        self.assertEqual(conf_stats["doubt"]["count"], 1)
        self.assertEqual(conf_stats["understand"]["count"], 0)

    # 8. File Upload & Secure Download
    def test_file_upload_and_download(self):
        # Teacher Setup
        self.client.post("/api/auth/teacher/register", json={"name":"Prof Files","username":"p_file","password":"password123","confirm_password":"password123"})
        self.client.post("/api/auth/teacher/login", json={"username":"p_file","password":"password123"})
        self.client.post("/api/auth/teacher/verify-subject", json={"subject_code":"MAT121","access_code":"MAT121"})
        c_res = self.client.post("/api/teacher/classrooms", json={"name":"File Class","allow_qr_auto_enroll":True})
        cid = c_res.get_json()["classroom"]["id"]

        # Teacher uploads study file
        data = {
            "classroom_id": str(cid),
            "title": "Calculus Notes",
            "description": "Essential formulas",
            "file": (io.BytesIO(b"Derivative of x^2 is 2x"), "calculus_formulas.txt")
        }
        f_res = self.client.post("/api/teacher/files", data=data, content_type="multipart/form-data")
        self.assertEqual(f_res.status_code, 201)
        file_id = f_res.get_json()["file"]["id"]

        # Enrolled Student downloads file
        s_client = self.app.test_client()
        s_client.post("/api/auth/student/register", json={"name":"Reader Student","enrollment_no":"5566778899","password":"password123","confirm_password":"password123"})
        # Enroll student in classroom
        from backend.models import ClassroomMembership
        db = db_session()
        sp = db.query(StudentProfile).filter_by(enrollment_no="5566778899").first()
        mem = ClassroomMembership(classroom_id=cid, student_id=sp.user_id)
        db.add(mem)
        db.commit()

        # Student lists files
        list_res = s_client.get("/api/student/files")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.get_json()["files"]), 1)

        # Student downloads file
        dl_res = s_client.get(f"/api/student/files/{file_id}/download")
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.data, b"Derivative of x^2 is 2x")

if __name__ == "__main__":
    unittest.main()

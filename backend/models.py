import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)  # 'student' or 'teacher'
    name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=True, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile = relationship("TeacherProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    classrooms_taught = relationship("Classroom", back_populates="teacher")
    audit_events = relationship("AuditEvent", back_populates="user")
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "name": self.name,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class StudentProfile(Base):
    __tablename__ = "student_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    enrollment_no = Column(String(10), unique=True, nullable=False, index=True)  # Strictly 10 digits
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="student_profile")
    
    def to_dict(self, mask: bool = False, alias: str = ""):
        enrollment_display = self.enrollment_no
        if mask and len(self.enrollment_no) == 10:
            enrollment_display = f"{self.enrollment_no[:4]}******" + (f" ({alias})" if alias else "")
        return {
            "id": self.id,
            "user_id": self.user_id,
            "enrollment_no": enrollment_display,
            "is_demo": self.is_demo,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    department = Column(String(100), default="General")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="teacher_profile")

class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # MAT121, CHM131, WSP111
    name = Column(String(100), nullable=False)
    access_code = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    classrooms = relationship("Classroom", back_populates="subject")
    
    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Classroom(Base):
    __tablename__ = "classrooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(30), unique=True, nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allow_qr_auto_enroll = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    subject = relationship("Subject", back_populates="classrooms")
    teacher = relationship("User", back_populates="classrooms_taught")
    memberships = relationship("ClassroomMembership", back_populates="classroom", cascade="all, delete-orphan")
    lectures = relationship("Lecture", back_populates="classroom", cascade="all, delete-orphan")
    files = relationship("UploadedFile", back_populates="classroom", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="classroom", cascade="all, delete-orphan")
    
    def to_dict(self):
        s_code = None
        s_name = None
        try:
            if self.subject:
                s_code = self.subject.code
                s_name = self.subject.name
        except Exception:
            pass
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "subject_id": self.subject_id,
            "subject_code": s_code,
            "subject_name": s_name,
            "teacher_id": self.teacher_id,
            "allow_qr_auto_enroll": self.allow_qr_auto_enroll,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ClassroomMembership(Base):
    __tablename__ = "classroom_memberships"
    
    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    classroom = relationship("Classroom", back_populates="memberships")
    student = relationship("User")

class Lecture(Base):
    __tablename__ = "lectures"
    
    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    classroom = relationship("Classroom", back_populates="lectures")
    qr_tokens = relationship("QRToken", back_populates="lecture", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="lecture", cascade="all, delete-orphan")
    presences = relationship("PresenceVerification", back_populates="lecture", cascade="all, delete-orphan")
    understanding_responses = relationship("UnderstandingResponse", back_populates="lecture", cascade="all, delete-orphan")
    doubts = relationship("Doubt", back_populates="lecture", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="lecture")
    files = relationship("UploadedFile", back_populates="lecture")
    
    def to_dict(self):
        c_name = None
        s_code = None
        s_name = None
        try:
            if self.classroom:
                c_name = self.classroom.name
                if self.classroom.subject:
                    s_code = self.classroom.subject.code
                    s_name = self.classroom.subject.name
        except Exception:
            pass
        return {
            "id": self.id,
            "classroom_id": self.classroom_id,
            "classroom_name": c_name,
            "subject_code": s_code,
            "subject_name": s_name,
            "topic": self.topic,
            "is_active": self.is_active,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None
        }

class QRToken(Base):
    __tablename__ = "qr_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    
    lecture = relationship("Lecture", back_populates="qr_tokens")

class PresenceVerification(Base):
    __tablename__ = "presence_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="VERIFIED")  # 'VERIFIED', 'PENDING', 'REJECTED'
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    device_info = Column(String(255), nullable=True)
    verified_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    lecture = relationship("Lecture", back_populates="presences")
    student = relationship("User")

class Attendance(Base):
    __tablename__ = "attendances"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), default="Not Marked")  # 'Present', 'In Progress', 'Not Marked', 'Pending Verification'
    qr_scanned_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    lecture = relationship("Lecture", back_populates="attendances")
    student = relationship("User")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="SET NULL"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_published = Column(Boolean, default=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    classroom = relationship("Classroom", back_populates="files")
    lecture = relationship("Lecture", back_populates="files")
    teacher = relationship("User")
    
    def to_dict(self):
        return {
            "id": self.id,
            "classroom_id": self.classroom_id,
            "lecture_id": self.lecture_id,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "title": self.title,
            "description": self.description,
            "is_published": self.is_published,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="SET NULL"), nullable=True)
    question_text = Column(Text, nullable=False)
    topic = Column(String(150), default="General")
    difficulty = Column(String(20), default="Medium")  # Easy, Medium, Hard
    is_compulsory = Column(Boolean, default=True)
    status = Column(String(20), default="PUBLISHED")  # DRAFT, PUBLISHED, CLOSED
    correct_answer = Column(String(5), nullable=False)  # 'A', 'B', 'C', 'D'
    reveal_answer = Column(Boolean, default=False)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    classroom = relationship("Classroom", back_populates="questions")
    lecture = relationship("Lecture", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    attempts = relationship("AnswerAttempt", back_populates="question", cascade="all, delete-orphan")
    
    def to_dict(self, include_correct: bool = False):
        data = {
            "id": self.id,
            "classroom_id": self.classroom_id,
            "lecture_id": self.lecture_id,
            "question_text": self.question_text,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "is_compulsory": self.is_compulsory,
            "status": self.status,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "options": [opt.to_dict() for opt in sorted(self.options, key=lambda x: x.key)],
            "reveal_answer": self.reveal_answer,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_correct or self.reveal_answer:
            data["correct_answer"] = self.correct_answer
        return data

class QuestionOption(Base):
    __tablename__ = "question_options"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(5), nullable=False)  # 'A', 'B', 'C', 'D'
    text = Column(String(255), nullable=False)
    
    question = relationship("Question", back_populates="options")
    
    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "text": self.text
        }

class AnswerAttempt(Base):
    __tablename__ = "answer_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    selected_option = Column(String(5), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    question = relationship("Question", back_populates="attempts")
    student = relationship("User")

class UnderstandingResponse(Base):
    __tablename__ = "understanding_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)  # 'UNDERSTAND', 'DOUBT', 'DONT_UNDERSTAND'
    topic = Column(String(150), default="General")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    lecture = relationship("Lecture", back_populates="understanding_responses")
    student = relationship("User")

class Doubt(Base):
    __tablename__ = "doubts"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(150), default="General")
    doubt_text = Column(Text, nullable=False)
    is_consented = Column(Boolean, default=True)  # Student explicitly checked disclosure confirmation
    status = Column(String(20), default="Pending")  # 'Pending', 'In Progress', 'Resolved'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    lecture = relationship("Lecture", back_populates="doubts")
    student = relationship("User")
    replies = relationship("TeacherReply", back_populates="doubt", cascade="all, delete-orphan")

class TeacherReply(Base):
    __tablename__ = "teacher_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    doubt_id = Column(Integer, ForeignKey("doubts.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reply_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    doubt = relationship("Doubt", back_populates="replies")
    teacher = relationship("User")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # 'VOLUNTARY_IDENTITY_DISCLOSURE', 'QR_SCAN', 'ATTENDANCE_OVERRIDE'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="audit_events")

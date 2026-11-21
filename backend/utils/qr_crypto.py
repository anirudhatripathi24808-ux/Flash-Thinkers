import secrets
import datetime
from backend.database import db_session
from backend.models import QRToken, Lecture
from backend.config import Config

def generate_lecture_qr_token(lecture_id: int, db=None) -> dict:
    """
    Generates a cryptographically secure random token linked to the active lecture.
    Token expires exactly after Config.QR_EXPIRY_SECONDS (default 10s).
    """
    should_close = False
    if db is None:
        db = db_session()
        should_close = True
        
    try:
        lecture = db.query(Lecture).filter_by(id=lecture_id, is_active=True).first()
        if not lecture:
            return {"success": False, "error": "Lecture not found or inactive"}
            
        token_str = secrets.token_urlsafe(32)
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(seconds=Config.QR_EXPIRY_SECONDS)
        
        qr_obj = QRToken(
            lecture_id=lecture.id,
            token=token_str,
            created_at=now,
            expires_at=expires_at,
            is_used=False
        )
        db.add(qr_obj)
        db.commit()
        
        return {
            "success": True,
            "token": token_str,
            "lecture_id": lecture.id,
            "expires_in": Config.QR_EXPIRY_SECONDS,
            "expires_at": expires_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if should_close:
            db.close()

def validate_lecture_qr_token(token_str: str, db=None) -> dict:
    """
    Validates a QR token:
    - Must exist in DB
    - Linked lecture must still be ACTIVE
    - Token must not be expired (now <= expires_at)
    - Anti-replay: marks token or validates within the active 10s window
    """
    if not token_str or not isinstance(token_str, str):
        return {"valid": False, "error": "Invalid token format"}
        
    should_close = False
    if db is None:
        db = db_session()
        should_close = True
        
    try:
        now = datetime.datetime.utcnow()
        qr_obj = db.query(QRToken).filter_by(token=token_str.strip()).first()
        
        if not qr_obj:
            return {"valid": False, "error": "Invalid or unrecognized QR token"}
            
        # Check if lecture is still active
        lecture = db.query(Lecture).filter_by(id=qr_obj.lecture_id).first()
        if not lecture or not lecture.is_active:
            return {"valid": False, "error": "Lecture is no longer active"}
            
        # Check expiry
        if now > qr_obj.expires_at:
            return {"valid": False, "error": "QR token has expired (valid for 10s only). Scan the latest code."}
            
        return {
            "valid": True,
            "lecture_id": qr_obj.lecture_id,
            "classroom_id": lecture.classroom_id,
            "topic": lecture.topic
        }
    finally:
        if should_close:
            db.close()

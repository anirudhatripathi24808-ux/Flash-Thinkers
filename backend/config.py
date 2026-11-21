import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "flashnova-futuristic-edtech-secret-key-2026")
    
    # Database Configuration (SQLite default for local, PostgreSQL compatible for production)
    db_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'flashnova.db'}")
    # Fix Render Postgres uri prefix if needed (postgres:// -> postgresql://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Settings
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "jpg", "jpeg", "png", "txt"}
    
    # Security & QR Settings
    QR_EXPIRY_SECONDS = int(os.getenv("QR_EXPIRY_SECONDS", "10"))
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Default Subject Access Codes (Configurable via Backend/Environment)
    SUBJECT_ACCESS_CODES = {
        "MAT121": os.getenv("MAT121_CODE", "MAT121"),
        "CHM131": os.getenv("CHM131_CODE", "CHM131"),
        "WSP111": os.getenv("WSP111_CODE", "WSP111"),
    }
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

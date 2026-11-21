import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from backend.config import Config

# Ensure upload directory exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Create engine
engine_kwargs = {}
if Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, **engine_kwargs)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    import backend.models  # Ensure models are imported
    Base.metadata.create_all(bind=engine)
    seed_subjects()

def seed_subjects():
    from backend.models import Subject
    db = db_session()
    try:
        defaults = [
            ("MAT121", "Mathematics", Config.SUBJECT_ACCESS_CODES.get("MAT121", "MAT121")),
            ("CHM131", "Chemistry", Config.SUBJECT_ACCESS_CODES.get("CHM131", "CHM131")),
            ("WSP111", "Workshop", Config.SUBJECT_ACCESS_CODES.get("WSP111", "WSP111")),
        ]
        for code, name, access_code in defaults:
            subj = db.query(Subject).filter_by(code=code).first()
            if not subj:
                subj = Subject(code=code, name=name, access_code=access_code)
                db.add(subj)
            else:
                subj.access_code = access_code
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding subjects: {e}")
    finally:
        db.close()

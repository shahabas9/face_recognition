"""
Database models for Face Recognition System with optional anti-spoofing fields.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import urllib.parse
from config.settings import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DB

# URL encode password to handle special characters
encoded_password = urllib.parse.quote_plus(MYSQL_PASSWORD)
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Person(Base):
    """Person/Employee enrolled in the system"""
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    face_embedding = Column(Text, nullable=False)  # JSON string of embedding vector (or list of vectors)
    department = Column(String(255))
    extra_info = Column(Text)  # Additional JSON metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DetectionEvent(Base):
    """Detection/Identification events from cameras"""
    __tablename__ = "detection_events"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String(100), index=True)  # Null if unknown
    camera_id = Column(String(100), index=True, nullable=False)
    location = Column(String(255))
    confidence = Column(Float)
    embedding_distance = Column(Float)
    snapshot_path = Column(String(500))
    bounding_box = Column(String(100))  # JSON: [x, y, w, h]
    is_unknown = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    client_ip = Column(String(50))
    request_source = Column(String(50))  # 'api', 'webcam', 'mobile'

    # Anti-spoofing metadata
    spoofing_detected = Column(Boolean, default=False, index=True, nullable=False)
    spoofing_reason = Column(String(500), nullable=True)
    liveness_score = Column(Float, nullable=True)
    spoofing_type = Column(String(50), nullable=True)


class Attendance(Base):
    """Attendance records (subset of detection events)"""
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String(100), index=True, nullable=False)
    camera_id = Column(String(100))
    status = Column(String(50), default="PRESENT")
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_id = Column(Integer)  # Reference to DetectionEvent
    liveness_verified = Column(Boolean, default=False, nullable=False)


class APILog(Base):
    """API request logs"""
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), index=True)
    method = Column(String(10))
    client_ip = Column(String(50))
    status_code = Column(Integer)
    response_time_ms = Column(Float)
    person_id = Column(String(100), index=True)  # If applicable
    camera_id = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    error_message = Column(Text)
    spoofing_detected = Column(Boolean, default=False, nullable=False)


# ============================================================================
# INDEXES FOR PERFORMANCE
# ============================================================================
Index('idx_detection_person_time', DetectionEvent.person_id, DetectionEvent.timestamp)
Index('idx_detection_camera_time', DetectionEvent.camera_id, DetectionEvent.timestamp)
Index('idx_detection_spoofing', DetectionEvent.spoofing_detected, DetectionEvent.timestamp)
Index('idx_attendance_person_date', Attendance.person_id, Attendance.timestamp)
Index('idx_api_endpoint_time', APILog.endpoint, APILog.timestamp)


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_next_person_id(db) -> str:
    """Generate next person ID"""
    from config.settings import PERSON_ID_PREFIX, REUSE_DELETED_IDS
    
    # Get all existing IDs
    existing_persons = db.query(Person.person_id).all()
    existing_ids = {p.person_id for p in existing_persons}
    
    if REUSE_DELETED_IDS:
        # Find the first available gap
        counter = 1
        while True:
            candidate = f"{PERSON_ID_PREFIX}{counter:03d}"
            if candidate not in existing_ids:
                return candidate
            counter += 1
    else:
        # Find the highest number and increment
        max_num = 0
        for person_id in existing_ids:
            if person_id.startswith(PERSON_ID_PREFIX):
                try:
                    num = int(person_id[len(PERSON_ID_PREFIX):])
                    max_num = max(max_num, num)
                except ValueError:
                    continue
        
        return f"{PERSON_ID_PREFIX}{max_num + 1:03d}"
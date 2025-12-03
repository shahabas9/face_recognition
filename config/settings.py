"""
Configuration settings for Face Recognition System.
Supports both macOS and Linux environments.
"""
import os
from pathlib import Path
from typing import Optional
import torch
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Environment settings
ENV = os.getenv("ENV", "development")  # development, production

# API Configuration
API_TITLE = "Person Identification System"
API_VERSION = "2.0.0"
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Security
API_KEY = os.getenv("API_KEY", "testkey123")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

# Database Configuration
MYSQL_USER = os.getenv("MYSQL_USER", "2cloud")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "shahabas@2cloud")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "face_recognition")

# Face Recognition Settings
RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.6"))
MIN_FACE_SIZE = int(os.getenv("MIN_FACE_SIZE", "60"))
DETECTION_CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", "0.7"))

# Performance Settings
IDENTIFICATION_TIMEOUT_MS = int(os.getenv("IDENTIFICATION_TIMEOUT_MS", "300"))
PROCESS_FPS = int(os.getenv("PROCESS_FPS", "6"))  # Frames per second to process from stream

# Device Settings (auto-detect)
FORCE_CPU = os.getenv("FORCE_CPU", "true").lower() == "false"

def get_device():
    """Detect available compute device"""
    if FORCE_CPU:
        return "cpu"
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"

# Storage Settings
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
LOGS_DIR = BASE_DIR / "logs"
MAX_SNAPSHOT_AGE_DAYS = int(os.getenv("MAX_SNAPSHOT_AGE_DAYS", "7"))
MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "100"))

# Create directories if they don't exist
SNAPSHOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# IP Webcam Settings
IP_WEBCAM_URL = os.getenv("IP_WEBCAM_URL", "http://192.168.1.107:8080/video")
STREAM_RECONNECT_DELAY = int(os.getenv("STREAM_RECONNECT_DELAY", "10"))
STREAM_TIMEOUT_MS = int(os.getenv("STREAM_TIMEOUT_MS", "5000"))
ENABLE_WEBCAM_FALLBACK = os.getenv("ENABLE_WEBCAM_FALLBACK", "true").lower() == "true"
FALLBACK_CAMERA_INDEX = int(os.getenv("FALLBACK_CAMERA_INDEX", "0"))
FALLBACK_CAMERA_ID = os.getenv("FALLBACK_CAMERA_ID", "laptop-webcam")
FALLBACK_CAMERA_NAME = os.getenv("FALLBACK_CAMERA_NAME", "Laptop Webcam")
FALLBACK_CAMERA_WIDTH = int(os.getenv("FALLBACK_CAMERA_WIDTH", "640"))
FALLBACK_CAMERA_HEIGHT = int(os.getenv("FALLBACK_CAMERA_HEIGHT", "480"))

# Face Distance Gating Settings
FACE_REAL_WIDTH_M = float(os.getenv("FACE_REAL_WIDTH_M", "0.16"))  # average adult face width (meters)
FACE_FOCAL_LENGTH_PX = float(os.getenv("FACE_FOCAL_LENGTH_PX", "1900"))  # approximate focal length constant
FACE_DISTANCE_MIN_M = float(os.getenv("FACE_DISTANCE_MIN_M", "1.0"))
FACE_DISTANCE_MAX_M = float(os.getenv("FACE_DISTANCE_MAX_M", "2.8"))
FACE_DISTANCE_ALERT_M = float(os.getenv("FACE_DISTANCE_ALERT_M", "2.6"))
FACE_DISTANCE_SMOOTH_ALPHA = float(os.getenv("FACE_DISTANCE_SMOOTH_ALPHA", "0.3"))
ENABLE_FACE_DISTANCE_GATING = os.getenv("ENABLE_FACE_DISTANCE_GATING", "true").lower() == "true"

# Mobile Device Spoof Detection Settings
ENABLE_MOBILE_SPOOF_DETECTION = os.getenv("ENABLE_MOBILE_SPOOF_DETECTION", "true").lower() == "true"
MOBILE_DETECTION_MODEL_PATH = os.getenv(
    "MOBILE_DETECTION_MODEL_PATH",
    str(BASE_DIR / "models" / "best.pt")
)
MOBILE_DETECTION_CONFIDENCE = float(os.getenv("MOBILE_DETECTION_CONFIDENCE", "0.2"))
MOBILE_DEVICE_CLASSES = [
    int(cls.strip())
    for cls in os.getenv("MOBILE_DEVICE_CLASSES", "1,3").split(",")
    if cls.strip().isdigit()
]
MOBILE_FACE_ENCLOSURE_RATIO = float(os.getenv("MOBILE_FACE_ENCLOSURE_RATIO", "0.85"))

# Event Settings
EVENT_COOLDOWN_SECONDS = int(os.getenv("EVENT_COOLDOWN_SECONDS", "5"))
ATTENDANCE_COOLDOWN_SECONDS = int(os.getenv("ATTENDANCE_COOLDOWN_SECONDS", "5"))  # 5 minutes
SPOOF_PENALTY_SECONDS = int(os.getenv("SPOOF_PENALTY_SECONDS", "900"))  # 15 minutes block after spoof


# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# CORS Settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Person ID Generation
AUTO_GENERATE_PERSON_ID = True
PERSON_ID_PREFIX = "P"
REUSE_DELETED_IDS = os.getenv("REUSE_DELETED_IDS", "true").lower() == "true"


# Liveness Detection Settings
ENABLE_LIVENESS = os.getenv("ENABLE_LIVENESS", "false").lower() == "true"
LIVENESS_THRESHOLD = float(os.getenv("LIVENESS_THRESHOLD", "0.7"))

# Debugging
SAVE_FAILED_RECOGNITION_FRAMES = os.getenv("SAVE_FAILED_RECOGNITION_FRAMES", "true").lower() == "true"


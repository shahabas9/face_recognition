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
PROCESS_FPS = int(os.getenv("PROCESS_FPS", "3"))  # Frames per second to process from stream

# Device Settings (auto-detect)
FORCE_CPU = os.getenv("FORCE_CPU", "true").lower() == "true"

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

# Event Settings
EVENT_COOLDOWN_SECONDS = int(os.getenv("EVENT_COOLDOWN_SECONDS", "30"))
ATTENDANCE_COOLDOWN_SECONDS = int(os.getenv("ATTENDANCE_COOLDOWN_SECONDS", "300"))  # 5 minutes

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
LIVENESS_THRESHOLD = float(os.getenv("LIVENESS_THRESHOLD", "0.7"))  # Default threshold


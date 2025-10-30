"""
IP Webcam Service for processing video streams from mobile phones.
Supports MJPEG and RTSP streams from IP Webcam apps.
"""
import cv2
import time
import threading
import logging
from datetime import datetime
from PIL import Image
from typing import Optional
from sqlalchemy.orm import Session

from config.ip_webcam_config import get_active_webcam_sources, get_stream_url
from config.settings import (
    STREAM_RECONNECT_DELAY,
    STREAM_TIMEOUT_MS,
    EVENT_COOLDOWN_SECONDS
)
from app.services.face_recognition_service import FaceRecognitionService
from app.services.storage_service import StorageService
from app.models import DetectionEvent, SessionLocal

logger = logging.getLogger(__name__)


class IPWebcamProcessor:
    """Process video stream from IP webcam"""
    
    def __init__(
        self,
        source_name: str,
        face_service: FaceRecognitionService,
        storage_service: StorageService,
    ):
        self.source_name = source_name
        self.face_service = face_service
        self.storage_service = storage_service
        
        # Get source configuration
        sources = get_active_webcam_sources()
        if source_name not in sources:
            raise ValueError(f"Unknown or disabled webcam source: {source_name}")
        
        self.config = sources[source_name]
        self.stream_url = get_stream_url(source_name)
        self.camera_id = self.config['camera_id']
        self.location = self.config.get('location', 'Unknown')
        self.fps_limit = self.config.get('fps_limit', 5)
        
        # Processing state
        self.is_running = False
        self.camera = None
        self.process_thread = None
        
        # Event cooldown (don't create duplicate events too quickly)
        self.last_event_time = {}
        self.event_cooldown = EVENT_COOLDOWN_SECONDS
        
        logger.info(f"📹 IP Webcam Processor initialized: {self.config['name']}")
        logger.info(f"   Camera ID: {self.camera_id}")
        logger.info(f"   Location: {self.location}")
        logger.info(f"   Stream URL: {self.stream_url}")
    
    def start(self):
        """Start webcam processing in background thread"""
        if self.is_running:
            logger.warning(f"Webcam {self.source_name} already running")
            return
        
        self.is_running = True
        self.process_thread = threading.Thread(
            target=self._process_stream,
            daemon=True,
            name=f"IPWebcam-{self.source_name}"
        )
        self.process_thread.start()
        logger.info(f"✅ Started webcam processor: {self.config['name']}")
    
    def stop(self):
        """Stop webcam processing"""
        self.is_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        logger.info(f"🛑 Stopped webcam processor: {self.config['name']}")
    
    def _connect_camera(self) -> bool:
        """Connect to IP webcam stream"""
        try:
            logger.info(f"🔗 Connecting to {self.config['name']}...")
            
            self.camera = cv2.VideoCapture(self.stream_url)
            
            # Set timeouts
            self.camera.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, STREAM_TIMEOUT_MS)
            self.camera.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, STREAM_TIMEOUT_MS)
            
            if not self.camera.isOpened():
                logger.error(f"❌ Failed to open stream: {self.stream_url}")
                return False
            
            # Test frame read
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logger.error("❌ Connected but cannot read frames")
                return False
            
            logger.info(f"✅ Connected to {self.config['name']}")
            logger.info(f"   Frame size: {frame.shape[1]}x{frame.shape[0]}")
            
            return True
        
        except Exception as e:
            logger.error(f"🚨 Error connecting to webcam: {e}")
            return False
    
    def _should_create_event(self, person_id: str) -> bool:
        """Check if we should create a new event (cooldown logic)"""
        current_time = time.time()
        last_time = self.last_event_time.get(person_id, 0)
        
        if current_time - last_time > self.event_cooldown:
            self.last_event_time[person_id] = current_time
            return True
        
        return False
    
    def _create_detection_event(
        self,
        person_id: Optional[str],
        name: Optional[str],
        confidence: Optional[float],
        embedding_distance: Optional[float],
        snapshot_path: Optional[str],
        bounding_box: Optional[list],
        is_unknown: bool = False,
        spoofing_detected: bool = False,
        spoofing_reason: Optional[str] = None,
        liveness_score: Optional[float] = None,
        spoofing_type: Optional[str] = None
    ):
        """Create detection event in database"""
        try:
            db = SessionLocal()
            try:
                event = DetectionEvent(
                    person_id=person_id,
                    camera_id=self.camera_id,
                    location=self.location,
                    confidence=confidence,
                    embedding_distance=embedding_distance,
                    snapshot_path=snapshot_path,
                    bounding_box=str(bounding_box) if bounding_box else None,
                    is_unknown=is_unknown,
                    timestamp=datetime.utcnow(),
                    request_source='webcam',
                    spoofing_detected=spoofing_detected,
                    spoofing_reason=spoofing_reason,
                    liveness_score=liveness_score,
                    spoofing_type=spoofing_type
                )
                
                db.add(event)
                db.commit()
                
                if is_unknown:
                    logger.info(f"📝 Event: Unknown person detected at {self.location}")
                else:
                    logger.info(
                        f"📝 Event: {name} detected at {self.location} "
                        f"(confidence: {confidence:.2f})"
                    )
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error creating detection event: {e}")
    
    def _print_detection(self, name: str, person_id: str, confidence: float):
        """Print detection banner"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*70}")
        print(f"✅ PERSON IDENTIFIED - {self.config['name']}")
        print(f"┌{'─'*68}┐")
        print(f"│ Name: {name} ({person_id})")
        print(f"│ Confidence: {confidence*100:.1f}%")
        print(f"│ Location: {self.location}")
        print(f"│ Time: {timestamp}")
        print(f"└{'─'*68}┘")
        print(f"{'='*70}\n")
    
    def _process_stream(self):
        """Main processing loop for webcam stream"""
        frame_count = 0
        connection_attempts = 0
        max_attempts = 3
        
        while self.is_running:
            try:
                # Connect to camera
                if not self._connect_camera():
                    connection_attempts += 1
                    if connection_attempts >= max_attempts:
                        logger.error(
                            f"❌ Failed to connect after {max_attempts} attempts. "
                            f"Stopping processor."
                        )
                        break
                    
                    logger.warning(
                        f"🔄 Retrying in {STREAM_RECONNECT_DELAY} seconds... "
                        f"(Attempt {connection_attempts}/{max_attempts})"
                    )
                    time.sleep(STREAM_RECONNECT_DELAY)
                    continue
                
                # Reset connection attempts
                connection_attempts = 0
                frame_count = 0
                
                logger.info(f"🎥 Starting face detection on {self.config['name']}...")
                
                # Calculate frame skip for FPS limit
                frame_skip = max(1, int(30 / self.fps_limit))  # Assume 30 FPS source
                
                # Main processing loop
                while self.is_running:
                    ret, frame = self.camera.read()
                    
                    if not ret or frame is None:
                        logger.warning("❌ Lost connection to stream")
                        break
                    
                    frame_count += 1
                    
                    # Process at limited FPS
                    if frame_count % frame_skip != 0:
                        time.sleep(0.01)
                        continue
                    
                    # Convert to PIL Image
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    
                    # ================================================================
                    # STEP 1: DETECT FACES
                    # ================================================================
                    faces = self.face_service.detect_faces(pil_image)
                    
                    if faces is None or len(faces) == 0:
                        if frame_count % 30 == 0:
                            logger.debug("No faces detected in frame")
                        time.sleep(0.05)
                        continue
                    
                    # ================================================================
                    # STEP 2: IDENTIFICATION (includes liveness check)
                    # ================================================================
                    result = self.face_service.identify_person(
                        pil_image,
                        return_bbox=True
                    )
                    
                    # Check if liveness failed
                    if result and 'error' in result and result['error'] == 'Liveness check failed':
                        # Liveness check failed - log and skip
                        liveness_info = result.get('liveness', {})
                        if frame_count % 30 == 0:
                            logger.warning(
                                f"🚫 SPOOFING DETECTED - Liveness: {liveness_info.get('confidence', 0):.3f} "
                                f"< {liveness_info.get('threshold', 0.7)} (model: {liveness_info.get('model', 'unknown')})"
                            )
                        
                        # Optionally save spoofed snapshot for analysis
                        snapshot_rel_path, _ = self.storage_service.save_snapshot(
                            pil_image,
                            prefix="spoofed",
                            camera_id=self.camera_id,
                            subdirectory="spoofing"
                        )
                        
                        # Create spoofing event
                        self._create_detection_event(
                            person_id=None,
                            name=None,
                            confidence=None,
                            embedding_distance=None,
                            snapshot_path=snapshot_rel_path,
                            bounding_box=None,
                            is_unknown=True,
                            spoofing_detected=True,
                            spoofing_reason="Liveness check failed",
                            liveness_score=liveness_info.get('confidence'),
                            spoofing_type="print_or_screen",
                        )
                        
                        time.sleep(0.1)
                        continue
                    
                    if result and result['person_id']:
                        # LEGITIMATE IDENTIFICATION (liveness passed)
                        if self._should_create_event(result['person_id']):
                            person_id = result['person_id']
                            
                            # Save snapshot
                            snapshot_rel_path, _ = self.storage_service.save_snapshot(
                                pil_image,
                                prefix="webcam",
                                person_id=person_id,
                                camera_id=self.camera_id,
                                subdirectory="events"
                            )
                            
                            # Extract liveness info
                            liveness_info = result.get('liveness', {})
                            liveness_score = liveness_info.get('confidence') if liveness_info else None
                            
                            # Create event
                            self._create_detection_event(
                                person_id=result['person_id'],
                                name=result['name'],
                                confidence=result['confidence'],
                                embedding_distance=result.get('embedding_distance'),
                                snapshot_path=snapshot_rel_path,
                                bounding_box=result.get('bounding_box'),
                                is_unknown=False,
                                spoofing_detected=False,
                                spoofing_reason=None,
                                liveness_score=liveness_score,
                                spoofing_type=None,
                            )
                            
                            # Print detection with liveness info
                            self._print_detection(
                                result['name'],
                                result['person_id'],
                                result['confidence']
                            )
                            if liveness_score:
                                logger.info(f"   Liveness Score: {liveness_score:.3f}")
                    else:
                        # Face detected but not identified
                        if frame_count % 30 == 0:
                            logger.debug(
                                f"⚠️  Face detected but not identified "
                                f"(confidence below threshold)"
                            )
                    
                    # Small delay
                    time.sleep(0.05)
                
                # Clean up
                if self.camera:
                    self.camera.release()
                    self.camera = None
                
                if self.is_running:
                    logger.warning(
                        f"🔄 Stream disconnected, reconnecting in "
                        f"{STREAM_RECONNECT_DELAY} seconds..."
                    )
                    time.sleep(STREAM_RECONNECT_DELAY)
            
            except Exception as e:
                logger.error(f"🚨 Error in stream processing: {e}", exc_info=True)
                if self.camera:
                    self.camera.release()
                    self.camera = None
                
                if self.is_running:
                    time.sleep(STREAM_RECONNECT_DELAY)
        
        logger.info(f"👋 Exited processing loop for {self.config['name']}")


class IPWebcamManager:
    """Manage multiple IP webcam processors"""
    
    def __init__(
        self,
        face_service: FaceRecognitionService,
        storage_service: StorageService,
    ):
        self.face_service = face_service
        self.storage_service = storage_service
        self.processors = {}
        
        logger.info("📹 IP Webcam Manager initialized")
    
    def start_all(self):
        """Start all enabled webcam sources"""
        sources = get_active_webcam_sources()
        
        if not sources:
            logger.warning("⚠️  No enabled webcam sources found")
            return
        
        for source_name in sources:
            try:
                processor = IPWebcamProcessor(
                    source_name,
                    self.face_service,
                    self.storage_service,
                )
                processor.start()
                self.processors[source_name] = processor
            except Exception as e:
                logger.error(f"Failed to start processor {source_name}: {e}")
        
        logger.info(f"✅ Started {len(self.processors)} webcam processors")
    
    def stop_all(self):
        """Stop all webcam processors"""
        for processor in self.processors.values():
            processor.stop()
        
        self.processors.clear()
        logger.info("🛑 All webcam processors stopped")
    
    def get_status(self) -> dict:
        """Get status of all processors"""
        return {
            name: {
                "running": processor.is_running,
                "camera_id": processor.camera_id,
                "location": processor.location
            }
            for name, processor in self.processors.items()
        }
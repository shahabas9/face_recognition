"""
IP Webcam Service for processing video streams from mobile phones.
Supports MJPEG and RTSP streams from IP Webcam apps.
"""
import cv2
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from PIL import Image
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
import numpy as np
from app.services.face_recognition_service import FaceRecognitionService
from app.services.storage_service import StorageService
from app.models import DetectionEvent, SessionLocal
from ultralytics import YOLO

from config.ip_webcam_config import get_active_webcam_sources, get_stream_url
from config.settings import (
    ATTENDANCE_COOLDOWN_SECONDS,
    STREAM_RECONNECT_DELAY,
    STREAM_TIMEOUT_MS,
    EVENT_COOLDOWN_SECONDS,
    SPOOF_PENALTY_SECONDS,
    ENABLE_WEBCAM_FALLBACK,
    FALLBACK_CAMERA_INDEX,
    FALLBACK_CAMERA_ID,
    FALLBACK_CAMERA_NAME,
    FALLBACK_CAMERA_WIDTH,
    FALLBACK_CAMERA_HEIGHT,
    FACE_DISTANCE_SMOOTH_ALPHA,
    ENABLE_MOBILE_SPOOF_DETECTION,
    MOBILE_DETECTION_MODEL_PATH,
    MOBILE_DETECTION_CONFIDENCE,
    MOBILE_DEVICE_CLASSES,
    MOBILE_FACE_ENCLOSURE_RATIO,
    SAVE_FAILED_RECOGNITION_FRAMES,
    PROCESS_FPS,
)

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
        self.primary_camera_id = self.camera_id
        self.primary_location = self.location
        self.primary_name = self.config.get('name', source_name)
        self.enable_webcam_fallback = ENABLE_WEBCAM_FALLBACK
        self.fallback_camera_index = FALLBACK_CAMERA_INDEX
        self.fallback_camera_id = FALLBACK_CAMERA_ID
        self.fallback_camera_name = FALLBACK_CAMERA_NAME
        self.fallback_camera_width = FALLBACK_CAMERA_WIDTH
        self.fallback_camera_height = FALLBACK_CAMERA_HEIGHT
        self.distance_smooth_alpha = FACE_DISTANCE_SMOOTH_ALPHA
        self.mobile_detection_enabled = ENABLE_MOBILE_SPOOF_DETECTION
        self.mobile_detector = None
        self.mobile_prediction_classes = set(MOBILE_DEVICE_CLASSES)
        self.mobile_detection_confidence = MOBILE_DETECTION_CONFIDENCE
        self.mobile_face_enclosure_ratio = MOBILE_FACE_ENCLOSURE_RATIO
        self.mobile_model_path = Path(MOBILE_DETECTION_MODEL_PATH)
        self.mobile_detector_loaded = False
        self._mobile_detection_disabled_logged = False
        
        # Processing state
        self.is_running = False
        self.camera = None
        self.process_thread = None
        self.fallback_active = False
        self.active_source_label = self.primary_name
        self.ema_distance = None
        
        # Event cooldown (don't create duplicate events too quickly)
        self.last_event_time = {}
        self.event_cooldown = EVENT_COOLDOWN_SECONDS
        
        # Spoof penalty tracking (block recognition after spoof detected)
        self.spoof_penalty_until = {}  # person_id -> timestamp when penalty expires
        self.spoof_penalty_duration = SPOOF_PENALTY_SECONDS
        
        # Attendance cooldown tracking
        self.last_attendance_time = {} # person_id -> timestamp of last file log

        
        logger.info(f"📹 IP Webcam Processor initialized: {self.primary_name}")
        logger.info(f"   Camera ID: {self.camera_id}")
        logger.info(f"   Location: {self.location}")
        logger.info(f"   Stream URL: {self.stream_url}")
        if self.mobile_detection_enabled:
            logger.info(
                "   Mobile spoof detection: enabled (model: %s, classes: %s, conf: %.2f, enclosure_ratio: %.2f)",
                self.mobile_model_path,
                sorted(self.mobile_prediction_classes),
                self.mobile_detection_confidence,
                self.mobile_face_enclosure_ratio,
            )
        else:
            logger.info("   Mobile spoof detection: disabled")

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
        logger.info(f"✅ Started webcam processor: {self.primary_name}")

    def stop(self):
        """Stop webcam processing"""
        self.is_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        logger.info(f"🛑 Stopped webcam processor: {self.active_source_label}")
    
    def _connect_camera(self) -> bool:
        """Connect to IP webcam stream"""
        try:
            logger.info(f"🔗 Connecting to {self.primary_name}...")
            
            self.camera = cv2.VideoCapture(self.stream_url)
            
            # Set timeouts for network streams
            self.camera.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, STREAM_TIMEOUT_MS)
            self.camera.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, STREAM_TIMEOUT_MS)
            
            if self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    self._activate_primary_camera(frame)
                    return True
                logger.error("❌ Connected but cannot read frames")
                self.camera.release()
            else:
                logger.error(f"❌ Failed to open stream: {self.stream_url}")

            # Attempt fallback webcam if enabled
            if self.enable_webcam_fallback:
                return self._activate_fallback_camera()

            return False
        
        except Exception as e:
            logger.error(f"🚨 Error connecting to webcam: {e}")
            if self.enable_webcam_fallback:
                return self._activate_fallback_camera()
            return False

    def _load_mobile_detector(self):
        """Lazy-load YOLO model for mobile spoof detection."""
        if not self.mobile_detection_enabled:
            if not self._mobile_detection_disabled_logged:
                logger.warning("📵 Mobile spoof detection disabled; skipping mobile inference")
                self._mobile_detection_disabled_logged = True
            return
        if self.mobile_detector is None:
            if not self.mobile_model_path.exists():
                logger.error(
                    "🚫 Mobile detection model not found at %s. Spoof detection disabled.",
                    self.mobile_model_path,
                )
                self.mobile_detection_enabled = False
                return
            try:
                logger.info("📦 Loading mobile detection model from %s", self.mobile_model_path)
                self.mobile_detector = YOLO(str(self.mobile_model_path))
                logger.info("✅ Mobile detection model loaded")
                self.mobile_detector_loaded = True
            except Exception as exc:
                logger.error(f"🚨 Failed to load mobile detection model: {exc}")
                self.mobile_detection_enabled = False

    def _detect_mobile_devices(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Run YOLO inference to detect mobile devices in the frame."""
        if not self.mobile_detection_enabled:
            return []
        self._load_mobile_detector()
        if self.mobile_detector is None:
            return []
        try:
            results = self.mobile_detector.predict(frame, conf=self.mobile_detection_confidence, verbose=False)
            mobile_boxes: List[Tuple[int, int, int, int]] = []
            if not results:
                return mobile_boxes
            for result in results:
                boxes = getattr(result, 'boxes', None)
                if boxes is None:
                    continue
                for box in boxes:
                    cls_tensor = getattr(box, 'cls', None)
                    score_tensor = getattr(box, 'conf', None)
                    if cls_tensor is None or score_tensor is None:
                        continue
                    cls = int(cls_tensor[0])
                    score = float(score_tensor[0])
                    if cls not in self.mobile_prediction_classes:
                        continue
                    if score < self.mobile_detection_confidence:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mobile_boxes.append((x1, y1, x2, y2))
            if mobile_boxes:
                logger.debug(
                    "📱 Mobile detector found %d device(s) | classes=%s",
                    len(mobile_boxes),
                    sorted(self.mobile_prediction_classes),
                )
            return mobile_boxes
        except Exception as exc:
            logger.error(f"🚨 Error during mobile detection: {exc}")
            return []

    @staticmethod
    def _face_inside_box(
        face_box: List[int],
        mobile_box: Tuple[int, int, int, int],
        enclosure_ratio: float
    ) -> Tuple[bool, float]:
        """Determine if the face bounding box is largely enclosed within the mobile device box."""
        if not face_box or len(face_box) < 4:
            return False, 0.0
        x, y, w, h = face_box
        fx2, fy2 = x + w, y + h
        mx1, my1, mx2, my2 = mobile_box
        intersection_x1 = max(x, mx1)
        intersection_y1 = max(y, my1)
        intersection_x2 = min(fx2, mx2)
        intersection_y2 = min(fy2, my2)
        if intersection_x2 <= intersection_x1 or intersection_y2 <= intersection_y1:
            return False, 0.0
        face_area = w * h
        if face_area <= 0:
            return False, 0.0
        intersection_area = (intersection_x2 - intersection_x1) * (intersection_y2 - intersection_y1)
        ratio = intersection_area / face_area
        return (ratio >= enclosure_ratio), ratio

    def _activate_primary_camera(self, frame: np.ndarray) -> bool:
        """Enable primary IP camera after successful connection."""
        self.fallback_active = False
        self.camera_id = self.primary_camera_id
        self.location = self.primary_location
        self.active_source_label = self.primary_name
        logger.info(f"✅ Connected to {self.primary_name}")
        logger.info(f"   Frame size: {frame.shape[1]}x{frame.shape[0]}")
        return True

    def _activate_fallback_camera(self) -> bool:
        """Switch to local fallback webcam when IP stream is unavailable."""
        try:
            logger.warning("🔄 Switching to fallback webcam source")
            self.camera = cv2.VideoCapture(self.fallback_camera_index)
            if not self.camera.isOpened():
                logger.error("❌ Fallback webcam could not be opened")
                return False
            # Configure resolution for local webcam
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.fallback_camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.fallback_camera_height)
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logger.error("❌ Fallback webcam opened but frame read failed")
                self.camera.release()
                return False
            self.fallback_active = True
            self.camera_id = self.fallback_camera_id
            self.location = self.fallback_camera_name
            self.active_source_label = self.fallback_camera_name
            logger.info(f"✅ Using fallback webcam: {self.fallback_camera_name} (index {self.fallback_camera_index})")
            logger.info(f"   Frame size: {frame.shape[1]}x{frame.shape[0]}")
            return True
        
        except Exception as e:
            logger.error(f"🚨 Error activating fallback webcam: {e}")
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
        print(f"✅ PERSON IDENTIFIED - {self.active_source_label}")
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
                
                logger.info(f"🎥 Starting face detection on {self.active_source_label}...")
                if self.fallback_active:
                    logger.info("   Operating in fallback webcam mode")
                
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
                    
                    # Use first face to estimate distance
                    face_img, bbox = faces[0]
                    distance_m = self.face_service.estimate_distance(bbox)
                    if distance_m is not None:
                        if self.ema_distance is None:
                            self.ema_distance = distance_m
                        else:
                            self.ema_distance = (
                                self.distance_smooth_alpha * distance_m
                                + (1 - self.distance_smooth_alpha) * self.ema_distance
                            )
                        if self.face_service.distance_gating_enabled and not (
                            self.face_service.distance_min_m <= distance_m <= self.face_service.distance_max_m
                        ):
                            if frame_count % 30 == 0:
                                logger.debug(
                                    "🚧 Face detected at %.3fm outside allowed range %.3f-%.3fm",
                                    distance_m,
                                    self.face_service.distance_min_m,
                                    self.face_service.distance_max_m,
                                )
                            time.sleep(0.05)
                            continue
                    else:
                        self.ema_distance = None
                    
                    mobile_boxes = self._detect_mobile_devices(frame)
                    face_in_mobile = False
                    best_overlap_ratio = 0.0
                    if mobile_boxes:
                        for mobile_box in mobile_boxes:
                            inside, ratio = self._face_inside_box(
                                bbox,
                                mobile_box,
                                self.mobile_face_enclosure_ratio
                            )
                            best_overlap_ratio = max(best_overlap_ratio, ratio)
                            if inside:
                                face_in_mobile = True
                                best_overlap_ratio = ratio
                                break
                        if frame_count % 30 == 0:
                            logger.debug(
                                "📱 Mobile detection summary - boxes=%d, face_in_mobile=%s, best_overlap=%.2f",
                                len(mobile_boxes),
                                face_in_mobile,
                                best_overlap_ratio,
                            )
                        if face_in_mobile and frame_count % 30 == 0:
                            logger.warning(
                                "📱 Potential spoof detected: face appears within mobile device (overlap=%.2f)",
                                best_overlap_ratio,
                            )
                    
                    
                    # If face appears within mobile device, we still want to IDENTIFY the person
                    # so we can apply the spoof penalty to their specific ID.
                    # The spoof check will happen AFTER identification in the loop below.
                    if face_in_mobile:
                        if frame_count % 30 == 0:
                            logger.debug(
                                "📱 Potential spoof detected (overlap=%.2f), proceeding to identification to apply penalty...",
                                best_overlap_ratio,
                            )


                    # ================================================================
                    # STEP 2: IDENTIFICATION (includes liveness check if not hybrid)
                    # ================================================================
                    results = self.face_service.identify_all_persons(
                        pil_image,
                        return_bbox=True,
                        pre_detected_faces=faces,
                    )
                    
                    # Process each identified person
                    if results:
                        for result in results:
                            person_id = result['person_id']
                            
                            # ================================================================
                            # CHECK SPOOF PENALTY
                            # ================================================================
                            current_time = time.time()
                            if person_id in self.spoof_penalty_until:
                                penalty_expires = self.spoof_penalty_until[person_id]
                                if current_time < penalty_expires:
                                    # Person is still under penalty
                                    remaining_seconds = int(penalty_expires - current_time)
                                    remaining_minutes = remaining_seconds // 60
                                    if frame_count % 30 == 0:  # Log every ~1 second
                                        logger.warning(
                                            f"🚫 BLOCKED: {result['name']} is under spoof penalty "
                                            f"({remaining_minutes}m {remaining_seconds % 60}s remaining)"
                                        )
                                    continue  # Skip this person entirely
                                else:
                                    # Penalty expired, remove from tracking
                                    del self.spoof_penalty_until[person_id]
                                    logger.info(f"✅ Spoof penalty expired for {result['name']}")
                            
                            
                            # ================================================================
                            # TERMINAL PRINTING (Before spoof check for visibility)
                            # ================================================================
                            if frame_count % 5 == 0: # Slight throttle for terminal to avoid flooding
                                self._print_detection(
                                    result['name'],
                                    person_id,
                                    result['confidence']
                                )
                                if result.get('distance_m') is not None:
                                    logger.info(
                                        "   Distance: %.3fm (valid range)",
                                        result['distance_m']
                                    )

                            # ================================================================
                            # EVENT CREATION (Database & Snapshots)
                            # Controlled by EVENT_COOLDOWN_SECONDS (e.g., 30s)
                            # ================================================================

                            
                            # Check cooldown for this specific person
                            if not self._should_create_event(person_id):
                                continue
                            
                            # Check if this face is enclosed by a mobile device
                            bbox = result.get('bounding_box')
                            if bbox and mobile_boxes:
                                face_in_mobile = False
                                best_overlap_ratio = 0.0
                                for mobile_box in mobile_boxes:
                                    inside, ratio = self._face_inside_box(
                                        bbox,
                                        mobile_box,
                                        self.mobile_face_enclosure_ratio
                                    )
                                    best_overlap_ratio = max(best_overlap_ratio, ratio)
                                    if inside:
                                        face_in_mobile = True
                                        break
                                
                                if face_in_mobile:
                                    # ================================================================
                                    # SPOOF DETECTED - APPLY PENALTY
                                    # ================================================================
                                    penalty_expires = current_time + self.spoof_penalty_duration
                                    self.spoof_penalty_until[person_id] = penalty_expires
                                    
                                    logger.warning(
                                        f"🚫 SPOOF ALERT: {result['name']} face enclosed by mobile device (overlap={best_overlap_ratio:.2f})"
                                    )
                                    logger.warning(
                                        f"⏱️  PENALTY APPLIED: {result['name']} blocked for {self.spoof_penalty_duration // 60} minutes"
                                    )
                                    
                                    # Create spoof event for this person
                                    snapshot_rel_path, _ = self.storage_service.save_snapshot(
                                        pil_image,
                                        prefix="spoofed",
                                        person_id=person_id,
                                        camera_id=self.camera_id,
                                        subdirectory="spoofing"
                                    )
                                    self._create_detection_event(
                                        person_id=person_id,
                                        name=result['name'],
                                        confidence=result['confidence'],
                                        embedding_distance=result.get('embedding_distance'),
                                        snapshot_path=snapshot_rel_path,
                                        bounding_box=[int(b) for b in bbox],
                                        is_unknown=False,
                                        spoofing_detected=True,
                                        spoofing_reason=f"Face enclosed by mobile device (overlap={best_overlap_ratio:.2f})",
                                        liveness_score=None,
                                        spoofing_type="mobile_display",
                                    )
                                    continue  # Skip this person, move to next
                            
                            # LEGITIMATE IDENTIFICATION
                            # Save snapshot
                            snapshot_rel_path, _ = self.storage_service.save_snapshot(
                                pil_image,
                                prefix="webcam",
                                person_id=person_id,
                                camera_id=self.camera_id,
                                subdirectory="events"
                            )
                            
                            # Log to attendance text file (only for legitimate, non-spoofed detections)
                            self._log_recognition_to_file(
                                person_id=person_id,
                                name=result['name'],
                                confidence=result['confidence']
                            )

                            
                            # Create event
                            self._create_detection_event(
                                person_id=person_id,
                                name=result['name'],
                                confidence=result['confidence'],
                                embedding_distance=result.get('embedding_distance'),
                                snapshot_path=snapshot_rel_path,
                                bounding_box=result.get('bounding_box'),
                                is_unknown=False,
                                spoofing_detected=False,
                                spoofing_reason=None,
                                liveness_score=None,
                                spoofing_type=None,
                            )

                    else:
                        # Faces detected but none identified
                        if frame_count % 30 == 0:
                            logger.debug(
                                f"⚠️  {len(faces)} face(s) detected but none identified "
                                f"(confidence below threshold or outside distance range)"
                            )
                        
                        
                        # Save failed recognition frame for debugging
                        # ONLY if at least one face is within valid distance range
                        if SAVE_FAILED_RECOGNITION_FRAMES and len(faces) > 0:
                            # Check if any face is within range
                            any_face_in_range = False
                            for _, bbox in faces:
                                dist = self.face_service.estimate_distance(bbox)
                                if dist is not None:
                                    if self.face_service.distance_min_m <= dist <= self.face_service.distance_max_m:
                                        any_face_in_range = True
                                        break
                            
                            # Only save if we have a face in range that wasn't identified
                            if any_face_in_range and frame_count % (PROCESS_FPS * 2) == 0:
                                try:
                                    snapshot_rel_path, _ = self.storage_service.save_snapshot(
                                        pil_image,
                                        prefix="failed",
                                        camera_id=self.camera_id,
                                        subdirectory="failed"
                                    )
                                    logger.debug(f"💾 Saved failed recognition frame (face in range): {snapshot_rel_path}")
                                except Exception as e:
                                    logger.error(f"Failed to save failed recognition frame: {e}")




                    
                    # Small delay
                    time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error processing stream: {e}", exc_info=True)
                time.sleep(1)
                
                # Clean up
                if self.camera:
                    self.camera.release()
                    self.camera = None
                    self.fallback_active = False
                    self.active_source_label = self.primary_name
                
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

    def _log_recognition_to_file(self, person_id: str, name: str, confidence: float):
        """
        Append recognition details to a daily text file
        Format: Date, Time, ID, Name, Department (if available)
        """
        try:
            from datetime import datetime
            from config.settings import LOGS_DIR, ATTENDANCE_COOLDOWN_SECONDS
            
            now = datetime.now()
            current_timestamp = now.timestamp()
            
            # Check cooldown
            last_log_time = self.last_attendance_time.get(person_id, 0)
            diff = current_timestamp - last_log_time
            
            # Debug log to see what's happening
            logger.debug(f"Attendance check: {name} | Diff: {diff:.1f}s | Cooldown: {ATTENDANCE_COOLDOWN_SECONDS}s")
            
            if diff < ATTENDANCE_COOLDOWN_SECONDS:

                # Too soon, skip logging
                return


            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            # Create daily log file path
            log_file = LOGS_DIR / f"recognitions_{date_str}.txt"
            
            # Get department (optional - would need DB lookup, using placeholder for now)
            # For efficiency, we're not querying DB here, but you could add it if critical
            department = "N/A" 
            
            # Format line
            log_line = f"{date_str} | {time_str} | ID: {person_id} | Name: {name} | Conf: {confidence:.3f}\n"
            
            # Append to file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
            
            # Update last log time
            self.last_attendance_time[person_id] = current_timestamp
                
        except Exception as e:
            logger.error(f"Failed to write recognition to text file: {e}")




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

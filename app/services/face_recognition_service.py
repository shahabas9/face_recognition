# app/services/face_recognition_service.py
"""
Face Recognition Service using FaceNet and MTCNN
Handles face detection, embedding extraction, and person identification.
"""
import torch
import numpy as np
import json
import logging
from PIL import Image
from typing import Optional, List, Tuple, Dict
from sklearn.metrics.pairwise import cosine_similarity
from facenet_pytorch import MTCNN, InceptionResnetV1
from sqlalchemy.orm import Session

from app.models import Person
from config.settings import (
    RECOGNITION_THRESHOLD,
    MIN_FACE_SIZE,
    DETECTION_CONFIDENCE,
    get_device,
    FACE_REAL_WIDTH_M,
    FACE_FOCAL_LENGTH_PX,
    FACE_DISTANCE_MIN_M,
    FACE_DISTANCE_MAX_M,
    FACE_DISTANCE_ALERT_M,
    ENABLE_FACE_DISTANCE_GATING,
)

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """Face recognition service using FaceNet and MTCNN"""
    
    def __init__(self):
        self.device = get_device()
        logger.info(f"🔧 Initializing Face Recognition Service on {self.device}")
        
        # Initialize MTCNN for face detection
        # Force CPU for stability across macOS and Linux
        self.mtcnn = MTCNN(
            keep_all=True,
            device='cpu',
            min_face_size=MIN_FACE_SIZE,
            thresholds=[DETECTION_CONFIDENCE, 0.7, 0.7],
            post_process=True
        )
        logger.info("✅ MTCNN face detector initialized")
        
        # Initialize FaceNet for embeddings
        self.facenet = InceptionResnetV1(pretrained='vggface2').eval().to('cpu')
        logger.info("✅ FaceNet embedding model loaded (VGGFace2)")
        
        self.recognition_threshold = RECOGNITION_THRESHOLD
        self.face_real_width_m = FACE_REAL_WIDTH_M
        self.face_focal_length_px = FACE_FOCAL_LENGTH_PX
        self.distance_min_m = FACE_DISTANCE_MIN_M
        self.distance_max_m = FACE_DISTANCE_MAX_M
        self.distance_alert_m = FACE_DISTANCE_ALERT_M
        self.distance_gating_enabled = ENABLE_FACE_DISTANCE_GATING
        
        # Cache for person embeddings
        self.person_embeddings: List[np.ndarray] = []
        self.person_ids: List[str] = []
        self.person_names: List[str] = []
        
        # Load persons from database
        self.load_persons()
    
    def load_persons(self, db: Optional[Session] = None):
        """Load all active persons from database into memory cache"""
        try:
            from app.models import SessionLocal
            
            if db is None:
                db = SessionLocal()
                should_close = True
            else:
                should_close = False
            
            persons = db.query(Person).filter(Person.is_active == True).all()
            
            self.person_embeddings.clear()
            self.person_ids.clear()
            self.person_names.clear()
            
            for person in persons:
                try:
                    # Deserialize embedding from JSON
                    embedding_data = json.loads(person.face_embedding)
                    
                    # Handle both single embedding (list) and multiple embeddings (list of lists)
                    if not embedding_data:
                        continue
                        
                    # Check if it's a list of lists (multiple embeddings)
                    if isinstance(embedding_data[0], list):
                        for emb_list in embedding_data:
                            embedding = np.array(emb_list, dtype=np.float32)
                            self.person_embeddings.append(embedding)
                            self.person_ids.append(person.person_id)
                            self.person_names.append(person.name)
                    else:
                        # Single embedding (legacy support)
                        embedding = np.array(embedding_data, dtype=np.float32)
                        self.person_embeddings.append(embedding)
                        self.person_ids.append(person.person_id)
                        self.person_names.append(person.name)
                        
                except Exception as e:
                    logger.error(f"Error loading person {person.name}: {e}")
            
            if should_close:
                db.close()
            
            logger.info(f"✅ Loaded {len(self.person_embeddings)} face embeddings into cache")
            
        except Exception as e:
            logger.error(f"❌ Error loading persons from database: {e}")

    def estimate_distance(self, bounding_box: List[int]) -> Optional[float]:
        """Estimate face distance from camera using bounding box width."""
        try:
            if not bounding_box or len(bounding_box) < 4:
                return None
            _, _, width_px, _ = bounding_box
            if width_px <= 0:
                return None
            return (self.face_real_width_m * self.face_focal_length_px) / float(width_px)
        except Exception as exc:
            logger.debug(f"Error estimating face distance: {exc}")
            return None

    def detect_faces(self, image: Image.Image) -> Optional[List[Tuple[np.ndarray, List[int]]]]:
        """
        Detect faces in image and return face regions with bounding boxes.
        Tries multiple rotations (0°, 90°, 180°, 270°) to handle sideways images.

        Returns:
            List of (face_image, [x, y, w, h]) tuples, or None if no faces
        """
        try:
            rotations = [0, 90, 180, 270]
            best_faces = None
            used_rotation = 0

            for angle in rotations:
                rotated_image = image.rotate(angle, expand=True)
                boxes, probs = self.mtcnn.detect(rotated_image)

                if boxes is not None and len(boxes) > 0:
                    faces = []
                    for box, prob in zip(boxes, probs):
                        if prob < DETECTION_CONFIDENCE:
                            continue

                        x1, y1, x2, y2 = [max(0, int(coord)) for coord in box]
                        w, h = x2 - x1, y2 - y1

                        if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                            continue

                        face_img = rotated_image.crop((x1, y1, x2, y2))
                        faces.append((face_img, [x1, y1, w, h]))

                    if faces:
                        best_faces = faces
                        used_rotation = angle
                        break  # stop once we find faces

            if best_faces:
                logger.debug(f"✅ Faces detected (rotation: {used_rotation}°)")
                return best_faces
            else:
                logger.debug("❌ No faces detected at any rotation")
                return None

        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return None

    def get_face_embedding(
        self,
        image: Image.Image,
        pre_detected_faces: Optional[List[Tuple[Image.Image, List[int]]]] = None
    ) -> Optional[np.ndarray]:
        """
        Extract face embedding from image
        
        Args:
            image: PIL Image containing a face
            
        Returns:
            512-dimensional embedding vector or None if no face detected
        """
        try:
            # Detect faces
            faces = pre_detected_faces if pre_detected_faces is not None else self.detect_faces(image)
            
            if faces is None or len(faces) == 0:
                return None
            
            # Use the first (largest) face
            face_img, bbox = faces[0]
            
            # Resize to 160x160 for FaceNet
            face_img = face_img.resize((160, 160))
            
            # Convert to tensor and normalize
            face_array = np.array(face_img)
            if face_array.size == 0:
                return None
            
            # Ensure RGB
            if len(face_array.shape) == 2:
                face_array = np.stack([face_array] * 3, axis=-1)
            elif face_array.shape[2] == 4:
                face_array = face_array[:, :, :3]
            
            # Convert to tensor
            face_tensor = torch.tensor(face_array).permute(2, 0, 1).float()
            # Normalize to [-1, 1]
            face_tensor = (face_tensor - 127.5) / 128.0
            face_tensor = face_tensor.unsqueeze(0)
            
            # Generate embedding
            with torch.no_grad():
                embedding = self.facenet(face_tensor)
                if embedding is None:
                    logger.error("FaceNet returned None embedding")
                    return None
                
                return embedding.cpu().numpy().flatten()
        
        except Exception as e:
            logger.error(f"Error extracting face embedding: {e}")
            return None

    def identify_person(
        self,
        image: Image.Image,
        return_bbox: bool = False,
        pre_detected_faces: Optional[List[Tuple[Image.Image, List[int]]]] = None
    ) -> Optional[Dict]:
        """
        Identify person in image
        
        Args:
            image: PIL Image containing a face
            return_bbox: Whether to include bounding box in result
        
        Returns:
            Dict with identification result or None if no match
            {
                'person_id': str,
                'name': str,
                'confidence': float,
                'embedding_distance': float,
                'bounding_box': [x, y, w, h] (optional),
            }
        """
        if not self.person_embeddings:
            logger.warning("No persons enrolled in system")
            return None
        try:
            # Detect faces and get bounding box
            faces = pre_detected_faces if pre_detected_faces is not None else self.detect_faces(image)
            
            if faces is None or len(faces) == 0:
                logger.debug("No faces detected in image")
                return None
            
            # Use the first face
            face_img, bbox = faces[0]
            distance_m = self.estimate_distance(bbox)
            within_range = True
            if distance_m is not None:
                within_range = self.distance_min_m <= distance_m <= self.distance_max_m
                if self.distance_gating_enabled and not within_range:
                    logger.debug(
                        "Face detected but distance %.3fm outside configured range %.3f-%.3fm",
                        distance_m,
                        self.distance_min_m,
                        self.distance_max_m,
                    )
                    return None
            elif self.distance_gating_enabled:
                logger.debug("Face detected but distance could not be estimated; proceeding without gating")
            
            # Get embedding for detected face
            face_img_resized = face_img.resize((160, 160))
            face_array = np.array(face_img_resized)
            
            if len(face_array.shape) == 2:
                face_array = np.stack([face_array] * 3, axis=-1)
            elif face_array.shape[2] == 4:
                face_array = face_array[:, :, :3]
            
            face_tensor = torch.tensor(face_array).permute(2, 0, 1).float()
            face_tensor = (face_tensor - 127.5) / 128.0
            face_tensor = face_tensor.unsqueeze(0)
            
            with torch.no_grad():
                current_embedding = self.facenet(face_tensor).cpu().numpy().flatten()
            
            # Compare with all enrolled persons
            current_embedding = current_embedding.reshape(1, -1)
            person_embeddings = np.array(self.person_embeddings)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(current_embedding, person_embeddings)[0]
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_similarity = similarities[best_idx]
            
            # Calculate distance (1 - similarity for cosine)
            embedding_distance = 1.0 - best_similarity
            
            if best_similarity >= self.recognition_threshold:
                result = {
                    'person_id': self.person_ids[best_idx],
                    'name': self.person_names[best_idx],
                    'confidence': float(best_similarity),
                    'embedding_distance': float(embedding_distance)
                }
                
                if return_bbox:
                    result['bounding_box'] = bbox
                if distance_m is not None:
                    result['distance_m'] = float(distance_m)
                    result['distance_within_range'] = within_range
                    result['distance_alert'] = distance_m <= self.distance_alert_m

                logger.info(
                    f"✅ IDENTIFIED: {result['name']} "
                    f"(confidence: {best_similarity:.3f}) | "
                    f"Distance: {embedding_distance:.4f}"
                )
                return result
            else:
                logger.debug(
                    f"Face detected but confidence too low: {best_similarity:.3f} "
                    f"< {self.recognition_threshold}"
                )
                return None
        
        except Exception as e:
            logger.error(f"Error in person identification: {e}", exc_info=True)
            return None
    
    def identify_all_persons(
        self,
        image: Image.Image,
        return_bbox: bool = False,
        pre_detected_faces: Optional[List[Tuple[Image.Image, List[int]]]] = None
    ) -> List[Dict]:
        """
        Identify all persons in image
        
        Args:
            image: PIL Image containing faces
            return_bbox: Whether to include bounding box in results
            pre_detected_faces: Optional pre-detected faces to use
        
        Returns:
            List of dicts with identification results, one per detected face
            Each dict contains:
            {
                'person_id': str,
                'name': str,
                'confidence': float,
                'embedding_distance': float,
                'bounding_box': [x, y, w, h] (optional),
                'distance_m': float (optional),
                'distance_within_range': bool (optional),
                'distance_alert': bool (optional)
            }
            Returns empty list if no persons identified
        """
        if not self.person_embeddings:
            logger.warning("No persons enrolled in system")
            return []
        
        results = []
        
        try:
            # Detect all faces
            faces = pre_detected_faces if pre_detected_faces is not None else self.detect_faces(image)
            
            if faces is None or len(faces) == 0:
                logger.debug("No faces detected in image")
                return []
            
            logger.debug(f"Processing {len(faces)} detected face(s)")
            
            # Process each detected face
            for face_idx, (face_img, bbox) in enumerate(faces):
                # Check distance gating
                distance_m = self.estimate_distance(bbox)
                within_range = True
                
                if distance_m is not None:
                    within_range = self.distance_min_m <= distance_m <= self.distance_max_m
                    if self.distance_gating_enabled and not within_range:
                        logger.debug(
                            f"Face {face_idx+1} at distance {distance_m:.3f}m outside range "
                            f"{self.distance_min_m:.3f}-{self.distance_max_m:.3f}m, skipping"
                        )
                        continue
                elif self.distance_gating_enabled:
                    logger.debug(f"Face {face_idx+1}: distance could not be estimated; proceeding without gating")
                
                # Get embedding for detected face
                face_img_resized = face_img.resize((160, 160))
                face_array = np.array(face_img_resized)
                
                if len(face_array.shape) == 2:
                    face_array = np.stack([face_array] * 3, axis=-1)
                elif face_array.shape[2] == 4:
                    face_array = face_array[:, :, :3]
                
                face_tensor = torch.tensor(face_array).permute(2, 0, 1).float()
                face_tensor = (face_tensor - 127.5) / 128.0
                face_tensor = face_tensor.unsqueeze(0)
                
                with torch.no_grad():
                    current_embedding = self.facenet(face_tensor).cpu().numpy().flatten()
                
                # Compare with all enrolled persons
                current_embedding = current_embedding.reshape(1, -1)
                person_embeddings = np.array(self.person_embeddings)
                
                # Calculate cosine similarities
                similarities = cosine_similarity(current_embedding, person_embeddings)[0]
                
                # Find best match
                best_idx = np.argmax(similarities)
                best_similarity = similarities[best_idx]
                
                # Calculate distance (1 - similarity for cosine)
                embedding_distance = 1.0 - best_similarity
                
                if best_similarity >= self.recognition_threshold:
                    result = {
                        'person_id': self.person_ids[best_idx],
                        'name': self.person_names[best_idx],
                        'confidence': float(best_similarity),
                        'embedding_distance': float(embedding_distance)
                    }
                    
                    if return_bbox:
                        result['bounding_box'] = bbox
                    if distance_m is not None:
                        result['distance_m'] = float(distance_m)
                        result['distance_within_range'] = within_range
                        result['distance_alert'] = distance_m <= self.distance_alert_m
                    
                    results.append(result)
                    
                    logger.info(
                        f"✅ IDENTIFIED ({face_idx+1}/{len(faces)}): {result['name']} "
                        f"(confidence: {best_similarity:.3f}) | "
                        f"Distance: {embedding_distance:.4f}"
                    )
                else:
                    logger.debug(
                        f"Face {face_idx+1} detected but confidence too low: {best_similarity:.3f} "
                        f"< {self.recognition_threshold}"
                    )
            
            return results
        
        except Exception as e:
            logger.error(f"Error in multi-person identification: {e}", exc_info=True)
            return []

    
    def enroll_person(
        self,
        images: List[Image.Image],
        person_id: str,
        name: str,
        db: Session,
    ) -> Tuple[bool, str, Optional[List[np.ndarray]]]:
        """
        Enroll a new person with multiple images
        
        Args:
            images: List of PIL Images containing person's face
            person_id: Unique person identifier
            name: Person's name
            db: Database session
            
        Returns:
            (success: bool, message: str, embeddings: Optional[List[np.ndarray]])
        """
        try:
            # Check if person_id already exists
            existing = db.query(Person).filter(Person.person_id == person_id).first()
            if existing:
                return False, f"Person ID {person_id} already exists", None

            embeddings = []
            
            for i, image in enumerate(images):
                # Detect faces
                faces = self.detect_faces(image)
                if faces is None or len(faces) == 0:
                    logger.warning(f"No face detected in image {i+1}")
                    continue
                
                # Extract face embedding
                embedding = self.get_face_embedding(image, pre_detected_faces=faces)
                
                if embedding is not None:
                    embeddings.append(embedding)
            
            if not embeddings:
                return False, "Failed to extract any face embeddings from provided images", None
            
            # All validations passed
            logger.info(
                f"✅ Enrollment approved for {name} with {len(embeddings)} embeddings"
            )
            
            return (
                True, 
                f"Created {len(embeddings)} face embeddings successfully", 
                embeddings
            )
        
        except Exception as e:
            logger.error(f"Error enrolling person: {e}", exc_info=True)
            return False, f"Error: {str(e)}", None
    
    def update_threshold(self, new_threshold: float) -> bool:
        """
        Update recognition threshold
        
        Args:
            new_threshold: New threshold value (0.0-1.0)
            
        Returns:
            bool: Success status
        """
        if 0.0 <= new_threshold <= 1.0:
            self.recognition_threshold = new_threshold
            logger.info(f"Recognition threshold updated to {new_threshold}")
            return True
        
        logger.warning(f"Invalid threshold value: {new_threshold}")
        return False
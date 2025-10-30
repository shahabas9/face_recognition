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
    ENABLE_LIVENESS
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
                    embedding = np.array(embedding_data, dtype=np.float32)
                    
                    self.person_embeddings.append(embedding)
                    self.person_ids.append(person.person_id)
                    self.person_names.append(person.name)
                except Exception as e:
                    logger.error(f"Error loading person {person.name}: {e}")
            
            if should_close:
                db.close()
            
            logger.info(f"✅ Loaded {len(self.person_embeddings)} persons into cache")
            
        except Exception as e:
            logger.error(f"❌ Error loading persons from database: {e}")
    
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
            # Convert PIL Image to numpy array for liveness check
            image_np = np.array(image)
            
            # Check liveness if enabled
            if ENABLE_LIVENESS:
                from .liveness_service import liveness_service
                
                # Check if liveness service is initialized
                if not liveness_service.initialized:
                    logger.error("❌ Liveness service not initialized! Call liveness_service.initialize() first.")
                    logger.error("   Continuing without liveness check...")
                else:
                    liveness_result = liveness_service.check_liveness(image_np)
                    
                    if not liveness_result.get('is_live', False):
                        logger.warning(
                            f"Liveness check failed (score: {liveness_result.get('confidence', 0):.3f} < "
                            f"{liveness_result.get('threshold', 0.7)})"
                        )
                        return {
                            'error': 'Liveness check failed',
                            'liveness': liveness_result
                        }
            
            # Detect faces and get bounding box
            faces = pre_detected_faces if pre_detected_faces is not None else self.detect_faces(image)
            
            if faces is None or len(faces) == 0:
                logger.debug("No faces detected in image")
                return None
            
            # Use the first face
            face_img, bbox = faces[0]
            
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
                
                # Add liveness info if enabled
                if ENABLE_LIVENESS:
                    result['liveness'] = liveness_result
                
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
    
    def enroll_person(
        self,
        image: Image.Image,
        person_id: str,
        name: str,
        db: Session,
        pre_detected_faces: Optional[List[Tuple[Image.Image, List[int]]]] = None
    ) -> Tuple[bool, str, Optional[np.ndarray]]:
        """
        Enroll a new person
        
        Args:
            image: PIL Image containing person's face
            person_id: Unique person identifier
            name: Person's name
            db: Database session
            
        Returns:
            (success: bool, message: str, embedding: Optional[np.ndarray])
        """
        try:
            # Detect faces first
            faces = self.detect_faces(image)
            if faces is None or len(faces) == 0:
                return False, "No face detected in image", None
            
            # Extract face embedding
            embedding = self.get_face_embedding(image, pre_detected_faces=faces)
            
            if embedding is None:
                return False, "Failed to extract face embedding", None
            
            # Check if person_id already exists
            existing = db.query(Person).filter(Person.person_id == person_id).first()
            if existing:
                return False, f"Person ID {person_id} already exists", None
            
            # All validations passed
            logger.info(
                f"✅ Enrollment approved for {name}"
            )
            
            return (
                True, 
                "Face embedding created successfully", 
                embedding
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
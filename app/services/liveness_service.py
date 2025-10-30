import cv2
import numpy as np
import logging
from typing import Dict, Optional
import onnxruntime as ort
from pathlib import Path
from config.settings import LIVENESS_THRESHOLD

logger = logging.getLogger(__name__)

class LivenessService:
    def __init__(self, threshold: float = None):
        # Use threshold from settings if not provided
        self.threshold = threshold if threshold is not None else LIVENESS_THRESHOLD
        self.app = None
        self.inspire_session = None
        self.use_inspireface = False
        self.initialized = False

    def initialize(self):
        """Initialize InspireFace with Megatron (liveness) and Pikachu (detection)"""
        if not self.initialized:
            try:
                import inspireface as isf
                
                # Pull the latest models
                logger.info("Downloading InspireFace models...")
                isf.pull_latest_model("Megatron")  # Liveness detection
                isf.pull_latest_model("Pikachu")   # Face detection
                logger.info("✅ InspireFace models downloaded successfully")
                
                # Initialize InspireFace session with liveness detection
                # HF_ENABLE_LIVENESS enables RGB liveness detection (Megatron)
                # Pikachu is automatically used for face detection
                options = isf.HF_ENABLE_LIVENESS
                
                # Create session with liveness enabled
                self.inspire_session = isf.InspireFaceSession(
                    options,
                    isf.HF_DETECT_MODE_ALWAYS_DETECT
                )
                
                self.use_inspireface = True
                self.initialized = True
                logger.info("✅ InspireFace initialized with Megatron (liveness) + Pikachu (detection)")
                    
            except ImportError:
                logger.error("⚠️  inspireface package not installed")
                logger.error("Install with: pip install inspireface")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize InspireFace: {e}")
                raise

    def check_liveness(self, image: np.ndarray) -> Dict:
        """
        Check liveness of faces in the image using InsightFace
        Returns:
            Dict with 'is_live' (bool) and 'confidence' (float)
        """
        if not self.initialized:
            self.initialize()

        try:
            import inspireface as isf
            
            # Ensure image is in BGR format (OpenCV format)
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            
            # Try to detect faces using InspireFace (Pikachu model)
            # First attempt with default settings
            inspire_faces = self.inspire_session.face_detection(image)
            detection_image = image
            rotation_angle = 0
            
            # If no faces found, try with different rotations
            if not inspire_faces or len(inspire_faces) == 0:
                logger.debug("No faces detected, trying rotations...")
                for angle in [90, 270, 180]:  # Try common rotation angles
                    h, w = image.shape[:2]
                    center = (w // 2, h // 2)
                    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    
                    # Calculate new dimensions
                    cos = abs(rotation_matrix[0, 0])
                    sin = abs(rotation_matrix[0, 1])
                    new_w = int((h * sin) + (w * cos))
                    new_h = int((h * cos) + (w * sin))
                    
                    # Adjust rotation matrix
                    rotation_matrix[0, 2] += (new_w / 2) - center[0]
                    rotation_matrix[1, 2] += (new_h / 2) - center[1]
                    
                    rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h))
                    inspire_faces = self.inspire_session.face_detection(rotated)
                    
                    if inspire_faces and len(inspire_faces) > 0:
                        logger.info(f"Faces detected after {angle}° rotation")
                        detection_image = rotated
                        rotation_angle = angle
                        break
            
            # If still no faces, try with image preprocessing
            if not inspire_faces or len(inspire_faces) == 0:
                logger.debug("No faces detected after rotation, trying enhancement...")
                # Try enhancing the image
                enhanced = cv2.convertScaleAbs(image, alpha=1.2, beta=30)
                inspire_faces = self.inspire_session.face_detection(enhanced)
                if inspire_faces and len(inspire_faces) > 0:
                    detection_image = enhanced
            
            if not inspire_faces or len(inspire_faces) == 0:
                return {
                    "is_live": False,
                    "confidence": 0.0,
                    "error": "No face detected by Pikachu",
                    "threshold": self.threshold,
                    "model": "megatron+pikachu"
                }
            
            # Run face pipeline with liveness enabled (Megatron model)
            # Use the detection_image (which may be rotated/enhanced)
            exec_param = isf.SessionCustomParameter(enable_liveness=True)
            results = self.inspire_session.face_pipeline(detection_image, inspire_faces, exec_param)
            
            if not results or len(results) == 0:
                return {
                    "is_live": False,
                    "confidence": 0.0,
                    "error": "Liveness pipeline failed",
                    "threshold": self.threshold,
                    "model": "megatron+pikachu"
                }
            
            # Get liveness confidence from first face (Megatron output)
            face_ext = results[0]
            liveness_confidence = face_ext.rgb_liveness_confidence
            
            # Additional check: Analyze image for screen artifacts
            # For now, analyze the whole image since face bbox extraction is tricky
            screen_artifacts_score = self._detect_screen_artifacts(detection_image, None)
            
            # Combine scores: both must pass
            # If screen artifacts detected, reduce liveness confidence
            # Only penalize if BOTH conditions are met:
            # 1. High artifact score (>0.6)
            # 2. Low liveness score (<0.7)
            if screen_artifacts_score > 0.6 and liveness_confidence < 0.7:
                logger.debug(f"Screen artifacts detected: {screen_artifacts_score:.3f}")
                # Penalize the liveness score
                adjusted_confidence = liveness_confidence * (1.0 - screen_artifacts_score * 0.3)
            else:
                # No significant artifacts or liveness is good, use raw liveness score
                adjusted_confidence = liveness_confidence
            
            # Determine if live based on threshold
            is_live = adjusted_confidence >= self.threshold
            
            logger.debug(f"Megatron liveness: {liveness_confidence:.3f}, screen_artifacts: {screen_artifacts_score:.3f}, adjusted: {adjusted_confidence:.3f}, threshold={self.threshold}, is_live={is_live}")
            
            return {
                "is_live": is_live,
                "confidence": float(adjusted_confidence),
                "raw_liveness": float(liveness_confidence),
                "screen_artifacts": float(screen_artifacts_score),
                "threshold": self.threshold,
                "num_faces": len(inspire_faces),
                "model": "megatron+pikachu+artifacts"
            }
            
        except Exception as e:
            logger.error(f"Error in liveness check: {e}", exc_info=True)
            return {
                "is_live": False,
                "confidence": 0.0,
                "error": str(e),
                "threshold": self.threshold
            }
    
    def _detect_screen_artifacts(self, image: np.ndarray, face_bbox) -> float:
        """
        Detect screen artifacts like moiré patterns, pixel grids, reflections
        Returns score 0-1 (higher = more likely a screen)
        """
        try:
            # Use whole image for artifact detection
            # (Face-specific detection would be more accurate but requires correct bbox extraction)
            face_region = image
            
            if face_region.size == 0:
                return 0.0
            
            # Convert to grayscale
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # 1. Check for high-frequency patterns (moiré, pixel grid)
            # Apply FFT to detect periodic patterns
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            magnitude_spectrum = np.abs(fshift)
            
            # Check for strong periodic components (typical of screens)
            h, w = magnitude_spectrum.shape
            center_h, center_w = h // 2, w // 2
            # Exclude DC component
            magnitude_spectrum[center_h-5:center_h+5, center_w-5:center_w+5] = 0
            
            # Calculate energy in high-frequency bands
            high_freq_energy = np.sum(magnitude_spectrum[center_h-h//4:center_h+h//4, center_w-w//4:center_w+w//4])
            total_energy = np.sum(magnitude_spectrum)
            
            if total_energy > 0:
                freq_ratio = high_freq_energy / total_energy
            else:
                freq_ratio = 0
            
            # 2. Check for uniform lighting (screens have very uniform backlight)
            std_dev = np.std(gray)
            mean_val = np.mean(gray)
            if mean_val > 0:
                uniformity_score = 1.0 - min(std_dev / mean_val, 1.0)
            else:
                uniformity_score = 0
            
            # 3. Check for sharp edges (screen bezels)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # 4. Texture analysis - Real skin has micro-textures, screens are too smooth
            # Calculate local binary patterns (LBP) for texture
            # Real skin: High variance in texture
            # Screen: Low variance (too smooth/uniform)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            texture_variance = np.var(laplacian)
            
            # Normalize texture variance (typical range: 0-1000 for real faces)
            # Screens typically have lower variance (0-200)
            if texture_variance < 100:
                texture_smoothness = 0.8  # Very smooth = likely screen
            elif texture_variance < 300:
                texture_smoothness = 0.5  # Somewhat smooth = suspicious
            else:
                texture_smoothness = 0.1  # Normal texture = likely real
            
            # 5. Color distribution analysis
            # Real skin has natural color gradients
            # Screens have artificial color distribution
            b, g, r = cv2.split(face_region)
            color_std = (np.std(r) + np.std(g) + np.std(b)) / 3
            
            # Real faces have more color variation
            if color_std < 15:
                color_uniformity = 0.7  # Too uniform = likely screen
            elif color_std < 25:
                color_uniformity = 0.4  # Somewhat uniform = suspicious
            else:
                color_uniformity = 0.1  # Normal variation = likely real
            
            # Combine scores
            # High freq_ratio = likely screen (moiré patterns)
            # High uniformity = likely screen (flat lighting)
            # High edge density = might be screen bezel
            # High texture_smoothness = likely screen (too smooth)
            # High color_uniformity = likely screen (artificial colors)
            
            artifact_score = (
                min(freq_ratio * 2.0, 1.0) * 0.25 +  # Frequency patterns (25% weight)
                uniformity_score * 0.15 +             # Lighting uniformity (15% weight)
                min(edge_density * 5.0, 1.0) * 0.15 + # Edge density (15% weight)
                texture_smoothness * 0.25 +           # Texture analysis (25% weight) - NEW
                color_uniformity * 0.20               # Color distribution (20% weight) - NEW
            )
            
            return min(artifact_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error detecting screen artifacts: {e}")
            return 0.0

# Singleton instance
liveness_service = LivenessService()
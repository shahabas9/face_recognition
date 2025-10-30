#!/usr/bin/env python3
"""
Face Detection Diagnostic Tool
Tests face detection on a webcam frame to diagnose issues
"""
import sys
import cv2
import numpy as np
from PIL import Image
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.face_recognition_service import FaceRecognitionService
from config.settings import MIN_FACE_SIZE, DETECTION_CONFIDENCE, RECOGNITION_THRESHOLD

def test_webcam_detection(stream_url: str):
    """Test face detection on webcam stream"""
    
    print("=" * 80)
    print("🔍 FACE DETECTION DIAGNOSTIC TOOL")
    print("=" * 80)
    print()
    
    print("📊 Current Settings:")
    print(f"  MIN_FACE_SIZE: {MIN_FACE_SIZE} pixels")
    print(f"  DETECTION_CONFIDENCE: {DETECTION_CONFIDENCE} ({DETECTION_CONFIDENCE*100}%)")
    print(f"  RECOGNITION_THRESHOLD: {RECOGNITION_THRESHOLD} ({RECOGNITION_THRESHOLD*100}%)")
    print()
    
    # Initialize service
    print("🔧 Initializing face recognition service...")
    service = FaceRecognitionService()
    print(f"✅ Loaded {len(service.person_ids)} enrolled persons")
    for i, (pid, name) in enumerate(zip(service.person_ids, service.person_names)):
        print(f"   {i+1}. {name} ({pid})")
    print()
    
    # Connect to webcam
    print(f"📹 Connecting to webcam: {stream_url}")
    cap = cv2.VideoCapture(stream_url)
    
    if not cap.isOpened():
        print("❌ Failed to connect to webcam!")
        return
    
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read frame from webcam!")
        cap.release()
        return
    
    print(f"✅ Connected! Frame size: {frame.shape[1]}x{frame.shape[0]}")
    print()
    
    # Test detection on 5 frames
    print("🔍 Testing face detection on 5 frames...")
    print("-" * 80)
    
    for i in range(5):
        ret, frame = cap.read()
        
        if not ret:
            print(f"Frame {i+1}: ❌ Failed to read")
            continue
        output_dir = Path("diagnostic_frames")
        output_dir.mkdir(exist_ok=True)
        frame_path = output_dir / f"frame_{i+1}.jpg"
        cv2.imwrite(str(frame_path), frame)
        print(f"🖼️  Saved frame {i+1} -> {frame_path}")
        # Convert to PIL Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        
        # Detect faces
        faces = service.detect_faces(pil_image)
        
        if faces:
            print(f"Frame {i+1}: ✅ Detected {len(faces)} face(s)")
            for j, (face_img, bbox) in enumerate(faces):
                x, y, w, h = bbox
                print(f"         Face {j+1}: Size {w}x{h} at position ({x}, {y})")
                
                # Try to identify
                result = service.identify_person(pil_image, return_bbox=True)
                if result:
                    print(f"         ✅ IDENTIFIED: {result['name']} (confidence: {result['confidence']:.3f})")
                else:
                    # Check why identification failed
                    embedding = service.get_face_embedding(pil_image)
                    if embedding is not None and service.person_embeddings:
                        from sklearn.metrics.pairwise import cosine_similarity
                        current_emb = embedding.reshape(1, -1)
                        person_embs = np.array(service.person_embeddings)
                        similarities = cosine_similarity(current_emb, person_embs)[0]
                        best_sim = np.max(similarities)
                        best_idx = np.argmax(similarities)
                        best_name = service.person_names[best_idx]
                        
                        print(f"         ❌ Not identified (best match: {best_name} at {best_sim:.3f}, threshold: {RECOGNITION_THRESHOLD})")
                        if best_sim < RECOGNITION_THRESHOLD:
                            print(f"         💡 Confidence too low! Increase similarity or lower threshold")
        else:
            print(f"Frame {i+1}: ❌ No faces detected")
            
            # Check MTCNN raw detection
            boxes, probs = service.mtcnn.detect(pil_image)
            if boxes is not None:
                print(f"         ⚠️  MTCNN found {len(boxes)} potential face(s) but filtered out:")
                for j, (box, prob) in enumerate(zip(boxes, probs)):
                    x1, y1, x2, y2 = box
                    w, h = x2 - x1, y2 - y1
                    print(f"         Box {j+1}: {w:.0f}x{h:.0f} pixels, confidence: {prob:.3f}")
                    
                    if prob < DETECTION_CONFIDENCE:
                        print(f"                 ❌ Rejected: confidence {prob:.3f} < {DETECTION_CONFIDENCE}")
                    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                        print(f"                 ❌ Rejected: size {w:.0f}x{h:.0f} < {MIN_FACE_SIZE}")
            else:
                print(f"         ⚠️  No faces found by MTCNN at all")
        
        print()
    
    cap.release()
    
    print("=" * 80)
    print("📋 DIAGNOSIS SUMMARY")
    print("=" * 80)
    print()
    print("Possible reasons for no detection:")
    print()
    print("1. **Face too far from camera**")
    print(f"   → Face must be at least {MIN_FACE_SIZE}x{MIN_FACE_SIZE} pixels")
    print("   → Move closer to the camera")
    print()
    print("2. **Detection confidence too low**")
    print(f"   → MTCNN confidence must be ≥ {DETECTION_CONFIDENCE}")
    print("   → Improve lighting, face camera directly")
    print()
    print("3. **Recognition threshold too high**")
    print(f"   → Similarity must be ≥ {RECOGNITION_THRESHOLD}")
    print("   → Enrolled face might be different (angle, lighting)")
    print()
    print("4. **Poor image quality**")
    print("   → Ensure good lighting")
    print("   → Face should be clear and facing camera")
    print()
    print("🔧 To lower thresholds temporarily, run:")
    print("   export DETECTION_CONFIDENCE=0.5")
    print("   export RECOGNITION_THRESHOLD=0.5")
    print("   export MIN_FACE_SIZE=40")
    print("   python main.py")
    print()

if __name__ == "__main__":
    # Use the configured webcam URL
    from config.ip_webcam_config import get_stream_url
    
    try:
        stream_url = get_stream_url("mobile_webcam_1")
        test_webcam_detection(stream_url)
    except KeyboardInterrupt:
        print("\n👋 Test stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

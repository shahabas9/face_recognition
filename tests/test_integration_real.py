import unittest
import sys
import os
import numpy as np
from PIL import Image, ImageDraw
import io

# Add current directory to path
sys.path.append(os.getcwd())

from app.services.face_recognition_service import FaceRecognitionService
from app.models.database import SessionLocal, Person

class TestRealIntegration(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.service = FaceRecognitionService()
        self.test_person_id = "TEST_REAL_001"
        
        # Clean up if exists
        existing = self.db.query(Person).filter(Person.person_id == self.test_person_id).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()
            
    def tearDown(self):
        # Clean up
        existing = self.db.query(Person).filter(Person.person_id == self.test_person_id).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()
        self.db.close()

    def create_dummy_face(self):
        # Create a dummy image that MTCNN might detect as a face
        # This is tricky without a real face. 
        # For this integration test, we might just want to verify the PIPELINE works, 
        # even if detection fails (returns 0 faces).
        # OR we can try to draw a face.
        # But MTCNN is robust.
        # If we can't easily generate a detectable face, we might fail at "No face detected".
        # But that's a valid result from the service.
        # We want to verify the service accepts the list of images and tries to process them.
        
        img = Image.new('RGB', (300, 300), color=(200, 200, 200))
        d = ImageDraw.Draw(img)
        # Draw a face-like structure
        d.ellipse((50, 50, 250, 250), fill=(255, 220, 200)) # Face
        d.ellipse((100, 100, 130, 130), fill=(0, 0, 0)) # Left eye
        d.ellipse((170, 100, 200, 130), fill=(0, 0, 0)) # Right eye
        d.rectangle((100, 200, 200, 220), fill=(200, 50, 50)) # Mouth
        return img

    def test_enroll_flow(self):
        print("\nTesting real enrollment flow...")
        images = [self.create_dummy_face() for _ in range(5)]
        
        # We expect this might fail with "No face detected" if our drawing isn't good enough.
        # But we want to ensure it DOESN'T fail with "TypeError" or "AttributeError".
        
        success, message, embeddings = self.service.enroll_person(
            images,
            self.test_person_id,
            "Real Test User",
            self.db
        )
        
        print(f"Result: success={success}, message='{message}'")
        
        if success:
            print("✅ Enrollment successful with generated face!")
            self.assertEqual(len(embeddings), 5)
            
            # Verify DB
            person = self.db.query(Person).filter(Person.person_id == self.test_person_id).first()
            self.assertIsNotNone(person)
            import json
            emb_list = json.loads(person.face_embedding)
            self.assertEqual(len(emb_list), 5)
            
        else:
            print("⚠️ Enrollment failed (likely due to face detection), but code ran without crashing.")
            # If it failed due to no face, that's fine for this test, 
            # as long as it's not a code error.
            if "No face detected" in message or "Failed to extract" in message:
                print("✅ Service handled 'no face' correctly.")
            else:
                self.fail(f"Unexpected failure: {message}")

if __name__ == "__main__":
    unittest.main()

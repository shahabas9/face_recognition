import unittest
from unittest.mock import MagicMock, patch
import sys
import numpy as np
from PIL import Image

# Mock dependencies that might be missing
sys.modules['torch'] = MagicMock()
sys.modules['facenet_pytorch'] = MagicMock()
sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.metrics'] = MagicMock()
sys.modules['sklearn.metrics.pairwise'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.ext'] = MagicMock()
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['pymysql'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()

# Mock app.models to avoid importing database.py
mock_models = MagicMock()
sys.modules['app.models'] = mock_models
sys.modules['app.models.database'] = MagicMock()

# Define Person mock
class MockPerson:
    person_id = "mock_id"
    is_active = True
    face_embedding = "[]"
    name = "Mock Name"
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

mock_models.Person = MockPerson

# Now import service
from app.services.face_recognition_service import FaceRecognitionService

class TestMultiEnrollment(unittest.TestCase):
    def setUp(self):
        self.service = FaceRecognitionService()
        # Mock MTCNN and FaceNet to avoid actual inference
        self.service.mtcnn = MagicMock()
        self.service.facenet = MagicMock()
        
    def test_enroll_person_multi_image(self):
        # Mock database session
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None # No existing person
        
        # Mock face detection to return a dummy face
        # detect_faces returns list of (face_img, box)
        dummy_face = Image.new('RGB', (160, 160))
        self.service.detect_faces = MagicMock(return_value=[(dummy_face, [0, 0, 100, 100])])
        
        # Mock embedding extraction
        # get_face_embedding returns numpy array
        dummy_embedding = np.random.rand(512).astype(np.float32)
        self.service.get_face_embedding = MagicMock(return_value=dummy_embedding)
        
        # Create 5 dummy images
        images = [Image.new('RGB', (300, 300)) for _ in range(5)]
        
        # Call enroll_person
        success, message, embeddings = self.service.enroll_person(
            images,
            "TEST_P001",
            "Test User",
            db
        )
        
        # Verify results
        self.assertTrue(success)
        self.assertIn("Created 5 face embeddings", message)
        self.assertEqual(len(embeddings), 5)
        self.assertTrue(all(isinstance(e, np.ndarray) for e in embeddings))
        
        print("✅ Unit Test Passed: enroll_person handled 5 images correctly")

if __name__ == "__main__":
    unittest.main()

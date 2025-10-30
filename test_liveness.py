import cv2
from app.services.liveness_service import liveness_service

# Initialize
liveness_service.initialize()

# Test with an image
image = cv2.imread("webcam_spoof_20251030_142128_mobile-entrance-1_e6b7c129.jpg")
result = liveness_service.check_liveness(image)
print(f"Liveness: {result['is_live']} (Confidence: {result['confidence']:.2f})")
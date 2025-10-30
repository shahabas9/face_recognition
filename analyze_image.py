import cv2
import numpy as np
from app.services.liveness_service import liveness_service

# Initialize liveness service
print("Initializing liveness detection...")
liveness_service.initialize()
print("✅ Liveness detection ready\n")

# Test the specific image
image_path = "snapshots/events/2025-10-30/webcam_20251030_220358_P001_mobile-entrance-1_2cd042a6.jpg"
print(f"Analyzing: {image_path}\n")

# Read image
image = cv2.imread(image_path)

if image is None:
    print("❌ Could not read image")
    exit(1)

print(f"Image shape: {image.shape}")
print(f"Image size: {image.shape[1]}x{image.shape[0]} pixels\n")

# Check liveness with detailed output
result = liveness_service.check_liveness(image)

print("=" * 80)
print("LIVENESS DETECTION RESULT")
print("=" * 80)
print(f"Is Live: {result.get('is_live', False)}")
print(f"Confidence: {result.get('confidence', 0.0):.4f}")
print(f"Threshold: {result.get('threshold', 0.7):.4f}")
print(f"Model Used: {result.get('model', 'unknown')}")
print(f"Number of Faces: {result.get('num_faces', 0)}")

if result.get('error'):
    print(f"Error: {result.get('error')}")

print("=" * 80)

# Analyze why it might be classified incorrectly
confidence = result.get('confidence', 0.0)
threshold = result.get('threshold', 0.7)
model = result.get('model', 'unknown')

print("\n📊 ANALYSIS:")
print("=" * 80)

if model == 'fallback':
    print("⚠️  WARNING: Using fallback detection (not true liveness)")
    print("   The system is using face detection confidence as a proxy for liveness.")
    print("   This means it's only checking if a face is detected clearly, NOT if it's live.")
    print("\n   Why this happens:")
    print("   - Megatron liveness model failed to load")
    print("   - System falls back to basic face detection confidence")
    print("   - A clear photo of a face will score high (false positive)")
    
    print("\n   Solution:")
    print("   - Need to properly load a true liveness detection model")
    print("   - Consider using a different liveness approach")
    print("   - Lower the threshold if using fallback mode")

elif confidence > threshold:
    print(f"✅ Confidence ({confidence:.4f}) exceeds threshold ({threshold:.4f})")
    print(f"   Difference: {(confidence - threshold):.4f}")
    print("\n   Possible reasons for false positive:")
    print("   - High-quality spoof image (clear, well-lit)")
    print("   - Liveness model not trained on this type of spoof")
    print("   - Threshold too low for your use case")
    print("\n   Recommendations:")
    print(f"   - Increase threshold to at least {(confidence + 0.05):.2f}")
    print("   - Use multiple liveness checks (blink detection, depth, etc.)")
    print("   - Collect more spoof samples to retrain/tune")

print("=" * 80)

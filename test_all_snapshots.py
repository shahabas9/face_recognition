import cv2
import os
from pathlib import Path
from app.services.liveness_service import liveness_service

# Initialize liveness service
print("Initializing liveness detection...")
liveness_service.initialize()
print("✅ Liveness detection ready\n")

# Path to snapshots
snapshots_dir = Path("snapshots/events/2025-10-28 13-10-25-438")

if not snapshots_dir.exists():
    print(f"❌ Directory not found: {snapshots_dir}")
    exit(1)

# Get all image files
image_files = list(snapshots_dir.glob("*.jpg")) + list(snapshots_dir.glob("*.png"))

if not image_files:
    print(f"❌ No images found in {snapshots_dir}")
    exit(1)

print(f"Found {len(image_files)} images to test\n")
print("=" * 80)

# Track results
live_images = []
spoofed_images = []
error_images = []

# Test each image
for idx, image_path in enumerate(sorted(image_files), 1):
    print(f"\n[{idx}/{len(image_files)}] Testing: {image_path.name}")
    
    # Read image
    image = cv2.imread(str(image_path))
    
    if image is None:
        print(f"  ❌ Could not read image")
        error_images.append(image_path.name)
        continue
    
    # Check liveness
    result = liveness_service.check_liveness(image)
    
    # Display result
    is_live = result.get('is_live', False)
    confidence = result.get('confidence', 0.0)
    threshold = result.get('threshold', 0.7)
    model = result.get('model', 'unknown')
    error = result.get('error', None)
    
    if error:
        print(f"  ❌ Error: {error}")
        error_images.append(image_path.name)
    elif is_live:
        print(f"  ✅ LIVE - Confidence: {confidence:.3f} (threshold: {threshold}) [model: {model}]")
        live_images.append((image_path.name, confidence))
    else:
        print(f"  🚫 SPOOFED - Confidence: {confidence:.3f} (threshold: {threshold}) [model: {model}]")
        spoofed_images.append((image_path.name, confidence))

# Summary
print("\n" + "=" * 80)
print("\n📊 SUMMARY")
print("=" * 80)
print(f"Total Images: {len(image_files)}")
print(f"✅ Live: {len(live_images)}")
print(f"🚫 Spoofed: {len(spoofed_images)}")
print(f"❌ Errors: {len(error_images)}")

if live_images:
    print("\n✅ LIVE IMAGES:")
    for name, conf in sorted(live_images, key=lambda x: x[1], reverse=True):
        print(f"  - {name} (confidence: {conf:.3f})")

if spoofed_images:
    print("\n🚫 SPOOFED IMAGES:")
    for name, conf in sorted(spoofed_images, key=lambda x: x[1]):
        print(f"  - {name} (confidence: {conf:.3f})")

if error_images:
    print("\n❌ ERROR IMAGES:")
    for name in error_images:
        print(f"  - {name}")

print("\n" + "=" * 80)

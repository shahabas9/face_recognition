#!/usr/bin/env python3
"""
Real-time webcam liveness detection test
Press 'q' to quit, 's' to save snapshot
"""

import cv2
import numpy as np
from app.services.liveness_service import liveness_service
import time

print("Initializing liveness detection...")
liveness_service.initialize()
print("✅ Liveness detection ready\n")

# Open webcam (0 is usually the default camera)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Could not open webcam")
    exit(1)

# Set camera resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("📷 Webcam opened successfully")
print("Press 'q' to quit, 's' to save snapshot")
print("-" * 80)

frame_count = 0
last_check_time = time.time()

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Failed to grab frame")
        break
    
    frame_count += 1
    
    # Check liveness every 10 frames (to avoid overload)
    current_time = time.time()
    if current_time - last_check_time >= 0.5:  # Check every 0.5 seconds
        last_check_time = current_time
        
        # Run liveness detection
        result = liveness_service.check_liveness(frame)
        
        # Display results on frame
        is_live = result.get('is_live', False)
        confidence = result.get('confidence', 0.0)
        error = result.get('error', '')
        model = result.get('model', 'unknown')
        
        # Choose color based on result
        if error:
            color = (0, 0, 255)  # Red for error
            text = f"ERROR: {error}"
        elif is_live:
            color = (0, 255, 0)  # Green for live
            text = f"LIVE: {confidence:.3f}"
        else:
            color = (0, 165, 255)  # Orange for spoof
            text = f"SPOOF: {confidence:.3f}"
        
        # Draw rectangle and text
        cv2.rectangle(frame, (10, 10), (400, 100), (0, 0, 0), -1)
        cv2.putText(frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"Model: {model}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Print to console
        print(f"[{frame_count:05d}] {text} (model: {model})")
    
    # Display the frame
    cv2.imshow('Liveness Detection - Press Q to quit, S to save', frame)
    
    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        print("\n👋 Quitting...")
        break
    elif key == ord('s'):
        # Save snapshot
        filename = f"webcam_snapshot_{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        print(f"📸 Saved snapshot: {filename}")

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("✅ Done!")

"""
Simulate IP webcam processing by reading frames from a video file or images
"""
import cv2
import requests
import time
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/v1/identify_image"
API_KEY = "testkey123"
CAMERA_ID = "simulation-test"

# Test video or image directory
TEST_VIDEO = "test_video.mp4"  # Place a test video here
TEST_IMAGES_DIR = Path("tests/sample_images")


def simulate_webcam_from_video(video_path, frame_skip=30):
    """
    Simulate webcam by processing frames from video file
    
    Args:
        video_path: Path to video file
        frame_skip: Process every Nth frame
    """
    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        return
    
    print(f"📹 Starting webcam simulation from: {video_path}")
    print(f"   Processing every {frame_skip} frames")
    print("="*80 + "\n")
    
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    processed_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        
        if not ret:
            break
        
        frame_count += 1
        
        # Process only every Nth frame
        if frame_count % frame_skip != 0:
            continue
        
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        
        # Send to API
        files = {"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")}
        data = {"camera_id": CAMERA_ID}
        headers = {"X-API-Key": API_KEY}
        
        try:
            start_time = time.time()
            response = requests.post(API_URL, files=files, data=data, headers=headers)
            elapsed = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result_data = response.json()
                result = result_data.get("result", {})
                
                if result.get("person_id"):
                    print(f"🎯 Frame {frame_count}: Identified {result['name']} "
                          f"(confidence: {result['confidence']:.2%}) "
                          f"[{elapsed:.1f}ms]")
                else:
                    print(f"❓ Frame {frame_count}: Unknown person [{elapsed:.1f}ms]")
            else:
                print(f"❌ Frame {frame_count}: API error {response.status_code}")
            
            processed_count += 1
            
        except Exception as e:
            print(f"❌ Error processing frame {frame_count}: {e}")
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.1)
    
    cap.release()
    
    print("\n" + "="*80)
    print(f"✅ Simulation complete")
    print(f"   Total frames: {frame_count}")
    print(f"   Processed frames: {processed_count}")
    print("="*80)


def simulate_webcam_from_images(images_dir, delay=2.0):
    """
    Simulate webcam by processing images from directory
    
    Args:
        images_dir: Directory containing images
        delay: Delay between images in seconds
    """
    images_dir = Path(images_dir)
    
    if not images_dir.exists():
        print(f"❌ Directory not found: {images_dir}")
        return
    
    # Find all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(images_dir.glob(ext))
    
    if not image_files:
        print(f"❌ No images found in {images_dir}")
        return
    
    print(f"📹 Starting webcam simulation from directory: {images_dir}")
    print(f"   Found {len(image_files)} images")
    print(f"   Delay: {delay}s between images")
    print("="*80 + "\n")
    
    for idx, img_path in enumerate(image_files, 1):
        print(f"Processing image {idx}/{len(image_files)}: {img_path.name}")
        
        # Read and send image
        with open(img_path, 'rb') as f:
            files = {"image": f}
            data = {"camera_id": CAMERA_ID}
            headers = {"X-API-Key": API_KEY}
            
            try:
                start_time = time.time()
                response = requests.post(API_URL, files=files, data=data, headers=headers)
                elapsed = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    result_data = response.json()
                    result = result_data.get("result", {})
                    
                    if result.get("person_id"):
                        print(f"  🎯 Identified: {result['name']} "
                              f"(confidence: {result['confidence']:.2%}) "
                              f"[{elapsed:.1f}ms]")
                    else:
                        print(f"  ❓ Unknown person [{elapsed:.1f}ms]")
                else:
                    print(f"  ❌ API error {response.status_code}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        if idx < len(image_files):
            time.sleep(delay)
    
    print("\n" + "="*80)
    print(f"✅ Simulation complete")
    print(f"   Processed {len(image_files)} images")
    print("="*80)


if __name__ == "__main__":
    import sys
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://localhost:8000")
        print("Start the server with: python main.py")
        sys.exit(1)
    
    print("\n" + "🎥"*40)
    print("IP WEBCAM SIMULATION TEST")
    print("🎥"*40 + "\n")
    
    print("Choose simulation mode:")
    print("1. Process images from directory (recommended for testing)")
    print("2. Process video file")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        # Simulate from images
        if TEST_IMAGES_DIR.exists():
            simulate_webcam_from_images(TEST_IMAGES_DIR, delay=1.0)
        else:
            print(f"\n⚠️  Create {TEST_IMAGES_DIR} and add test images")
    elif choice == "2":
        # Simulate from video
        if Path(TEST_VIDEO).exists():
            simulate_webcam_from_video(TEST_VIDEO, frame_skip=30)
        else:
            print(f"\n⚠️  Place a test video file at {TEST_VIDEO}")
    else:
        print("Invalid choice")

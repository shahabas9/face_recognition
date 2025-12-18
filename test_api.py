import requests
import uuid
import json
import sys

def test_enrollment(base_url="http://localhost:8000"):
    endpoint = f"{base_url}/api/v1/enroll_s3"
    
    print(f"Testing Endpoint: {endpoint}")
    
    # Sample Data
    payload = {
        "name": "Test User",
        "department": "Engineering",
        "image_urls": [
              "https://raw.githubusercontent.com/scikit-image/scikit-image/main/skimage/data/astronaut.png",
              "https://raw.githubusercontent.com/scikit-image/scikit-image/main/skimage/data/camera.png",
              "https://raw.githubusercontent.com/scikit-image/scikit-image/main/skimage/data/coffee.png",
              "https://raw.githubusercontent.com/scikit-image/scikit-image/main/skimage/data/horse.png",
              "https://raw.githubusercontent.com/scikit-image/scikit-image/main/skimage/data/moon.png"
        ],
        # "person_id": str(uuid.uuid4()) # Optional: Let server generate it
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "testkey123"
    }
    
    try:
        print("\nSending request...")
        response = requests.post(endpoint, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        try:
            data = response.json()
            print("\nResponse Body:")
            print(json.dumps(data, indent=2))
            
            if response.status_code == 200:
                print("\n✅ Test Passed!")
            else:
                print("\n❌ Test Failed")
                
        except json.JSONDecodeError:
            print("Response is not JSON:", response.text)
            
    except Exception as e:
        print(f"\n❌ Connection Error: {str(e)}")
        print("Make sure the server is running and accessible.")

if __name__ == "__main__":
    url = "http://localhost:8000"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # Ensure no trailing slash
    url = url.rstrip("/")
    
    test_enrollment(url)

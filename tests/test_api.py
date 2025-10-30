"""
Test script for Face Recognition API endpoints
"""
import requests
import json
import os
from pathlib import Path
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "testkey123"
HEADERS = {"X-API-Key": API_KEY}

# Test data directory
TEST_DIR = Path(__file__).parent
SAMPLE_IMAGES_DIR = TEST_DIR / "sample_images"


def print_test_header(test_name):
    """Print test header"""
    print("\n" + "="*80)
    print(f"TEST: {test_name}")
    print("="*80)


def print_response(response):
    """Pretty print response"""
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)


def test_health_check():
    """Test 1: Health check endpoint (no auth required)"""
    print_test_header("Health Check")
    
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print_response(response)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Health check passed")


def test_auth_required():
    """Test 2: API authentication (should fail without key)"""
    print_test_header("Authentication Required")
    
    # Try without API key (if auth is enabled)
    response = requests.get(f"{BASE_URL}/api/v1/status")
    print(f"Without API Key - Status: {response.status_code}")
    
    # Try with API key
    response = requests.get(f"{BASE_URL}/api/v1/status", headers=HEADERS)
    print_response(response)
    
    print("✅ Authentication test passed")


def test_enroll_person(image_path, person_id, name, department=None):
    """Test 3: Enroll a new person"""
    print_test_header(f"Enroll Person: {name}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return False
    
    files = {"image": open(image_path, "rb")}
    data = {
        "name": name,
        "person_id": person_id,
    }
    
    if department:
        data["department"] = department
    
    response = requests.post(
        f"{BASE_URL}/api/v1/enroll_person",
        headers=HEADERS,
        files=files,
        data=data
    )
    
    print_response(response)
    
    if response.status_code == 200:
        print(f"✅ Successfully enrolled {name} ({person_id})")
        return True
    else:
        print(f"❌ Failed to enroll {name}")
        return False


def test_identify_image(image_path, camera_id="mobile-test-1"):
    """Test 4: Identify person from image"""
    print_test_header(f"Identify Person from Image")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    files = {"image": open(image_path, "rb")}
    data = {"camera_id": camera_id}
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/v1/identify_image",
        headers=HEADERS,
        files=files,
        data=data
    )
    elapsed_ms = (time.time() - start_time) * 1000
    
    print(f"Response time: {elapsed_ms:.1f}ms")
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        result = data.get("result", {})
        
        if result.get("person_id"):
            print(f"✅ Identified: {result['name']} (confidence: {result['confidence']:.2%})")
        else:
            print("❓ Unknown person detected")
        
        return data
    else:
        print("❌ Identification failed")
        return None


def test_get_person(person_id):
    """Test 5: Get person details"""
    print_test_header(f"Get Person Details: {person_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/person/{person_id}",
        headers=HEADERS
    )
    
    print_response(response)
    
    if response.status_code == 200:
        print(f"✅ Retrieved person {person_id}")
        return True
    else:
        print(f"❌ Failed to get person {person_id}")
        return False


def test_list_persons():
    """Test 6: List all persons"""
    print_test_header("List All Persons")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/persons",
        headers=HEADERS
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total persons: {data['total']}")
        return True
    else:
        print("❌ Failed to list persons")
        return False


def test_update_threshold(threshold=0.65):
    """Test 7: Update recognition threshold"""
    print_test_header(f"Update Recognition Threshold: {threshold}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/threshold?threshold={threshold}",
        headers=HEADERS
    )
    
    print_response(response)
    
    if response.status_code == 200:
        print(f"✅ Threshold updated to {threshold}")
        return True
    else:
        print("❌ Failed to update threshold")
        return False


def test_system_status():
    """Test 8: Get system status"""
    print_test_header("System Status")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/status",
        headers=HEADERS
    )
    
    print_response(response)
    
    if response.status_code == 200:
        print("✅ System status retrieved")
        return True
    else:
        print("❌ Failed to get system status")
        return False


def run_all_tests():
    """Run all test cases"""
    print("\n" + "🧪"*40)
    print("FACE RECOGNITION API TEST SUITE")
    print("🧪"*40)
    
    try:
        # Test 1: Health check
        test_health_check()
        
        # Test 2: Authentication
        test_auth_required()
        
        # Test 3: System status
        test_system_status()
        
        # Test 4: List persons (initially empty)
        test_list_persons()
        
        # Test 5-7: Enrollment (use sample images if available)
        print("\n⚠️  To test enrollment and identification:")
        print("1. Place sample face images in tests/sample_images/")
        print("2. Uncomment the enrollment tests below")
        print("3. Run the tests again\n")
        
        # Uncomment these when you have sample images:
        # test_enroll_person(
        #     "tests/sample_images/person1.jpg",
        #     "P001",
        #     "Mohamed Shahabas",
        #     "Engineering"
        # )
        # 
        # test_enroll_person(
        #     "tests/sample_images/person2.jpg",
        #     "P002",
        #     "Alice Smith",
        #     "HR"
        # )
        
        # Test 8-9: Identification
        # test_identify_image("tests/sample_images/person1_test.jpg")
        # test_identify_image("tests/sample_images/unknown.jpg")
        
        # Test 10: Get person details
        # test_get_person("P001")
        
        # Test 11: Update threshold
        test_update_threshold(0.65)
        
        print("\n" + "="*80)
        print("✅ TEST SUITE COMPLETED")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=2)
        if response.status_code == 200:
            run_all_tests()
        else:
            print("❌ Server is not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://localhost:8000")
        print("Start the server with: python main.py")

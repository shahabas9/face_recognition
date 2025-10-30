"""
Test script for Detection Events API endpoints
Tests the new mobile app integration endpoints
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "testkey123"
HEADERS = {"X-API-Key": API_KEY}


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_response(response):
    """Pretty print response"""
    print(f"\nStatus Code: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)


def test_health():
    """Test health endpoint"""
    print_section("TEST 1: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)
    return response.status_code == 200


def test_detection_events_all():
    """Test getting all detection events"""
    print_section("TEST 2: Get All Detection Events (Last 24 hours)")
    
    params = {
        "hours": 24,
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(
        f"{BASE_URL}/detection_events",
        headers=HEADERS,
        params=params
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Found {data.get('total_count', 0)} total events")
        print(f"   Page {data.get('page', 1)} of {(data.get('total_count', 0) // data.get('page_size', 10)) + 1}")
        print(f"   Returned {len(data.get('events', []))} events on this page")
        return True
    return False


def test_detection_events_filtered_by_person():
    """Test filtering detection events by person_id"""
    print_section("TEST 3: Get Detection Events for Specific Person")
    
    # First, get any person_id from the database
    persons_response = requests.get(f"{BASE_URL}/persons", headers=HEADERS)
    if persons_response.status_code == 200:
        persons = persons_response.json()
        if persons:
            person_id = persons[0]['person_id']
            print(f"Testing with person_id: {person_id}")
            
            params = {
                "person_id": person_id,
                "hours": 168  # Last 7 days
            }
            
            response = requests.get(
                f"{BASE_URL}/detection_events",
                headers=HEADERS,
                params=params
            )
            print_response(response)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Found {data.get('total_count', 0)} events for {person_id}")
                return True
        else:
            print("⚠️  No persons enrolled yet. Skipping this test.")
            return True
    return False


def test_detection_events_filtered_by_camera():
    """Test filtering detection events by camera_id"""
    print_section("TEST 4: Get Detection Events for Specific Camera")
    
    # First check if there are any events
    check_response = requests.get(
        f"{BASE_URL}/detection_events",
        headers=HEADERS,
        params={"page_size": 1}
    )
    
    if check_response.status_code == 200:
        check_data = check_response.json()
        if check_data.get('events'):
            camera_id = check_data['events'][0]['camera_id']
            print(f"Testing with camera_id: {camera_id}")
            
            params = {
                "camera_id": camera_id,
                "hours": 48
            }
            
            response = requests.get(
                f"{BASE_URL}/detection_events",
                headers=HEADERS,
                params=params
            )
            print_response(response)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Found {data.get('total_count', 0)} events for camera {camera_id}")
                return True
        else:
            print("⚠️  No detection events exist yet. Skipping this test.")
            return True
    return False


def test_detection_events_pagination():
    """Test pagination"""
    print_section("TEST 5: Test Pagination")
    
    params = {
        "page": 1,
        "page_size": 5,
        "hours": 720  # Last 30 days
    }
    
    response = requests.get(
        f"{BASE_URL}/detection_events",
        headers=HEADERS,
        params=params
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        total_count = data.get('total_count', 0)
        page_size = data.get('page_size', 5)
        
        print(f"\n✅ Pagination working:")
        print(f"   Total events: {total_count}")
        print(f"   Page size: {page_size}")
        print(f"   Events on page 1: {len(data.get('events', []))}")
        
        # Test page 2 if there are enough events
        if total_count > page_size:
            print(f"\n   Testing page 2...")
            params['page'] = 2
            response2 = requests.get(
                f"{BASE_URL}/detection_events",
                headers=HEADERS,
                params=params
            )
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"   Events on page 2: {len(data2.get('events', []))}")
        
        return True
    return False


def test_latest_detection():
    """Test getting latest detection"""
    print_section("TEST 6: Get Latest Detection Event")
    
    response = requests.get(
        f"{BASE_URL}/detection_events/latest",
        headers=HEADERS
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Latest detection:")
        print(f"   Person: {data.get('person_name', 'Unknown')}")
        print(f"   Camera: {data.get('camera_id')}")
        print(f"   Location: {data.get('location', 'N/A')}")
        print(f"   Time: {data.get('timestamp')}")
        print(f"   Confidence: {data.get('confidence', 0) * 100:.1f}%")
        return True
    elif response.status_code == 404:
        print("\n⚠️  No detection events found (404). This is expected if no detections exist yet.")
        return True
    return False


def test_latest_detection_for_person():
    """Test getting latest detection for specific person"""
    print_section("TEST 7: Get Latest Detection for Specific Person")
    
    # Get a person_id first
    persons_response = requests.get(f"{BASE_URL}/persons", headers=HEADERS)
    if persons_response.status_code == 200:
        persons = persons_response.json()
        if persons:
            person_id = persons[0]['person_id']
            person_name = persons[0]['name']
            print(f"Testing with: {person_name} ({person_id})")
            
            params = {"person_id": person_id}
            response = requests.get(
                f"{BASE_URL}/detection_events/latest",
                headers=HEADERS,
                params=params
            )
            print_response(response)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Latest detection for {person_name}:")
                print(f"   Camera: {data.get('camera_id')}")
                print(f"   Time: {data.get('timestamp')}")
                return True
            elif response.status_code == 404:
                print(f"\n⚠️  No detections found for {person_name} (404)")
                return True
        else:
            print("⚠️  No persons enrolled. Skipping this test.")
            return True
    return False


def test_include_unknown():
    """Test including unknown person detections"""
    print_section("TEST 8: Get Detection Events Including Unknown Persons")
    
    params = {
        "include_unknown": True,
        "hours": 24,
        "page_size": 10
    }
    
    response = requests.get(
        f"{BASE_URL}/detection_events",
        headers=HEADERS,
        params=params
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        unknown_count = sum(1 for event in data.get('events', []) if event.get('is_unknown'))
        print(f"\n✅ Total events: {data.get('total_count', 0)}")
        print(f"   Unknown persons in results: {unknown_count}")
        return True
    return False


def test_time_range():
    """Test different time ranges"""
    print_section("TEST 9: Test Different Time Ranges")
    
    time_ranges = [1, 6, 24, 72, 168]  # 1 hour, 6 hours, 1 day, 3 days, 7 days
    
    for hours in time_ranges:
        params = {"hours": hours, "page_size": 1}
        response = requests.get(
            f"{BASE_URL}/detection_events",
            headers=HEADERS,
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('total_count', 0)
            print(f"   Last {hours:3d} hours: {count:4d} events")
    
    print("\n✅ Time range tests completed")
    return True


def test_response_structure():
    """Test response structure and data types"""
    print_section("TEST 10: Validate Response Structure")
    
    response = requests.get(
        f"{BASE_URL}/detection_events",
        headers=HEADERS,
        params={"page_size": 1}
    )
    
    if response.status_code == 200:
        data = response.json()
        
        # Check top-level structure
        assert 'status' in data, "Missing 'status' field"
        assert 'total_count' in data, "Missing 'total_count' field"
        assert 'page' in data, "Missing 'page' field"
        assert 'page_size' in data, "Missing 'page_size' field"
        assert 'events' in data, "Missing 'events' field"
        
        print("✅ Top-level structure valid")
        
        # Check event structure if events exist
        if data.get('events'):
            event = data['events'][0]
            required_fields = [
                'id', 'camera_id', 'is_unknown', 'timestamp'
            ]
            for field in required_fields:
                assert field in event, f"Missing required field: {field}"
            
            print("✅ Event structure valid")
            print("\nEvent fields present:")
            for key in event.keys():
                value_type = type(event[key]).__name__
                print(f"   - {key}: {value_type}")
        
        return True
    return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪" * 35)
    print("  DETECTION EVENTS API TEST SUITE")
    print("🧪" * 35)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Health Check", test_health),
        ("Get All Detection Events", test_detection_events_all),
        ("Filter by Person ID", test_detection_events_filtered_by_person),
        ("Filter by Camera ID", test_detection_events_filtered_by_camera),
        ("Pagination", test_detection_events_pagination),
        ("Get Latest Detection", test_latest_detection),
        ("Latest Detection for Person", test_latest_detection_for_person),
        ("Include Unknown Persons", test_include_unknown),
        ("Time Range Filtering", test_time_range),
        ("Response Structure Validation", test_response_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*70}\n")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        exit(1)

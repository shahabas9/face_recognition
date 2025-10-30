# 📱 Mobile Application Integration Guide

## Overview

This guide explains how to integrate the face recognition system with your mobile application. The system provides REST APIs to fetch identification events from IP webcam/video streams in real-time.

## 🎯 Use Cases

1. **Real-time Attendance Monitoring** - View who entered which location and when
2. **Security Dashboard** - Monitor all detection events across multiple cameras
3. **Person Tracking** - Track a specific person's movements across locations
4. **Access Control** - Get notified when specific persons are detected

## 🔌 API Endpoints for Mobile Apps

### Base URL
```
http://YOUR_SERVER_IP:8000/api/v1
```

### Authentication
All API requests (except `/health`) require authentication via API key header:
```
X-API-Key: your_api_key_here
```

---

## 📋 Detection Events API

### 1. Get Detection Events (Paginated List)

Retrieve detection events from video streams with comprehensive filtering options.

**Endpoint:** `GET /api/v1/detection_events`

**Query Parameters:**
- `person_id` (optional) - Filter by specific person ID
- `camera_id` (optional) - Filter by specific camera ID
- `location` (optional) - Filter by location name
- `hours` (optional, default: 24) - Get events from last N hours (max: 720)
- `include_unknown` (optional, default: false) - Include unknown person detections
- `page` (optional, default: 1) - Page number
- `page_size` (optional, default: 50, max: 500) - Items per page

**Example Requests:**

```bash
# Get all detections from last 24 hours
curl "http://localhost:8000/api/v1/detection_events" \
     -H "X-API-Key: testkey123"

# Get detections for specific person
curl "http://localhost:8000/api/v1/detection_events?person_id=P001" \
     -H "X-API-Key: testkey123"

# Get detections from specific camera in last 2 hours
curl "http://localhost:8000/api/v1/detection_events?camera_id=front-door&hours=2" \
     -H "X-API-Key: testkey123"

# Get detections with pagination
curl "http://localhost:8000/api/v1/detection_events?page=1&page_size=20" \
     -H "X-API-Key: testkey123"

# Get all detections including unknown persons
curl "http://localhost:8000/api/v1/detection_events?include_unknown=true" \
     -H "X-API-Key: testkey123"
```

**Response:**

```json
{
  "status": "ok",
  "total_count": 15,
  "page": 1,
  "page_size": 50,
  "events": [
    {
      "id": 123,
      "person_id": "P001",
      "person_name": "Mohamed Shahabas",
      "department": "Engineering",
      "camera_id": "front-door",
      "location": "Main Entrance",
      "confidence": 0.95,
      "embedding_distance": 0.18,
      "bounding_box": "[120, 85, 200, 250]",
      "is_unknown": false,
      "timestamp": "2025-10-14T10:30:45",
      "snapshot_url": "http://localhost:8000/snapshots/events/20251014_103045_P001.jpg",
      "request_source": "webcam"
    },
    {
      "id": 122,
      "person_id": "P002",
      "person_name": "John Doe",
      "department": "Sales",
      "camera_id": "reception",
      "location": "Reception Area",
      "confidence": 0.89,
      "embedding_distance": 0.25,
      "bounding_box": "[95, 70, 180, 230]",
      "is_unknown": false,
      "timestamp": "2025-10-14T10:25:12",
      "snapshot_url": "http://localhost:8000/snapshots/events/20251014_102512_P002.jpg",
      "request_source": "webcam"
    }
  ]
}
```

---

### 2. Get Latest Detection Event

Retrieve the most recent detection event. Useful for real-time dashboards and notifications.

**Endpoint:** `GET /api/v1/detection_events/latest`

**Query Parameters:**
- `camera_id` (optional) - Filter by specific camera ID
- `person_id` (optional) - Filter by specific person ID

**Example Requests:**

```bash
# Get latest detection from any camera
curl "http://localhost:8000/api/v1/detection_events/latest" \
     -H "X-API-Key: testkey123"

# Get latest detection for specific person
curl "http://localhost:8000/api/v1/detection_events/latest?person_id=P001" \
     -H "X-API-Key: testkey123"

# Get latest detection from specific camera
curl "http://localhost:8000/api/v1/detection_events/latest?camera_id=front-door" \
     -H "X-API-Key: testkey123"
```

**Response:**

```json
{
  "id": 123,
  "person_id": "P001",
  "person_name": "Mohamed Shahabas",
  "department": "Engineering",
  "camera_id": "front-door",
  "location": "Main Entrance",
  "confidence": 0.95,
  "embedding_distance": 0.18,
  "bounding_box": "[120, 85, 200, 250]",
  "is_unknown": false,
  "timestamp": "2025-10-14T10:30:45",
  "snapshot_url": "http://localhost:8000/snapshots/events/20251014_103045_P001.jpg",
  "request_source": "webcam"
}
```

**Error Response (404):**

```json
{
  "detail": "No detection events found matching criteria"
}
```

---

## 📸 Snapshot Images

Each detection event includes a `snapshot_url` field pointing to the captured image. You can:

1. **Display in mobile app** - Load the image URL directly in your image view
2. **Download for offline use** - Cache images locally
3. **Share/Export** - Allow users to share detection images

**Example:**
```
http://localhost:8000/snapshots/events/20251014_103045_P001.jpg
```

---

## 🔄 Polling vs WebSocket

### Polling (Recommended for Mobile)

Poll the `/detection_events/latest` endpoint every 5-10 seconds:

```javascript
// Pseudo-code
setInterval(async () => {
  const response = await fetch('http://server:8000/api/v1/detection_events/latest', {
    headers: { 'X-API-Key': 'testkey123' }
  });
  const event = await response.json();
  updateUI(event);
}, 5000); // Poll every 5 seconds
```

### Benefits of Polling
- Simple implementation
- Works with existing REST API
- Battery-efficient on mobile
- No persistent connection needed

---

## 📱 Mobile App Implementation Examples

### Flutter Example

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class DetectionService {
  final String baseUrl = 'http://YOUR_SERVER_IP:8000/api/v1';
  final String apiKey = 'testkey123';
  
  Future<List<DetectionEvent>> getDetectionEvents({
    String? personId,
    String? cameraId,
    int hours = 24,
    int page = 1,
    int pageSize = 50,
  }) async {
    final queryParams = {
      if (personId != null) 'person_id': personId,
      if (cameraId != null) 'camera_id': cameraId,
      'hours': hours.toString(),
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    
    final uri = Uri.parse('$baseUrl/detection_events')
        .replace(queryParameters: queryParams);
    
    final response = await http.get(
      uri,
      headers: {'X-API-Key': apiKey},
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['events'] as List)
          .map((e) => DetectionEvent.fromJson(e))
          .toList();
    } else {
      throw Exception('Failed to load detection events');
    }
  }
  
  Future<DetectionEvent?> getLatestDetection({
    String? cameraId,
    String? personId,
  }) async {
    final queryParams = {
      if (cameraId != null) 'camera_id': cameraId,
      if (personId != null) 'person_id': personId,
    };
    
    final uri = Uri.parse('$baseUrl/detection_events/latest')
        .replace(queryParameters: queryParams);
    
    final response = await http.get(
      uri,
      headers: {'X-API-Key': apiKey},
    );
    
    if (response.statusCode == 200) {
      return DetectionEvent.fromJson(json.decode(response.body));
    } else if (response.statusCode == 404) {
      return null; // No events found
    } else {
      throw Exception('Failed to load latest detection');
    }
  }
}

class DetectionEvent {
  final int id;
  final String? personId;
  final String? personName;
  final String? department;
  final String cameraId;
  final String? location;
  final double? confidence;
  final String timestamp;
  final String? snapshotUrl;
  
  DetectionEvent({
    required this.id,
    this.personId,
    this.personName,
    this.department,
    required this.cameraId,
    this.location,
    this.confidence,
    required this.timestamp,
    this.snapshotUrl,
  });
  
  factory DetectionEvent.fromJson(Map<String, dynamic> json) {
    return DetectionEvent(
      id: json['id'],
      personId: json['person_id'],
      personName: json['person_name'],
      department: json['department'],
      cameraId: json['camera_id'],
      location: json['location'],
      confidence: json['confidence']?.toDouble(),
      timestamp: json['timestamp'],
      snapshotUrl: json['snapshot_url'],
    );
  }
}
```

### React Native Example

```javascript
// DetectionService.js
const API_BASE_URL = 'http://YOUR_SERVER_IP:8000/api/v1';
const API_KEY = 'testkey123';

export const getDetectionEvents = async ({
  personId = null,
  cameraId = null,
  hours = 24,
  page = 1,
  pageSize = 50,
} = {}) => {
  const params = new URLSearchParams({
    ...(personId && { person_id: personId }),
    ...(cameraId && { camera_id: cameraId }),
    hours: hours.toString(),
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  
  const response = await fetch(`${API_BASE_URL}/detection_events?${params}`, {
    headers: {
      'X-API-Key': API_KEY,
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch detection events');
  }
  
  return await response.json();
};

export const getLatestDetection = async ({
  cameraId = null,
  personId = null,
} = {}) => {
  const params = new URLSearchParams({
    ...(cameraId && { camera_id: cameraId }),
    ...(personId && { person_id: personId }),
  });
  
  const url = `${API_BASE_URL}/detection_events/latest${params.toString() ? '?' + params : ''}`;
  
  const response = await fetch(url, {
    headers: {
      'X-API-Key': API_KEY,
    },
  });
  
  if (response.status === 404) {
    return null; // No events found
  }
  
  if (!response.ok) {
    throw new Error('Failed to fetch latest detection');
  }
  
  return await response.json();
};

// Usage in component
import React, { useState, useEffect } from 'react';
import { View, Text, Image, FlatList } from 'react-native';
import { getDetectionEvents } from './DetectionService';

const DetectionsList = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadEvents();
  }, []);
  
  const loadEvents = async () => {
    try {
      setLoading(true);
      const data = await getDetectionEvents({ hours: 24 });
      setEvents(data.events);
    } catch (error) {
      console.error('Error loading events:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const renderEvent = ({ item }) => (
    <View style={styles.eventCard}>
      {item.snapshot_url && (
        <Image
          source={{ uri: item.snapshot_url }}
          style={styles.snapshot}
        />
      )}
      <Text style={styles.name}>{item.person_name || 'Unknown'}</Text>
      <Text style={styles.location}>{item.location}</Text>
      <Text style={styles.confidence}>
        Confidence: {(item.confidence * 100).toFixed(1)}%
      </Text>
      <Text style={styles.timestamp}>{item.timestamp}</Text>
    </View>
  );
  
  return (
    <FlatList
      data={events}
      renderItem={renderEvent}
      keyExtractor={(item) => item.id.toString()}
      onRefresh={loadEvents}
      refreshing={loading}
    />
  );
};
```

### Swift (iOS) Example

```swift
import Foundation

struct DetectionEvent: Codable {
    let id: Int
    let personId: String?
    let personName: String?
    let department: String?
    let cameraId: String
    let location: String?
    let confidence: Double?
    let timestamp: String
    let snapshotUrl: String?
    
    enum CodingKeys: String, CodingKey {
        case id
        case personId = "person_id"
        case personName = "person_name"
        case department
        case cameraId = "camera_id"
        case location
        case confidence
        case timestamp
        case snapshotUrl = "snapshot_url"
    }
}

struct DetectionEventsResponse: Codable {
    let status: String
    let totalCount: Int
    let page: Int
    let pageSize: Int
    let events: [DetectionEvent]
    
    enum CodingKeys: String, CodingKey {
        case status
        case totalCount = "total_count"
        case page
        case pageSize = "page_size"
        case events
    }
}

class DetectionService {
    let baseURL = "http://YOUR_SERVER_IP:8000/api/v1"
    let apiKey = "testkey123"
    
    func getDetectionEvents(
        personId: String? = nil,
        cameraId: String? = nil,
        hours: Int = 24,
        page: Int = 1,
        pageSize: Int = 50,
        completion: @escaping (Result<DetectionEventsResponse, Error>) -> Void
    ) {
        var components = URLComponents(string: "\(baseURL)/detection_events")!
        components.queryItems = [
            URLQueryItem(name: "hours", value: String(hours)),
            URLQueryItem(name: "page", value: String(page)),
            URLQueryItem(name: "page_size", value: String(pageSize))
        ]
        
        if let personId = personId {
            components.queryItems?.append(URLQueryItem(name: "person_id", value: personId))
        }
        if let cameraId = cameraId {
            components.queryItems?.append(URLQueryItem(name: "camera_id", value: cameraId))
        }
        
        var request = URLRequest(url: components.url!)
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(NSError(domain: "No data", code: 0)))
                return
            }
            
            do {
                let response = try JSONDecoder().decode(DetectionEventsResponse.self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    func getLatestDetection(
        cameraId: String? = nil,
        personId: String? = nil,
        completion: @escaping (Result<DetectionEvent?, Error>) -> Void
    ) {
        var components = URLComponents(string: "\(baseURL)/detection_events/latest")!
        components.queryItems = []
        
        if let cameraId = cameraId {
            components.queryItems?.append(URLQueryItem(name: "camera_id", value: cameraId))
        }
        if let personId = personId {
            components.queryItems?.append(URLQueryItem(name: "person_id", value: personId))
        }
        
        var request = URLRequest(url: components.url!)
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(NSError(domain: "Invalid response", code: 0)))
                return
            }
            
            if httpResponse.statusCode == 404 {
                completion(.success(nil))
                return
            }
            
            guard let data = data else {
                completion(.failure(NSError(domain: "No data", code: 0)))
                return
            }
            
            do {
                let event = try JSONDecoder().decode(DetectionEvent.self, from: data)
                completion(.success(event))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}
```

---

## 🎨 UI/UX Recommendations

### Detection Event Card
- **Show snapshot image** prominently
- **Person name** as title
- **Confidence score** as badge (color-coded: green > 90%, yellow 70-90%, red < 70%)
- **Location and camera** as subtitle
- **Timestamp** in relative format ("2 minutes ago")

### Real-time Dashboard
- **Auto-refresh** every 5-10 seconds
- **Pull-to-refresh** gesture
- **Filter options** (by person, camera, location, time range)
- **Search functionality**

### Notifications
- Push notification when specific person detected
- In-app notification for real-time events
- Configurable notification preferences

---

## 🔐 Security Best Practices

1. **Store API key securely** - Use encrypted storage (Keychain on iOS, Keystore on Android)
2. **Use HTTPS** - Always use SSL/TLS in production
3. **Implement token refresh** - Consider JWT tokens for better security
4. **Validate responses** - Check status codes and handle errors gracefully
5. **Rate limiting** - Implement client-side rate limiting to avoid overwhelming the server

---

## 📊 Performance Optimization

1. **Image caching** - Cache snapshot images locally to reduce bandwidth
2. **Lazy loading** - Load images on-demand as user scrolls
3. **Pagination** - Use appropriate page sizes (20-50 items)
4. **Incremental updates** - Only fetch new events since last update
5. **Background refresh** - Use background tasks for periodic updates

---

## 🧪 Testing

### Test with cURL

```bash
# Set your API key
API_KEY="testkey123"
BASE_URL="http://localhost:8000/api/v1"

# Test detection events endpoint
curl "${BASE_URL}/detection_events?hours=24" \
     -H "X-API-Key: ${API_KEY}" | jq

# Test latest detection endpoint
curl "${BASE_URL}/detection_events/latest" \
     -H "X-API-Key: ${API_KEY}" | jq
```

### Sample Test Data

If you need to generate test data, you can trigger detections by:
1. Enrolling test persons via `/api/v1/enroll_person`
2. Setting up IP webcam stream
3. Showing enrolled person's photo to the webcam

---

## 📞 Support & Troubleshooting

### Common Issues

**404 Error on latest detection:**
- No detection events exist in the database
- Filters are too restrictive (no matching events)

**Empty events array:**
- No events in the specified time range
- Check `hours` parameter

**Snapshot images not loading:**
- Verify server is running
- Check firewall/network settings
- Ensure snapshots directory has proper permissions

### API Documentation

Visit the interactive API documentation at:
```
http://YOUR_SERVER_IP:8000/docs
```

---

## 🎯 Next Steps

1. ✅ Integrate detection events API in your mobile app
2. ✅ Implement real-time polling/updates
3. ✅ Add filtering and search functionality
4. ✅ Display snapshot images
5. ✅ Implement push notifications
6. ✅ Add offline support with local caching

---

**For more information, see:**
- [README.md](README.md) - System overview
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation guide
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

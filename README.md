# 🎯 Person Identification System

Real-time face recognition system with IP webcam support and REST API for mobile app integration. Built with FastAPI, FaceNet, and MySQL.

## ✨ Features

- 📸 **Image-based Identification** - Upload images via REST API to identify persons
- 👤 **Person Enrollment** - Easy enrollment via API or web interface
- 📹 **IP Webcam Support** - Real-time processing from mobile phone cameras (IP Webcam app)
- 💾 **Event Logging** - Track all detections with snapshots and metadata
- 📱 **Detection Events API** - Fetch identification events from video streams for mobile apps
- 🔒 **API Authentication** - Secure API access with API keys
- 🚀 **Fast Performance** - ~300ms identification latency in typical setups
- 🐳 **Docker Support** - Easy deployment with Docker Compose
- 📲 **Mobile-Ready** - RESTful API with comprehensive mobile integration guide

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Face Detection**: MTCNN
- **Face Recognition**: FaceNet (VGGFace2 pretrained)
- **Database**: MySQL
- **Storage**: Local filesystem (S3-compatible storage ready)
- **Deployment**: Docker, Docker Compose

## 📋 Requirements

### System Requirements
- Python 3.10+
- MySQL 8.0+
- 4GB+ RAM recommended
- macOS or Linux

### Python Dependencies
See `requirements.txt` for complete list.

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd /Users/shahabas/work/face_recognition

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Key settings to update:**
- `MYSQL_PASSWORD` - Your MySQL password
- `API_KEY` - Your API key for authentication
- `IP_WEBCAM_URL` - Your mobile phone's IP webcam URL

### 3. Setup Database

```bash
# Create MySQL database
mysql -u root -p

# In MySQL shell:
CREATE DATABASE face_recognition CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '2cloud'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON face_recognition.* TO '2cloud'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Run the Application

```bash
# Start the server
python main.py
```

The server will start on `http://localhost:8000`

**Access points:**
- 🌐 **Web Interface**: http://localhost:8000
- 📚 **API Documentation**: http://localhost:8000/docs
- 🧪 **Test Interface**: http://localhost:8000/test

## 🐳 Docker Deployment

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## 📱 IP Webcam Setup

### Mobile Phone Setup

1. **Install IP Webcam App**
   - Android: [IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)
   - iOS: [IP Camera Lite](https://apps.apple.com/app/ip-camera-lite/id1013455241)

2. **Start the Server**
   - Open the app
   - Scroll down and tap "Start Server"
   - Note the IP address (e.g., `http://192.168.1.100:8080`)

3. **Configure the System**
   - Edit `config/ip_webcam_config.py`
   - Update the `mjpeg_url` with your camera's IP
   - Set `enabled: True` for the camera

4. **Restart the Application**
   ```bash
   python main.py
   ```

The system will automatically start processing frames from your mobile camera!

## 🔌 API Usage

### Authentication

Include API key in header for protected endpoints:
```bash
X-API-Key: testkey123
```

### Example Requests

#### 1. Enroll a Person

```bash
curl -X POST http://localhost:8000/api/v1/enroll_person \
  -H "X-API-Key: testkey123" \
  -F "name=Mohamed Shahabas" \
  -F "person_id=P001" \
  -F "department=Engineering" \
  -F "image=@photo.jpg"
```

**Response:**
```json
{
  "status": "ok",
  "person_id": "P001",
  "name": "Mohamed Shahabas",
  "message": "Successfully enrolled Mohamed Shahabas",
  "embedding_created": true,
  "snapshot_saved": true
}
```

#### 2. Identify Person from Image

```bash
curl -X POST http://localhost:8000/api/v1/identify_image \
  -H "X-API-Key: testkey123" \
  -F "image=@test_photo.jpg" \
  -F "camera_id=mobile-test-1"
```

**Response (Identified):**
```json
{
  "status": "ok",
  "timestamp": "2025-10-14T11:00:00+05:30",
  "camera_id": "mobile-test-1",
  "result": {
    "person_id": "P001",
    "name": "Mohamed Shahabas",
    "confidence": 0.92,
    "embedding_distance": 0.24,
    "bounding_box": [120, 85, 200, 250],
    "snapshot_url": "http://localhost:8000/snapshots/events/2025-10-14/api_20251014_110000_P001_mobile-test-1_abc123.jpg"
  }
}
```

**Response (Unknown):**
```json
{
  "status": "ok",
  "timestamp": "2025-10-14T11:00:00+05:30",
  "camera_id": "mobile-test-1",
  "result": {
    "person_id": null,
    "name": null,
    "confidence": 0.0,
    "embedding_distance": null,
    "bounding_box": null,
    "snapshot_url": "http://localhost:8000/snapshots/events/2025-10-14/unknown_20251014_110000_mobile-test-1_xyz789.jpg"
  }
}
```

#### 3. Get Person Details

```bash
curl -X GET http://localhost:8000/api/v1/person/P001 \
  -H "X-API-Key: testkey123"
```

#### 4. List All Persons

```bash
curl -X GET http://localhost:8000/api/v1/persons \
  -H "X-API-Key: testkey123"
```

#### 5. System Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## 📖 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/identify_image` | Identify person from image | ✅ |
| `POST` | `/api/v1/enroll_person` | Enroll new person | ✅ |
| `GET` | `/api/v1/person/{person_id}` | Get person details | ✅ |
| `GET` | `/api/v1/persons` | List all persons | ✅ |
| `DELETE` | `/api/v1/person/{person_id}` | Delete/deactivate person | ✅ |
| `GET` | `/api/v1/detection_events` | Get detection events from video streams 🆕 | ✅ |
| `GET` | `/api/v1/detection_events/latest` | Get latest detection event 🆕 | ✅ |
| `GET` | `/api/v1/health` | Health check | ❌ |
| `GET` | `/api/v1/status` | System status | ✅ |
| `POST` | `/api/v1/threshold` | Update recognition threshold | ✅ |
| `POST` | `/api/v1/reload_persons` | Reload persons cache | ✅ |
| `POST` | `/api/v1/cleanup_snapshots` | Clean old snapshots | ✅ |

### 🆕 Detection Events API (For Mobile Apps)

The new detection events endpoints allow mobile apps to retrieve identification events from video streams:

```bash
# Get all detections from last 24 hours
curl "http://localhost:8000/api/v1/detection_events" \
  -H "X-API-Key: testkey123"

# Get detections for specific person
curl "http://localhost:8000/api/v1/detection_events?person_id=P001&hours=48" \
  -H "X-API-Key: testkey123"

# Get latest detection
curl "http://localhost:8000/api/v1/detection_events/latest" \
  -H "X-API-Key: testkey123"
```

**For complete mobile integration guide, see:** [MOBILE_APP_INTEGRATION.md](MOBILE_APP_INTEGRATION.md)

## 🧪 Testing

### Run API Tests

```bash
# Make sure server is running first
python main.py

# In another terminal:
python tests/test_api.py
```

### Test with Sample Images

```bash
# Create sample images directory
mkdir -p tests/sample_images

# Add test images, then run
python tests/test_webcam_simulation.py
```

### Use Postman Collection

1. Import `postman_collection.json` into Postman
2. Set the `base_url` variable to `http://localhost:8000`
3. Update the API key if changed
4. Start testing!

### cURL Examples

```bash
# Make executable
chmod +x curl_examples.sh

# Run examples
./curl_examples.sh
```

## ⚙️ Configuration

### Key Configuration Files

- `config/settings.py` - Main application settings
- `config/ip_webcam_config.py` - IP webcam sources
- `.env` - Environment variables (create from `.env.example`)

### Important Settings

```python
# Recognition threshold (0.0 - 1.0)
# Higher = more strict matching
RECOGNITION_THRESHOLD = 0.6

# Minimum face size to detect (pixels)
MIN_FACE_SIZE = 60

# Event cooldown (seconds)
# Prevents duplicate events for same person
EVENT_COOLDOWN_SECONDS = 30

# Force CPU usage (set to false to use GPU if available)
FORCE_CPU = true
```

## 📁 Project Structure

```
face_recognition/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── identify.py      # Identification endpoints
│   │           ├── enroll.py        # Enrollment endpoints
│   │           └── system.py        # System management
│   ├── core/
│   │   └── security.py              # API authentication
│   ├── models/
│   │   └── database.py              # Database models
│   ├── schemas/
│   │   └── requests.py              # Pydantic schemas
│   └── services/
│       ├── face_recognition_service.py
│       ├── ip_webcam_service.py
│       └── storage_service.py
├── config/
│   ├── settings.py                  # Main configuration
│   └── ip_webcam_config.py          # Webcam sources
├── tests/
│   ├── test_api.py                  # API tests
│   └── test_webcam_simulation.py    # Webcam simulation
├── snapshots/                       # Stored snapshots
├── logs/                            # Application logs
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── docker-compose.yml               # Docker setup
├── Dockerfile                       # Docker image
└── README.md                        # This file
```

## 🔧 Troubleshooting

### Database Connection Issues

```bash
# Check MySQL is running
mysql -u 2cloud -p

# Verify database exists
SHOW DATABASES;

# Check connection settings in .env
```

### IP Webcam Not Connecting

1. Ensure phone and computer are on same WiFi network
2. Check firewall isn't blocking the connection
3. Verify the IP address and port in config
4. Test URL in browser: `http://<phone-ip>:8080`

### Face Not Detected

- Ensure good lighting
- Face should be clearly visible and forward-facing
- Minimum face size: 60x60 pixels
- Try adjusting `DETECTION_CONFIDENCE` in settings

### Low Recognition Accuracy

- Adjust `RECOGNITION_THRESHOLD` (default: 0.6)
- Enroll multiple photos of the same person
- Ensure enrollment photos are high quality
- Check lighting conditions match between enrollment and identification

## 📊 Performance

### Benchmarks (on Apple M3 / Modern Hardware)

- Face Detection: ~50-100ms
- Embedding Extraction: ~100-150ms
- Anti-Spoofing Analysis: ~50-150ms (if enabled)
- Database Lookup: ~10-20ms
- **Total Identification Time**: ~200-300ms (without anti-spoofing)
- **Total Identification Time**: ~300-400ms (with anti-spoofing)

### Optimization Tips

1. **Use GPU**: Set `FORCE_CPU=false` if GPU available
2. **Reduce FPS**: Lower `PROCESS_FPS` for webcam processing
3. **Database Indexing**: Already optimized with indexes
4. **Caching**: Person embeddings cached in memory

## 🔒 Security Best Practices

1. **Change Default API Key**
   ```bash
   # In .env
   API_KEY=your_secure_random_key_here
   REQUIRE_AUTH=true
   ```

2. **Use HTTPS in Production**
3. **Use HTTPS in Production**
   - Deploy behind nginx/Apache with SSL
   - Use Let's Encrypt for free SSL certificates

4. **Database Security**
   - Use strong MySQL passwords
   - Restrict network access to MySQL
   - Regular backups

5. **Privacy Compliance**
   - Store only necessary data
   - Implement data retention policies
   - Provide data deletion capabilities
   - Comply with GDPR/local privacy laws

## 🤝 Support & Contributing

### Getting Help

- Check the [API Documentation](http://localhost:8000/docs)
- Review test scripts for usage examples
- Check logs in `logs/app.log`

### Known Issues

- MPS (Apple Silicon) has compatibility issues with some PyTorch operations - CPU mode is forced for stability
- RTSP streams may have reconnection issues - MJPEG is more stable

## 📝 License

This project is for internal use. Ensure compliance with face recognition laws in your jurisdiction.

## 🎓 Credits

- **FaceNet**: Face recognition model
- **MTCNN**: Face detection
- **FastAPI**: Web framework
- **IP Webcam App**: Mobile camera streaming

---

**Made with ❤️ for secure and efficient person identification**

# 🚀 Setup Guide - Face Recognition System

Complete step-by-step guide to get your Face Recognition System up and running.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] macOS or Linux operating system
- [ ] Python 3.10 or higher
- [ ] MySQL 8.0 or higher
- [ ] 4GB+ RAM
- [ ] Internet connection (for downloading models)
- [ ] (Optional) Mobile phone for IP webcam

---

## 🛠️ Installation Steps

### Step 1: Verify Python Installation

```bash
python3 --version
# Should show Python 3.10.x or higher
```

If Python is not installed or version is too old:
- **macOS**: `brew install python@3.10`
- **Linux**: `sudo apt-get install python3.10`

### Step 2: Verify MySQL Installation

```bash
mysql --version
# Should show MySQL 8.0.x or higher
```

If MySQL is not installed:

**macOS:**
```bash
brew install mysql
brew services start mysql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

### Step 3: Setup MySQL Database

```bash
# Connect to MySQL
mysql -u root -p
# Enter your MySQL root password
```

Run these SQL commands:
```sql
-- Create database
CREATE DATABASE face_recognition CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (change password!)
CREATE USER '2cloud'@'localhost' IDENTIFIED BY 'shahabas@2cloud';

-- Grant privileges
GRANT ALL PRIVILEGES ON face_recognition.* TO '2cloud'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
SELECT user FROM mysql.user WHERE user='2cloud';

-- Exit
EXIT;
```

### Step 4: Setup Python Virtual Environment

```bash
# Navigate to project directory
cd /Users/shahabas/work/face_recognition

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# You should see (venv) in your terminal prompt

# Upgrade pip
pip install --upgrade pip
```

### Step 5: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# This will take 5-10 minutes and install:
# - FastAPI and uvicorn
# - PyTorch and torchvision
# - FaceNet-PyTorch
# - OpenCV
# - SQLAlchemy and MySQL connectors
# - And more...
```

**Note**: On Apple Silicon (M1/M2/M3), torch may take longer to install.

### Step 6: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit the file
nano .env  # or use your preferred editor
```

**Important settings to update in `.env`:**

```bash
# Database (MUST UPDATE)
MYSQL_PASSWORD=your_actual_mysql_password

# API Security (RECOMMENDED TO CHANGE)
API_KEY=your_secure_random_api_key_here
REQUIRE_AUTH=true

# IP Webcam (UPDATE WHEN READY)
IP_WEBCAM_URL=http://192.168.1.100:8080/video

# Keep these as default for now
RECOGNITION_THRESHOLD=0.6
FORCE_CPU=true
```

Save and exit (Ctrl+X, then Y, then Enter in nano).

### Step 7: Run Setup Script (Optional)

```bash
# Run automated setup
python setup.py

# This will:
# - Check Python and MySQL
# - Create necessary directories
# - Create .env file
# - Test imports
```

### Step 8: Initialize Database Tables

The tables will be created automatically when you first run the application.

### Step 9: Start the Application

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
python main.py
```

You should see:
```
================================================================================
🎯 PERSON IDENTIFICATION SYSTEM
================================================================================
📍 API Version: 1.0.0
⏰ Started at: 2025-10-14 11:00:00
================================================================================

✅ System initialized
📊 Total persons enrolled: 0
🌐 API Server: http://0.0.0.0:8000
📚 API Documentation: http://0.0.0.0:8000/docs
🧪 Test Interface: http://0.0.0.0:8000/test
================================================================================
```

---

## ✅ Verify Installation

### 1. Check Health Endpoint

```bash
curl http://localhost:8000/api/v1/health
```

Should return:
```json
{
  "status": "healthy",
  "total_persons": 0,
  "active_persons": 0,
  "device": "cpu",
  "system": "FastAPI + FaceNet + InsightFace",
  "database": "MySQL",
  "webcam_active": false,
  "api_version": "1.0.0"
}
```

### 2. Access Web Interface

Open your browser and go to:
- http://localhost:8000 - Main page
- http://localhost:8000/docs - API documentation
- http://localhost:8000/test - Test interface

### 3. Test API with Authentication

```bash
curl http://localhost:8000/api/v1/status \
  -H "X-API-Key: testkey123"
```

---

## 👤 Enroll Your First Person

### Option 1: Using Test Interface (Easiest)

1. Open http://localhost:8000/test
2. Click "Enroll Person" tab
3. Fill in:
   - Name: Your Name
   - Person ID: P001 (or leave empty for auto-generation)
   - Department: (optional)
4. Upload a clear face photo
5. Click "Enroll Person"

### Option 2: Using cURL

```bash
# Prepare a photo (make sure face is clearly visible)
# Then run:

curl -X POST http://localhost:8000/api/v1/enroll_person \
  -H "X-API-Key: testkey123" \
  -F "name=Mohamed Shahabas" \
  -F "person_id=P001" \
  -F "department=Engineering" \
  -F "image=@/path/to/your/photo.jpg"
```

---

## 🔍 Test Identification

### Option 1: Using Test Interface

1. Open http://localhost:8000/test
2. Stay on "Identify Person" tab
3. Upload a photo (ideally of the person you enrolled)
4. Click "Identify Person"
5. Check the result

### Option 2: Using cURL

```bash
curl -X POST http://localhost:8000/api/v1/identify_image \
  -H "X-API-Key: testkey123" \
  -F "image=@/path/to/test_photo.jpg" \
  -F "camera_id=mobile-test-1"
```

---

## 📱 Setup IP Webcam (Optional)

### For Android Phones

1. **Install App**
   - Open Google Play Store
   - Search for "IP Webcam"
   - Install "IP Webcam" by Pavel Khlebovich

2. **Configure App**
   - Open IP Webcam app
   - Scroll down
   - Tap "Start Server"
   - Note the URL shown (e.g., `http://192.168.1.100:8080`)

3. **Update Configuration**
   ```bash
   # Edit config file
   nano config/ip_webcam_config.py
   ```
   
   Update:
   ```python
   IP_WEBCAM_SOURCES = {
       "mobile_webcam_1": {
           "name": "Mobile Phone - Main Entrance",
           "enabled": True,  # Set to True
           "mjpeg_url": "http://192.168.1.100:8080/video",  # Your phone's IP
           "camera_id": "mobile-entrance-1",
           "location": "Main Entrance",
           "use_rtsp": False,
           "fps_limit": 5,
       }
   }
   ```

4. **Restart Application**
   ```bash
   # Stop the server (Ctrl+C)
   # Start again
   python main.py
   ```

### For iOS Phones

1. **Install App**
   - Open App Store
   - Search for "IP Camera Lite"
   - Install the app

2. Follow similar steps as Android above

---

## 🐳 Docker Setup (Alternative)

If you prefer Docker:

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

---

## 🧪 Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run API tests
python tests/test_api.py

# Run webcam simulation (requires test images)
python tests/test_webcam_simulation.py
```

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to MySQL"

**Solution:**
1. Check MySQL is running: `mysql -u 2cloud -p`
2. Verify password in `.env` matches MySQL user password
3. Check database exists: `SHOW DATABASES;` in MySQL

### Issue: "No face detected"

**Solution:**
1. Ensure photo has a clear, forward-facing face
2. Check lighting is good
3. Face should be at least 60x60 pixels
4. Try a different photo

### Issue: "Module not found"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in .env
API_PORT=8001
```

### Issue: "Models downloading slowly"

**Solution:**
- First run downloads FaceNet models (~100MB)
- This is normal and only happens once
- Be patient, it may take 5-10 minutes

---

## 📊 Performance Tips

1. **Use GPU** (if available):
   ```bash
   # In .env
   FORCE_CPU=false
   ```

2. **Adjust Recognition Threshold**:
   ```bash
   # Lower = more lenient, Higher = more strict
   RECOGNITION_THRESHOLD=0.55  # More lenient
   RECOGNITION_THRESHOLD=0.70  # More strict
   ```

3. **Optimize Webcam Processing**:
   ```python
   # In config/ip_webcam_config.py
   "fps_limit": 2,  # Process fewer frames per second
   ```

---

## 🔒 Security Hardening

### For Production Deployment:

1. **Change API Key**:
   ```bash
   # Generate strong random key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Update in .env
   API_KEY=your_generated_key_here
   REQUIRE_AUTH=true
   ```

2. **Use HTTPS**:
   - Deploy behind nginx with SSL
   - Use Let's Encrypt for free certificates

3. **Secure MySQL**:
   ```bash
   # Run MySQL security script
   sudo mysql_secure_installation
   ```

4. **Firewall Rules**:
   ```bash
   # Allow only necessary ports
   sudo ufw allow 8000/tcp
   sudo ufw enable
   ```

---

## 📞 Next Steps

1. ✅ Enroll multiple people
2. ✅ Test identification accuracy
3. ✅ Setup IP webcam for real-time detection
4. ✅ Integrate with your mobile app
5. ✅ Deploy to production server
6. ✅ Setup automated backups

---

## 💡 Tips for Best Results

### Good Enrollment Photos:
- ✅ Clear, high-resolution
- ✅ Good lighting
- ✅ Face centered and forward-facing
- ✅ Neutral expression
- ✅ No sunglasses or hats

### Bad Enrollment Photos:
- ❌ Blurry or low quality
- ❌ Poor lighting
- ❌ Face turned away
- ❌ Partial face visible
- ❌ Heavy shadows

---

**Need help?** Check the main README.md or review the API documentation at http://localhost:8000/docs

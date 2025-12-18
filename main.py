"""
Face Recognition System - Main Application
Supports IP Webcam integration and REST API for mobile apps
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    API_TITLE,
    API_VERSION,
    API_HOST,
    API_PORT,
    CORS_ORIGINS,
    LOG_LEVEL,
    LOG_FORMAT,
    LOGS_DIR,
    SNAPSHOTS_DIR,
    get_device
)
from app.models import create_tables
from app.services import (
    FaceRecognitionService,
    StorageService,
    IPWebcamManager,
)
from app.api.v1 import api_router
from app.api.v1.endpoints import identify, enroll_old as enroll, enroll_s3, system

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "app.log")
    ]
)
logger = logging.getLogger(__name__)

# Global service instances
face_service: FaceRecognitionService = None
storage_service: StorageService = None
webcam_manager: IPWebcamManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Face Recognition System")
    
    print("\n" + "="*80)
    print("🎯 PERSON IDENTIFICATION SYSTEM v2.0")
    print("="*80)
    print(f"📍 API Version: {API_VERSION}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🖥️  Device: {get_device().upper()}")
    print("="*80)
    
    print("\n📊 Initializing database...")
    create_tables()
    
    # Initialize services
    global face_service, storage_service, webcam_manager
    
    
    
    
    print("🔧 Initializing Face Recognition Service...")
    face_service = FaceRecognitionService()

    print("💾 Initializing Storage Service...")
    storage_service = StorageService()

    print("📹 Initializing IP Webcam Manager...")
    webcam_manager = IPWebcamManager(face_service, storage_service)

    # Inject services into API endpoints
    identify.set_services(face_service, storage_service)
    enroll.set_services(face_service, storage_service)
    enroll_s3.set_services(face_service, storage_service)
    system.set_services(face_service, storage_service, webcam_manager)
    
    # Start webcam processors
    print("🎥 Starting webcam processors...")
    webcam_manager.start_all()
    
    print("\n✅ SYSTEM INITIALIZED")
    print("="*80)
    print(f"📊 Total persons enrolled: {len(face_service.person_ids)}")
    print(f"🌐 API Server: http://{API_HOST}:{API_PORT}")
    print(f"📚 API Documentation: http://{API_HOST}:{API_PORT}/docs")
    print(f"🧪 Test Interface: http://{API_HOST}:{API_PORT}/test")
    print("="*80 + "\n")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    if webcam_manager:
        webcam_manager.stop_all()
    print("\n🛑 System shutdown complete\n")


# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description="""
    ## Person Identification System
    
    Real-time face recognition with IP webcam support.
    
    ### ✨ Core Features:
    - 📸 Identify persons from uploaded images
    - 👤 Enroll new persons via API
    - 📹 Real-time detection from IP webcams (mobile phones)
    - 💾 Event logging and snapshot storage
    - 🔒 API key authentication
    
    ### 🚀 Quick Start:
    1. Enroll a person: `POST /api/v1/enroll_person`
    2. Identify from image: `POST /api/v1/identify_image`
    3. Check system health: `GET /api/v1/health`
    
    ### 🔐 Authentication:
    Include header: `X-API-Key: testkey123`
    """,
    version=API_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for snapshots
app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with system information"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Person Identification System</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ color: #667eea; margin-top: 0; }}
            h2 {{ color: #764ba2; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .badge {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                margin: 0 5px;
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .feature {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }}
            .feature strong {{
                display: block;
                margin-bottom: 10px;
                color: #667eea;
            }}
            .endpoint {{
                background: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-radius: 6px;
                border-left: 4px solid #667eea;
            }}
            .method {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
                margin-right: 10px;
                font-size: 12px;
            }}
            .post {{ background: #28a745; color: white; }}
            .get {{ background: #007bff; color: white; }}
            code {{
                background: #2d3748;
                color: #68d391;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 14px;
            }}
            a {{ color: #667eea; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Person Identification System v2.0</h1>
            <p>
                <span class="badge">FastAPI</span>
                <span class="badge">FaceNet</span>
                <span class="badge">IP Webcam</span>
                <span class="badge">MySQL</span>
            </p>
            
            <h2>📚 Documentation</h2>
            <div class="endpoint">
                <a href="/docs" target="_blank">🔷 Interactive API Documentation (Swagger UI)</a>
            </div>
            <div class="endpoint">
                <a href="/redoc" target="_blank">🔷 Alternative API Documentation (ReDoc)</a>
            </div>
            <div class="endpoint">
                <a href="/test" target="_blank">🔷 Test Interface</a>
            </div>
            
            <h2>🔌 Key API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/v1/identify_image</code>
                <p>Identify person from image</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/v1/enroll_person</code>
                <p>Enroll new person</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/person/{{person_id}}</code>
                <p>Get person details by ID</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/health</code>
                <p>System health check</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/status</code>
                <p>Detailed system status</p>
            </div>
            
            <h2>🧪 Quick Test</h2>
            <pre style="background:#2d3748;color:#68d391;padding:20px;border-radius:6px;overflow-x:auto;">
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Enroll a person
curl -X POST http://localhost:8000/api/v1/enroll_person \
     -H "X-API-Key: testkey123" \
     -F "name=John Doe" \
     -F "person_id=P001" \
     -F "image=@photo.jpg"

# Identify person
curl -X POST http://localhost:8000/api/v1/identify_image \
     -H "X-API-Key: testkey123" \
     -F "image=@test_photo.jpg" \
     -F "camera_id=mobile-test-1"
            </pre>
            
            <h2>📹 IP Webcam Setup</h2>
            <ol>
                <li>Install "IP Webcam" app on Android or "IP Camera Lite" on iOS</li>
                <li>Start the server in the app (note the IP address)</li>
                <li>Update <code>config/ip_webcam_config.py</code> with your camera IP</li>
                <li>Restart the system to start processing webcam stream</li>
            </ol>
        </div>
    </body>
    </html>
    """


@app.get("/test", response_class=HTMLResponse)
async def test_interface():
    """Test interface for uploading images"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Interface - Person Identification</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #f5f7fa;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            h1 { color: #2d3748; margin-top: 0; }
            h2 { color: #4a5568; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                font-weight: 600;
                margin-bottom: 8px;
                color: #4a5568;
            }
            input[type="text"], input[type="file"], select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                font-size: 14px;
                box-sizing: border-box;
            }
            input[type="file"] {
                padding: 10px;
            }
            button {
                background: #667eea;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin-right: 10px;
                margin-bottom: 10px;
            }
            button:hover {
                background: #5a67d8;
            }
            button:disabled {
                background: #cbd5e0;
                cursor: not-allowed;
            }
            .btn-secondary {
                background: #718096;
            }
            .btn-secondary:hover {
                background: #4a5568;
            }
            .response {
                margin-top: 30px;
                padding: 20px;
                border-radius: 6px;
                display: none;
            }
            .success {
                background: #f0fdf4;
                border: 2px solid #86efac;
                color: #166534;
            }
            .error {
                background: #fef2f2;
                border: 2px solid #fca5a5;
                color: #991b1b;
            }
            .warning {
                background: #fffbeb;
                border: 2px solid #fcd34d;
                color: #92400e;
            }
            pre {
                background: #2d3748;
                color: #68d391;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                white-space: pre-wrap;
                font-size: 12px;
            }
            .tabs {
                display: flex;
                border-bottom: 2px solid #e2e8f0;
                margin-bottom: 20px;
            }
            .tab {
                padding: 12px 24px;
                cursor: pointer;
                border-bottom: 3px solid transparent;
                font-weight: 600;
                color: #718096;
            }
            .tab.active {
                color: #667eea;
                border-bottom-color: #667eea;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            
            /* Webcam styles */
            .webcam-container {
                margin-top: 10px;
                background: #000;
                border-radius: 8px;
                overflow: hidden;
                width: 100%;
                max-width: 640px;
                position: relative;
            }
            video {
                width: 100%;
                display: block;
            }
            .thumbnails {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 15px;
            }
            .thumbnail {
                width: 100px;
                height: 100px;
                object-fit: cover;
                border-radius: 6px;
                border: 2px solid #e2e8f0;
            }
            .thumbnail.captured {
                border-color: #48bb78;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 Test Interface</h1>
            <p style="color: #666; margin: 20px 0;">
                Use this interface to test identification and enrollment operations quickly.
            </p>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('identify')">Identify Person</div>
                <div class="tab" onclick="showTab('enroll')">Enroll Person</div>
            </div>
            
            <!-- Identify Tab -->
            <div id="identify-tab" class="tab-content active">
                <h2>📸 Identify Person from Image</h2>
                <form id="identifyForm" onsubmit="identifyPerson(event)">
                    <div class="form-group">
                        <label>Camera ID</label>
                        <input type="text" id="camera_id" value="mobile-test-1" required>
                    </div>
                    <div class="form-group">
                        <label>Upload Image</label>
                        <input type="file" id="identify_image" accept="image/*" required onchange="previewImage(this, 'identifyPreview')">
                        <img id="identifyPreview" style="display:none;max-width:400px;margin-top:15px;border-radius:6px;">
                    </div>
                    <button type="submit">🔍 Identify Person</button>
                </form>
                
                <div id="identifyResponse" class="response"></div>
            </div>
            
            <!-- Enroll Tab -->
            <div id="enroll-tab" class="tab-content">
                <h2>👤 Enroll New Person</h2>
                <form id="enrollForm" onsubmit="enrollPerson(event)">
                    <div class="form-group">
                        <label>Full Name *</label>
                        <input type="text" id="name" placeholder="e.g., Mohamed Shahabas" required>
                    </div>
                    <div class="form-group">
                        <label>Person ID (optional, auto-generated if empty)</label>
                        <input type="text" id="person_id" placeholder="e.g., P001">
                    </div>
                    <div class="form-group">
                        <label>Department (optional)</label>
                        <input type="text" id="department" placeholder="e.g., Engineering">
                    </div>
                    
                    <div class="form-group">
                        <label>Capture Face Images (5 required) *</label>
                        <div class="webcam-controls">
                            <button type="button" class="btn-secondary" onclick="startCamera()">📷 Start Camera</button>
                            <button type="button" id="captureBtn" onclick="captureImages()" disabled>📸 Capture 5 Images</button>
                        </div>
                        
                        <div class="webcam-container" id="webcamContainer" style="display:none;">
                            <video id="video" autoplay playsinline></video>
                        </div>
                        
                        <div class="thumbnails" id="thumbnails"></div>
                        <canvas id="canvas" style="display:none;"></canvas>
                    </div>
                    
                    <button type="submit" id="enrollBtn" disabled>✅ Enroll Person</button>
                </form>
                
                <div id="enrollResponse" class="response"></div>
            </div>
        </div>
        
        <script>
            let capturedBlobs = [];
            let stream = null;

            function showTab(tab) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                event.target.classList.add('active');
                document.getElementById(tab + '-tab').classList.add('active');
            }
            
            function previewImage(input, previewId) {
                const preview = document.getElementById(previewId);
                if (input.files && input.files[0]) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    };
                    reader.readAsDataURL(input.files[0]);
                }
            }
            
            async function startCamera() {
                try {
                    stream = await navigator.mediaDevices.getUserMedia({ video: true });
                    const video = document.getElementById('video');
                    video.srcObject = stream;
                    document.getElementById('webcamContainer').style.display = 'block';
                    document.getElementById('captureBtn').disabled = false;
                } catch (err) {
                    alert("Error accessing camera: " + err.message);
                }
            }
            
            async function captureImages() {
                const video = document.getElementById('video');
                const canvas = document.getElementById('canvas');
                const thumbnails = document.getElementById('thumbnails');
                const context = canvas.getContext('2d');
                
                capturedBlobs = [];
                thumbnails.innerHTML = '';
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                document.getElementById('captureBtn').disabled = true;
                document.getElementById('captureBtn').innerText = "Capturing...";
                
                for (let i = 0; i < 5; i++) {
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    // Create thumbnail
                    const thumb = document.createElement('img');
                    thumb.src = canvas.toDataURL('image/jpeg');
                    thumb.className = 'thumbnail captured';
                    thumbnails.appendChild(thumb);
                    
                    // Save blob
                    await new Promise(resolve => canvas.toBlob(blob => {
                        capturedBlobs.push(blob);
                        resolve();
                    }, 'image/jpeg'));
                    
                    // Wait 3 seconds before next capture
                    if (i < 4) {
                        document.getElementById('captureBtn').innerText = `Capturing... (${i+1}/5) - Wait 3s`;
                        await new Promise(r => setTimeout(r, 3000));
                    }
                }
                
                document.getElementById('captureBtn').innerText = "📸 Retake Images";
                document.getElementById('captureBtn').disabled = false;
                document.getElementById('enrollBtn').disabled = false;
            }
            
            async function identifyPerson(event) {
                event.preventDefault();
                
                const responseDiv = document.getElementById('identifyResponse');
                responseDiv.style.display = 'block';
                responseDiv.className = 'response';
                responseDiv.innerHTML = '⏳ Processing...';
                
                const formData = new FormData();
                formData.append('image', document.getElementById('identify_image').files[0]);
                formData.append('camera_id', document.getElementById('camera_id').value);
                
                try {
                    const response = await fetch('/api/v1/identify_image', {
                        method: 'POST',
                        headers: {
                            'X-API-Key': 'testkey123'
                        },
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        const result = data.result;
                        
                        if (result.person_id) {
                            responseDiv.className = 'response success';
                            responseDiv.innerHTML = `
                                <h3>✅ Person Identified</h3>
                                <p><strong>Name:</strong> ${result.name}</p>
                                <p><strong>Person ID:</strong> ${result.person_id}</p>
                                <p><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</p>
                                <p><strong>Camera:</strong> ${data.camera_id}</p>
                                <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                                ${result.snapshot_url ? '<p><strong>Snapshot:</strong> <a href="' + result.snapshot_url + '" target="_blank">View</a></p>' : ''}
                                <details style="margin-top: 20px;">
                            <summary>Show Full Response</summary>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        </details>
                            `;
                        } else {
                            responseDiv.className = 'response warning';
                            responseDiv.innerHTML = `
                                <h3>❓ Unknown Person</h3>
                                <p>No matching person found in the database.</p>
                                <p><strong>Camera:</strong> ${data.camera_id}</p>
                                <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                                <details style="margin-top: 20px;">
                                    <summary>Show Full Response</summary>
                                    <pre>${JSON.stringify(data, null, 2)}</pre>
                                </details>
                            `;
                        }
                    } else {
                        responseDiv.className = 'response error';
                        responseDiv.innerHTML = `
                            <h3>❌ Error</h3>
                            <p>${data.detail || 'Unknown error occurred'}</p>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        `;
                    }
                } catch (error) {
                    responseDiv.className = 'response error';
                    responseDiv.innerHTML = `<h3>❌ Network Error</h3><p>${error.message}</p>`;
                }
            }
            
            async function enrollPerson(event) {
                event.preventDefault();
                
                if (capturedBlobs.length < 5) {
                    alert("Please capture 5 images first!");
                    return;
                }
                
                const responseDiv = document.getElementById('enrollResponse');
                responseDiv.style.display = 'block';
                responseDiv.className = 'response';
                responseDiv.innerHTML = '⏳ Enrolling...';
                
                const formData = new FormData();
                formData.append('name', document.getElementById('name').value);
                
                // Append all captured images
                capturedBlobs.forEach((blob, index) => {
                    formData.append('images', blob, `capture_${index}.jpg`);
                });
                
                const personId = document.getElementById('person_id').value;
                if (personId) formData.append('person_id', personId);
                
                const department = document.getElementById('department').value;
                if (department) formData.append('department', department);
                
                try {
                    const response = await fetch('/api/v1/enroll_person', {
                        method: 'POST',
                        headers: {
                            'X-API-Key': 'testkey123'
                        },
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        responseDiv.className = 'response success';
                        responseDiv.innerHTML = `
                            <h3>✅ Person Enrolled Successfully</h3>
                            <p><strong>Name:</strong> ${data.name}</p>
                            <p><strong>Person ID:</strong> ${data.person_id}</p>
                            <p><strong>Embedding Created:</strong> ${data.embedding_created ? 'Yes' : 'No'}</p>
                            <p><strong>Snapshot Saved:</strong> ${data.snapshot_saved ? 'Yes' : 'No'}</p>
                            <details style="margin-top: 20px;">
                                <summary>Show Full Response</summary>
                                <pre>${JSON.stringify(data, null, 2)}</pre>
                            </details>
                        `;
                        
                        // Reset form
                        document.getElementById('enrollForm').reset();
                        document.getElementById('thumbnails').innerHTML = '';
                        capturedBlobs = [];
                        document.getElementById('enrollBtn').disabled = true;
                    } else {
                        responseDiv.className = 'response error';
                        responseDiv.innerHTML = `
                            <h3>❌ Enrollment Failed</h3>
                            <p>${data.detail || 'Unknown error occurred'}</p>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        `;
                    }
                } catch (error) {
                    responseDiv.className = 'response error';
                    responseDiv.innerHTML = `<h3>❌ Network Error</h3><p>${error.message}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level=LOG_LEVEL.lower()
    )
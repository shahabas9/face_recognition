"""
System management and monitoring endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.core.security import verify_api_key
from app.models import get_db, Person, DetectionEvent
from app.schemas import HealthCheckResponse, DetectionEventsListResponse, DetectionEventDetailResponse
from app.services import FaceRecognitionService, StorageService, IPWebcamManager
from config.settings import (
    API_VERSION,
    get_device,
    API_HOST,
    API_PORT,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Service dependencies
face_service: Optional[FaceRecognitionService] = None
storage_service: Optional[StorageService] = None
webcam_manager: Optional[IPWebcamManager] = None


def set_services(
    face_svc: FaceRecognitionService,
    storage_svc: StorageService,
    webcam_mgr: IPWebcamManager,
):
    """Set service dependencies"""
    global face_service, storage_service, webcam_manager
    face_service = face_svc
    storage_service = storage_svc
    webcam_manager = webcam_mgr


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    
    **Example:**
    ```bash
    curl http://localhost:8000/api/v1/health
    ```
    """
    total_persons = db.query(Person).count()
    active_persons = db.query(Person).filter(Person.is_active == True).count()
    
    webcam_status = False
    if webcam_manager:
        status = webcam_manager.get_status()
        webcam_status = any(s['running'] for s in status.values())
    
    return HealthCheckResponse(
        status="healthy",
        total_persons=total_persons,
        active_persons=active_persons,
        device=get_device(),
        system="FastAPI + FaceNet + InsightFace",
        database="MySQL",
        webcam_active=webcam_status,
        api_version=API_VERSION,
        stats=None
    )


@router.get("/status")
async def get_system_status(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Get detailed system status
    
    **Example:**
    ```bash
    curl http://localhost:8000/api/v1/status \\
         -H "X-API-Key: testkey123"
    ```
    """
    # Storage stats
    storage_stats = storage_service.get_storage_stats() if storage_service else {}
    
    # Webcam status
    webcam_status = {}
    if webcam_manager:
        webcam_status = webcam_manager.get_status()
    
    # Database stats
    total_persons = db.query(Person).count()
    active_persons = db.query(Person).filter(Person.is_active == True).count()
    total_events = db.query(DetectionEvent).count()
    
    return {
        "status": "running",
        "device": get_device(),
        "api_version": API_VERSION,
        "database": {
            "total_persons": total_persons,
            "active_persons": active_persons,
            "total_detection_events": total_events
        },
        "face_recognition": {
            "loaded_persons": len(face_service.person_ids) if face_service else 0,
            "recognition_threshold": face_service.recognition_threshold if face_service else 0.6,
            "model": "FaceNet (VGGFace2)"
        },
        "storage": storage_stats,
        "webcams": webcam_status
    }


@router.post("/threshold")
async def update_threshold(
    threshold: float,
    api_key: str = Depends(verify_api_key)
):
    """
    Update recognition threshold
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/threshold?threshold=0.65" \\
         -H "X-API-Key: testkey123"
    ```
    """
    if not 0.0 <= threshold <= 1.0:
        raise HTTPException(
            status_code=400,
            detail="Threshold must be between 0.0 and 1.0"
        )
    
    if face_service.update_threshold(threshold):
        return {
            "status": "ok",
            "message": f"Recognition threshold updated to {threshold}",
            "threshold": threshold
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to update threshold"
        )


@router.post("/cleanup_snapshots")
async def cleanup_snapshots(
    max_age_days: int = 7,
    api_key: str = Depends(verify_api_key)
):
    """
    Clean up old snapshots
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/cleanup_snapshots?max_age_days=7" \\
         -H "X-API-Key: testkey123"
    ```
    """
    deleted_count = storage_service.cleanup_old_snapshots(max_age_days)
    
    return {
        "status": "ok",
        "message": f"Cleaned up snapshots older than {max_age_days} days",
        "deleted_directories": deleted_count
    }


@router.post("/reload_persons")
async def reload_persons(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Reload persons from database into memory cache
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/reload_persons \\
         -H "X-API-Key: testkey123"
    ```
    """
    face_service.load_persons(db)
    
    return {
        "status": "ok",
        "message": "Persons reloaded from database",
        "total_loaded": len(face_service.person_ids)
    }


@router.get("/detection_events", response_model=DetectionEventsListResponse)
async def get_detection_events(
    person_id: Optional[str] = Query(None, description="Filter by person ID"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    location: Optional[str] = Query(None, description="Filter by location"),
    hours: int = Query(24, description="Get events from last N hours", ge=1, le=720),
    include_unknown: bool = Query(False, description="Include unknown person detections"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(50, description="Items per page", ge=1, le=500),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Get detection events from video streams with person details
    
    This endpoint retrieves identification events from IP webcam/video streams,
    including full person details for mobile application integration.
    
    **Filters:**
    - `person_id`: Filter by specific person
    - `camera_id`: Filter by specific camera
    - `location`: Filter by location
    - `hours`: Get events from last N hours (default: 24)
    - `include_unknown`: Include unknown person detections (default: false)
    
    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 500)
    
    **Example:**
    ```bash
    # Get all events from last 24 hours
    curl http://localhost:8000/api/v1/detection_events \\
         -H "X-API-Key: testkey123"
    
    # Get events for specific person
    curl "http://localhost:8000/api/v1/detection_events?person_id=P001" \\
         -H "X-API-Key: testkey123"
    
    # Get events from specific camera in last 2 hours
    curl "http://localhost:8000/api/v1/detection_events?camera_id=front-door&hours=2" \\
         -H "X-API-Key: testkey123"
    ```
    """
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Build query
        query = db.query(DetectionEvent).filter(
            DetectionEvent.timestamp >= time_threshold
        )
        
        # Apply filters
        if person_id:
            query = query.filter(DetectionEvent.person_id == person_id)
        
        if camera_id:
            query = query.filter(DetectionEvent.camera_id == camera_id)
        
        if location:
            query = query.filter(DetectionEvent.location == location)
        
        if not include_unknown:
            query = query.filter(DetectionEvent.is_unknown == False)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        events = query.order_by(DetectionEvent.timestamp.desc()) \
                     .offset((page - 1) * page_size) \
                     .limit(page_size) \
                     .all()
        
        # Build response with person details
        event_details = []
        for event in events:
            # Get person details if not unknown
            person_name = None
            department = None
            
            if event.person_id and not event.is_unknown:
                person = db.query(Person).filter(Person.person_id == event.person_id).first()
                if person:
                    person_name = person.name
                    department = person.department
            
            # Build snapshot URL
            snapshot_url = None
            if event.snapshot_path:
                snapshot_url = f"http://{API_HOST}:{API_PORT}/snapshots/{event.snapshot_path}"
            
            event_details.append(DetectionEventDetailResponse(
                id=event.id,
                person_id=event.person_id,
                person_name=person_name,
                department=department,
                camera_id=event.camera_id,
                location=event.location,
                confidence=event.confidence,
                embedding_distance=event.embedding_distance,
                bounding_box=event.bounding_box,
                is_unknown=event.is_unknown,
                timestamp=event.timestamp.isoformat() if event.timestamp else None,
                snapshot_url=snapshot_url,
                request_source=event.request_source
            ))
        
        return DetectionEventsListResponse(
            status="ok",
            total_count=total_count,
            page=page,
            page_size=page_size,
            events=event_details
        )
    
    except Exception as e:
        logger.error(f"Error fetching detection events: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch detection events: {str(e)}"
        )


@router.get("/detection_events/latest", response_model=DetectionEventDetailResponse)
async def get_latest_detection(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    person_id: Optional[str] = Query(None, description="Filter by person ID"),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Get the most recent detection event
    
    Useful for real-time updates and dashboard displays.
    
    **Example:**
    ```bash
    # Get latest detection from any camera
    curl http://localhost:8000/api/v1/detection_events/latest \\
         -H "X-API-Key: testkey123"
    
    # Get latest detection for specific person
    curl "http://localhost:8000/api/v1/detection_events/latest?person_id=P001" \\
         -H "X-API-Key: testkey123"
    ```
    """
    try:
        # Build query
        query = db.query(DetectionEvent).filter(DetectionEvent.is_unknown == False)
        
        if camera_id:
            query = query.filter(DetectionEvent.camera_id == camera_id)
        
        if person_id:
            query = query.filter(DetectionEvent.person_id == person_id)
        
        # Get latest event
        event = query.order_by(DetectionEvent.timestamp.desc()).first()
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail="No detection events found matching criteria"
            )
        
        # Get person details
        person_name = None
        department = None
        
        if event.person_id:
            person = db.query(Person).filter(Person.person_id == event.person_id).first()
            if person:
                person_name = person.name
                department = person.department
        
        # Build snapshot URL
        snapshot_url = None
        if event.snapshot_path:
            snapshot_url = f"http://{API_HOST}:{API_PORT}/snapshots/{event.snapshot_path}"
        
        return DetectionEventDetailResponse(
            id=event.id,
            person_id=event.person_id,
            person_name=person_name,
            department=department,
            camera_id=event.camera_id,
            location=event.location,
            confidence=event.confidence,
            embedding_distance=event.embedding_distance,
            bounding_box=event.bounding_box,
            is_unknown=event.is_unknown,
            timestamp=event.timestamp.isoformat() if event.timestamp else None,
            snapshot_url=snapshot_url,
            request_source=event.request_source
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latest detection: {str(e)}"
        )

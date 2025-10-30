"""
Identification API endpoints
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import base64
import io
import logging
import time
from datetime import datetime
from PIL import Image
from typing import Optional

from app.core.security import verify_api_key
from app.models import get_db, DetectionEvent
from app.schemas import (
    IdentifyImageResponse,
    IdentificationResult,
    ErrorResponse,
)
from app.services import FaceRecognitionService, StorageService

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected by the main app
face_service: Optional[FaceRecognitionService] = None
storage_service: Optional[StorageService] = None


def set_services(
    face_svc: FaceRecognitionService,
    storage_svc: StorageService,
):
    """Set service dependencies"""
    global face_service, storage_service
    face_service = face_svc
    storage_service = storage_svc


@router.post("/identify_image", response_model=IdentifyImageResponse)
async def identify_image(
    request: Request,
    image: Optional[UploadFile] = File(None),
    image_b64: Optional[str] = Form(None),
    camera_id: str = Form("mobile-test-1"),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Identify person from uploaded image
    
    **Request Options:**
    - **Multipart Form**: Upload image file with field name "image"
    - **JSON/Form**: Provide base64-encoded image in "image_b64" field
    
    **Example curl:**
    ```bash
    # Upload image file
    curl -X POST http://localhost:8000/api/v1/identify_image \\
         -H "X-API-Key: testkey123" \\
         -F "image=@photo.jpg" \\
         -F "camera_id=mobile-test-1"
    
    # Base64 image
    curl -X POST http://localhost:8000/api/v1/identify_image \\
         -H "X-API-Key: testkey123" \\
         -F "image_b64=<base64_string>" \\
         -F "camera_id=mobile-test-1"
    ```
    """
    start_time = time.time()
    
    try:
        # Parse image from request
        pil_image = None
        
        if image:
            # Multipart file upload
            image_data = await image.read()
            pil_image = Image.open(io.BytesIO(image_data)).convert('RGB')
        elif image_b64:
            # Base64 encoded image
            try:
                # Remove data URL prefix if present
                if ',' in image_b64:
                    image_b64 = image_b64.split(',')[1]
                
                image_bytes = base64.b64decode(image_b64)
                pil_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid base64 image data: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="No image provided. Use 'image' file upload or 'image_b64' field."
            )
        
        result = face_service.identify_person(pil_image, return_bbox=True)
        
        # Check if liveness check failed
        if result and 'error' in result and result['error'] == 'Liveness check failed':
            # Liveness check failed - return error with liveness details
            liveness_info = result.get('liveness', {})
            
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Liveness check failed - Spoofing detected",
                    "liveness": {
                        "is_live": liveness_info.get('is_live', False),
                        "confidence": liveness_info.get('confidence', 0.0),
                        "threshold": liveness_info.get('threshold', 0.7),
                        "model": liveness_info.get('model', 'megatron+pikachu')
                    },
                    "message": f"Liveness confidence {liveness_info.get('confidence', 0.0):.3f} is below threshold {liveness_info.get('threshold', 0.7)}"
                }
            )
        
        # Save snapshot
        snapshot_rel_path = ""
        snapshot_url = None
        
        if result:
            # Identified person - save snapshot
            snapshot_rel_path, _ = storage_service.save_snapshot(
                pil_image,
                prefix="api",
                person_id=result['person_id'],
                camera_id=camera_id,
                subdirectory="events"
            )
            
            if snapshot_rel_path:
                snapshot_url = storage_service.get_snapshot_url(
                    snapshot_rel_path,
                    base_url=str(request.base_url).rstrip('/')
                )
        else:
            # Unknown person - still save snapshot
            snapshot_rel_path, _ = storage_service.save_snapshot(
                pil_image,
                prefix="unknown",
                camera_id=camera_id,
                subdirectory="events"
            )
            
            if snapshot_rel_path:
                snapshot_url = storage_service.get_snapshot_url(
                    snapshot_rel_path,
                    base_url=str(request.base_url).rstrip('/')
                )
        
        # Extract liveness info if available
        liveness_info = result.get('liveness') if result else None
        liveness_score = liveness_info.get('confidence') if liveness_info else None
        
        # Create detection event
        event = DetectionEvent(
            person_id=result['person_id'] if result else None,
            camera_id=camera_id,
            confidence=result['confidence'] if result else None,
            embedding_distance=result.get('embedding_distance') if result else None,
            snapshot_path=snapshot_rel_path,
            bounding_box=str(result['bounding_box']) if result and 'bounding_box' in result else None,
            is_unknown=(result is None),
            timestamp=datetime.utcnow(),
            client_ip=request.client.host if request.client else None,
            request_source='api',
            spoofing_detected=False,
            spoofing_reason=None,
            liveness_score=liveness_score,
            spoofing_type=None
        )

        db.add(event)
        db.commit()

        identification_result = IdentificationResult(
            person_id=result['person_id'] if result else None,
            name=result['name'] if result else None,
            confidence=result['confidence'] if result else 0.0,
            embedding_distance=result.get('embedding_distance') if result else None,
            bounding_box=result.get('bounding_box') if result else None,
            snapshot_url=snapshot_url,
            liveness=liveness_info,
            spoofing_detected=False,
            spoofing_reason=None,
            spoofing_details=None
        )

        response_time = (time.time() - start_time) * 1000
        completion_label = result['name'] if result else 'Unknown'

        logger.info(
            "✅ Identification request completed in %.1fms - Result: %s",
            response_time,
            completion_label,
        )
        
        return IdentifyImageResponse(
            status="ok",
            timestamp=datetime.now().isoformat(),
            camera_id=camera_id,
            result=identification_result,
            processing_time_ms=response_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in identify_image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/test")
async def test_identify_endpoint():
    """
    Test endpoint to verify API is working
    """
    return {
        "status": "ok",
        "message": "Identification API is working",
        "endpoint": "/api/v1/identify_image",
        "methods": ["POST"],
        "total_persons_enrolled": len(face_service.person_ids) if face_service else 0
    }

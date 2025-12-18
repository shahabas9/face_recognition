"""
S3 Enrollment API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import io
import logging
import httpx
import uuid
from datetime import datetime
from PIL import Image
from typing import Optional, List

from app.core.security import verify_api_key
from app.models import get_db, Person
from app.schemas import EnrollS3Request, EnrollS3Response
from app.services import FaceRecognitionService, StorageService

logger = logging.getLogger(__name__)

router = APIRouter()

# Service dependencies
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

@router.post("/enroll_s3", response_model=EnrollS3Response)
async def enroll_person_s3(
    request: EnrollS3Request,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Enroll a new person using images from S3 URLs
    """
    try:
        
        # Validate inputs
        if not request.image_urls or len(request.image_urls) < 1:
            raise HTTPException(status_code=400, detail="At least one image URL is required")

        if len(request.image_urls) < 5:
            logger.warning(f"Enrolling {request.name} with fewer than 5 images ({len(request.image_urls)})")

        # Generate person_id if not provided
        person_id = request.person_id
        if not person_id:
            # Use UUID as requested
            person_id = str(uuid.uuid4())
            logger.info(f"Generated person_id (UUID): {person_id}")
        
        # Validate person_id doesn't exist
        existing = db.query(Person).filter(Person.person_id == person_id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Person ID '{person_id}' already exists"
            )
            
        # 1. Fetch images from URLs
        pil_images = []
        async with httpx.AsyncClient() as client:
            for url in request.image_urls:
                try:
                    resp = await client.get(url, timeout=10.0)
                    resp.raise_for_status()
                    image_data = resp.content
                    pil_image = Image.open(io.BytesIO(image_data)).convert('RGB')
                    pil_images.append(pil_image)
                except Exception as e:
                    logger.error(f"Failed to download image from {url}: {str(e)}")
                    # Continue with other images or fail? 
                    # User requirement implies specific 5 images. If some fail, it might be bad.
                    # But failing entire request for one bad URL might be annoying.
                    # I'll raise error if we don't have enough valid images.
        
        if not pil_images:
            raise HTTPException(status_code=400, detail="Failed to fetch any valid images from provided URLs")

        if len(pil_images) < 5:
             logger.warning(f"Only {len(pil_images)} images successfully fetched")

        # 2. Enroll person (extract embeddings)
        if not face_service:
             raise HTTPException(status_code=500, detail="Face service not initialized")

        success, message, embeddings = face_service.enroll_person(
            pil_images,
            person_id,
            request.name,
            db
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # 3. Save snapshots (optional but recommended for verifying enrollments)
        if storage_service:
            snapshot_saved = False
            for i, pil_image in enumerate(pil_images):
                snapshot_rel_path, _ = storage_service.save_snapshot(
                    pil_image,
                    prefix=f"enroll_s3_{i+1}",
                    person_id=person_id,
                    subdirectory="enrollments"
                )
                if snapshot_rel_path:
                    snapshot_saved = True
        else:
            snapshot_saved = False

        # 4. Serialize embeddings
        embeddings_json = json.dumps([emb.tolist() for emb in embeddings])
        
        # 5. Create person record
        # Parse metadata and include S3 URLs
        metadata_dict = request.metadata or {}
        metadata_dict["s3_image_urls"] = request.image_urls
        
        person = Person(
            person_id=person_id,
            name=request.name,
            face_embedding=embeddings_json,
            department=request.department,
            extra_info=json.dumps(metadata_dict),
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(person)
        db.commit()
        db.refresh(person)
        
        # Reload persons in face service
        face_service.load_persons(db)
        
        logger.info(f"✅ Enrolled new person from S3: {request.name} ({person_id}) with {len(embeddings)} embeddings")
        
        return EnrollS3Response(
            status="ok",
            face_uuid=person_id,
            name=request.name
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enrolling person from S3: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error enrolling person: {str(e)}"
        )

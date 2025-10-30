"""
Person enrollment API endpoints
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import json
import io
import logging
from datetime import datetime
from PIL import Image
from typing import Optional

from app.core.security import verify_api_key
from app.models import get_db, Person, get_next_person_id
from app.schemas import EnrollPersonResponse, PersonResponse, ErrorResponse
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


@router.post("/enroll_person", response_model=EnrollPersonResponse)
async def enroll_person(
    request: Request,
    name: str = Form(...),
    person_id: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    image: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Enroll a new person in the system
    
    **Request:**
    - **name**: Person's full name (required)
    - **person_id**: Unique ID (optional, auto-generated if not provided)
    - **department**: Department or group (optional)
    - **metadata**: Additional JSON metadata (optional)
    - **image**: Face image file (required)
    
    **Example curl:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/enroll_person \\
         -H "X-API-Key: testkey123" \\
         -F "name=Mohamed Shahabas" \\
         -F "person_id=P001" \\
         -F "department=Engineering" \\
         -F "image=@person_photo.jpg"
    ```
    """
    try:
        # Read and process image
        image_data = await image.read()
        pil_image = Image.open(io.BytesIO(image_data)).convert('RGB')
        
        # Generate person_id if not provided
        if not person_id:
            person_id = get_next_person_id(db)
            logger.info(f"Auto-generated person_id: {person_id}")
        
        # Validate person_id doesn't exist
        existing = db.query(Person).filter(Person.person_id == person_id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Person ID '{person_id}' already exists"
            )
        
        # Enroll person (extract embedding)
        success, message, embedding = face_service.enroll_person(
            pil_image,
            person_id,
            name,
            db
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Save snapshot
        snapshot_rel_path, snapshot_full_path = storage_service.save_snapshot(
            pil_image,
            prefix="enroll",
            person_id=person_id,
            subdirectory="enrollments"
        )
        
        # Serialize embedding
        embedding_json = json.dumps(embedding.tolist())
        
        # Parse metadata if provided
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON, storing as-is: {metadata}")
                metadata_dict = {"raw": metadata}
        
        # Create person record
        person = Person(
            person_id=person_id,
            name=name,
            face_embedding=embedding_json,
            department=department,
            metadata=json.dumps(metadata_dict) if metadata_dict else None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(person)
        db.commit()
        db.refresh(person)
        
        # Reload persons in face service
        face_service.load_persons(db)
        
        logger.info(f"✅ Enrolled new person: {name} ({person_id})")
        
        return EnrollPersonResponse(
            status="ok",
            person_id=person_id,
            name=name,
            message=f"Successfully enrolled {name}",
            embedding_created=True,
            snapshot_saved=(snapshot_rel_path != "")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enrolling person: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error enrolling person: {str(e)}"
        )


@router.get("/person/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Get person metadata by ID
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8000/api/v1/person/P001 \\
         -H "X-API-Key: testkey123"
    ```
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    
    if not person:
        raise HTTPException(
            status_code=404,
            detail=f"Person '{person_id}' not found"
        )
    
    return PersonResponse(
        person_id=person.person_id,
        name=person.name,
        department=person.department,
        is_active=person.is_active,
        created_at=person.created_at.isoformat()
    )


@router.get("/persons")
async def list_persons(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """
    List all enrolled persons
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8000/api/v1/persons \\
         -H "X-API-Key: testkey123"
    ```
    """
    query = db.query(Person)
    
    if active_only:
        query = query.filter(Person.is_active == True)
    
    persons = query.all()
    
    return {
        "status": "ok",
        "total": len(persons),
        "persons": [
            {
                "person_id": p.person_id,
                "name": p.name,
                "department": p.department,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat()
            }
            for p in persons
        ]
    }


@router.delete("/person/{person_id}")
async def delete_person(
    person_id: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) a person
    
    **Example:**
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/person/P001 \\
         -H "X-API-Key: testkey123"
    ```
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    
    if not person:
        raise HTTPException(
            status_code=404,
            detail=f"Person '{person_id}' not found"
        )
    
    # Soft delete (deactivate)
    person.is_active = False
    db.commit()
    
    # Reload persons in face service
    face_service.load_persons(db)
    
    logger.info(f"🗑️  Deactivated person: {person.name} ({person_id})")
    
    return {
        "status": "ok",
        "message": f"Person '{person_id}' deactivated",
        "person_id": person_id
    }

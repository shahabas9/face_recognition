"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request Models
class EnrollPersonRequest(BaseModel):
    person_id: Optional[str] = Field(None, description="Unique person ID (auto-generated if not provided)")
    name: str = Field(..., description="Full name of the person")
    department: Optional[str] = Field(None, description="Department or group")
    metadata: Optional[dict] = Field(None, description="Additional metadata as JSON")


class EnrollS3Request(BaseModel):
    name: str = Field(..., description="Full name of the person")
    department: Optional[str] = Field(None, description="Department or group")
    image_urls: List[str] = Field(..., description="List of 5 S3 image URLs")
    person_id: Optional[str] = Field(None, description="Unique person ID (auto-generated if not provided)")
    metadata: Optional[dict] = Field(None, description="Additional metadata as JSON")


class IdentifyImageRequest(BaseModel):
    image_b64: str = Field(..., description="Base64-encoded image")
    camera_id: Optional[str] = Field("mobile-test-1", description="Camera/source identifier")


class IdentificationResult(BaseModel):
    """Result of face identification"""
    person_id: Optional[str] = Field(None, description="Person ID if identified, null if unknown")
    name: Optional[str] = Field(None, description="Person name if identified")
    confidence: float = Field(..., description="Recognition confidence score (0-1)")
    embedding_distance: Optional[float] = Field(None, description="Embedding distance metric (0-2)")
    bounding_box: Optional[List[int]] = Field(None, description="Face bounding box [x, y, w, h]")
    snapshot_url: Optional[str] = Field(None, description="URL to saved snapshot")
    spoofing_detected: bool = Field(False, description="True if spoofing was detected")
    spoofing_reason: Optional[str] = Field(None, description="Reason for spoof detection")
    spoofing_details: Optional[Dict[str, Any]] = Field(None, description="Model-specific spoofing metadata")


class IdentifyImageResponse(BaseModel):
    """Response for image identification request"""
    status: str = Field("ok", description="Response status (ok/error)")
    timestamp: str = Field(..., description="Server timestamp (ISO 8601)")
    camera_id: str = Field(..., description="Camera/source identifier")
    result: IdentificationResult
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = Field("error", description="Response status")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")


class EnrollPersonResponse(BaseModel):
    """Response for person enrollment"""
    status: str = "ok"
    person_id: str = Field(..., description="Enrolled person ID")
    name: str = Field(..., description="Enrolled person name")
    message: str = Field(..., description="Status message")
    embedding_created: bool = Field(..., description="Whether face embedding was successfully created")
    snapshot_saved: bool = Field(..., description="Whether snapshot was saved")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


class EnrollS3Response(BaseModel):
    """Response for S3 person enrollment"""
    status: str = "ok"
    face_uuid: str = Field(..., description="Enrolled person UUID")
    name: str = Field(..., description="Enrolled person name")


class DetectionEventResponse(BaseModel):
    """Basic detection event"""
    id: int
    person_id: Optional[str]
    camera_id: str
    location: Optional[str]
    confidence: Optional[float]
    is_unknown: bool
    spoofing_detected: bool = Field(False, description="True if spoofing was detected")
    spoofing_reason: Optional[str]
    liveness_score: Optional[float]
    timestamp: str
    snapshot_url: Optional[str]
    
    class Config:
        from_attributes = True


class DetectionEventDetailResponse(BaseModel):
    """Detection event with comprehensive details"""
    id: int
    person_id: Optional[str]
    person_name: Optional[str]
    department: Optional[str]
    camera_id: str
    location: Optional[str]
    confidence: Optional[float] = Field(None, description="Recognition confidence (0-1)")
    embedding_distance: Optional[float] = Field(None, description="Embedding distance (0-2)")
    bounding_box: Optional[str] = Field(None, description="Face bounding box JSON or string")
    is_unknown: bool = Field(..., description="Whether person was unknown/unidentified")
    spoofing_detected: bool = Field(False, description="True if spoofing was detected")
    spoofing_reason: Optional[str]
    liveness_score: Optional[float]
    spoofing_type: Optional[str]
    timestamp: str = Field(..., description="Detection timestamp (ISO 8601)")
    snapshot_url: Optional[str]
    request_source: Optional[str]


class DetectionEventsListResponse(BaseModel):
    """List of detection events with pagination"""
    status: str = "ok"
    total_count: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Events per page")
    has_more: Optional[bool] = Field(None, description="Whether more events are available")
    events: List[DetectionEventDetailResponse]


class SystemStatsResponse(BaseModel):
    """System statistics and health information"""
    total_enrollments: int
    failed_enrollments: int
    successful_identifications: int
    unknown_faces: int
    error_rate: float = Field(..., description="Error rate as percentage (0-100)")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="System status (ok/warning/error)")
    total_persons: int = Field(..., description="Total enrolled persons")
    active_persons: int = Field(..., description="Active (non-deleted) persons")
    device: str = Field(..., description="Compute device (CPU/GPU/MPS)")
    system: str = Field(..., description="Operating system")
    database: str = Field(..., description="Database status")
    webcam_active: bool = Field(..., description="Webcam status")
    api_version: str = Field(..., description="API version")
    uptime_seconds: Optional[int] = Field(None, description="System uptime in seconds")
    stats: Optional[SystemStatsResponse] = Field(None, description="System statistics")


class ThresholdUpdateRequest(BaseModel):
    """Request to update detection thresholds"""
    recognition_threshold: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0,
        description="Face recognition threshold (0-1)"
    )


class ThresholdUpdateResponse(BaseModel):
    """Response to threshold update"""
    status: str = "ok"
    message: str
    updated_thresholds: Dict[str, float] = Field(..., description="Updated threshold values")


class BulkIdentificationRequest(BaseModel):
    """Request to identify multiple images"""
    images: List[IdentifyImageRequest] = Field(..., description="List of images to identify")


class BulkIdentificationResponse(BaseModel):
    """Response for bulk identification"""
    status: str = "ok"
    timestamp: str
    total_processed: int
    results: List[IdentifyImageResponse] = Field(..., description="Identification results")


# Response Models
class PersonResponse(BaseModel):
    """Person information response"""
    person_id: str
    name: str
    department: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True
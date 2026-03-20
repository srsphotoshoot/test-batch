"""
Data models and JSON schemas for Streamlit-FastAPI communication
"""
import sys
import os

# Handle imports whether run directly or as module
try:
    from config import BatchStatus
except ImportError:
    # Add parent to path if running directly
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import BatchStatus

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

# ==================================================
# REQUEST SCHEMAS
# ==================================================
class GenerationRequest(BaseModel):
    """Request to generate image for a batch"""
    batch_id: str = Field(..., description="Unique batch identifier")
    request_id: str = Field(..., description="Request tracking ID")
    
    # Images (base64 encoded)
    main_image_b64: str = Field(..., description="Main image in base64")
    ref1_image_b64: str = Field(..., description="Reference 1 image in base64")
    ref2_image_b64: str = Field(..., description="Reference 2 image in base64")
    
    # Generation parameters
    background_color: str = Field(default="royal grey", description="Background color")
    pose_style: str = Field(default="Natural Standing", description="Pose style")
    resolution: str = Field(default="2K", description="Generation resolution")

class HealthCheckRequest(BaseModel):
    """Health check request"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ==================================================
# RESPONSE SCHEMAS
# ==================================================
class GenerationResponse(BaseModel):
    """Response after image generation"""
    status: str = Field(..., description="Success or error")
    batch_id: str = Field(..., description="Batch ID")
    request_id: str = Field(..., description="Request ID")
    
    # Generated image (base64 if successful)
    generated_image_b64: Optional[str] = Field(None, description="Generated image in base64")
    
    # Error details
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_version: str = Field(default="1.0.0")

class BatchMetadata(BaseModel):
    """Metadata for a batch (stored in Streamlit state)"""
    id: str
    output_name: str
    background: str
    pose: str
    resolution: str
    status: BatchStatus
    created_at: float
    finalized: bool
    request_id: Optional[str] = None

# ==================================================
# BATCH IMAGE PAYLOAD (for encoding images)
# ==================================================
class ImagePayload(BaseModel):
    """Payload for single image in batch"""
    name: str
    data: str  # base64
    size_bytes: int

class BatchPayload(BaseModel):
    """Complete batch payload"""
    batch_id: str
    images: Dict[str, ImagePayload]  # {"main": {...}, "ref1": {...}, "ref2": {...}}

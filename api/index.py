"""
FastAPI Backend - Batch Mode SRS System
Replaces Streamlit UI, handles all batch processing
"""
import os
import sys
from pathlib import Path
from pydantic import BaseModel

# Handle imports
import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config import FASTAPI_HOST, FASTAPI_PORT, DEBUG, GEMINI_API_KEY, MODEL_NAME, SIGNUP_PASSKEY
from schemas import GenerationRequest, GenerationResponse, HealthCheckResponse
from logger_util import ContextLogger
import database as db
import service
from image_optimizer import ImageUploadOptimizer

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks, Request, Depends, Response
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import base64
from io import BytesIO
from PIL import Image, ImageOps, ImageEnhance
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, List
import asyncio
import traceback

# Gemini API
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

GEMINI_KEY = GEMINI_API_KEY if 'GEMINI_API_KEY' in globals() else os.getenv("SRS_KEY")

# Initialize Gemini
if HAS_GENAI and GEMINI_KEY:
    gemini_client = genai.Client(api_key=GEMINI_KEY)
else:
    gemini_client = None

# ==================================================
# FASTAPI SETUP
# ==================================================
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    db.init_db()
    # Start background worker
    asyncio.create_task(service.start_queue_worker())
    yield

app = FastAPI(
    title="Shree Radha Studio (SRS) API",
    description="REST API for professional batch image generation",
    version="1.2.0",
    lifespan=lifespan
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://test-batch-eta.vercel.app",
        "https://test-batch-production.up.railway.app"
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZIP middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

logger = ContextLogger("api")

# ==================================================
# USER AUTH MODELS
# ==================================================

class SignupRequest(BaseModel):
    email: str
    password: str
    passkey: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    role: str


# ==================================================
# USER AUTHENTICATION
# ==================================================

def verify_token(request: Request):
    """Verify JWT token from Authorization header"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    payload = db.verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    return payload


@app.post("/signup")
async def signup(data: SignupRequest):
    """
    Create a new user account with passkey verification
    """

    try:
        # Verify passkey against dynamic signup codes
        if not db.verify_signup_code(data.passkey):
            logger.warning(f"Signup attempt with invalid passkey: {data.email}")
            raise HTTPException(
                status_code=400,
                detail="Invalid passkey. Please get a fresh code from your admin."
            )

        # Check if user already exists
        existing_user = db.get_user_by_email(data.email)

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User already exists"
            )

        # Create user (Hashing is handled inside db.create_user with rounds=10 for speed)
        db.create_user(
            email=data.email, 
            password=data.password, 
            first_name=data.first_name, 
            last_name=data.last_name, 
            role="user"
        )

        logger.info(f"New user created: {data.email} ({data.first_name} {data.last_name})")

        return {
            "status": "success",
            "message": "User created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Signup failed"
        )


@app.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """
    Login existing user and return JWT token
    """

    try:

        # Prevent empty login
        if not data.email or not data.password:
            raise HTTPException(
                status_code=400,
                detail="Email and password required"
            )

        # Verify user
        user = db.get_user(data.email, data.password)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # Create JWT token
        token = db.create_jwt_token(user)

        logger.info(f"User login successful: {data.email}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user["id"],
            email=user["email"],
            role=user["role"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Login failed"
        )
# ==================================================
# HELPER FUNCTIONS (from copy.py)
# ==================================================

def compress_upload_image(img, target_quality=85):
    """
    Compress image to target size range (1-2MB) with intelligent quality reduction.
    From copy.py - preserves quality while managing file size.
    """
    img = ImageOps.exif_transpose(img).convert("RGB")
    
    target_min = 1048576  # 1 MB
    target_max = 2097152  # 2 MB
    
    # Start with target quality
    quality = target_quality
    while quality >= 55:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0, 2)
        size = buf.tell()
        
        if target_min <= size <= target_max:
            buf.seek(0)
            size_mb = round(size / (1024 * 1024), 2)
            logger.info(f"✅ Image compressed: {size_mb} MB at quality {quality}%")
            return Image.open(BytesIO(buf.getvalue()))
        
        quality -= 2
    
    # Last resort: return at quality 55
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=55, optimize=True)
    buf.seek(0)
    size_mb = round(buf.tell() / (1024 * 1024), 2)
    logger.info(f"✅ Image compressed to {size_mb} MB at quality 55% (minimum)")
    return Image.open(buf)

def pil_image_to_part(img):
    """Convert PIL Image to Gemini Part (PNG format)"""
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return types.Part.from_bytes(
        data=buf.getvalue(),
        mime_type="image/png"
    )

def extract_image_safe(resp):
    return service.extract_image(resp)

# ==================================================
# ADMIN ENDPOINTS
# ==================================================

@app.get("/api/admin/users")
async def get_admin_users(current_user: Dict = Depends(verify_token)):
    """Get all users - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    try:
        users = db.get_all_users()
        return {
            "status": "success",
            "users": users
        }
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch users"
        )


@app.get("/api/admin/signup-code")
async def get_signup_code(current_user: Dict = Depends(verify_token)):
    """Get the current active signup code - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    code = db.get_active_signup_code()
    return {"status": "success", "code": code}


@app.post("/api/admin/signup-code/rotate")
async def rotate_signup_code(current_user: Dict = Depends(verify_token)):
    """Generate a new signup code - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    new_code = db.rotate_signup_code()
    logger.info(f"Signup code rotated by admin {current_user.get('email')}")
    return {"status": "success", "code": new_code, "message": "Signup code rotated successfully"}


@app.put("/api/admin/users/{user_id}/role")
async def update_user_role(user_id: int, role: str, current_user: Dict = Depends(verify_token)):
    """Update user role - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    if role not in ["user", "admin"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )
    
    try:
        db.update_user_role(user_id, role)
        logger.info(f"User {user_id} role updated to {role}")
        return {
            "status": "success",
            "message": f"User role updated to {role}"
        }
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user role"
        )


@app.put("/api/admin/users/{user_id}/limits")
async def update_user_limits(user_id: int, batch_limit: int = None, daily_upload_limit: int = None, current_user: Dict = Depends(verify_token)):
    """Update user limits - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    try:
        db.set_user_limits(user_id, batch_limit, daily_upload_limit)
        logger.info(f"User {user_id} limits updated: batch_limit={batch_limit}, daily_upload_limit={daily_upload_limit}")
        return {
            "status": "success",
            "message": "User limits updated successfully",
            "batch_limit": batch_limit,
            "daily_upload_limit": daily_upload_limit
        }
    except Exception as e:
        logger.error(f"Error updating user limits: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user limits"
        )


@app.delete("/api/admin/users/{user_id}")
async def delete_admin_user(user_id: int, current_user: Dict = Depends(verify_token)):
    """Delete user - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    if user_id == current_user.get("user_id"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete yourself"
        )
    
    try:
        db.delete_user(user_id)
        logger.info(f"User {user_id} deleted")
        return {
            "status": "success",
            "message": "User deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user"
        )


@app.get("/api/admin/stats")
async def get_admin_stats(current_user: Dict = Depends(verify_token)):
    """Get system statistics - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    try:
        total_users = db.get_all_users().__len__()
        queue_status = db.get_queue_status()
        
        return {
            "status": "success",
            "stats": {
                "total_users": total_users,
                "queued_batches": queue_status.get("queued", 0),
                "generating_batches": queue_status.get("generating", 0),
                "total_batches": len(db.list_batches()),
                "completed_batches": len([b for b in db.list_batches() if b.get("status") == "completed"]),
                "failed_batches": len([b for b in db.list_batches() if b.get("status") == "failed"])
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch stats"
        )


@app.get("/api/admin/upload-stats")
async def get_upload_stats(current_user: Dict = Depends(verify_token)):
    """Get image upload statistics - Admin only"""
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    try:
        batches = db.list_batches()
        
        # Calculate upload statistics
        total_uploads = 0
        total_size_original = 0
        total_size_compressed = 0
        successful_uploads = 0
        
        for batch in batches:
            images = batch.get("images", {})
            for role, image_data in images.items():
                if image_data is not None:
                    total_uploads += 1
                    successful_uploads += 1
                    
                    if isinstance(image_data, dict):
                        orig_size = image_data.get("size_original_mb", 0)
                        comp_size = image_data.get("size_compressed_mb", 0)
                        total_size_original += orig_size
                        total_size_compressed += comp_size
        
        avg_size_original = total_size_original / total_uploads if total_uploads > 0 else 0
        avg_size_compressed = total_size_compressed / total_uploads if total_uploads > 0 else 0
        avg_compression_ratio = total_size_original / total_size_compressed if total_size_compressed > 0 else 1
        space_saved = total_size_original - total_size_compressed
        success_rate = (successful_uploads / total_uploads * 100) if total_uploads > 0 else 100
        
        return {
            "status": "success",
            "upload_stats": {
                "total_uploads": total_uploads,
                "successful_uploads": successful_uploads,
                "avg_size_original_mb": avg_size_original,
                "avg_size_compressed_mb": avg_size_compressed,
                "avg_compression_ratio": avg_compression_ratio,
                "total_space_saved_mb": space_saved,
                "success_rate": success_rate
            }
        }
    except Exception as e:
        logger.error(f"Error fetching upload stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch upload stats"
        )


@app.get("/api/admin/db/config")
async def get_db_config(current_user: Dict = Depends(verify_token)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    import db_engine
    return {
        "status": "success",
        "current_url": db_engine.get_db_url(),
        "config_file_exists": os.path.exists(db_engine.CONFIG_PATH)
    }

@app.post("/api/admin/db/test")
async def test_db_connection(data: Dict, current_user: Dict = Depends(verify_token)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Database URL required")
    
    from sqlalchemy import create_engine
    try:
        # Adjust postgres:// to postgresql:// if needed
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        test_engine = create_engine(url, connect_args={"connect_timeout": 5})
        with test_engine.connect() as conn:
            return {"status": "success", "message": "Connection successful!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/admin/db/save")
async def save_db_config(data: Dict, current_user: Dict = Depends(verify_token)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Database URL required")
    
    import db_engine
    try:
        with open(db_engine.CONFIG_PATH, "w") as f:
            json.dump({"DATABASE_URL": url}, f)
        
        db_engine.reset_engine()
        db.init_db() # Create tables in new DB
        
        return {"status": "success", "message": "Configuration saved and engine restarted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/db/export")
async def export_db(current_user: Dict = Depends(verify_token)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    import db_engine
    if not os.path.exists(db_engine.DEFAULT_SQLITE_PATH):
        raise HTTPException(status_code=404, detail="SQLite database file not found")
        
    return FileResponse(
        db_engine.DEFAULT_SQLITE_PATH, 
        filename="batches_backup.db",
        media_type="application/x-sqlite3"
    )

@app.post("/api/admin/db/import")
async def import_db(file: UploadFile = File(...), current_user: Dict = Depends(verify_token)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    import db_engine
    content = await file.read()
    
    # Save as backup first
    if os.path.exists(db_engine.DEFAULT_SQLITE_PATH):
        os.rename(db_engine.DEFAULT_SQLITE_PATH, db_engine.DEFAULT_SQLITE_PATH + ".bak")
        
    try:
        with open(db_engine.DEFAULT_SQLITE_PATH, "wb") as f:
            f.write(content)
        
        db_engine.reset_engine()
        return {"status": "success", "message": "Database imported successfully"}
    except Exception as e:
        if os.path.exists(db_engine.DEFAULT_SQLITE_PATH + ".bak"):
            os.rename(db_engine.DEFAULT_SQLITE_PATH + ".bak", db_engine.DEFAULT_SQLITE_PATH)
        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# HEALTH CHECK
# ==================================================
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        api_version="1.0.0"
    )

@app.get("/api/config")
async def get_config():
    from config import BACKGROUND_COLOR_OPTIONS, POSE_PROMPTS, RESOLUTION_OPTIONS, DRESS_TYPES, ASPECT_RATIO_OPTIONS
    # Flatten all backgrounds into a unique list for the UI
    all_backgrounds = []
    for bg_list in BACKGROUND_COLOR_OPTIONS.values():
        all_backgrounds.extend(bg_list)
    unique_backgrounds = sorted(list(set(all_backgrounds)))
    
    return {
        "backgrounds": unique_backgrounds,
        "poses": list(POSE_PROMPTS.keys()),
        "resolutions": list(RESOLUTION_OPTIONS.keys()),
        "aspect_ratios": ASPECT_RATIO_OPTIONS,
        "dress_types": DRESS_TYPES
    }

@app.get("/api/queue/status")
async def get_queue_status():
    return db.get_queue_status()

# ==================================================
# BATCH MANAGEMENT
# ==================================================
# @app.post("/api/batch/create")
# async def create_batch(
#     output_name: str = Form(...),
#     background: str = Form(default="royal grey"),
#     pose: str = Form(default="Natural Standing"),
#     resolution: str = Form(default="2K"),
#     aspect_ratio: str = Form(default="1:1"),
#     dress_type: str = Form(default="Normal Mode")
# ):
#     try:
#         batch_id = str(uuid.uuid4())
#         # batch_data = {
#         #     "id": batch_id,
#         #     "output_name": output_name,
#         #     "background": background,
#         #     "pose": pose,
#         #     "resolution": resolution,
#         #     "aspect_ratio": aspect_ratio,
#         #     "dress_type": dress_type,
#         #     "status": "pending",
#         #     "created_at": datetime.utcnow().isoformat(),
#         #     "images": {"main": None, "ref1": None, "ref2": None},
#         #     "generated_image": None,
#         #     "error": None
#         # 
#         batch_data = {
#                "id": batch_id,
#                "output_name": output_name,
#                "background": background,
#                "pose": pose,
#                "resolution": resolution,
#                "aspect_ratio": aspect_ratio,
#                "dress_type": dress_type,
#                "status": "queued",
#                "created_at": datetime.utcnow().isoformat(),
#                "images": {"main": None, "ref1": None, "ref2": None},
#                "generated_image": None,
#                "error": None
#       }
@app.post("/api/batch/create")
async def create_batch(
    output_name: str = Form(...),
    background: str = Form(default="royal grey"),
    pose: str = Form(default="Natural Standing"),
    resolution: str = Form(default="2K"),
    aspect_ratio: str = Form(default="1:1"),
    dress_type: str = Form(default="Normal Mode"),
    blouse_color: str = Form(default="#FFFFFF"),
    lehenga_color: str = Form(default="#FFFFFF"),
    dupatta_color: str = Form(default="#FFFFFF"),
    request: Request = None
):
    try:
        batch_id = str(uuid.uuid4())
        user_id = None
        
        # Try to get user_id from token if provided
        if request:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = db.verify_jwt_token(token)
                if payload:
                    user_id = payload.get("user_id")
        
        # Check batch limit if user is authenticated
        if user_id:
            batch_count = db.get_batch_count(user_id)
            batch_limit = db.get_batch_limit(user_id)
            if batch_count >= batch_limit:
                logger.warning(f"❌ User {user_id} exceeded batch limit ({batch_count}/{batch_limit})")
                raise HTTPException(
                    status_code=429,
                    detail=f"Batch limit reached. You have created {batch_count}/{batch_limit} batches."
                )
            db.increment_batch_count(user_id)

        batch_data = {
            "id": batch_id,
            "output_name": output_name,
            "background": background,
            "pose": pose,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "dress_type": dress_type,
            "blouse_color": blouse_color,
            "lehenga_color": lehenga_color,
            "dupatta_color": dupatta_color,
            "user_id": user_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "images": {
                "main": None,
                "ref1": None,
                "ref2": None
            },
            "generated_image": None,
            "error": None
        }

        db.save_batch(batch_data)
        logger.info(f"✅ Batch created: {batch_id}")

        return {
            "status": "success",
            "batch_id": batch_id,
            "message": "Batch created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch creation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch creation failed: {str(e)}"
        )

@app.get("/api/batch/{batch_id}")
async def get_batch(batch_id: str):
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Calculate queue position if queued
    queue_pos = -1
    if batch["status"] == "queued":
        queue_pos = db.get_queue_position(batch_id)

    return {
        "id": batch["id"],
        "output_name": batch["output_name"],
        "background": batch["background"],
        "pose": batch["pose"],
        "resolution": batch["resolution"],
        "aspect_ratio": batch.get("aspect_ratio", "1:1"),
        "dress_type": batch["dress_type"],
        "status": batch["status"],
        "queue_position": queue_pos,
        "created_at": batch["created_at"],
        "has_main": batch["images"]["main"] is not None,
        "has_ref1": batch["images"]["ref1"] is not None,
        "has_ref2": batch["images"]["ref2"] is not None,
        "has_generated": batch["generated_image"] is not None,
        "error": batch["error"]
    }

@app.get("/api/batches")
async def list_batches(current_user: Dict = Depends(verify_token)):
    """Get batches - Admin sees all, users see only their own"""
    try:
        if current_user.get("role") == "admin":
            # Admin sees all batches
            batches = db.list_batches()
        else:
            # Regular user sees only their batches
            batches = db.list_user_batches(current_user.get("user_id"))
        
        return {
            "status": "success",
            "batches": batches,
            "user_role": current_user.get("role")
        }
    except Exception as e:
        logger.error(f"Error fetching batches: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch batches"
        )

@app.get("/api/batches/all")
async def list_all_batches(current_user: Dict = Depends(verify_token)):
    """Get all batches - Admin only"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return db.list_batches()

# ==================================================
# IMAGE UPLOAD (OPTIMIZED)
# ==================================================
@app.post("/api/batch/{batch_id}/upload/{role}")
async def upload_image(batch_id: str, role: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), request: Request = None):
    """
    Optimized image upload endpoint with async processing
    Automatically compresses images and returns progress
    """
    try:
        batch = db.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Validate role
        if role not in ['main', 'ref1', 'ref2']:
            raise HTTPException(status_code=400, detail="Invalid role. Must be main, ref1, or ref2")
        
        # Check daily upload limit if user owns this batch
        user_id = batch.get("user_id")
        if user_id:
            limit_check = db.check_daily_upload_limit(user_id)
            if not limit_check["allowed"]:
                logger.warning(f"❌ User {user_id} daily upload limit exceeded: {limit_check['reason']}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily upload limit reached. You have uploaded {limit_check['current']}/{limit_check['limit']} times today."
                )
        
        # Read file with size tracking
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        
        # Validate file size (max 50MB)
        if file_size_mb > 50:
            raise HTTPException(status_code=413, detail="File too large. Maximum 50MB allowed")
        
        logger.info(f"📥 Uploading {role} for batch {batch_id}: {file_size_mb:.2f}MB")
        
        # Optimize image upload
        try:
            upload_result = await ImageUploadOptimizer.optimize_upload(
                file_content=content,
                filename=file.filename or f"{role}_{batch_id}",
                needs_quality=True,
                progress_callback=None  # Could use websockets for real progress
            )
        except Exception as e:
            logger.error(f"❌ Upload optimization failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")
        
        # Increment daily upload count
        if user_id:
            db.increment_daily_uploads(user_id)
        
        # Save metadata to batch (Instant UI Feedback)
        batch["images"][role] = {
            "b64": upload_result['b64'],
            "filename": upload_result['filename'],
            "uploaded_at": upload_result['uploaded_at'],
            "size_original_mb": upload_result['size_original_mb'],
            "size_compressed_mb": upload_result['size_compressed_mb'],
            "compression_ratio": upload_result['compression_ratio']
        }
        
        # 1. Perform a LIGHTWEIGHT sync save (metadata only)
        # This returns a response to the user almost instantly
        db.save_batch(batch, raw_images=None)
        
        # 2. Perform a HEAVY async save in the background (binary data)
        # This keeps the UI responsive even if the DB connection is slow
        background_tasks.add_task(
            db.save_batch_binary,
            batch_id,
            role,
            upload_result['raw_bytes']
        )
        
        logger.info(
            f"✅ {role} metadata saved. Binary upload queued in background. "
            f"Speedup: Instant response triggered."
        )
        
        return {
            "status": "uploaded",
            "role": role,
            "size_original_mb": upload_result['size_original_mb'],
            "size_compressed_mb": upload_result['size_compressed_mb'],
            "compression_ratio": round(upload_result['compression_ratio'], 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading image: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/batch/{batch_id}/image/{role}")
async def get_image(batch_id: str, role: str):
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if role not in batch["images"] or batch["images"][role] is None:
        raise HTTPException(status_code=404, detail=f"Image {role} not found")
    
    return {"b64": batch["images"][role]["b64"]}

    return {"b64": batch["generated_image"]}
    
@app.get("/api/batch/{batch_id}/image/{role}/raw")
async def get_image_raw(batch_id: str, role: str):
    """Serve image as raw binary for better performance"""
    # We use a fresh DB session here to fetch the deferred binary column
    import database as db_mod
    from db_engine import SessionLocal
    from database import Batch
    
    session = SessionLocal()
    try:
        batch = session.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
            
        # Prioritize Binary column for speed (Zero decoding overhead)
        raw_data = None
        if role == 'main': raw_data = batch.main_image_bin
        elif role == 'ref1': raw_data = batch.ref1_image_bin
        elif role == 'ref2': raw_data = batch.ref2_image_bin
        
        if raw_data:
            return Response(content=raw_data, media_type="image/png")
            
        # Fallback to legacy Base64 if binary is missing (for old batches)
        batch_meta = db_mod.get_batch(batch_id)
        if role not in batch_meta["images"] or batch_meta["images"][role] is None:
            raise HTTPException(status_code=404, detail=f"Image {role} not found")
            
        b64_data = batch_meta["images"][role]["b64"]
        if "," in b64_data:
            b64_data = b64_data.split(",")[1]
        
        return Response(content=base64.b64decode(b64_data), media_type="image/png")
    finally:
        session.close()

@app.get("/api/batch/{batch_id}/generated-image/raw")
async def get_generated_image_raw(batch_id: str):
    """Serve generated image as raw binary"""
    from db_engine import SessionLocal
    from database import Batch
    
    session = SessionLocal()
    try:
        batch = session.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
            
        # Prioritize Binary column
        if batch.generated_image_bin:
            return Response(content=batch.generated_image_bin, media_type="image/png")
            
        # Fallback to legacy Base64
        if batch.generated_image_b64:
            b64_data = batch.generated_image_b64
            if "," in b64_data:
                b64_data = b64_data.split(",")[1]
            return Response(content=base64.b64decode(b64_data), media_type="image/png")
            
        raise HTTPException(status_code=404, detail="No generated image yet")
    finally:
        session.close()

# ==================================================
# BATCH PROCESSING
# ==================================================
# Prompt building logic moved to service.py to avoid duplication
def build_final_prompt(*args, **kwargs):
    # This is a shim for any legacy calls, but we should use service.build_prompt(batch_dict)
    raise NotImplementedError("Use service.build_prompt instead")
@app.post("/api/batch/{batch_id}/generate")
async def generate_image(batch_id: str):
    try:
        batch = db.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if not all([batch["images"]["main"], batch["images"]["ref1"], batch["images"]["ref2"]]):
            raise HTTPException(status_code=400, detail="All images (main, ref1, ref2) required")
        
        batch["status"] = "queued"
        db.save_batch(batch)
        
        logger.info(f"Batch queued: {batch_id}")
        return {"status": "queued", "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Error queuing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batch/{batch_id}/generate-sync")
async def generate_image_sync(batch_id: str):
    """Generate image synchronously (for testing)"""
    try:
        batch = db.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Validate all images present
        if not all([batch["images"]["main"], batch["images"]["ref1"], batch["images"]["ref2"]]):
            raise HTTPException(status_code=400, detail="All images (main, ref1, ref2) required")
        
        await service.process_batch_worker(batch_id)
        return await get_batch(batch_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        currently_processing = None
        if batch_id in processing_queue:
            processing_queue.remove(batch_id)
        logger.info(f"🏁 Batch processing finished for: {batch_id}")


@app.delete("/api/batch/{batch_id}")
async def delete_batch(batch_id: str):
    db.delete_batch(batch_id)
    return {"status": "deleted"}

# ==================================================
# FRONTEND STATIC SERVING
# ==================================================
# The frontend/build directory is in the project root
frontend_build_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "build")

if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_path, "static")), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str, request: Request):
        """Serve frontend files or fallback to index.html for client-side routing"""
        # Skip API routes and auth routes - let them be handled by specific endpoints
        # This won't actually prevent them since those routes are already registered,
        # but this is a safety check for documentation
        
        # Check if the requested file exists in the build directory
        file_path = os.path.join(frontend_build_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fallback to serving React's index.html for client-side routing
        # This enables client-side routing in the React app
        index_path = os.path.join(frontend_build_path, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        
        # If nothing found, return 404
        raise HTTPException(status_code=404, detail="File not found")
else:
    logger.warning("Frontend build directory not found. Please run 'npm run build' in the frontend directory.")
    @app.get("/")
    async def root():
        return {"message": "API is running, but React frontend build is missing."}

# ==================================================
# RUN SERVER
# ==================================================
if __name__ == "__main__":
    logger.info(f"Starting API server on {FASTAPI_HOST}:{FASTAPI_PORT}")
    logger.info("⚙️  Keep-Alive: 5s | Concurrent: 100 | Max Requests: 10000")
    uvicorn.run(
        app,
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        reload=False,
        log_level="info",
        timeout_keep_alive=5,           # Keep-alive timeout (5 seconds)
        limit_concurrency=100,          # Max concurrent connections
        limit_max_requests=10000,       # Max requests before reload
        workers=1                       # Single worker for development
    )

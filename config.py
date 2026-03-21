"""
Configuration and constants for SRS System
"""
import os
from enum import Enum
from pathlib import Path

# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================
try:
    from dotenv import load_dotenv
    # Load from .env file (works in dev and prod)
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # Fallback to searching for .env
except ImportError:
    pass

# ==================================================
# ENVIRONMENT CONFIG
# ==================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
DEBUG = ENVIRONMENT == "dev"

# API Configuration
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("PORT", os.getenv("FASTAPI_PORT", "8000")))
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", f"http://{FASTAPI_HOST}:{FASTAPI_PORT}")

# Gemini Configuration (FastAPI only)
GEMINI_API_KEY = os.getenv("SRS_KEY")
if not GEMINI_API_KEY:
    import sys
    print("⚠️  WARNING: SRS_KEY environment variable not set!", file=sys.stderr)
MODEL_NAME = "gemini-3.1-flash-image-preview"

# Signup Configuration
SIGNUP_PASSKEY = os.getenv("SIGNUP_PASSKEY")
if not SIGNUP_PASSKEY:
    import sys
    print("⚠️  WARNING: SIGNUP_PASSKEY environment variable not set!", file=sys.stderr)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    import sys
    print("⚠️  WARNING: JWT_SECRET_KEY environment variable not set!", file=sys.stderr)

# Admin Configuration
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@srs.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "srsadmin123")

# Image Configuration
MAX_IMAGE_DIM = 2048
TARGET_SIZE_MIN = 1 * 1024 * 1024
TARGET_SIZE_MAX = 2 * 1024 * 1024
COMPRESSION_QUALITY_MIN = 55
COMPRESSION_QUALITY_MAX = 95

# ==================================================
# ENUMS
# ==================================================
class BatchStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    DONE = "done"
    ERROR = "error"

class BatchRole(str, Enum):
    MAIN = "main"
    REF1 = "ref1"
    REF2 = "ref2"

# ==================================================
# PROMPTS & CONFIG
# ==================================================
BASE_PROMPT_MAP = {
    "Normal Mode": "Generate a photorealistic image of a professional Indian fashion model wearing this exact dress outfit. Simply add a human model body to the dress - do NOT modify any aspect of the garment.",
    "Printed Lehenga": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT PRINTED LEHENGA outfit.",
    "Heavy Lehenga": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT HEAVY LEHENGA outfit.",
    "Western Dress": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT WESTERN DRESS outfit.",
    "Indo-Western": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT INDO-WESTERN outfit.",
    "Gown": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT GOWN.",
    "Saree": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT SAREE outfit.",
    "Plazo-set": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT PLAZO-SET outfit."
}

LOCKED_REGION_MAP = {
    "Normal Mode": """
LOCKED REGIONS (ABSOLUTE - DO NOT MODIFY):
- Entire Dress Structure
- All Seams and Construction
- Embroidery and Patterns (if any)
- Fabric Texture and Weave
- All Geometric Details
- Border and Hem Details
- Dupatta (if present)
- ANY and ALL dress components
ONLY add human body to the dress without ANY modifications.
""",
    "Printed Lehenga": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam
- Lehenga Skirt
- Embroidery Pattern
""",
    "Heavy Lehenga": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam
- Heavy Embroidery Details
- Skirt Silhouette
""",
    "Western Dress": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Sleeve ends
- Neckline
- Waist definition
- Dress hem
""",
    "Indo-Western": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Sleeve ends
- Top-to-bottom transition seam
- Waist details
- Bottom silhouette
""",
    "Gown": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Bodice seam
- Waist transition (if present)
- Gown length and flow
""",
    "Saree": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Blouse Back
- Saree Pleats
- Saree Pallu
- Waist definition
- Border Details
""",
    "Plazo-set": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Kurta Front and Back
- Neckline
- Sleeve Details
- Plazo Length and Fit
- Border Pattern
"""
}

DUPATTA_LOCK_PROMPT = """
CRITICAL DUPATTA ENFORCEMENT (HIGHEST PRIORITY):
- Dupatta width MUST remain unchanged
- Border thickness MUST remain identical
- Embroidery scale MUST NOT change
- Motif spacing MUST NOT change
- Thread density MUST match reference
FAIL THE IMAGE IF DUPATTA DIFFERS.
"""

BACKGROUND_COLOR_OPTIONS = {
    "Normal Mode": ["royal outdoor", "royal grey", "royal brown", "royal cream", "royal outdoor garden", "fort outdoor", "Butique", "royal indian fort"],
    "Printed Lehenga": ["royal grey", "royal brown", "royal cream"],
    "Heavy Lehenga": ["royal outdoor", "royal indian fort", "royal palace"],
    "Western Dress": ["royal grey", "royal brown", "royal cream","butique"],
    "Indo-Western": ["royal outdoor", "royal indian fort", "royal palace"],
    "Gown": ["royal outdoor", "royal indian fort", "royal palace"],
    "Saree": ["royal grey", "royal brown", "royal cream","butique"],
    "Plazo-set": ["royal grey", "royal brown", "royal cream", "butique"]
}

ORNATE_BACKGROUND_DESCRIPTIONS = {
    "Heavy Lehenga": "BACKGROUND: Royal outdoor background with ornate settings.",
    "Indo-Western": "BACKGROUND: Royal outdoor background with contemporary elegance.",
    "Gown": "BACKGROUND: Elegant outdoor background with sophisticated ambiance."
}

BACKGROUND_DESCRIPTIONS_MAP = {
    "royal outdoor": "BACKGROUND: Royal outdoor background with elegant settings.",
    "royal grey": "BACKGROUND: Plain simple studio background with royal grey.",
    "royal brown": "BACKGROUND: Plain simple studio background with royal brown.",
    "royal cream": "BACKGROUND: Plain simple studio background with royal cream.",
    "inside butique showroom ": "BACKGROUND: Inside boutique showroom with sophisticated ambiance.",
    "royal outdoor garden": "BACKGROUND: Royal outdoor garden background with natural elegance.",
    "fort outdoor": "BACKGROUND: Fort outdoor background with royal heritage settings.",
    "royal indian fort": "BACKGROUND: Royal outdoor background with Indian fort architecture.",
    "royal palace": "BACKGROUND: Royal outdoor background with palace settings.",
    "Butique": "BACKGROUND: High-end fashion boutique interior.\n- Neutral luxury palette (beige / ivory / warm grey)\n- Polished stone or marble flooring\n- Soft warm ambient lighting with diffused ceiling spotlights\n- Minimal gold/brass accents\n- Sparse clothing racks far in background\n- Shallow depth-of-field, background softly blurred\n- No mannequins, mirrors, signage, or logos\n- Background must NOT alter garment colors\n"
}

POSE_PROMPTS = {
    "Natural Standing": "POSE: Natural upright standing pose.",
    "Soft Fashion": "POSE: Slight hip shift, relaxed arms.",
    "Editorial": "POSE: Editorial fashion pose.",
    "Walk": "POSE: Mild walking stance."
}

RESOLUTION_OPTIONS = {
    "1K": "1024x1024",
    "2K": "2048x2048",
    "4K": "4096x4096"
}

# Alias for compatibility
RESOLUTION_MAP = RESOLUTION_OPTIONS

DRESS_TYPES = list(BASE_PROMPT_MAP.keys())

ASPECT_RATIO_OPTIONS = ["1:1", "9:16", "16:9", "3:4", "4:3"]
ASPECT_RATIO_MAP = {
    "1:1": "1:1",
    "9:16": "9:16",
    "16:9": "16:9",
    "3:4": "3:4",
    "4:3": "4:3"
}

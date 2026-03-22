import os
import base64
import asyncio
import traceback
from io import BytesIO
from PIL import Image, ImageOps
from datetime import datetime
from google import genai
from google.genai import types
import database as db
from logger_util import ContextLogger

logger = ContextLogger("service")

# Load configuration
try:
    from config import (
        GEMINI_API_KEY, MODEL_NAME, 
        BASE_PROMPT_MAP, LOCKED_REGION_MAP, BACKGROUND_DESCRIPTIONS_MAP, 
        ORNATE_BACKGROUND_DESCRIPTIONS, POSE_PROMPTS, DUPATTA_LOCK_PROMPT
    )
    GEMINI_KEY = GEMINI_API_KEY
except ImportError:
    GEMINI_KEY = os.getenv("SRS_KEY")
    MODEL_NAME = "gemini-3-pro-image-preview"

# Initialize Client
client = None
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)

generation_lock = asyncio.Lock()

def compress_image(img, target_quality=85, max_dim=1024):
    """
    Downscale the image to drastically reduce Gemini input tokens (based on pixel resolution) 
    and output as JPEG to save network bandwidth.
    """
    img = ImageOps.exif_transpose(img).convert("RGB")
    
    # Downscale resolution to heavily reduce Gemini input tokens
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / float(max(w, h))
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=target_quality, optimize=True)
    return Image.open(BytesIO(buf.getvalue()))

def pil_to_part(img):
    buf = BytesIO()
    # Sending as JPEG instead of PNG to drastically cut bandwidth & upload times
    img.save(buf, format="JPEG", quality=85)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")

def extract_image(resp):
    try:
        candidates = getattr(resp, 'candidates', [])
        logger.info(f"Full Gemini response cand count: {len(candidates)}")
        for i, cand in enumerate(candidates):
            logger.info(f"Candidate {i} finish_reason: {getattr(cand, 'finish_reason', 'UNKNOWN')}")
            content = getattr(cand, 'content', None)
            if not content:
                logger.info(f"Candidate {i} has NO content")
                continue
                
            parts = getattr(content, 'parts', [])
            if parts is None:
                logger.info(f"Candidate {i} content parts is NONE")
                continue
                
            logger.info(f"Candidate {i} parts count: {len(parts)}")
            for j, part in enumerate(parts):
                inline = getattr(part, "inline_data", None)
                text = getattr(part, "text", None)
                if inline:
                    logger.info(f"Part {j} has inline_data: {inline.mime_type}")
                    if inline.mime_type.startswith("image/"):
                        return base64.b64decode(inline.data) if isinstance(inline.data, str) else inline.data
                if text:
                    logger.info(f"Part {j} has text: {text[:100]}...")
    except Exception as e:
        logger.error(f"Error in extract_image: {str(e)}", exc_info=True)
    return None

def build_prompt(batch):
    """
    Token-optimized prompt builder. Uses high-density instructions to reduce token count.
    """
    dress_type = batch.get("dress_type", "Normal Mode")
    bg_color = batch.get("background", "royal grey")
    pose_style = batch.get("pose", "Natural Standing")
    
    blouse_color = batch.get("blouse_color", "#FFFFFF")
    lehenga_color = batch.get("lehenga_color", "#FFFFFF")
    dupatta_color = batch.get("dupatta_color", "#FFFFFF")

    # Background Selection
    if bg_color in BACKGROUND_DESCRIPTIONS_MAP:
        bg_prompt = BACKGROUND_DESCRIPTIONS_MAP[bg_color]
    elif dress_type in ORNATE_BACKGROUND_DESCRIPTIONS:
        bg_prompt = ORNATE_BACKGROUND_DESCRIPTIONS[dress_type]
    else:
        bg_prompt = f"BACKGROUND: {bg_color}."

    # Dense shared constraints targeting maximum token efficiency
    dense_rules = f"""
MODEL: Adult Indian female, standard runway posture, studio lighting.
TASK: Mannequin-to-human projection. 
CONSTRAINTS (STRICT): Preserve EXACT original garment geometry, seams, embroidery, drape, and patterns. Do NOT redesign, beautify, or hallucinate missing details. Adjust ONLY for natural human anatomy.
{DUPATTA_LOCK_PROMPT}
"""

    base_p = BASE_PROMPT_MAP.get(dress_type, BASE_PROMPT_MAP["Normal Mode"])
    region_lock = LOCKED_REGION_MAP.get(dress_type, "")
    
    color_lock = f"COLORS(HEX): Blouse:{blouse_color}, Lehenga:{lehenga_color}, Dupatta:{dupatta_color}."
    
    if dress_type == "Normal Mode":
        prompt_core = f"{base_p}\n{dense_rules}\n{region_lock}"
    else:
        prompt_core = f"{base_p}\n{dense_rules}\n{region_lock}\n{color_lock}"

    pose_p = POSE_PROMPTS.get(pose_style, "")
    ratio = batch.get('aspect_ratio', '1:1')
    res = batch.get('resolution', '2K')

    return f"{prompt_core}\n{bg_prompt}\n{pose_p}\n[RATIO:{ratio}|QUAL:{res}]"

async def generate_with_fallback(parts, aspect_ratio_str, resolution_str):
    """Try requested resolution and aspect ratio natively."""
    
    order = [resolution_str]
    if resolution_str == "4K":
        order += ["2K", "1K"]
    elif resolution_str == "2K":
        order += ["1K"]

    last_err = None
    logger.info(f"🚀 GENERATE_WITH_FALLBACK target: {aspect_ratio_str} at {resolution_str}")
    
    for res_key in order:
        try:
            logger.info(f"🔥 Attempting Gemini Generation with aspect_ratio={aspect_ratio_str} and image_size='{res_key}'")
            
            return await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio_str,
                        image_size=res_key
                    )
                )
            )
        except Exception as e:
            logger.warning(f"Generation failed at {res_key} ({aspect_ratio_str}): {str(e)}")
            last_err = e
            continue
    raise last_err

async def process_batch_worker(batch_id):
    async with generation_lock:
        batch = db.get_batch(batch_id)
        if not batch or batch["status"] != "queued":
            return

        try:
            batch["status"] = "generating"
            db.save_batch(batch)
            logger.info(f"Processing batch {batch_id}")

            if not client:
                raise Exception("Gemini client not initialized")

            # Prepare images
            images = []
            for role in ["main", "ref1", "ref2"]:
                img_data = base64.b64decode(batch["images"][role]["b64"])
                img = Image.open(BytesIO(img_data))
                img = compress_image(img)
                images.append(pil_to_part(img))

            prompt = build_prompt(batch)
            parts = [types.Part.from_text(text=prompt)] + images

            response = await generate_with_fallback(
                parts,
                batch.get("aspect_ratio", "1:1"),
                batch.get("resolution", "2K")
            )

            img_bytes = extract_image(response)
            if not img_bytes:
                raise Exception("Failed to extract image from response")

            batch["generated_image"] = base64.b64encode(img_bytes).decode('utf-8')
            batch["status"] = "done"
            db.save_batch(batch)
            logger.info(f"Batch {batch_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {str(e)}")
            batch["status"] = "error"
            batch["error"] = str(e)
            db.save_batch(batch)

async def start_queue_worker():
    """Background loop to process queued batches"""
    db.init_db()
    logger.info("Queue worker started")
    while True:
        batch_id = db.get_next_queued_batch()
        if batch_id:
            await process_batch_worker(batch_id)
        else:
            await asyncio.sleep(2)

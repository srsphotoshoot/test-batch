"""
Optimized Image Upload Service
Handles async uploads with progress tracking and timeout prevention
"""
import asyncio
import os
from io import BytesIO
from PIL import Image, ImageOps
from datetime import datetime
import base64
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

class ImageUploadOptimizer:
    """Optimizes image uploads with compression and async processing"""
    
    # Compression presets
    PRESETS = {
        'fast': {'quality': 75, 'max_dim': 1024, 'chunk_size': 256},
        'quality': {'quality': 85, 'max_dim': 1500, 'chunk_size': 512},
        'balanced': {'quality': 80, 'max_dim': 1200, 'chunk_size': 384}
    }
    
    # Size thresholds (in MB)
    SIZE_THRESHOLDS = {
        'small': 1.0,    # < 1MB
        'medium': 3.0,   # 1-3 MB
        'large': 10.0    # 3-10 MB
    }
    
    @staticmethod
    def get_image_category(file_size_mb: float) -> str:
        """Determine image category by size"""
        if file_size_mb < ImageUploadOptimizer.SIZE_THRESHOLDS['small']:
            return 'small'
        elif file_size_mb < ImageUploadOptimizer.SIZE_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'large'
    
    @staticmethod
    def get_compression_preset(file_size_mb: float, needs_quality: bool = False) -> dict:
        """Get compression preset based on file size and requirements"""
        category = ImageUploadOptimizer.get_image_category(file_size_mb)
        
        if category == 'small' and not needs_quality:
            return ImageUploadOptimizer.PRESETS['fast']
        elif category == 'large' or file_size_mb > ImageUploadOptimizer.SIZE_THRESHOLDS['medium']:
            return ImageUploadOptimizer.PRESETS['balanced']
        else:
            return ImageUploadOptimizer.PRESETS['quality']
    
    @staticmethod
    async def compress_image_async(
        file_content: bytes,
        target_quality: int = 80,
        max_dim: int = 1200,
        progress_callback: Optional[Callable] = None
    ) -> bytes:
        """
        Async image compression with progress tracking
        
        Args:
            file_content: Raw image bytes
            target_quality: JPEG quality (1-100)
            max_dim: Maximum dimension in pixels
            progress_callback: Function to report progress (0-100)
        
        Returns:
            Compressed image bytes in PNG format
        """
        def compress_sync():
            try:
                # Parse image
                if progress_callback:
                    progress_callback(10)
                
                img = Image.open(BytesIO(file_content))
                
                # Handle EXIF and convert
                if progress_callback:
                    progress_callback(20)
                    
                img = ImageOps.exif_transpose(img).convert("RGB")
                
                # Downscale if needed
                if progress_callback:
                    progress_callback(30)
                    
                w, h = img.size
                if max(w, h) > max_dim:
                    ratio = max_dim / float(max(w, h))
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Compress
                if progress_callback:
                    progress_callback(60)
                    
                buf = BytesIO()
                img.save(buf, format="PNG", quality=target_quality, optimize=True)
                compressed = buf.getvalue()
                
                if progress_callback:
                    progress_callback(100)
                
                return compressed
            
            except Exception as e:
                logger.error(f"Compression error: {str(e)}")
                raise
        
        # Run compression in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, compress_sync)
    
    @staticmethod
    async def optimize_upload(
        file_content: bytes,
        filename: str,
        needs_quality: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """
        Optimize image upload with automatic settings
        
        Returns:
            {
                'b64': base64_encoded_image,
                'size_original_mb': float,
                'size_compressed_mb': float,
                'compression_ratio': float,
                'metadata': {...}
            }
        """
        try:
            file_size_mb = len(file_content) / (1024 * 1024)
            
            # Get compression settings
            preset = ImageUploadOptimizer.get_compression_preset(file_size_mb, needs_quality)
            
            logger.info(f"📦 Uploading {filename} ({file_size_mb:.2f}MB) - Using {preset} preset")
            
            # Compress
            compressed = await ImageUploadOptimizer.compress_image_async(
                file_content,
                target_quality=preset['quality'],
                max_dim=preset['max_dim'],
                progress_callback=progress_callback
            )
            
            compressed_size_mb = len(compressed) / (1024 * 1024)
            compression_ratio = file_size_mb / compressed_size_mb if compressed_size_mb > 0 else 1
            
            # Convert to base64
            b64 = base64.b64encode(compressed).decode('utf-8')
            
            logger.info(
                f"✅ {filename} optimized: {file_size_mb:.2f}MB → {compressed_size_mb:.2f}MB "
                f"({compression_ratio:.1f}x compression)"
            )
            
            return {
                'b64': b64,
                'size_original_mb': file_size_mb,
                'size_compressed_mb': compressed_size_mb,
                'compression_ratio': compression_ratio,
                'filename': filename,
                'uploaded_at': datetime.utcnow().isoformat(),
                'preset_used': preset
            }
        
        except Exception as e:
            logger.error(f"Upload optimization failed: {str(e)}")
            raise

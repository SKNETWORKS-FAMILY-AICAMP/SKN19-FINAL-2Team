"""
Image processing utilities for profile images.
Handles validation, conversion, and resizing to 256x256 webp format.
"""

import io
import os
import logging
from typing import BinaryIO

from PIL import Image, ImageOps
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

# Constants (can be overridden by environment variables)
PROFILE_IMAGE_MAX_MB = int(os.environ.get('PROFILE_IMAGE_MAX_MB', '5'))
PROFILE_IMAGE_SIZE = int(os.environ.get('PROFILE_IMAGE_SIZE', '256'))
PROFILE_IMAGE_FORMAT = os.environ.get('PROFILE_IMAGE_FORMAT', 'webp')
PROFILE_IMAGE_QUALITY = 85  # WebP quality (0-100)

# Allowed content types
ALLOWED_CONTENT_TYPES = {
    'image/png',
    'image/jpeg',
    'image/webp',
}

MAX_BYTES = PROFILE_IMAGE_MAX_MB * 1024 * 1024


async def validate_and_read_upload(file: UploadFile) -> bytes:
    """
    Validate uploaded file size and content type, then read it into memory.

    Args:
        file: FastAPI UploadFile object

    Returns:
        File contents as bytes

    Raises:
        HTTPException 400: If content type is not allowed
        HTTPException 413: If file size exceeds limit
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # Early rejection based on Content-Length header (if available)
    if hasattr(file, 'size') and file.size is not None:
        if file.size > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {PROFILE_IMAGE_MAX_MB}MB"
            )

    # Also check Content-Length from headers if available
    if hasattr(file, 'headers'):
        content_length = file.headers.get('content-length')
        if content_length:
            try:
                if int(content_length) > MAX_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {PROFILE_IMAGE_MAX_MB}MB"
                    )
            except (ValueError, TypeError):
                pass  # Ignore invalid Content-Length

    # Read file with size limit (chunked reading)
    chunks = []
    total_size = 0

    try:
        while True:
            chunk = await file.read(8192)  # Read 8KB at a time
            if not chunk:
                break

            total_size += len(chunk)
            if total_size > MAX_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {PROFILE_IMAGE_MAX_MB}MB"
                )

            chunks.append(chunk)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading upload file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file")

    return b''.join(chunks)


def convert_to_profile_webp(image_data: bytes) -> bytes:
    """
    Convert image to 256x256 WebP format with center-crop.

    Processing steps:
    1. Decode image (validate it's a real image)
    2. Apply EXIF orientation correction
    3. Center-crop and resize to 256x256
    4. Encode as WebP

    Args:
        image_data: Raw image bytes (PNG, JPEG, or WebP)

    Returns:
        WebP image bytes (256x256)

    Raises:
        HTTPException 400: If image is corrupted or cannot be decoded
    """
    try:
        # Decode image
        img = Image.open(io.BytesIO(image_data))

        # Apply EXIF orientation correction
        img = ImageOps.exif_transpose(img)

        # Convert to RGB if necessary (WebP requires RGB mode)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        elif img.mode == 'RGBA':
            # Create white background for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background

        # Center-crop to square
        width, height = img.size
        min_dim = min(width, height)

        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim

        img = img.crop((left, top, right, bottom))

        # Resize to target size
        target_size = (PROFILE_IMAGE_SIZE, PROFILE_IMAGE_SIZE)
        img = img.resize(target_size, Image.Resampling.LANCZOS)

        # Encode as WebP
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=PROFILE_IMAGE_QUALITY)
        output.seek(0)

        webp_bytes = output.getvalue()
        logger.info(f"Converted image to WebP: {len(image_data)} -> {len(webp_bytes)} bytes")

        return webp_bytes

    except Exception as e:
        logger.error(f"Image conversion failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file"
        )


async def process_profile_image_upload(file: UploadFile) -> bytes:
    """
    Complete pipeline: validate, read, and convert profile image to WebP.

    Args:
        file: FastAPI UploadFile object

    Returns:
        WebP image bytes (256x256)

    Raises:
        HTTPException: Various error codes depending on validation/conversion failures
    """
    # Validate and read file
    image_data = await validate_and_read_upload(file)

    # Convert to WebP
    webp_data = convert_to_profile_webp(image_data)

    return webp_data

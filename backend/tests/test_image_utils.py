"""
Tests for image_utils module (profile image processing).
"""

import io
import sys
from pathlib import Path
import pytest
from PIL import Image
from fastapi import HTTPException, UploadFile

# Add backend directory to Python path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.image_utils import (
    convert_to_profile_webp,
    validate_and_read_upload,
    process_profile_image_upload,
    MAX_BYTES,
)


def create_test_image_bytes(width: int, height: int, format: str = 'PNG') -> bytes:
    """Helper: Create a test image as bytes."""
    img = Image.new('RGB', (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


class MockUploadFile:
    """Mock UploadFile for testing."""

    def __init__(self, content: bytes, content_type: str, filename: str = "test.png"):
        self.content = content
        self.content_type = content_type
        self.filename = filename
        self._position = 0

    async def read(self, size: int = -1) -> bytes:
        """Simulate chunked reading."""
        if size == -1:
            chunk = self.content[self._position:]
            self._position = len(self.content)
            return chunk
        else:
            chunk = self.content[self._position:self._position + size]
            self._position += len(chunk)
            return chunk


def test_convert_png_to_webp_256x256():
    """Test: PNG input → WebP output, 256x256."""
    # Create a 512x512 PNG
    png_bytes = create_test_image_bytes(512, 512, format='PNG')

    # Convert
    webp_bytes = convert_to_profile_webp(png_bytes)

    # Verify output is WebP and 256x256
    img = Image.open(io.BytesIO(webp_bytes))
    assert img.format == 'WEBP', f"Expected WEBP, got {img.format}"
    assert img.size == (256, 256), f"Expected 256x256, got {img.size}"
    assert img.mode == 'RGB', f"Expected RGB mode, got {img.mode}"


def test_convert_jpeg_to_webp():
    """Test: JPEG input → WebP output."""
    jpeg_bytes = create_test_image_bytes(400, 300, format='JPEG')

    webp_bytes = convert_to_profile_webp(jpeg_bytes)

    img = Image.open(io.BytesIO(webp_bytes))
    assert img.format == 'WEBP'
    assert img.size == (256, 256)


def test_convert_non_square_center_crop():
    """Test: Non-square image is center-cropped."""
    # Create 400x200 image (2:1 aspect ratio)
    wide_bytes = create_test_image_bytes(400, 200, format='PNG')

    webp_bytes = convert_to_profile_webp(wide_bytes)

    img = Image.open(io.BytesIO(webp_bytes))
    assert img.size == (256, 256), "Non-square image should be center-cropped to square"


def test_convert_corrupted_image_raises_400():
    """Test: Corrupted image raises HTTPException 400."""
    corrupted_data = b'\x89PNG\r\n\x1a\n\x00\x00corrupted'

    with pytest.raises(HTTPException) as exc_info:
        convert_to_profile_webp(corrupted_data)

    assert exc_info.value.status_code == 400
    assert "Invalid or corrupted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_and_read_upload_success():
    """Test: Valid upload is read successfully."""
    content = create_test_image_bytes(100, 100)
    upload = MockUploadFile(content, content_type='image/png')

    result = await validate_and_read_upload(upload)

    assert result == content
    assert len(result) > 0


@pytest.mark.asyncio
async def test_validate_and_read_upload_invalid_content_type():
    """Test: Invalid content type raises 400."""
    upload = MockUploadFile(b'fake_gif', content_type='image/gif')

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_read_upload(upload)

    assert exc_info.value.status_code == 400
    assert "Invalid content type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_and_read_upload_file_too_large():
    """Test: File exceeding 5MB raises 413."""
    # Create a file that's 5MB + 1 byte
    oversized_content = b'0' * (MAX_BYTES + 1)
    upload = MockUploadFile(oversized_content, content_type='image/png')

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_read_upload(upload)

    assert exc_info.value.status_code == 413
    assert "File too large" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_profile_image_upload_full_pipeline():
    """Test: Full pipeline (validate + convert) works."""
    png_bytes = create_test_image_bytes(300, 300, format='PNG')
    upload = MockUploadFile(png_bytes, content_type='image/png')

    webp_bytes = await process_profile_image_upload(upload)

    # Verify output
    img = Image.open(io.BytesIO(webp_bytes))
    assert img.format == 'WEBP'
    assert img.size == (256, 256)

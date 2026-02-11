"""
S3 Storage Adapter for profile images and other assets.
Handles S3 upload, deletion, and CDN URL generation.
"""

import os
import uuid
import logging
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Create and return a boto3 S3 client using environment variables."""
    region = os.environ.get('AWS_REGION', 'ap-northeast-2')
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

    kwargs = {
        'region_name': region,
    }

    if aws_access_key_id and aws_secret_access_key:
        kwargs['aws_access_key_id'] = aws_access_key_id
        kwargs['aws_secret_access_key'] = aws_secret_access_key

    if aws_session_token:
        kwargs['aws_session_token'] = aws_session_token

    return boto3.client('s3', **kwargs)


def _get_bucket_name() -> str:
    """Get S3 bucket name from environment."""
    bucket = os.environ.get('AWS_BUCKET_NAME')
    if not bucket:
        raise ValueError("AWS_BUCKET_NAME environment variable is required")
    return bucket


def _get_cdn_domain() -> str:
    """Get CloudFront domain from environment (with trailing slash stripped)."""
    domain = os.environ.get('CLOUDFRONT_DOMAIN')
    if not domain:
        raise ValueError("CLOUDFRONT_DOMAIN environment variable is required")
    return domain.rstrip('/')


def _get_profile_prefix() -> str:
    """Get S3 prefix for profile images."""
    return os.environ.get('S3_PREFIX_PROFILE_IMAGES', 'profile_images')


def build_cdn_url(key: str) -> str:
    """
    Build a full CDN URL from an S3 key.

    Args:
        key: S3 object key (e.g., "profile_images/abc123.webp")

    Returns:
        Full CDN URL (e.g., "https://cdn.example.com/profile_images/abc123.webp")
    """
    cdn_domain = _get_cdn_domain()
    return f"{cdn_domain}/{key}"


def parse_key_from_cdn_url(url: str) -> Optional[str]:
    """
    Parse S3 key from a CDN URL, only if it matches our CDN domain and profile prefix.

    Args:
        url: Full URL (e.g., "https://cdn.example.com/profile_images/abc123.webp")

    Returns:
        S3 key if URL matches our CDN domain and profile prefix, else None
    """
    cdn_domain = _get_cdn_domain()
    profile_prefix = _get_profile_prefix()

    if not url.startswith(cdn_domain):
        return None

    key = url[len(cdn_domain) + 1:]  # +1 to skip the '/'

    if not key.startswith(profile_prefix):
        return None

    return key


def upload_bytes(*, key: str, data: bytes, content_type: str) -> None:
    """
    Upload bytes to S3 with the given key.

    Args:
        key: S3 object key
        data: Binary data to upload
        content_type: MIME type (e.g., "image/webp")

    Raises:
        ClientError: If S3 upload fails
    """
    s3 = _get_s3_client()
    bucket = _get_bucket_name()

    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded {len(data)} bytes to s3://{bucket}/{key}")
    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise


def delete_key(key: str) -> None:
    """
    Delete an S3 object by key (best-effort).

    Args:
        key: S3 object key to delete

    Note:
        Does not raise exception on failure, only logs.
    """
    s3 = _get_s3_client()
    bucket = _get_bucket_name()

    try:
        s3.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted s3://{bucket}/{key}")
    except ClientError as e:
        logger.warning(f"Failed to delete S3 object {key}: {e}")


def upload_profile_webp(data: bytes) -> Tuple[str, str]:
    """
    Upload a profile image (webp format) to S3 with a random UUID key.

    Args:
        data: WebP image binary data

    Returns:
        Tuple of (s3_key, cdn_url)
        - s3_key: S3 object key (e.g., "profile_images/abc-123.webp")
        - cdn_url: Full CDN URL

    Raises:
        ClientError: If S3 upload fails
    """
    profile_prefix = _get_profile_prefix()
    random_uuid = str(uuid.uuid4())
    key = f"{profile_prefix}/{random_uuid}.webp"

    upload_bytes(key=key, data=data, content_type='image/webp')

    cdn_url = build_cdn_url(key)
    return key, cdn_url

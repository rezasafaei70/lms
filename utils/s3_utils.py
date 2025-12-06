"""
S3 URL Utilities
"""
from django.conf import settings


def get_s3_url(s3_key, signed=True):
    """
    Generate full S3 URL from key
    
    Args:
        s3_key: The S3 object key
        signed: Whether to generate a signed URL (default True for private objects)
    
    Returns:
        Full S3 URL string
    """
    if not s3_key:
        return None
    
    # If it's already a full URL, return as is
    s3_key_str = str(s3_key)
    if s3_key_str.startswith('http'):
        return s3_key_str
    
    # For private files, always generate signed URL
    if signed:
        try:
            from utils.storage import get_s3_upload_manager
            manager = get_s3_upload_manager()
            return manager.get_file_url(s3_key_str)
        except Exception as e:
            import logging
            logging.error(f"Failed to generate presigned URL for {s3_key_str}: {e}")
            # Fallback to public URL
            pass
    
    # Generate public URL (fallback or for public files)
    endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', 'https://s3.ir-thr-at1.arvanstorage.ir')
    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'lmspezeshki')
    return f"{endpoint}/{bucket}/{s3_key_str}"


def get_image_url_field():
    """
    Returns a SerializerMethodField getter for S3 image URLs
    """
    def get_image_url(serializer, obj):
        if hasattr(obj, 'image') and obj.image:
            return get_s3_url(str(obj.image))
        return None
    return get_image_url


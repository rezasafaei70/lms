"""
S3 Storage Backend with Multipart Upload Support
"""
import os
import uuid
import logging
from typing import Optional, Tuple
from django.conf import settings
from django.core.files.storage import default_storage
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class S3MediaStorage(S3Boto3Storage):
    """
    Custom S3 storage for media files
    """
    location = 'media'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
    querystring_auth = True
    querystring_expire = 3600  # 1 hour


class S3StaticStorage(S3Boto3Storage):
    """
    Custom S3 storage for static files
    """
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = True
    querystring_auth = False


class S3MultipartUploadManager:
    """
    Manager for S3 Multipart Upload operations
    
    Features:
    - Initialize multipart upload
    - Upload parts
    - Complete/Abort upload
    - Presigned URL generation for direct browser upload
    """
    
    # Minimum part size: 5MB (S3 requirement)
    MIN_PART_SIZE = 5 * 1024 * 1024
    # Maximum part size: 5GB
    MAX_PART_SIZE = 5 * 1024 * 1024 * 1024
    # Maximum file size: 5TB
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024 * 1024
    
    def __init__(self):
        import boto3
        from botocore.config import Config
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            )
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def generate_upload_key(self, folder: str, filename: str) -> str:
        """
        Generate unique S3 key for upload
        """
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return f"media/{folder}/{unique_name}"
    
    def calculate_part_size(self, file_size: int) -> int:
        """
        Calculate optimal part size based on file size
        
        S3 allows maximum 10,000 parts per upload
        """
        # If file is smaller than minimum part size, return file size
        if file_size < self.MIN_PART_SIZE:
            return file_size
        
        # Calculate part size to keep under 10000 parts
        part_size = max(self.MIN_PART_SIZE, file_size // 9999)
        
        # Round up to nearest MB
        part_size = ((part_size + 1024 * 1024 - 1) // (1024 * 1024)) * 1024 * 1024
        
        return min(part_size, self.MAX_PART_SIZE)
    
    def initiate_upload(
        self,
        folder: str,
        filename: str,
        content_type: str,
        file_size: int,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Initiate multipart upload
        
        Returns:
            {
                'upload_id': str,
                'key': str,
                'part_size': int,
                'total_parts': int
            }
        """
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum allowed ({self.MAX_FILE_SIZE} bytes)")
        
        key = self.generate_upload_key(folder, filename)
        part_size = self.calculate_part_size(file_size)
        total_parts = (file_size + part_size - 1) // part_size
        
        extra_args = {
            'Bucket': self.bucket_name,
            'Key': key,
            'ContentType': content_type,
        }
        
        if metadata:
            extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
        
        response = self.s3_client.create_multipart_upload(**extra_args)
        
        logger.info(f"Initiated multipart upload: {key}, upload_id: {response['UploadId']}")
        
        return {
            'upload_id': response['UploadId'],
            'key': key,
            'part_size': part_size,
            'total_parts': total_parts,
            'file_size': file_size,
        }
    
    def generate_presigned_part_urls(
        self,
        key: str,
        upload_id: str,
        total_parts: int,
        expires_in: int = 3600
    ) -> list:
        """
        Generate presigned URLs for each part upload
        
        Returns list of {part_number, presigned_url}
        """
        urls = []
        for part_number in range(1, total_parts + 1):
            presigned_url = self.s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'UploadId': upload_id,
                    'PartNumber': part_number,
                },
                ExpiresIn=expires_in
            )
            urls.append({
                'part_number': part_number,
                'presigned_url': presigned_url,
            })
        
        return urls
    
    def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        body: bytes
    ) -> dict:
        """
        Upload a single part (server-side upload)
        """
        response = self.s3_client.upload_part(
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=body
        )
        
        return {
            'part_number': part_number,
            'etag': response['ETag']
        }
    
    def complete_upload(
        self,
        key: str,
        upload_id: str,
        parts: list
    ) -> dict:
        """
        Complete multipart upload
        
        Args:
            parts: list of {'part_number': int, 'etag': str}
        
        Returns:
            {'location': str, 'key': str, 'url': str}
        """
        # Sort parts by part number
        sorted_parts = sorted(parts, key=lambda x: x['part_number'])
        
        multipart_upload = {
            'Parts': [
                {
                    'ETag': part['etag'],
                    'PartNumber': part['part_number']
                }
                for part in sorted_parts
            ]
        }
        
        response = self.s3_client.complete_multipart_upload(
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id,
            MultipartUpload=multipart_upload
        )
        
        logger.info(f"Completed multipart upload: {key}")
        
        # Generate URL
        url = self.get_file_url(key)
        
        return {
            'location': response.get('Location', ''),
            'key': key,
            'url': url,
        }
    
    def abort_upload(self, key: str, upload_id: str) -> bool:
        """
        Abort multipart upload
        """
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=self.bucket_name,
                Key=key,
                UploadId=upload_id
            )
            logger.info(f"Aborted multipart upload: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to abort upload {key}: {e}")
            return False
    
    def get_file_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get presigned URL for file download
        """
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
            },
            ExpiresIn=expires_in
        )
    
    def delete_file(self, key: str) -> bool:
        """
        Delete file from S3
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Deleted file: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False
    
    def simple_upload(
        self,
        folder: str,
        file_obj,
        filename: str,
        content_type: str
    ) -> dict:
        """
        Simple upload for small files (< 5MB)
        """
        key = self.generate_upload_key(folder, filename)
        
        self.s3_client.upload_fileobj(
            file_obj,
            self.bucket_name,
            key,
            ExtraArgs={
                'ContentType': content_type,
            }
        )
        
        url = self.get_file_url(key)
        
        return {
            'key': key,
            'url': url,
        }


def get_s3_upload_manager() -> S3MultipartUploadManager:
    """
    Get singleton instance of S3MultipartUploadManager
    """
    if not hasattr(get_s3_upload_manager, '_instance'):
        get_s3_upload_manager._instance = S3MultipartUploadManager()
    return get_s3_upload_manager._instance


def upload_file_to_s3(
    file_obj,
    folder: str,
    filename: str = None,
    content_type: str = None
) -> Tuple[str, str]:
    """
    Upload file to S3 using appropriate method based on file size
    
    Returns:
        (key, url)
    """
    manager = get_s3_upload_manager()
    
    filename = filename or getattr(file_obj, 'name', 'file')
    content_type = content_type or getattr(file_obj, 'content_type', 'application/octet-stream')
    
    # Get file size
    file_obj.seek(0, 2)
    file_size = file_obj.tell()
    file_obj.seek(0)
    
    # Use simple upload for small files
    if file_size < manager.MIN_PART_SIZE:
        result = manager.simple_upload(folder, file_obj, filename, content_type)
        return result['key'], result['url']
    
    # Use multipart upload for large files
    upload_info = manager.initiate_upload(
        folder=folder,
        filename=filename,
        content_type=content_type,
        file_size=file_size
    )
    
    parts = []
    part_number = 1
    part_size = upload_info['part_size']
    
    try:
        while True:
            chunk = file_obj.read(part_size)
            if not chunk:
                break
            
            part_result = manager.upload_part(
                key=upload_info['key'],
                upload_id=upload_info['upload_id'],
                part_number=part_number,
                body=chunk
            )
            parts.append(part_result)
            part_number += 1
        
        result = manager.complete_upload(
            key=upload_info['key'],
            upload_id=upload_info['upload_id'],
            parts=parts
        )
        
        return result['key'], result['url']
    
    except Exception as e:
        # Abort upload on failure
        manager.abort_upload(
            key=upload_info['key'],
            upload_id=upload_info['upload_id']
        )
        raise e


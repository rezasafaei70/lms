"""
Custom DRF Fields for S3 File Handling
"""
from rest_framework import serializers
from django.conf import settings


class S3FileField(serializers.Field):
    """
    Custom field for handling S3 file references
    
    Usage in serializer:
        class MySerializer(serializers.ModelSerializer):
            profile_picture = S3FileField(folder='profiles')
            
            class Meta:
                model = MyModel
                fields = ['id', 'profile_picture']
    
    Input (write):
        - Direct file upload in multipart form
        - S3 key string (from multipart upload)
        - File ID from UploadedFile
        
    Output (read):
        {
            "key": "media/profiles/xxx.jpg",
            "url": "https://...",
            "filename": "profile.jpg"
        }
    """
    
    def __init__(self, folder='uploads', **kwargs):
        self.folder = folder
        super().__init__(**kwargs)
    
    def to_representation(self, value):
        """
        Convert model field value to output representation
        """
        if not value:
            return None
        
        # If it's a Django FileField/ImageField
        if hasattr(value, 'name') and hasattr(value, 'url'):
            return {
                'key': value.name,
                'url': value.url if value else None,
                'filename': value.name.split('/')[-1] if value.name else None,
            }
        
        # If it's a string (S3 key)
        if isinstance(value, str):
            from utils.storage import get_s3_upload_manager
            try:
                manager = get_s3_upload_manager()
                url = manager.get_file_url(value)
                return {
                    'key': value,
                    'url': url,
                    'filename': value.split('/')[-1],
                }
            except Exception:
                return {
                    'key': value,
                    'url': None,
                    'filename': value.split('/')[-1],
                }
        
        return None
    
    def to_internal_value(self, data):
        """
        Convert input data to model field value
        """
        if not data:
            return None
        
        # If it's a file object (direct upload)
        if hasattr(data, 'read'):
            from utils.storage import upload_file_to_s3
            key, url = upload_file_to_s3(
                file_obj=data,
                folder=self.folder,
                filename=getattr(data, 'name', 'file'),
                content_type=getattr(data, 'content_type', 'application/octet-stream')
            )
            return key
        
        # If it's a string (S3 key or file_id)
        if isinstance(data, str):
            # Check if it's a UUID (file_id)
            import uuid
            try:
                file_id = uuid.UUID(data)
                from apps.core.models import UploadedFile
                uploaded_file = UploadedFile.objects.get(id=file_id)
                uploaded_file.is_temp = False
                uploaded_file.save()
                return uploaded_file.s3_key
            except (ValueError, UploadedFile.DoesNotExist):
                # It's an S3 key
                return data
        
        # If it's a dict with 'key' or 'file_id'
        if isinstance(data, dict):
            if 'key' in data:
                return data['key']
            if 'file_id' in data:
                from apps.core.models import UploadedFile
                uploaded_file = UploadedFile.objects.get(id=data['file_id'])
                uploaded_file.is_temp = False
                uploaded_file.save()
                return uploaded_file.s3_key
        
        raise serializers.ValidationError('فرمت فایل نامعتبر است')


class S3ImageField(S3FileField):
    """
    S3 field specifically for images with validation
    """
    
    ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    
    def to_internal_value(self, data):
        if hasattr(data, 'content_type'):
            if data.content_type not in self.ALLOWED_TYPES:
                raise serializers.ValidationError(
                    'فرمت تصویر نامعتبر است. فرمت‌های مجاز: JPEG, PNG, GIF, WebP'
                )
        
        return super().to_internal_value(data)


class S3VideoField(S3FileField):
    """
    S3 field specifically for videos with validation
    """
    
    ALLOWED_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']
    
    def to_internal_value(self, data):
        if hasattr(data, 'content_type'):
            if data.content_type not in self.ALLOWED_TYPES:
                raise serializers.ValidationError(
                    'فرمت ویدیو نامعتبر است. فرمت‌های مجاز: MP4, WebM, MOV'
                )
        
        return super().to_internal_value(data)


class S3DocumentField(S3FileField):
    """
    S3 field specifically for documents with validation
    """
    
    ALLOWED_TYPES = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ]
    
    def to_internal_value(self, data):
        if hasattr(data, 'content_type'):
            if data.content_type not in self.ALLOWED_TYPES:
                raise serializers.ValidationError(
                    'فرمت فایل نامعتبر است. فرمت‌های مجاز: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX'
                )
        
        return super().to_internal_value(data)


class MultipleS3FilesField(serializers.ListField):
    """
    Field for handling multiple S3 file uploads
    
    Usage:
        attachments = MultipleS3FilesField(folder='attachments', max_files=10)
    """
    
    def __init__(self, folder='uploads', max_files=10, **kwargs):
        self.folder = folder
        self.max_files = max_files
        kwargs['child'] = S3FileField(folder=folder)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        if len(data) > self.max_files:
            raise serializers.ValidationError(
                f'حداکثر {self.max_files} فایل مجاز است'
            )
        return super().to_internal_value(data)


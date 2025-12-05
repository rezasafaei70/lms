"""
Core Serializers - File Upload
"""
from rest_framework import serializers
from django.conf import settings
from .models import MultipartUpload, UploadedFile


class InitiateUploadSerializer(serializers.Serializer):
    """
    Serializer for initiating multipart upload
    """
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=100)
    file_size = serializers.IntegerField(min_value=1)
    
    # Target (optional - for direct model attachment)
    target_folder = serializers.CharField(
        max_length=100, 
        default='uploads',
        help_text='پوشه مقصد در S3'
    )
    target_model = serializers.CharField(
        max_length=100, 
        required=False,
        allow_blank=True,
        help_text='نام مدل مقصد (مثلا: accounts.User)'
    )
    target_field = serializers.CharField(
        max_length=100, 
        required=False,
        allow_blank=True,
        help_text='نام فیلد (مثلا: profile_picture)'
    )
    target_object_id = serializers.CharField(
        max_length=100, 
        required=False,
        allow_blank=True,
        help_text='شناسه آبجکت'
    )
    
    def validate_file_size(self, value):
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024)  # 100MB default
        if value > max_size:
            raise serializers.ValidationError(
                f'حجم فایل نمی‌تواند بیشتر از {max_size // (1024*1024)} مگابایت باشد'
            )
        return value
    
    def validate_content_type(self, value):
        allowed_types = getattr(settings, 'ALLOWED_UPLOAD_CONTENT_TYPES', None)
        if allowed_types and value not in allowed_types:
            raise serializers.ValidationError(
                f'نوع فایل {value} مجاز نیست'
            )
        return value


class InitiateUploadResponseSerializer(serializers.Serializer):
    """
    Response serializer for initiated upload
    """
    upload_id = serializers.UUIDField()
    s3_upload_id = serializers.CharField()
    s3_key = serializers.CharField()
    part_size = serializers.IntegerField()
    total_parts = serializers.IntegerField()
    presigned_urls = serializers.ListField(
        child=serializers.DictField()
    )


class UploadPartSerializer(serializers.Serializer):
    """
    Serializer for reporting uploaded part
    """
    upload_id = serializers.UUIDField()
    part_number = serializers.IntegerField(min_value=1)
    etag = serializers.CharField(max_length=255)


class CompleteUploadSerializer(serializers.Serializer):
    """
    Serializer for completing multipart upload
    """
    upload_id = serializers.UUIDField()
    parts = serializers.ListField(
        child=serializers.DictField(),
        help_text='لیست قسمت‌ها: [{part_number: 1, etag: "xxx"}, ...]'
    )
    
    def validate_parts(self, value):
        if not value:
            raise serializers.ValidationError('لیست قسمت‌ها نمی‌تواند خالی باشد')
        
        for part in value:
            if 'part_number' not in part or 'etag' not in part:
                raise serializers.ValidationError(
                    'هر قسمت باید شامل part_number و etag باشد'
                )
        return value


class CompleteUploadResponseSerializer(serializers.Serializer):
    """
    Response serializer for completed upload
    """
    key = serializers.CharField()
    url = serializers.CharField()
    file_id = serializers.UUIDField()


class AbortUploadSerializer(serializers.Serializer):
    """
    Serializer for aborting upload
    """
    upload_id = serializers.UUIDField()


class MultipartUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for MultipartUpload model
    """
    progress_percent = serializers.FloatField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MultipartUpload
        fields = [
            'id', 'upload_id', 's3_key', 'original_filename',
            'content_type', 'file_size', 'part_size', 'total_parts',
            'uploaded_parts', 'status', 'target_folder', 'target_model',
            'target_field', 'target_object_id', 'progress_percent',
            'is_expired', 'created_at', 'completed_at', 'final_url'
        ]
        read_only_fields = ['id', 'created_at']


class UploadedFileSerializer(serializers.ModelSerializer):
    """
    Serializer for UploadedFile model
    """
    url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = UploadedFile
        fields = [
            'id', 's3_key', 'original_filename', 'content_type',
            'file_size', 'file_size_mb', 'url', 'is_temp',
            'attached_to_model', 'attached_to_id', 'attached_to_field',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_url(self, obj):
        return obj.get_url()
    
    def get_file_size_mb(self, obj):
        return round(obj.file_size / (1024 * 1024), 2)


class SimpleUploadSerializer(serializers.Serializer):
    """
    Serializer for simple file upload (small files)
    """
    file = serializers.FileField()
    folder = serializers.CharField(max_length=100, default='uploads')
    
    # Target (optional)
    target_model = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_field = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_object_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_file(self, value):
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f'حجم فایل نمی‌تواند بیشتر از {max_size // (1024*1024)} مگابایت باشد'
            )
        return value


class S3FileFieldSerializer(serializers.Serializer):
    """
    Custom field serializer for S3 files
    Use this in your serializers to handle S3 file references
    """
    key = serializers.CharField(required=False, allow_blank=True)
    url = serializers.CharField(read_only=True)
    filename = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)


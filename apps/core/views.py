"""
Core Views - File Upload API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import MultipartUpload, UploadedFile
from .serializers import (
    InitiateUploadSerializer,
    InitiateUploadResponseSerializer,
    UploadPartSerializer,
    CompleteUploadSerializer,
    CompleteUploadResponseSerializer,
    AbortUploadSerializer,
    MultipartUploadSerializer,
    UploadedFileSerializer,
    SimpleUploadSerializer,
)
from utils.storage import get_s3_upload_manager, upload_file_to_s3

logger = logging.getLogger(__name__)


class FileUploadViewSet(viewsets.ViewSet):
    """
    ViewSet for handling file uploads
    
    Supports:
    - Simple upload (for small files < 5MB)
    - Multipart upload (for large files)
    - Direct browser upload using presigned URLs
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_upload(self, request):
        """
        Initiate multipart upload
        
        POST /api/v1/files/initiate/
        {
            "filename": "video.mp4",
            "content_type": "video/mp4",
            "file_size": 104857600,
            "target_folder": "courses/videos"
        }
        
        Returns presigned URLs for each part upload
        """
        serializer = InitiateUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            manager = get_s3_upload_manager()
            
            # Initiate S3 multipart upload
            upload_info = manager.initiate_upload(
                folder=data['target_folder'],
                filename=data['filename'],
                content_type=data['content_type'],
                file_size=data['file_size'],
                metadata={
                    'uploaded_by': str(request.user.id),
                    'original_filename': data['filename']
                }
            )
            
            # Generate presigned URLs for all parts
            presigned_urls = manager.generate_presigned_part_urls(
                key=upload_info['key'],
                upload_id=upload_info['upload_id'],
                total_parts=upload_info['total_parts'],
                expires_in=3600  # 1 hour
            )
            
            # Create tracking record
            multipart_upload = MultipartUpload.objects.create(
                upload_id=upload_info['upload_id'],
                s3_key=upload_info['key'],
                original_filename=data['filename'],
                content_type=data['content_type'],
                file_size=data['file_size'],
                part_size=upload_info['part_size'],
                total_parts=upload_info['total_parts'],
                target_folder=data['target_folder'],
                target_model=data.get('target_model', ''),
                target_field=data.get('target_field', ''),
                target_object_id=data.get('target_object_id', ''),
                user=request.user
            )
            
            response_data = {
                'upload_id': multipart_upload.id,
                's3_upload_id': upload_info['upload_id'],
                's3_key': upload_info['key'],
                'part_size': upload_info['part_size'],
                'total_parts': upload_info['total_parts'],
                'presigned_urls': presigned_urls
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to initiate upload: {e}")
            return Response(
                {'error': f'خطا در شروع آپلود: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='report-part')
    def report_part(self, request):
        """
        Report uploaded part (called by frontend after each part upload)
        
        POST /api/v1/files/report-part/
        {
            "upload_id": "uuid",
            "part_number": 1,
            "etag": "xxx"
        }
        """
        serializer = UploadPartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        multipart_upload = get_object_or_404(
            MultipartUpload,
            id=data['upload_id'],
            user=request.user
        )
        
        if multipart_upload.status not in [
            MultipartUpload.UploadStatus.INITIATED,
            MultipartUpload.UploadStatus.IN_PROGRESS
        ]:
            return Response(
                {'error': 'این آپلود قابل ادامه نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add part info
        multipart_upload.add_part(
            part_number=data['part_number'],
            etag=data['etag']
        )
        
        return Response({
            'message': 'قسمت ثبت شد',
            'progress': multipart_upload.progress_percent,
            'uploaded_parts': multipart_upload.uploaded_parts,
            'total_parts': multipart_upload.total_parts
        })
    
    @action(detail=False, methods=['post'], url_path='complete')
    def complete_upload(self, request):
        """
        Complete multipart upload
        
        POST /api/v1/files/complete/
        {
            "upload_id": "uuid",
            "parts": [
                {"part_number": 1, "etag": "xxx"},
                {"part_number": 2, "etag": "yyy"}
            ]
        }
        """
        serializer = CompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        multipart_upload = get_object_or_404(
            MultipartUpload,
            id=data['upload_id'],
            user=request.user
        )
        
        if multipart_upload.status == MultipartUpload.UploadStatus.COMPLETED:
            return Response(
                {'error': 'این آپلود قبلاً تکمیل شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = get_s3_upload_manager()
            
            # Complete S3 upload
            result = manager.complete_upload(
                key=multipart_upload.s3_key,
                upload_id=multipart_upload.upload_id,
                parts=data['parts']
            )
            
            # Update tracking record
            multipart_upload.complete(final_url=result['url'])
            
            # Create UploadedFile record
            uploaded_file = UploadedFile.objects.create(
                s3_key=multipart_upload.s3_key,
                original_filename=multipart_upload.original_filename,
                content_type=multipart_upload.content_type,
                file_size=multipart_upload.file_size,
                user=request.user,
                attached_to_model=multipart_upload.target_model,
                attached_to_id=multipart_upload.target_object_id,
                attached_to_field=multipart_upload.target_field,
                is_temp=True  # Will be set to False when attached to a model
            )
            
            return Response({
                'key': result['key'],
                'url': result['url'],
                'file_id': uploaded_file.id
            })
            
        except Exception as e:
            logger.error(f"Failed to complete upload: {e}")
            multipart_upload.fail(str(e))
            return Response(
                {'error': f'خطا در تکمیل آپلود: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='abort')
    def abort_upload(self, request):
        """
        Abort multipart upload
        
        POST /api/v1/files/abort/
        {
            "upload_id": "uuid"
        }
        """
        serializer = AbortUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        multipart_upload = get_object_or_404(
            MultipartUpload,
            id=data['upload_id'],
            user=request.user
        )
        
        if multipart_upload.status in [
            MultipartUpload.UploadStatus.COMPLETED,
            MultipartUpload.UploadStatus.ABORTED
        ]:
            return Response(
                {'error': 'این آپلود قابل لغو نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = get_s3_upload_manager()
            manager.abort_upload(
                key=multipart_upload.s3_key,
                upload_id=multipart_upload.upload_id
            )
            
            multipart_upload.abort()
            
            return Response({'message': 'آپلود لغو شد'})
            
        except Exception as e:
            logger.error(f"Failed to abort upload: {e}")
            return Response(
                {'error': f'خطا در لغو آپلود: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='simple')
    def simple_upload(self, request):
        """
        Simple file upload (for small files)
        
        POST /api/v1/files/simple/
        Content-Type: multipart/form-data
        
        file: <file>
        folder: "uploads"
        """
        serializer = SimpleUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        file = data['file']
        
        try:
            key, url = upload_file_to_s3(
                file_obj=file,
                folder=data['folder'],
                filename=file.name,
                content_type=file.content_type
            )
            
            # Create UploadedFile record
            uploaded_file = UploadedFile.objects.create(
                s3_key=key,
                original_filename=file.name,
                content_type=file.content_type,
                file_size=file.size,
                user=request.user,
                attached_to_model=data.get('target_model', ''),
                attached_to_id=data.get('target_object_id', ''),
                attached_to_field=data.get('target_field', ''),
                is_temp=True
            )
            
            return Response({
                'key': key,
                'url': url,
                'file_id': uploaded_file.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return Response(
                {'error': f'خطا در آپلود فایل: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='status/(?P<upload_id>[^/.]+)')
    def upload_status(self, request, upload_id=None):
        """
        Get upload status
        
        GET /api/v1/files/status/{upload_id}/
        """
        multipart_upload = get_object_or_404(
            MultipartUpload,
            id=upload_id,
            user=request.user
        )
        
        serializer = MultipartUploadSerializer(multipart_upload)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-uploads')
    def my_uploads(self, request):
        """
        Get user's uploads
        
        GET /api/v1/files/my-uploads/
        """
        uploads = MultipartUpload.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]
        
        serializer = MultipartUploadSerializer(uploads, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-files')
    def my_files(self, request):
        """
        Get user's uploaded files
        
        GET /api/v1/files/my-files/
        """
        files = UploadedFile.objects.filter(
            user=request.user,
            is_deleted=False
        ).order_by('-created_at')[:100]
        
        serializer = UploadedFileSerializer(files, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'], url_path='delete/(?P<file_id>[^/.]+)')
    def delete_file(self, request, file_id=None):
        """
        Delete uploaded file
        
        DELETE /api/v1/files/delete/{file_id}/
        """
        uploaded_file = get_object_or_404(
            UploadedFile,
            id=file_id,
            user=request.user
        )
        
        try:
            # Delete from S3
            uploaded_file.delete_from_s3()
            
            # Mark as deleted
            uploaded_file.is_deleted = True
            uploaded_file.deleted_at = timezone.now()
            uploaded_file.save()
            
            return Response({'message': 'فایل حذف شد'})
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return Response(
                {'error': f'خطا در حذف فایل: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='get-url')
    def get_presigned_url(self, request):
        """
        Get presigned URL for a file
        
        POST /api/v1/files/get-url/
        {
            "key": "media/uploads/xxx.pdf",
            "expires_in": 3600
        }
        """
        key = request.data.get('key')
        expires_in = request.data.get('expires_in', 3600)
        
        if not key:
            return Response(
                {'error': 'کلید فایل الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = get_s3_upload_manager()
            url = manager.get_file_url(key, expires_in)
            
            return Response({'url': url})
            
        except Exception as e:
            logger.error(f"Failed to get URL: {e}")
            return Response(
                {'error': f'خطا در دریافت آدرس: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


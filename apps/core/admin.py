"""
Core App Admin Configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import MultipartUpload, UploadedFile


@admin.register(MultipartUpload)
class MultipartUploadAdmin(admin.ModelAdmin):
    """
    Admin for MultipartUpload
    """
    list_display = [
        'id', 'original_filename', 'user', 'status',
        'progress_display', 'file_size_display', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'target_folder']
    search_fields = ['original_filename', 'user__mobile', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'id', 'upload_id', 's3_key', 'original_filename', 'content_type',
        'file_size', 'part_size', 'total_parts', 'uploaded_parts',
        'parts_data', 'status', 'target_folder', 'target_model',
        'target_field', 'target_object_id', 'user', 'completed_at',
        'final_url', 'error_message', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    
    def progress_display(self, obj):
        percent = obj.progress_percent
        color = 'green' if percent == 100 else 'orange' if percent > 0 else 'gray'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percent
        )
    progress_display.short_description = 'پیشرفت'
    
    def file_size_display(self, obj):
        size_mb = obj.file_size / (1024 * 1024)
        return f'{size_mb:.2f} MB'
    file_size_display.short_description = 'حجم'


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """
    Admin for UploadedFile
    """
    list_display = [
        'id', 'original_filename', 'user', 'content_type',
        'file_size_display', 'is_temp', 'is_deleted', 'created_at'
    ]
    list_filter = ['is_temp', 'is_deleted', 'content_type', 'created_at']
    search_fields = ['original_filename', 's3_key', 'user__mobile']
    readonly_fields = [
        'id', 's3_key', 'original_filename', 'content_type', 'file_size',
        'user', 'attached_to_model', 'attached_to_id', 'attached_to_field',
        'created_at', 'updated_at', 'deleted_at'
    ]
    ordering = ['-created_at']
    actions = ['mark_as_permanent', 'delete_from_s3']
    
    def file_size_display(self, obj):
        size_mb = obj.file_size / (1024 * 1024)
        return f'{size_mb:.2f} MB'
    file_size_display.short_description = 'حجم'
    
    @admin.action(description='تبدیل به فایل دائمی')
    def mark_as_permanent(self, request, queryset):
        queryset.update(is_temp=False)
    
    @admin.action(description='حذف از S3')
    def delete_from_s3(self, request, queryset):
        for file in queryset:
            file.delete_from_s3()
            file.is_deleted = True
            file.save()


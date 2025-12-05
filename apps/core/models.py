"""
Core Models - Including File Upload Tracking
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UUIDModel(models.Model):
    """
    Abstract base model with UUID primary key
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(UUIDModel):
    """
    Abstract base model with UUID and timestamp fields
    """
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """
    Manager that filters out soft-deleted objects
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def all_with_deleted(self):
        return super().get_queryset()
    
    def deleted_only(self):
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModel(models.Model):
    """
    Abstract base model for soft delete functionality
    """
    is_deleted = models.BooleanField(_('حذف شده'), default=False)
    deleted_at = models.DateTimeField(_('تاریخ حذف'), null=True, blank=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """
        Soft delete - mark as deleted instead of actual deletion
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def hard_delete(self, using=None, keep_parents=False):
        """
        Actually delete from database
        """
        super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """
        Restore soft-deleted object
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class SystemSettings(TimeStampedModel):
    """
    System-wide settings and configuration
    """
    class SettingType(models.TextChoices):
        FINANCIAL = 'financial', _('مالی')
        ACADEMIC = 'academic', _('آموزشی')
        GENERAL = 'general', _('عمومی')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(_('کلید'), max_length=100, unique=True)
    value = models.TextField(_('مقدار'))
    setting_type = models.CharField(
        _('نوع تنظیمات'),
        max_length=20,
        choices=SettingType.choices,
        default=SettingType.GENERAL
    )
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    
    class Meta:
        verbose_name = _('تنظیمات سیستم')
        verbose_name_plural = _('تنظیمات سیستم')
        db_table = 'system_settings'
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    @classmethod
    def get_setting(cls, key, default=None):
        """
        Get a setting value by key
        """
        try:
            setting = cls.objects.get(key=key, is_active=True)
            return setting.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_setting(cls, key, value, setting_type='general', description=''):
        """
        Set a setting value
        """
        setting, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'setting_type': setting_type,
                'description': description
            }
        )
        return setting
    
    @classmethod
    def get_annual_registration_fee(cls):
        """
        Get annual registration fee
        """
        value = cls.get_setting('annual_registration_fee', '0')
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0


class MultipartUpload(TimeStampedModel):
    """
    Track multipart upload progress
    """
    class UploadStatus(models.TextChoices):
        INITIATED = 'initiated', _('شروع شده')
        IN_PROGRESS = 'in_progress', _('در حال آپلود')
        COMPLETED = 'completed', _('تکمیل شده')
        FAILED = 'failed', _('ناموفق')
        ABORTED = 'aborted', _('لغو شده')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # S3 Upload Info
    upload_id = models.CharField(_('شناسه آپلود S3'), max_length=255)
    s3_key = models.CharField(_('کلید S3'), max_length=500)
    
    # File Info
    original_filename = models.CharField(_('نام فایل اصلی'), max_length=255)
    content_type = models.CharField(_('نوع محتوا'), max_length=100)
    file_size = models.BigIntegerField(_('حجم فایل'))
    
    # Upload Settings
    part_size = models.IntegerField(_('اندازه هر قسمت'))
    total_parts = models.IntegerField(_('تعداد کل قسمت‌ها'))
    uploaded_parts = models.IntegerField(_('قسمت‌های آپلود شده'), default=0)
    
    # Parts tracking (stored as JSON)
    parts_data = models.JSONField(_('اطلاعات قسمت‌ها'), default=list)
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.INITIATED
    )
    
    # Upload Target
    target_folder = models.CharField(_('پوشه مقصد'), max_length=100)
    target_model = models.CharField(_('مدل مقصد'), max_length=100, blank=True)
    target_field = models.CharField(_('فیلد مقصد'), max_length=100, blank=True)
    target_object_id = models.CharField(_('شناسه آبجکت'), max_length=100, blank=True)
    
    # User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploads',
        verbose_name=_('کاربر')
    )
    
    # Completion
    completed_at = models.DateTimeField(_('تاریخ تکمیل'), null=True, blank=True)
    final_url = models.URLField(_('آدرس نهایی'), max_length=1000, blank=True)
    
    # Error tracking
    error_message = models.TextField(_('پیام خطا'), blank=True)
    
    class Meta:
        verbose_name = _('آپلود چندبخشی')
        verbose_name_plural = _('آپلودهای چندبخشی')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.status}"
    
    @property
    def progress_percent(self) -> float:
        if self.total_parts == 0:
            return 0
        return round((self.uploaded_parts / self.total_parts) * 100, 2)
    
    @property
    def is_expired(self) -> bool:
        """
        Check if upload has expired (24 hours)
        """
        if self.status in [self.UploadStatus.COMPLETED, self.UploadStatus.ABORTED]:
            return False
        return timezone.now() > self.created_at + timezone.timedelta(hours=24)
    
    def add_part(self, part_number: int, etag: str):
        """
        Add uploaded part info
        """
        self.parts_data.append({
            'part_number': part_number,
            'etag': etag
        })
        self.uploaded_parts = len(self.parts_data)
        self.status = self.UploadStatus.IN_PROGRESS
        self.save()
    
    def complete(self, final_url: str):
        """
        Mark upload as completed
        """
        self.status = self.UploadStatus.COMPLETED
        self.completed_at = timezone.now()
        self.final_url = final_url
        self.save()
    
    def fail(self, error_message: str):
        """
        Mark upload as failed
        """
        self.status = self.UploadStatus.FAILED
        self.error_message = error_message
        self.save()
    
    def abort(self):
        """
        Mark upload as aborted
        """
        self.status = self.UploadStatus.ABORTED
        self.save()


class UploadedFile(TimeStampedModel):
    """
    Track all uploaded files for management
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File Info
    s3_key = models.CharField(_('کلید S3'), max_length=500, unique=True)
    original_filename = models.CharField(_('نام فایل اصلی'), max_length=255)
    content_type = models.CharField(_('نوع محتوا'), max_length=100)
    file_size = models.BigIntegerField(_('حجم فایل'))
    
    # User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='files',
        verbose_name=_('کاربر')
    )
    
    # Reference to what this file is attached to
    attached_to_model = models.CharField(_('مدل پیوست'), max_length=100, blank=True)
    attached_to_id = models.CharField(_('شناسه پیوست'), max_length=100, blank=True)
    attached_to_field = models.CharField(_('فیلد پیوست'), max_length=100, blank=True)
    
    # Status
    is_temp = models.BooleanField(_('موقت'), default=True)
    is_deleted = models.BooleanField(_('حذف شده'), default=False)
    deleted_at = models.DateTimeField(_('تاریخ حذف'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('فایل آپلود شده')
        verbose_name_plural = _('فایل‌های آپلود شده')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.original_filename
    
    def get_url(self, expires_in: int = 3600) -> str:
        """
        Get presigned URL for file
        """
        from utils.storage import get_s3_upload_manager
        manager = get_s3_upload_manager()
        return manager.get_file_url(self.s3_key, expires_in)
    
    def delete_from_s3(self):
        """
        Delete file from S3
        """
        from utils.storage import get_s3_upload_manager
        manager = get_s3_upload_manager()
        return manager.delete_file(self.s3_key)

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class Notification(TimeStampedModel):
    """
    Notification Model
    """
    class NotificationType(models.TextChoices):
        INFO = 'info', _('اطلاعات')
        SUCCESS = 'success', _('موفقیت')
        WARNING = 'warning', _('هشدار')
        ERROR = 'error', _('خطا')
        REMINDER = 'reminder', _('یادآوری')

    class NotificationCategory(models.TextChoices):
        ENROLLMENT = 'enrollment', _('ثبت‌نام')
        PAYMENT = 'payment', _('پرداخت')
        ATTENDANCE = 'attendance', _('حضور و غیاب')
        CLASS = 'class', _('کلاس')
        EXAM = 'exam', _('آزمون')
        ANNOUNCEMENT = 'announcement', _('اطلاعیه')
        SYSTEM = 'system', _('سیستم')

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('گیرنده')
    )
    
    # Content
    title = models.CharField(_('عنوان'), max_length=255)
    message = models.TextField(_('پیام'))
    
    # Type & Category
    notification_type = models.CharField(
        _('نوع'),
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    
    category = models.CharField(
        _('دسته‌بندی'),
        max_length=20,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM
    )
    
    # Link
    action_url = models.CharField(
        _('لینک عملیات'),
        max_length=500,
        null=True,
        blank=True
    )
    
    # Status
    is_read = models.BooleanField(_('خوانده شده'), default=False)
    read_at = models.DateTimeField(_('زمان خواندن'), null=True, blank=True)
    
    # Channel flags
    sent_via_sms = models.BooleanField(_('ارسال SMS'), default=False)
    sent_via_email = models.BooleanField(_('ارسال ایمیل'), default=False)
    sent_via_push = models.BooleanField(_('ارسال Push'), default=False)
    
    # Metadata
    metadata = models.JSONField(_('متادیتا'), default=dict, blank=True)
    
    # Expiration
    expires_at = models.DateTimeField(_('تاریخ انقضا'), null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = _('اعلان')
        verbose_name_plural = _('اعلانات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationTemplate(TimeStampedModel):
    """
    Notification Template Model
    """
    class TemplateType(models.TextChoices):
        SMS = 'sms', _('SMS')
        EMAIL = 'email', _('ایمیل')
        PUSH = 'push', _('Push')
        IN_APP = 'in_app', _('داخل برنامه')

    name = models.CharField(_('نام'), max_length=100, unique=True)
    template_type = models.CharField(
        _('نوع قالب'),
        max_length=20,
        choices=TemplateType.choices
    )
    
    # Content
    subject = models.CharField(
        _('موضوع'),
        max_length=255,
        null=True,
        blank=True,
        help_text='برای ایمیل'
    )
    content = models.TextField(
        _('محتوا'),
        help_text='از {{variable}} برای متغیرها استفاده کنید'
    )
    
    # Status
    is_active = models.BooleanField(_('فعال'), default=True)
    
    # Variables info
    available_variables = models.JSONField(
        _('متغیرهای موجود'),
        default=list,
        help_text='لیست متغیرهای قابل استفاده'
    )
    
    description = models.TextField(_('توضیحات'), null=True, blank=True)

    class Meta:
        db_table = 'notification_templates'
        verbose_name = _('قالب اعلان')
        verbose_name_plural = _('قالب‌های اعلان')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def render(self, context):
        """Render template with context"""
        import re
        content = self.content
        
        for key, value in context.items():
            pattern = r'\{\{' + key + r'\}\}'
            content = re.sub(pattern, str(value), content)
        
        return content


class UserNotificationSettings(TimeStampedModel):
    """
    User Notification Settings
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name=_('کاربر')
    )
    
    # Channel preferences
    enable_sms = models.BooleanField(_('فعال‌سازی SMS'), default=True)
    enable_email = models.BooleanField(_('فعال‌سازی ایمیل'), default=True)
    enable_push = models.BooleanField(_('فعال‌سازی Push'), default=True)
    enable_in_app = models.BooleanField(_('فعال‌سازی داخل برنامه'), default=True)
    
    # Category preferences
    notify_enrollment = models.BooleanField(_('اعلان ثبت‌نام'), default=True)
    notify_payment = models.BooleanField(_('اعلان پرداخت'), default=True)
    notify_attendance = models.BooleanField(_('اعلان حضور و غیاب'), default=True)
    notify_class = models.BooleanField(_('اعلان کلاس'), default=True)
    notify_exam = models.BooleanField(_('اعلان آزمون'), default=True)
    notify_announcement = models.BooleanField(_('اعلان اطلاعیه'), default=True)
    
    # Timing
    quiet_hours_start = models.TimeField(
        _('شروع ساعات سکوت'),
        null=True,
        blank=True,
        help_text='اعلان‌ها در این بازه ارسال نمی‌شوند'
    )
    quiet_hours_end = models.TimeField(
        _('پایان ساعات سکوت'),
        null=True,
        blank=True
    )
    
    # Frequency
    digest_mode = models.BooleanField(
        _('حالت خلاصه'),
        default=False,
        help_text='ارسال اعلان‌ها به صورت خلاصه روزانه'
    )

    class Meta:
        db_table = 'user_notification_settings'
        verbose_name = _('تنظیمات اعلان کاربر')
        verbose_name_plural = _('تنظیمات اعلانات کاربران')

    def __str__(self):
        return f"تنظیمات {self.user.get_full_name()}"


class SMSLog(TimeStampedModel):
    """
    SMS Log Model
    """
    class SMSStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        SENT = 'sent', _('ارسال شده')
        DELIVERED = 'delivered', _('تحویل داده شده')
        FAILED = 'failed', _('ناموفق')

    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_logs',
        verbose_name=_('گیرنده')
    )
    
    mobile = models.CharField(_('شماره موبایل'), max_length=11)
    message = models.TextField(_('پیام'))
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=SMSStatus.choices,
        default=SMSStatus.PENDING
    )
    
    # Gateway info
    gateway_message_id = models.CharField(
        _('شناسه پیام درگاه'),
        max_length=255,
        null=True,
        blank=True
    )
    
    # Timing
    sent_at = models.DateTimeField(_('زمان ارسال'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('زمان تحویل'), null=True, blank=True)
    
    # Error
    error_message = models.TextField(_('پیام خطا'), null=True, blank=True)
    
    # Cost
    cost = models.DecimalField(
        _('هزینه'),
        max_digits=10,
        decimal_places=0,
        default=0
    )

    class Meta:
        db_table = 'sms_logs'
        verbose_name = _('لاگ SMS')
        verbose_name_plural = _('لاگ‌های SMS')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"SMS to {self.mobile} - {self.status}"


class Announcement(TimeStampedModel):
    """
    General Announcement Model
    """
    class AnnouncementType(models.TextChoices):
        GENERAL = 'general', _('عمومی')
        URGENT = 'urgent', _('فوری')
        MAINTENANCE = 'maintenance', _('تعمیرات')
        EVENT = 'event', _('رویداد')

    class TargetAudience(models.TextChoices):
        ALL = 'all', _('همه')
        STUDENTS = 'students', _('دانش‌آموزان')
        TEACHERS = 'teachers', _('معلمان')
        STAFF = 'staff', _('کارمندان')
        CUSTOM = 'custom', _('سفارشی')

    title = models.CharField(_('عنوان'), max_length=255)
    content = models.TextField(_('محتوا'))
    
    # Type
    announcement_type = models.CharField(
        _('نوع'),
        max_length=20,
        choices=AnnouncementType.choices,
        default=AnnouncementType.GENERAL
    )
    
    # Target
    target_audience = models.CharField(
        _('مخاطبان'),
        max_length=20,
        choices=TargetAudience.choices,
        default=TargetAudience.ALL
    )
    
    specific_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='announcements',
        verbose_name=_('کاربران خاص')
    )
    
    specific_branches = models.ManyToManyField(
        'branches.Branch',
        blank=True,
        related_name='announcements',
        verbose_name=_('شعب خاص')
    )
    
    # Display
    is_published = models.BooleanField(_('منتشر شده'), default=False)
    publish_date = models.DateTimeField(_('تاریخ انتشار'), null=True, blank=True)
    expire_date = models.DateTimeField(_('تاریخ انقضا'), null=True, blank=True)
    
    # Priority
    is_pinned = models.BooleanField(_('سنجاق شده'), default=False)
    
    # Attachment
    attachment = models.FileField(
        _('پیوست'),
        upload_to='announcements/',
        null=True,
        blank=True
    )
    
    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements',
        verbose_name=_('ایجاد کننده')
    )
    
    # Stats
    view_count = models.PositiveIntegerField(_('تعداد بازدید'), default=0)

    class Meta:
        db_table = 'announcements'
        verbose_name = _('اطلاعیه')
        verbose_name_plural = _('اطلاعیه‌ها')
        ordering = ['-is_pinned', '-publish_date']
        indexes = [
            models.Index(fields=['is_published', 'publish_date']),
            models.Index(fields=['target_audience']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        """Check if announcement is currently active"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_published:
            return False
        
        if self.publish_date and now < self.publish_date:
            return False
        
        if self.expire_date and now > self.expire_date:
            return False
        
        return True

    def get_recipients(self):
        """Get list of recipient users"""
        from apps.accounts.models import User
        
        if self.target_audience == self.TargetAudience.CUSTOM:
            return self.specific_users.all()
        
        recipients = User.objects.filter(is_active=True)
        
        if self.target_audience == self.TargetAudience.STUDENTS:
            recipients = recipients.filter(role=User.UserRole.STUDENT)
        elif self.target_audience == self.TargetAudience.TEACHERS:
            recipients = recipients.filter(role=User.UserRole.TEACHER)
        elif self.target_audience == self.TargetAudience.STAFF:
            recipients = recipients.filter(
                role__in=[
                    User.UserRole.SUPER_ADMIN,
                    User.UserRole.BRANCH_MANAGER,
                    User.UserRole.ACCOUNTANT,
                    User.UserRole.RECEPTIONIST,
                    User.UserRole.SUPPORT
                ]
            )
        
        # Filter by branches
        if self.specific_branches.exists():
            # Students enrolled in branch classes
            # Staff assigned to branches
            # etc.
            pass
        
        return recipients
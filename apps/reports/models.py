from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.accounts.models import User
from apps.branches.models import Branch


class Report(TimeStampedModel):
    """
    Saved Report Model
    """
    class ReportType(models.TextChoices):
        FINANCIAL = 'financial', _('مالی')
        ENROLLMENT = 'enrollment', _('ثبت‌نام')
        ATTENDANCE = 'attendance', _('حضور و غیاب')
        ACADEMIC = 'academic', _('آکادمیک')
        TEACHER = 'teacher', _('معلمان')
        STUDENT = 'student', _('دانش‌آموزان')
        CUSTOM = 'custom', _('سفارشی')

    class ReportFormat(models.TextChoices):
        PDF = 'pdf', _('PDF')
        EXCEL = 'excel', _('Excel')
        CSV = 'csv', _('CSV')
        JSON = 'json', _('JSON')

    title = models.CharField(_('عنوان'), max_length=255)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    report_type = models.CharField(
        _('نوع گزارش'),
        max_length=20,
        choices=ReportType.choices
    )
    
    # Parameters
    parameters = models.JSONField(
        _('پارامترها'),
        default=dict,
        help_text='پارامترهای گزارش (تاریخ، شعبه، و...)'
    )
    
    # Generated file
    file = models.FileField(
        _('فایل'),
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True
    )
    
    file_format = models.CharField(
        _('فرمت فایل'),
        max_length=10,
        choices=ReportFormat.choices,
        default=ReportFormat.PDF
    )
    
    file_size = models.PositiveIntegerField(_('حجم فایل (بایت)'), null=True, blank=True)
    
    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_reports',
        verbose_name=_('ایجاد کننده')
    )
    
    # Branch filter
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name=_('شعبه')
    )
    
    # Status
    is_generated = models.BooleanField(_('تولید شده'), default=False)
    generated_at = models.DateTimeField(_('تاریخ تولید'), null=True, blank=True)
    
    # Scheduling
    is_scheduled = models.BooleanField(_('زمان‌بندی شده'), default=False)
    schedule_frequency = models.CharField(
        _('دوره تکرار'),
        max_length=20,
        null=True,
        blank=True,
        help_text='daily, weekly, monthly'
    )
    next_run = models.DateTimeField(_('اجرای بعدی'), null=True, blank=True)

    class Meta:
        db_table = 'reports'
        verbose_name = _('گزارش')
        verbose_name_plural = _('گزارشات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'created_by']),
            models.Index(fields=['branch', 'created_at']),
        ]

    def __str__(self):
        return self.title


class ReportTemplate(TimeStampedModel):
    """
    Report Template Model
    """
    name = models.CharField(_('نام'), max_length=255, unique=True)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    report_type = models.CharField(
        _('نوع گزارش'),
        max_length=20,
        choices=Report.ReportType.choices
    )
    
    # Template definition
    query = models.TextField(
        _('کوئری'),
        help_text='SQL Query یا ORM query definition'
    )
    
    columns = models.JSONField(
        _('ستون‌ها'),
        default=list,
        help_text='تعریف ستون‌های گزارش'
    )
    
    filters = models.JSONField(
        _('فیلترها'),
        default=list,
        help_text='فیلترهای قابل اعمال'
    )
    
    # Settings
    is_active = models.BooleanField(_('فعال'), default=True)
    is_public = models.BooleanField(_('عمومی'), default=False)
    
    # Permissions
    allowed_roles = models.JSONField(
        _('نقش‌های مجاز'),
        default=list,
        help_text='لیست نقش‌هایی که می‌توانند از این قالب استفاده کنند'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_templates',
        verbose_name=_('ایجاد کننده')
    )

    class Meta:
        db_table = 'report_templates'
        verbose_name = _('قالب گزارش')
        verbose_name_plural = _('قالب‌های گزارش')
        ordering = ['name']

    def __str__(self):
        return self.name
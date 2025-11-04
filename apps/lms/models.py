from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import User
from apps.courses.models import Class, ClassSession
from apps.enrollments.models import Enrollment


class CourseMaterial(TimeStampedModel, SoftDeleteModel):
    """
    Course Material Model
    """
    class MaterialType(models.TextChoices):
        PDF = 'pdf', _('PDF')
        VIDEO = 'video', _('ویدیو')
        AUDIO = 'audio', _('صوت')
        PRESENTATION = 'presentation', _('ارائه')
        DOCUMENT = 'document', _('سند')
        LINK = 'link', _('لینک')
        OTHER = 'other', _('سایر')

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='course_materials',  # تغییر نام
        verbose_name=_('کلاس')
    )
    
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='session_materials',  # تغییر نام
        verbose_name=_('جلسه')
    )
    
    title = models.CharField(_('عنوان'), max_length=255)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    material_type = models.CharField(
        _('نوع'),
        max_length=20,
        choices=MaterialType.choices
    )
    
    # File
    file = models.FileField(
        _('فایل'),
        upload_to='course_materials/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 
                                  'mp4', 'mp3', 'zip', 'rar']
            )
        ]
    )
    
    # External link
    external_link = models.URLField(_('لینک خارجی'), null=True, blank=True)
    
    # File info
    file_size = models.PositiveIntegerField(_('حجم فایل (بایت)'), null=True, blank=True)
    duration = models.PositiveIntegerField(
        _('مدت زمان (ثانیه)'),
        null=True,
        blank=True,
        help_text='برای ویدیو و صوت'
    )
    
    # Access control
    is_public = models.BooleanField(_('عمومی'), default=False)
    available_from = models.DateTimeField(_('در دسترس از'), null=True, blank=True)
    available_until = models.DateTimeField(_('در دسترس تا'), null=True, blank=True)
    
    # Order
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    
    # Stats
    download_count = models.PositiveIntegerField(_('تعداد دانلود'), default=0)
    view_count = models.PositiveIntegerField(_('تعداد بازدید'), default=0)
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_materials',
        verbose_name=_('آپلود شده توسط')
    )

    class Meta:
        db_table = 'course_materials'
        verbose_name = _('محتوای آموزشی')
        verbose_name_plural = _('محتوای آموزشی')
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['class_obj', 'session']),
            models.Index(fields=['material_type']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Calculate file size
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        super().save(*args, **kwargs)


class Assignment(TimeStampedModel, SoftDeleteModel):
    """
    Assignment Model
    """
    class AssignmentType(models.TextChoices):
        HOMEWORK = 'homework', _('تکلیف')
        PROJECT = 'project', _('پروژه')
        QUIZ = 'quiz', _('آزمون کوتاه')
        ESSAY = 'essay', _('مقاله')

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('کلاس')
    )
    
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_assignments',  # تغییر نام
        verbose_name=_('جلسه')
    )
    
    title = models.CharField(_('عنوان'), max_length=255)
    description = models.TextField(_('توضیحات'))
    
    assignment_type = models.CharField(
        _('نوع'),
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.HOMEWORK
    )
    
    # Files
    attachment = models.FileField(
        _('پیوست'),
        upload_to='assignments/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Grading
    max_score = models.DecimalField(
        _('حداکثر نمره'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Deadlines
    assigned_date = models.DateTimeField(_('تاریخ تعیین'), auto_now_add=True)
    due_date = models.DateTimeField(_('مهلت ارسال'))
    late_submission_allowed = models.BooleanField(_('مجاز به ارسال دیرهنگام'), default=False)
    late_penalty_percent = models.DecimalField(
        _('جریمه تاخیر (درصد)'),
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Visibility
    is_published = models.BooleanField(_('منتشر شده'), default=True)
    
    # Created by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assignments',
        verbose_name=_('ایجاد شده توسط')
    )

    class Meta:
        db_table = 'assignments'
        verbose_name = _('تکلیف')
        verbose_name_plural = _('تکالیف')
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['class_obj', 'due_date']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        from django.utils import timezone
        return timezone.now() > self.due_date


class AssignmentSubmission(TimeStampedModel):
    """
    Assignment Submission Model
    """
    class SubmissionStatus(models.TextChoices):
        SUBMITTED = 'submitted', _('ارسال شده')
        GRADED = 'graded', _('نمره داده شده')
        RETURNED = 'returned', _('بازگشت داده شده')
        LATE = 'late', _('تاخیر')

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_('تکلیف')
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        verbose_name=_('ثبت‌نام')
    )
    
    # Submission
    submission_text = models.TextField(_('متن پاسخ'), null=True, blank=True)
    attachment = models.FileField(
        _('فایل پاسخ'),
        upload_to='submissions/%Y/%m/',
        null=True,
        blank=True
    )
    
    submitted_at = models.DateTimeField(_('تاریخ ارسال'), auto_now_add=True)
    is_late = models.BooleanField(_('دیرهنگام'), default=False)
    
    # Grading
    score = models.DecimalField(
        _('نمره'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    feedback = models.TextField(_('بازخورد'), null=True, blank=True)
    
    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
        verbose_name=_('نمره دهنده')
    )
    graded_at = models.DateTimeField(_('تاریخ نمره‌دهی'), null=True, blank=True)
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED
    )
    
    # Resubmission
    resubmission_count = models.PositiveIntegerField(_('تعداد ارسال مجدد'), default=0)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = _('پاسخ تکلیف')
        verbose_name_plural = _('پاسخ‌های تکلیف')
        ordering = ['-submitted_at']
        unique_together = ['assignment', 'student']
        indexes = [
            models.Index(fields=['assignment', 'status']),
            models.Index(fields=['student', 'submitted_at']),
        ]

    def __str__(self):
        return f"{self.assignment.title} - {self.student.get_full_name()}"

    def save(self, *args, **kwargs):
        # Check if late
        if self.submitted_at > self.assignment.due_date:
            self.is_late = True
            
            # Apply penalty
            if self.score and self.assignment.late_penalty_percent > 0:
                penalty = (self.score * self.assignment.late_penalty_percent) / 100
                self.score = max(0, self.score - penalty)
        
        super().save(*args, **kwargs)


class OnlineSession(TimeStampedModel):
    """
    Online Session (BBB) Model
    """
    class SessionStatus(models.TextChoices):
        SCHEDULED = 'scheduled', _('برنامه‌ریزی شده')
        LIVE = 'live', _('در حال برگزاری')
        ENDED = 'ended', _('پایان یافته')
        CANCELLED = 'cancelled', _('لغو شده')

    class_session = models.OneToOneField(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='online_session',
        verbose_name=_('جلسه کلاس')
    )
    
    # BBB Info
    meeting_id = models.CharField(_('شناسه جلسه'), max_length=255, unique=True)
    moderator_password = models.CharField(_('رمز مدیر'), max_length=255)
    attendee_password = models.CharField(_('رمز شرکت‌کننده'), max_length=255)
    
    # Session info
    started_at = models.DateTimeField(_('شروع شده در'), null=True, blank=True)
    ended_at = models.DateTimeField(_('پایان یافته در'), null=True, blank=True)
    
    # Recording
    is_recorded = models.BooleanField(_('ضبط شده'), default=True)
    recording_url = models.URLField(_('لینک ضبط'), null=True, blank=True)
    recording_size = models.PositiveIntegerField(
        _('حجم ضبط (بایت)'),
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.SCHEDULED
    )
    
    # Participants
    max_participants = models.PositiveIntegerField(_('حداکثر شرکت‌کننده'), default=100)
    
    # Settings
    allow_chat = models.BooleanField(_('چت مجاز'), default=True)
    allow_webcam = models.BooleanField(_('دوربین مجاز'), default=True)
    allow_microphone = models.BooleanField(_('میکروفون مجاز'), default=True)
    allow_screen_share = models.BooleanField(_('اشتراک صفحه مجاز'), default=False)

    class Meta:
        db_table = 'online_sessions'
        verbose_name = _('جلسه آنلاین')
        verbose_name_plural = _('جلسات آنلاین')
        ordering = ['-created_at']

    def __str__(self):
        return f"جلسه آنلاین {self.class_session}"


class OnlineSessionParticipant(TimeStampedModel):
    """
    Online Session Participant Log
    """
    online_session = models.ForeignKey(
        OnlineSession,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_('جلسه آنلاین')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='online_session_participations',
        verbose_name=_('کاربر')
    )
    
    # Join info
    joined_at = models.DateTimeField(_('پیوست در'))
    left_at = models.DateTimeField(_('خروج در'), null=True, blank=True)
    
    # Duration
    duration_seconds = models.PositiveIntegerField(_('مدت (ثانیه)'), default=0)
    
    # Role
    is_moderator = models.BooleanField(_('مدیر'), default=False)

    class Meta:
        db_table = 'online_session_participants'
        verbose_name = _('شرکت‌کننده جلسه آنلاین')
        verbose_name_plural = _('شرکت‌کنندگان جلسه آنلاین')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.online_session}"

    def calculate_duration(self):
        """Calculate participation duration"""
        if self.left_at:
            delta = self.left_at - self.joined_at
            self.duration_seconds = int(delta.total_seconds())
            self.save()
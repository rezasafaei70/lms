from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import User
from apps.courses.models import Course, Class, Term
from apps.branches.models import Branch
import uuid


class Enrollment(TimeStampedModel, SoftDeleteModel):
    """
    Student Enrollment Model
    """
    class EnrollmentStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        APPROVED = 'approved', _('تایید شده')
        REJECTED = 'rejected', _('رد شده')
        ACTIVE = 'active', _('فعال')
        COMPLETED = 'completed', _('تکمیل شده')
        CANCELLED = 'cancelled', _('لغو شده')
        SUSPENDED = 'suspended', _('معلق')
        WITHDRAWN = 'withdrawn', _('انصراف')

    # Basic Info
    enrollment_number = models.CharField(
        _('شماره ثبت‌نام'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name=_('کلاس')
    )
    
    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name=_('ترم'),
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING
    )
    invoice = models.OneToOneField(
        'financial.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_enrollment',
        verbose_name=_('فاکتور')
    )
    
    # Dates
    enrollment_date = models.DateTimeField(_('تاریخ ثبت‌نام'), auto_now_add=True)
    approved_date = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)
    start_date = models.DateField(_('تاریخ شروع'), null=True, blank=True)
    end_date = models.DateField(_('تاریخ پایان'), null=True, blank=True)
    
    # Payment
    total_amount = models.DecimalField(
        _('مبلغ کل'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        _('مبلغ تخفیف'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    final_amount = models.DecimalField(
        _('مبلغ نهایی'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    paid_amount = models.DecimalField(
        _('مبلغ پرداخت شده'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_enrollments',
        verbose_name=_('تایید کننده')
    )
    
    # Progress
    attendance_rate = models.DecimalField(
        _('نرخ حضور'),
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_sessions_attended = models.PositiveIntegerField(
        _('جلسات حضور'),
        default=0
    )
    
    # Certificate
    certificate_issued = models.BooleanField(_('گواهینامه صادر شده'), default=False)
    certificate_issue_date = models.DateField(
        _('تاریخ صدور گواهینامه'),
        null=True,
        blank=True
    )
    certificate_number = models.CharField(
        _('شماره گواهینامه'),
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )
    
    # Notes
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)
    cancellation_reason = models.TextField(_('دلیل لغو'), null=True, blank=True)
    @property
    def is_paid(self):
        if not self.invoice:
            return False
        return self.invoice.is_paid
    class Meta:
        db_table = 'enrollments'
        verbose_name = _('ثبت‌نام')
        verbose_name_plural = _('ثبت‌نام‌ها')
        ordering = ['-enrollment_date']
        unique_together = ['student', 'class_obj'] # ⚠️ باید این را برای وضعیت‌های لغو شده نادیده گرفت
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'class_obj'],
                condition=~models.Q(status__in=['cancelled', 'rejected']),
                name='unique_active_enrollment'
            )
        ]

    def __str__(self):
        return f"{self.enrollment_number} - {self.student.get_full_name()}"

    def save(self, *args, **kwargs):
        # Generate enrollment number
        if not self.enrollment_number:
            from django.utils import timezone
            year = timezone.now().year
            count = Enrollment.objects.filter(
                enrollment_date__year=year
            ).count() + 1
            self.enrollment_number = f"EN{year}{count:06d}"
        
        # Calculate final amount
        self.final_amount = self.total_amount - self.discount_amount
        
        # Set dates from class
        if not self.start_date:
            self.start_date = self.class_obj.start_date
        if not self.end_date:
            self.end_date = self.class_obj.end_date
        
        super().save(*args, **kwargs)

    def clean(self):
        # Check if class is full
        if self.class_obj.is_full and not self.pk:
            raise ValidationError('این کلاس پر شده است')
        
        # Check registration period
        from django.utils import timezone
        now = timezone.now()
        if not self.class_obj.is_registration_open:
            raise ValidationError('ثبت‌نام در این کلاس بسته است')
        
        if not (self.class_obj.registration_start <= now <= self.class_obj.registration_end):
            raise ValidationError('زمان ثبت‌نام در این کلاس به پایان رسیده است')

    @property
    def is_paid(self):
        return self.paid_amount >= self.final_amount

    @property
    def remaining_amount(self):
        return self.final_amount - self.paid_amount

    @property
    def progress_percentage(self):
        if not self.class_obj.course.sessions_count:
            return 0
        return (self.total_sessions_attended / self.class_obj.course.sessions_count) * 100

    def update_attendance_rate(self):
        """Update attendance rate based on attendance records"""
        from apps.attendance.models import Attendance
        
        total_sessions = self.class_obj.sessions.filter(
            attendance_taken=True
        ).count()
        
        if total_sessions == 0:
            self.attendance_rate = 0
        else:
            attended_sessions = Attendance.objects.filter(
                enrollment=self,
                status=Attendance.AttendanceStatus.PRESENT
            ).count()
            
            self.attendance_rate = (attended_sessions / total_sessions) * 100
            self.total_sessions_attended = attended_sessions
        
        self.save()


class PlacementTest(TimeStampedModel):
    """
    Placement Test Model (آزمون تعیین سطح)
    """
    class TestStatus(models.TextChoices):
        SCHEDULED = 'scheduled', _('برنامه‌ریزی شده')
        IN_PROGRESS = 'in_progress', _('در حال برگزاری')
        COMPLETED = 'completed', _('تکمیل شده')
        CANCELLED = 'cancelled', _('لغو شده')

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='placement_tests',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='placement_tests',
        verbose_name=_('دوره')
    )
    
    # Test Details
    test_date = models.DateTimeField(_('تاریخ آزمون'))
    duration_minutes = models.PositiveIntegerField(_('مدت زمان (دقیقه)'), default=60)
    
    # Results
    score = models.DecimalField(
        _('نمره'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    determined_level = models.CharField(
        _('سطح تعیین شده'),
        max_length=20,
        choices=Course.CourseLevel.choices,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=TestStatus.choices,
        default=TestStatus.SCHEDULED
    )
    
    # Evaluator
    evaluated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluated_tests',
        verbose_name=_('ارزیاب'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    evaluated_at = models.DateTimeField(_('تاریخ ارزیابی'), null=True, blank=True)
    
    # Test Type
    is_online = models.BooleanField(_('آزمون آنلاین'), default=False)
    is_oral = models.BooleanField(_('آزمون شفاهی'), default=False)
    
    # Files
    test_file = models.FileField(
        _('فایل سوالات'),
        upload_to='placement_tests/questions/',
        null=True,
        blank=True
    )
    answer_file = models.FileField(
        _('فایل پاسخ'),
        upload_to='placement_tests/answers/',
        null=True,
        blank=True
    )
    
    # Feedback
    feedback = models.TextField(_('بازخورد'), null=True, blank=True)
    recommendations = models.TextField(_('توصیه‌ها'), null=True, blank=True)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'placement_tests'
        verbose_name = _('آزمون تعیین سطح')
        verbose_name_plural = _('آزمون‌های تعیین سطح')
        ordering = ['-test_date']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['test_date']),
        ]

    def __str__(self):
        return f"آزمون {self.student.get_full_name()} - {self.course.name}"


class WaitingList(TimeStampedModel):
    """
    Waiting List for Full Classes
    """
    class WaitingStatus(models.TextChoices):
        WAITING = 'waiting', _('در انتظار')
        NOTIFIED = 'notified', _('اطلاع داده شده')
        ENROLLED = 'enrolled', _('ثبت‌نام شده')
        EXPIRED = 'expired', _('منقضی شده')
        CANCELLED = 'cancelled', _('لغو شده')

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='waiting_lists',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='waiting_lists',
        verbose_name=_('کلاس')
    )
    
    # Position in queue
    position = models.PositiveIntegerField(_('موقعیت در صف'), default=1)
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=WaitingStatus.choices,
        default=WaitingStatus.WAITING
    )
    
    # Notification
    notified_at = models.DateTimeField(_('تاریخ اطلاع‌رسانی'), null=True, blank=True)
    notification_expires_at = models.DateTimeField(
        _('انقضای اطلاع‌رسانی'),
        null=True,
        blank=True
    )
    
    # Priority
    is_priority = models.BooleanField(_('اولویت دارد'), default=False)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'waiting_lists'
        verbose_name = _('لیست انتظار')
        verbose_name_plural = _('لیست‌های انتظار')
        ordering = ['is_priority', 'created_at']
        unique_together = ['student', 'class_obj']
        indexes = [
            models.Index(fields=['class_obj', 'status']),
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_obj.name}"

    def save(self, *args, **kwargs):
        # Calculate position
        if not self.position:
            max_position = WaitingList.objects.filter(
                class_obj=self.class_obj,
                status=self.WaitingStatus.WAITING
            ).aggregate(models.Max('position'))['position__max'] or 0
            self.position = max_position + 1
        
        super().save(*args, **kwargs)


class EnrollmentTransfer(TimeStampedModel):
    """
    Enrollment Transfer (انتقال به کلاس دیگر)
    """
    class TransferStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        APPROVED = 'approved', _('تایید شده')
        REJECTED = 'rejected', _('رد شده')
        COMPLETED = 'completed', _('انجام شده')

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name=_('ثبت‌نام')
    )
    
    from_class = models.ForeignKey(
        Class,
        on_delete=models.PROTECT,
        related_name='transfers_from',
        verbose_name=_('از کلاس')
    )
    
    to_class = models.ForeignKey(
        Class,
        on_delete=models.PROTECT,
        related_name='transfers_to',
        verbose_name=_('به کلاس')
    )
    
    # Request
    reason = models.TextField(_('دلیل انتقال'))
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_transfers',
        verbose_name=_('درخواست کننده')
    )
    request_date = models.DateTimeField(_('تاریخ درخواست'), auto_now_add=True)
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=TransferStatus.choices,
        default=TransferStatus.PENDING
    )
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transfers',
        verbose_name=_('تایید کننده')
    )
    approved_date = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)
    
    # Financial
    price_difference = models.DecimalField(
        _('اختلاف قیمت'),
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='مثبت: باید پرداخت شود، منفی: بازگشت داده می‌شود'
    )
    
    admin_notes = models.TextField(_('یادداشت مدیر'), null=True, blank=True)

    class Meta:
        db_table = 'enrollment_transfers'
        verbose_name = _('انتقال ثبت‌نام')
        verbose_name_plural = _('انتقالات ثبت‌نام')
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['enrollment', 'status']),
        ]

    def __str__(self):
        return f"انتقال {self.enrollment.student.get_full_name()}"


class AnnualRegistration(TimeStampedModel):
    """
    Annual Registration (ثبت‌نام سالانه)
    ✅ نسخه اصلاح شده با فیلدهای ضروری
    """
    class RegistrationStatus(models.TextChoices):
        DRAFT = 'draft', _('پیش‌نویس')
        PENDING_PAYMENT = 'pending_payment', _('در انتظار پرداخت')
        PENDING_VERIFICATION = 'pending_verification', _('در انتظار تایید مدارک')
        ACTIVE = 'active', _('فعال')
        EXPIRED = 'expired', _('منقضی شده')
        CANCELLED = 'cancelled', _('لغو شده')

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='annual_registrations',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='annual_registrations',
        verbose_name=_('شعبه')
    )
    
    # Academic Year
    academic_year = models.CharField(
        _('سال تحصیلی'),
        max_length=20,
        help_text='مثال: 1403-1404'
    )
    
    # ✅ تاریخ ثبت‌نام رسمی
    registration_date = models.DateField(
        _('تاریخ ثبت‌نام'),
        auto_now_add=True,
        help_text='تاریخ رسمی ثبت‌نام دانش‌آموز'
    )
    
    # Academic Period Dates
    start_date = models.DateField(
        _('تاریخ شروع سال تحصیلی'),
        help_text='معمولاً 1 مهر'
    )
    end_date = models.DateField(
        _('تاریخ پایان سال تحصیلی'),
        help_text='معمولاً 31 شهریور'
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=25,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.DRAFT,
        db_index=True
    )
    
    # ✅ ارتباط با Invoice
    invoice = models.OneToOneField(
        'financial.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='annual_registration_source',
        verbose_name=_('فاکتور')
    )
    
    # ✅ کش پرداخت (اختیاری - برای کوئری سریع)
    is_paid_cached = models.BooleanField(
        _('پرداخت شده'),
        default=False,
        db_index=True,
        editable=False,
        help_text='این فیلد خودکار از Invoice بروز می‌شود'
    )
    
    # Documents
    documents_submitted = models.BooleanField(_('مدارک ارسال شده'), default=False)
    documents_submitted_at = models.DateTimeField(
        _('تاریخ ارسال مدارک'),
        null=True,
        blank=True
    )
    
    documents_verified = models.BooleanField(_('مدارک تایید شده'), default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_annual_registrations',
        verbose_name=_('تایید کننده مدارک')
    )
    verified_at = models.DateTimeField(_('تاریخ تایید مدارک'), null=True, blank=True)
    
    # Activation
    activated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activated_registrations',
        verbose_name=_('فعال کننده')
    )
    activated_at = models.DateTimeField(_('تاریخ فعال‌سازی'), null=True, blank=True)
    
    # Settings snapshot
    registration_fee_amount = models.DecimalField(
        _('مبلغ شهریه (ثبت شده)'),
        max_digits=12,
        decimal_places=0,
        help_text='مبلغی که هنگام ثبت‌نام تعیین شده - یک snapshot از تنظیمات'
    )
    
    # Notes
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)
    cancellation_reason = models.TextField(_('دلیل لغو'), null=True, blank=True)

    class Meta:
        db_table = 'annual_registrations'
        verbose_name = _('ثبت‌نام سالانه')
        verbose_name_plural = _('ثبت‌نام‌های سالانه')
        ordering = ['-registration_date']
        unique_together = ['student', 'academic_year']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['academic_year']),
            models.Index(fields=['registration_date']),
            models.Index(fields=['is_paid_cached', 'status']),  # برای کوئری‌های ترکیبی
        ]

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.academic_year}"

    # =============== Properties ===============
    
    @property
    def is_paid(self):
        """
        بررسی پرداخت از طریق Invoice
        برای نمایش استفاده می‌شود
        """
        if not self.invoice:
            return False
        return self.invoice.is_paid

    @property
    def payment_status(self):
        """وضعیت پرداخت از Invoice"""
        if not self.invoice:
            return 'no_invoice'
        return self.invoice.status

    @property
    def total_amount(self):
        """مبلغ کل از Invoice"""
        if not self.invoice:
            return self.registration_fee_amount
        return self.invoice.total_amount

    @property
    def paid_amount(self):
        """مبلغ پرداخت شده از Invoice"""
        if not self.invoice:
            return 0
        return self.invoice.paid_amount

    @property
    def remaining_amount(self):
        """مبلغ باقی‌مانده"""
        return self.total_amount - self.paid_amount

    @property
    def is_active_now(self):
        """
        آیا همین الان فعال است؟
        """
        from django.utils import timezone
        if self.status != self.RegistrationStatus.ACTIVE:
            return False
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def can_activate(self):
        """
        آیا قابل فعال‌سازی است؟
        """
        return (
            self.is_paid and
            self.documents_verified and
            self.status == self.RegistrationStatus.PENDING_VERIFICATION
        )

    @property
    def days_until_expiry(self):
        """
        چند روز تا انقضا باقی مانده؟
        """
        from django.utils import timezone
        if self.status != self.RegistrationStatus.ACTIVE:
            return None
        today = timezone.now().date()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    # =============== Methods ===============
    
    def update_payment_cache(self):
        """
        بروزرسانی کش پرداخت
        این متد توسط signal فراخوانی می‌شود
        """
        if self.invoice:
            self.is_paid_cached = self.invoice.is_paid
            self.save(update_fields=['is_paid_cached'])

    def submit_documents(self):
        """
        ثبت ارسال مدارک
        """
        from django.utils import timezone
        self.documents_submitted = True
        self.documents_submitted_at = timezone.now()
        self.save(update_fields=['documents_submitted', 'documents_submitted_at'])

    def check_and_activate(self, activated_by=None):
        """
        بررسی شرایط و فعال‌سازی خودکار
        """
        if self.can_activate:
            from django.utils import timezone
            self.status = self.RegistrationStatus.ACTIVE
            self.activated_by = activated_by
            self.activated_at = timezone.now()
            self.save()
            return True
        return False

    def expire_if_needed(self):
        """
        اگر تاریخ گذشته، منقضی کن
        این متد توسط Celery Task روزانه اجرا می‌شود
        """
        from django.utils import timezone
        if (
            self.status == self.RegistrationStatus.ACTIVE and
            timezone.now().date() > self.end_date
        ):
            self.status = self.RegistrationStatus.EXPIRED
            self.save(update_fields=['status'])
            return True
        return False

    def cancel(self, reason=None):
        """
        لغو ثبت‌نام
        """
        self.status = self.RegistrationStatus.CANCELLED
        self.cancellation_reason = reason
        self.save()
class EnrollmentDocument(TimeStampedModel):
    """
    Enrollment Documents
    """
    class DocumentType(models.TextChoices):
        ID_CARD = 'id_card', _('کارت ملی')
        BIRTH_CERTIFICATE = 'birth_certificate', _('شناسنامه')
        PHOTO = 'photo', _('عکس')
        EDUCATION_CERTIFICATE = 'education_certificate', _('مدرک تحصیلی')
        MEDICAL_CERTIFICATE = 'medical_certificate', _('مدرک پزشکی')
        OTHER = 'other', _('سایر')

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('ثبت‌نام')
    )
    
    document_type = models.CharField(
        _('نوع مدرک'),
        max_length=30,
        choices=DocumentType.choices
    )
    
    title = models.CharField(_('عنوان'), max_length=200)
    file = models.FileField(_('فایل'), upload_to='enrollments/documents/')
    
    # Verification
    is_verified = models.BooleanField(_('تایید شده'), default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents',
        verbose_name=_('تایید کننده')
    )
    verified_at = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'enrollment_documents'
        verbose_name = _('مدرک ثبت‌نام')
        verbose_name_plural = _('مدارک ثبت‌نام')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.enrollment.student.get_full_name()}"
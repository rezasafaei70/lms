from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import User
from apps.branches.models import Branch, Classroom
import uuid


class Subject(TimeStampedModel, SoftDeleteModel):
    """
    مدل برای تعریف درس‌ها
    مثال: ریاضی ۱، فیزیک ۲، زیست‌شناسی کنکور
    """
    title = models.CharField(_('عنوان درس'), max_length=200, unique=True)
    code = models.CharField(_('کد درس'), max_length=50, unique=True, null=True, blank=True)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    # پایه تحصیلی مرتبط
    grade_level = models.ForeignKey(
        'accounts.GradeLevel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subjects',
        verbose_name=_('پایه تحصیلی')
    )
    
    # قیمت پایه برای تک‌درس
    base_price = models.DecimalField(
        _('قیمت پایه تک‌درس'),
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='قیمت در صورتی که دانش‌آموز فقط همین درس را بردارد'
    )
    
    # تعداد جلسات استاندارد
    standard_sessions = models.PositiveIntegerField(
        _('تعداد جلسات استاندارد'),
        default=24
    )
    
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        db_table = 'subjects'
        verbose_name = _('درس')
        verbose_name_plural = _('درس‌ها')
        ordering = ['title']

    def __str__(self):
        return self.title
class Course(TimeStampedModel, SoftDeleteModel):
    """
    Course Model
    """
    class CourseLevel(models.TextChoices):
        BEGINNER = 'beginner', _('مبتدی')
        ELEMENTARY = 'elementary', _('ابتدایی')
        PRE_INTERMEDIATE = 'pre_intermediate', _('پیش متوسط')
        INTERMEDIATE = 'intermediate', _('متوسط')
        UPPER_INTERMEDIATE = 'upper_intermediate', _('فوق متوسط')
        ADVANCED = 'advanced', _('پیشرفته')
        PROFICIENCY = 'proficiency', _('تخصصی')

    class CourseStatus(models.TextChoices):
        ACTIVE = 'active', _('فعال')
        INACTIVE = 'inactive', _('غیرفعال')
        DRAFT = 'draft', _('پیش‌نویس')
        ARCHIVED = 'archived', _('بایگانی شده')

    subjects = models.ManyToManyField(
        Subject,
        related_name='courses',
        verbose_name=_('درس‌های شامل دوره')
    )
    name = models.CharField(_('نام دوره'), max_length=200)
    code = models.CharField(_('کد دوره'), max_length=50, unique=True)
    slug = models.SlugField(_('اسلاگ'), unique=True, allow_unicode=True)
    
    # Description
    description = models.TextField(_('توضیحات'))
    short_description = models.CharField(_('توضیحات کوتاه'), max_length=500)
    
    # Level
    level = models.CharField(
        _('سطح'),
        max_length=20,
        choices=CourseLevel.choices,
        default=CourseLevel.BEGINNER
    )
    
    # Prerequisites
    prerequisites = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='prerequisite_for',
        verbose_name=_('پیش نیازها')
    )
    
    # Duration
    duration_hours = models.PositiveIntegerField(
        _('مدت دوره (ساعت)'),
        validators=[MinValueValidator(1)]
    )
    sessions_count = models.PositiveIntegerField(
        _('تعداد جلسات'),
        validators=[MinValueValidator(1)]
    )
    
    # Syllabus
    syllabus = models.TextField(_('سرفصل‌ها'), help_text='سرفصل‌های دوره')
    learning_outcomes = models.TextField(
        _('اهداف یادگیری'),
        help_text='چه چیزهایی یاد می‌گیرند'
    )
    
    # Pricing
    base_price = models.DecimalField(
        _('قیمت پایه'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    # Materials
    required_materials = models.TextField(
        _('مواد و کتب مورد نیاز'),
        null=True,
        blank=True
    )
    
    # Media
    thumbnail = models.ImageField(
        _('تصویر شاخص'),
        upload_to='courses/thumbnails/',
        null=True,
        blank=True
    )
    video_intro = models.FileField(
        _('ویدیو معرفی'),
        upload_to='courses/videos/',
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT
    )
    is_featured = models.BooleanField(_('دوره ویژه'), default=False)
    
    # Certificate
    provides_certificate = models.BooleanField(_('دارای گواهینامه'), default=True)
    certificate_template = models.FileField(
        _('قالب گواهینامه'),
        upload_to='courses/certificates/',
        null=True,
        blank=True
    )
    
    # Capacity
    min_students = models.PositiveIntegerField(
        _('حداقل دانش‌آموز'),
        default=5,
        validators=[MinValueValidator(1)]
    )
    max_students = models.PositiveIntegerField(
        _('حداکثر دانش‌آموز'),
        default=20,
        validators=[MinValueValidator(1)]
    )
    
    # SEO
    meta_description = models.CharField(
        _('توضیحات متا'),
        max_length=160,
        null=True,
        blank=True
    )
    meta_keywords = models.CharField(
        _('کلمات کلیدی'),
        max_length=255,
        null=True,
        blank=True
    )
    
    # Statistics
    total_enrollments = models.PositiveIntegerField(_('تعداد ثبت‌نام'), default=0)
    average_rating = models.DecimalField(
        _('میانگین امتیاز'),
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(_('تعداد نظرات'), default=0)

    class Meta:
        db_table = 'courses'
        verbose_name = _('دوره')
        verbose_name_plural = _('دوره‌ها')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['slug']),
            models.Index(fields=['level']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"
    def update_base_price(self):
        """
        قیمت پایه دوره را بر اساس جمع قیمت درس‌ها آپدیت می‌کند
        (می‌تواند با تخفیف پکیج همراه باشد)
        """
        total_price = self.subjects.aggregate(
            total=models.Sum('base_price')
        )['total'] or 0
        
        # اعمال تخفیف برای پکیج (مثلاً ۱۰٪)
        package_discount = 0.10
        self.base_price = total_price * (1 - package_discount)
        self.save()
    @property
    def is_active(self):
        return self.status == self.CourseStatus.ACTIVE


class Class(TimeStampedModel, SoftDeleteModel):
    """
    Class Session Model
    """
    class ClassType(models.TextChoices):
        IN_PERSON = 'in_person', _('حضوری')
        ONLINE = 'online', _('آنلاین')
        HYBRID = 'hybrid', _('ترکیبی')
        PRIVATE = 'private', _('خصوصی')
        SEMI_PRIVATE = 'semi_private', _('نیمه خصوصی')

    class ClassStatus(models.TextChoices):
        SCHEDULED = 'scheduled', _('برنامه‌ریزی شده')
        ONGOING = 'ongoing', _('در حال برگزاری')
        COMPLETED = 'completed', _('تمام شده')
        CANCELLED = 'cancelled', _('لغو شده')
        POSTPONED = 'postponed', _('به تعویق افتاده')

    class WeekDay(models.TextChoices):
        SATURDAY = 'saturday', _('شنبه')
        SUNDAY = 'sunday', _('یکشنبه')
        MONDAY = 'monday', _('دوشنبه')
        TUESDAY = 'tuesday', _('سه‌شنبه')
        WEDNESDAY = 'wednesday', _('چهارشنبه')
        THURSDAY = 'thursday', _('پنجشنبه')
        FRIDAY = 'friday', _('جمعه')

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='classes',
        verbose_name=_('دوره')
    )
    
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='classes',
        verbose_name=_('شعبه')
    )
    
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes',
        verbose_name=_('کلاس فیزیکی')
    )
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='teaching_classes',
        verbose_name=_('معلم'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    
    # Basic Info
    name = models.CharField(_('نام کلاس'), max_length=200)
    code = models.CharField(_('کد کلاس'), max_length=50, unique=True)
    
    # Type
    class_type = models.CharField(
        _('نوع کلاس'),
        max_length=20,
        choices=ClassType.choices,
        default=ClassType.IN_PERSON
    )
    
    # Schedule
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    
    # Weekly schedule (for recurring classes)
    schedule_days = models.JSONField(
        _('روزهای برگزاری'),
        default=list,
        help_text='لیست روزهای هفته: ["saturday", "monday"]'
    )
    start_time = models.TimeField(_('ساعت شروع'))
    end_time = models.TimeField(_('ساعت پایان'))
    
    # Capacity
    capacity = models.PositiveIntegerField(
        _('ظرفیت'),
        validators=[MinValueValidator(1)]
    )
    current_enrollments = models.PositiveIntegerField(_('ثبت‌نام‌های فعلی'), default=0)
    
    # Pricing
    price = models.DecimalField(
        _('شهریه'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    # Online Class Settings
    bbb_meeting_id = models.CharField(
        _('شناسه جلسه BBB'),
        max_length=255,
        null=True,
        blank=True
    )
    bbb_moderator_password = models.CharField(
        _('رمز مدیر BBB'),
        max_length=255,
        null=True,
        blank=True
    )
    bbb_attendee_password = models.CharField(
        _('رمز شرکت‌کننده BBB'),
        max_length=255,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=ClassStatus.choices,
        default=ClassStatus.SCHEDULED
    )
    
    # Registration
    registration_start = models.DateTimeField(_('شروع ثبت‌نام'))
    registration_end = models.DateTimeField(_('پایان ثبت‌نام'))
    is_registration_open = models.BooleanField(_('ثبت‌نام باز است'), default=True)
    
    # Notes
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    teacher_notes = models.TextField(_('یادداشت معلم'), null=True, blank=True)

    class Meta:
        db_table = 'classes'
        verbose_name = _('کلاس')
        verbose_name_plural = _('کلاس‌ها')
        ordering = ['-start_date', 'start_time']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['course', 'branch']),
            models.Index(fields=['teacher']),
            models.Index(fields=['start_date', 'status']),
        ]

    def __str__(self):
        return f"{self.name} - {self.teacher.get_full_name()}"

    @property
    def is_full(self):
        return self.current_enrollments >= self.capacity

    @property
    def available_seats(self):
        return self.capacity - self.current_enrollments

    @property
    def is_online(self):
        return self.class_type in [self.ClassType.ONLINE, self.ClassType.HYBRID]

    def save(self, *args, **kwargs):
        # Generate code if not exists
        if not self.code:
            import random
            year = self.start_date.year if self.start_date else 2024
            self.code = f"CLS{year}{random.randint(1000, 9999)}"
        
        # Create BBB meeting for online classes
        if self.is_online and not self.bbb_meeting_id:
            self._create_bbb_meeting()
        
        super().save(*args, **kwargs)

    def _create_bbb_meeting(self):
        """Create BigBlueButton meeting"""
        import secrets
        self.bbb_meeting_id = f"{self.code}_{uuid.uuid4().hex[:8]}"
        self.bbb_moderator_password = secrets.token_urlsafe(16)
        self.bbb_attendee_password = secrets.token_urlsafe(16)


class ClassSession(TimeStampedModel):
    """
    Individual Class Session (جلسه)
    """
    class SessionStatus(models.TextChoices):
        SCHEDULED = 'scheduled', _('برنامه‌ریزی شده')
        IN_PROGRESS = 'in_progress', _('در حال برگزاری')
        COMPLETED = 'completed', _('تمام شده')
        CANCELLED = 'cancelled', _('لغو شده')
        RESCHEDULED = 'rescheduled', _('تغییر زمان')

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('کلاس')
    )
    
    session_number = models.PositiveIntegerField(_('شماره جلسه'))
    title = models.CharField(_('عنوان جلسه'), max_length=200)
    
    # Schedule
    date = models.DateField(_('تاریخ'))
    start_time = models.TimeField(_('ساعت شروع'))
    end_time = models.TimeField(_('ساعت پایان'))
    
    # Content
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    topics = models.TextField(_('موضوعات'), null=True, blank=True)
    
    # حذف این فیلد - استفاده از related_name از CourseMaterial
    # materials = models.FileField(...)  # این خط را حذف کنید
    
    # Online Session
    bbb_recording_url = models.URLField(
        _('لینک ضبط'),
        null=True,
        blank=True
    )
    bbb_started_at = models.DateTimeField(_('شروع جلسه آنلاین'), null=True, blank=True)
    bbb_ended_at = models.DateTimeField(_('پایان جلسه آنلاین'), null=True, blank=True)
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.SCHEDULED
    )
    
    # Attendance
    attendance_taken = models.BooleanField(_('حضور گرفته شده'), default=False)
    
    # Notes
    teacher_notes = models.TextField(_('یادداشت معلم'), null=True, blank=True)

    class Meta:
        db_table = 'class_sessions'
        verbose_name = _('جلسه کلاس')
        verbose_name_plural = _('جلسات کلاس')
        ordering = ['date', 'start_time']
        unique_together = ['class_obj', 'session_number']
        indexes = [
            models.Index(fields=['class_obj', 'date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.class_obj.name} - جلسه {self.session_number}"
class Term(TimeStampedModel):
    """
    Academic Term Model
    """
    class TermStatus(models.TextChoices):
        UPCOMING = 'upcoming', _('آینده')
        ACTIVE = 'active', _('فعال')
        COMPLETED = 'completed', _('تمام شده')

    name = models.CharField(_('نام ترم'), max_length=100)
    code = models.CharField(_('کد ترم'), max_length=20, unique=True)
    
    # Dates
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    
    # Registration Period
    registration_start = models.DateField(_('شروع ثبت‌نام'))
    registration_end = models.DateField(_('پایان ثبت‌نام'))
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=TermStatus.choices,
        default=TermStatus.UPCOMING
    )
    
    # Discounts
    early_registration_discount = models.DecimalField(
        _('تخفیف ثبت‌نام زودهنگام'),
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='درصد'
    )
    early_registration_deadline = models.DateField(
        _('مهلت ثبت‌نام زودهنگام'),
        null=True,
        blank=True
    )
    
    # Description
    description = models.TextField(_('توضیحات'), null=True, blank=True)

    class Meta:
        db_table = 'terms'
        verbose_name = _('ترم')
        verbose_name_plural = _('ترم‌ها')
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.name


class TeacherReview(TimeStampedModel):
    """
    Teacher Review and Rating
    """
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('معلم'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_reviews',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('کلاس')
    )
    
    # Rating (1-5)
    rating = models.PositiveSmallIntegerField(
        _('امتیاز'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Review
    title = models.CharField(_('عنوان'), max_length=200, null=True, blank=True)
    comment = models.TextField(_('نظر'))
    
    # Approval
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reviews',
        verbose_name=_('تایید کننده')
    )
    approved_at = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)

    class Meta:
        db_table = 'teacher_reviews'
        verbose_name = _('نظر معلم')
        verbose_name_plural = _('نظرات معلمان')
        ordering = ['-created_at']
        unique_together = ['teacher', 'student', 'class_obj']
        indexes = [
            models.Index(fields=['teacher', 'is_approved']),
        ]

    def __str__(self):
        return f"نظر {self.student.get_full_name()} برای {self.teacher.get_full_name()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update teacher rating
        if is_new or self.is_approved:
            from apps.accounts.models import TeacherProfile
            try:
                profile = TeacherProfile.objects.get(user=self.teacher)
                profile.update_rating()
            except TeacherProfile.DoesNotExist:
                pass
            
class PrivateClassRequest(TimeStampedModel, SoftDeleteModel):
    """
    Private/Semi-Private Class Request Model
    جابجا شده از enrollments به courses
    """
    class RequestStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        APPROVED = 'approved', _('تایید شده')
        REJECTED = 'rejected', _('رد شده')
        SCHEDULED = 'scheduled', _('زمان‌بندی شده')
        ACTIVE = 'active', _('فعال')
        COMPLETED = 'completed', _('تکمیل شده')
        CANCELLED = 'cancelled', _('لغو شده')

    class ClassType(models.TextChoices):
        PRIVATE = 'private', _('خصوصی (1 نفر)')
        SEMI_PRIVATE_2 = 'semi_private_2', _('نیمه خصوصی (2 نفر)')
        SEMI_PRIVATE_3 = 'semi_private_3', _('نیمه خصوصی (3 نفر)')
        SEMI_PRIVATE_4 = 'semi_private_4', _('نیمه خصوصی (4-5 نفر)')

    # Request Info
    request_number = models.CharField(
        _('شماره درخواست'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    # Student(s)
    primary_student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='private_class_requests',
        verbose_name=_('دانش‌آموز اصلی'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    additional_students = models.ManyToManyField(
        User,
        blank=True,
        related_name='additional_private_classes',
        verbose_name=_('دانش‌آموزان اضافی'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    # Course & Branch
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='private_requests',
        verbose_name=_('دوره')
    )
    
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='private_requests',
        verbose_name=_('شعبه')
    )
    
    # Class Type
    class_type = models.CharField(
        _('نوع کلاس'),
        max_length=20,
        choices=ClassType.choices,
        default=ClassType.PRIVATE
    )
    
    # Preferences
    preferred_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_for_private',
        verbose_name=_('معلم ترجیحی'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    
    preferred_days = models.JSONField(
        _('روزهای ترجیحی'),
        default=list,
        help_text='["saturday", "monday"]'
    )
    
    preferred_time_slot = models.CharField(
        _('زمان ترجیحی'),
        max_length=20,
        choices=[
            ('morning', 'صبح (8-12)'),
            ('afternoon', 'بعدازظهر (12-16)'),
            ('evening', 'عصر (16-20)'),
            ('night', 'شب (20-23)'),
        ],
        default='morning'
    )
    
    preferred_location = models.CharField(
        _('محل ترجیحی'),
        max_length=20,
        choices=[
            ('branch', 'شعبه'),
            ('online', 'آنلاین'),
            ('home', 'منزل دانش‌آموز'),
        ],
        default='branch'
    )
    
    # Duration
    sessions_per_week = models.PositiveIntegerField(
        _('تعداد جلسات در هفته'),
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    
    total_sessions = models.PositiveIntegerField(
        _('تعداد کل جلسات'),
        default=24,
        validators=[MinValueValidator(4)]
    )
    
    session_duration = models.PositiveIntegerField(
        _('مدت هر جلسه (دقیقه)'),
        default=90,
        choices=[
            (60, '60 دقیقه'),
            (90, '90 دقیقه'),
            (120, '120 دقیقه'),
        ]
    )
    
    # Start Date
    preferred_start_date = models.DateField(
        _('تاریخ شروع ترجیحی'),
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    
    # ⚠️ حذف قسمت قیمت‌گذاری - باید از طریق Invoice مدیریت شود
    # pricing_approved = models.BooleanField(_('قیمت تایید شده'), default=False)
    
    # Assigned
    assigned_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_private_classes',
        verbose_name=_('معلم اختصاص داده شده'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    
    created_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='private_request_source',
        verbose_name=_('کلاس ایجاد شده')
    )
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_private_requests',
        verbose_name=_('تایید کننده')
    )
    approved_at = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)
    
    # Notes
    student_notes = models.TextField(_('یادداشت دانش‌آموز'), null=True, blank=True)
    admin_notes = models.TextField(_('یادداشت مدیر'), null=True, blank=True)
    rejection_reason = models.TextField(_('دلیل رد'), null=True, blank=True)

    class Meta:
        db_table = 'private_class_requests'
        verbose_name = _('درخواست کلاس خصوصی')
        verbose_name_plural = _('درخواست‌های کلاس خصوصی')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_number} - {self.primary_student.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            from django.utils import timezone
            year = timezone.now().year
            count = PrivateClassRequest.objects.filter(
                created_at__year=year
            ).count() + 1
            self.request_number = f"PVT{year}{count:05d}"
        
        super().save(*args, **kwargs)

    @property
    def student_count(self):
        return 1 + self.additional_students.count()

    def calculate_estimated_price(self):
        """محاسبه قیمت تخمینی - فقط برای نمایش"""
        # قیمت پایه بر اساس نوع کلاس
        base_prices = {
            self.ClassType.PRIVATE: 500000,
            self.ClassType.SEMI_PRIVATE_2: 350000,
            self.ClassType.SEMI_PRIVATE_3: 300000,
            self.ClassType.SEMI_PRIVATE_4: 250000,
        }
        
        base_price = base_prices.get(self.class_type, 500000)
        total = base_price * self.total_sessions
        
        # تخفیف بر اساس تعداد جلسات
        if self.total_sessions >= 48:
            discount_percent = 15
        elif self.total_sessions >= 36:
            discount_percent = 10
        elif self.total_sessions >= 24:
            discount_percent = 5
        else:
            discount_percent = 0
        
        discount = (total * discount_percent) / 100
        
        return {
            'base_price_per_session': base_price,
            'total_sessions': self.total_sessions,
            'subtotal': total,
            'discount_percent': discount_percent,
            'discount_amount': discount,
            'estimated_total': total - discount
        }
        
class PrivateClassPricing(TimeStampedModel):
    """
    قیمت‌گذاری کلاس‌های خصوصی
    """
    class_type = models.CharField(
        _('نوع کلاس'),
        max_length=20,
        choices=PrivateClassRequest.ClassType.choices,
        unique=True
    )
    
    price_per_session = models.DecimalField(
        _('قیمت هر جلسه'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    # تخفیف بر اساس تعداد جلسات
    discount_24_sessions = models.DecimalField(
        _('تخفیف 24 جلسه (درصد)'),
        max_digits=5,
        decimal_places=2,
        default=5
    )
    
    discount_36_sessions = models.DecimalField(
        _('تخفیف 36 جلسه (درصد)'),
        max_digits=5,
        decimal_places=2,
        default=10
    )
    
    discount_48_sessions = models.DecimalField(
        _('تخفیف 48 جلسه یا بیشتر (درصد)'),
        max_digits=5,
        decimal_places=2,
        default=15
    )
    
    is_active = models.BooleanField(_('فعال'), default=True)
    
    class Meta:
        db_table = 'private_class_pricing'
        verbose_name = _('قیمت‌گذاری کلاس خصوصی')
        verbose_name_plural = _('قیمت‌گذاری کلاس‌های خصوصی')

    def __str__(self):
        return f"{self.get_class_type_display()} - {self.price_per_session:,} تومان"

    def calculate_total(self, sessions):
        """محاسبه قیمت کل با تخفیف"""
        subtotal = self.price_per_session * sessions
        
        if sessions >= 48:
            discount_percent = self.discount_48_sessions
        elif sessions >= 36:
            discount_percent = self.discount_36_sessions
        elif sessions >= 24:
            discount_percent = self.discount_24_sessions
        else:
            discount_percent = 0
        
        discount = (subtotal * discount_percent) / 100
        
        return {
            'subtotal': subtotal,
            'discount_percent': discount_percent,
            'discount_amount': discount,
            'total': subtotal - discount
        }
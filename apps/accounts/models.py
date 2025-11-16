from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel
import jdatetime


class UserManager(BaseUserManager):
    """
    Custom user manager
    """
    def create_user(self, mobile, password=None, **extra_fields):
        if not mobile:
            raise ValueError('شماره موبایل الزامی است')
        
        user = self.model(mobile=mobile, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(mobile, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel, SoftDeleteModel):
    """
    Custom User Model
    """
    class UserRole(models.TextChoices):
        SUPER_ADMIN = 'super_admin', _('مدیر کل')
        BRANCH_MANAGER = 'branch_manager', _('مدیر شعبه')
        TEACHER = 'teacher', _('معلم')
        STUDENT = 'student', _('دانش آموز')
        ACCOUNTANT = 'accountant', _('حسابدار')
        RECEPTIONIST = 'receptionist', _('کارمند پذیرش')
        SUPPORT = 'support', _('پشتیبان')

    class Gender(models.TextChoices):
        MALE = 'male', _('مرد')
        FEMALE = 'female', _('زن')
        OTHER = 'other', _('سایر')

    # Phone validator
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره موبایل باید به فرمت 09xxxxxxxxx باشد"
    )

    # Basic Info
    mobile = models.CharField(
        _('شماره موبایل'),
        max_length=11,
        unique=True,
        validators=[phone_regex]
    )
    email = models.EmailField(_('ایمیل'), unique=True, null=True, blank=True)
    
    first_name = models.CharField(_('نام'), max_length=50)
    last_name = models.CharField(_('نام خانوادگی'), max_length=50)
    national_code = models.CharField(
        _('کد ملی'),
        max_length=10,
        unique=True,
        null=True,
        blank=True
    )
    
    # Personal Info
    gender = models.CharField(
        _('جنسیت'),
        max_length=10,
        choices=Gender.choices,
        null=True,
        blank=True
    )
    birth_date = models.DateField(_('تاریخ تولد'), null=True, blank=True)
    profile_picture = models.ImageField(
        _('تصویر پروفایل'),
        upload_to='profiles/',
        null=True,
        blank=True
    )
    
    # Contact Info
    phone = models.CharField(_('تلفن ثابت'), max_length=11, null=True, blank=True)
    address = models.TextField(_('آدرس'), null=True, blank=True)
    city = models.CharField(_('شهر'), max_length=50, null=True, blank=True)
    province = models.CharField(_('استان'), max_length=50, null=True, blank=True)
    postal_code = models.CharField(_('کد پستی'), max_length=10, null=True, blank=True)
    
    # Role & Permissions
    role = models.CharField(
        _('نقش'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT
    )
    
    # Status
    is_active = models.BooleanField(_('فعال'), default=True)
    is_staff = models.BooleanField(_('کارمند'), default=False)
    is_verified = models.BooleanField(_('تایید شده'), default=False)
    
    # Timestamps
    last_login_ip = models.GenericIPAddressField(_('آخرین IP'), null=True, blank=True)
    email_verified_at = models.DateTimeField(_('تاریخ تایید ایمیل'), null=True, blank=True)
    mobile_verified_at = models.DateTimeField(_('تاریخ تایید موبایل'), null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = _('کاربر')
        verbose_name_plural = _('کاربران')
        indexes = [
            models.Index(fields=['mobile']),
            models.Index(fields=['email']),
            models.Index(fields=['national_code']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.mobile})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def age(self):
        if self.birth_date:
            from django.utils import timezone
            today = timezone.now().date()
            return today.year - self.birth_date.year
        return None

    @property
    def jalali_birth_date(self):
        if self.birth_date:
            return jdatetime.date.fromgregorian(date=self.birth_date)
        return None


class OTP(TimeStampedModel):
    """
    One Time Password for mobile verification
    """
    class OTPPurpose(models.TextChoices):
        LOGIN = 'login', _('ورود')
        REGISTER = 'register', _('ثبت نام')
        RESET_PASSWORD = 'reset_password', _('بازیابی رمز')
        VERIFY_MOBILE = 'verify_mobile', _('تایید موبایل')

    mobile = models.CharField(_('شماره موبایل'), max_length=11)
    code = models.CharField(_('کد'), max_length=6)
    purpose = models.CharField(
        _('هدف'),
        max_length=20,
        choices=OTPPurpose.choices,
        default=OTPPurpose.LOGIN
    )
    
    is_used = models.BooleanField(_('استفاده شده'), default=False)
    is_expired = models.BooleanField(_('منقضی شده'), default=False)
    expires_at = models.DateTimeField(_('تاریخ انقضا'))
    
    ip_address = models.GenericIPAddressField(_('IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), null=True, blank=True)
    
    attempts = models.PositiveIntegerField(_('تعداد تلاش'), default=0)
    verified_at = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)

    class Meta:
        db_table = 'otps'
        verbose_name = _('کد یکبار مصرف')
        verbose_name_plural = _('کدهای یکبار مصرف')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile', 'code']),
            models.Index(fields=['mobile', 'is_used', 'is_expired']),
        ]

    def __str__(self):
        return f"{self.mobile} - {self.code}"

    def is_valid(self):
        from django.utils import timezone
        if self.is_used or self.is_expired:
            return False
        if timezone.now() > self.expires_at:
            self.is_expired = True
            self.save()
            return False
        return True

class GradeLevel(TimeStampedModel):
    """
    مدل برای تعریف پایه‌های تحصیلی
    مثال: اول ابتدایی، دهم تجربی، پیش‌دانشگاهی
    """
    name = models.CharField(_('نام پایه'), max_length=100, unique=True)
    order = models.PositiveIntegerField(
        _('ترتیب'),
        default=0,
        help_text='برای مرتب‌سازی پایه‌ها (مثلاً اول ابتدایی = 1)'
    )
    
    # برای گروه‌بندی (اختیاری)
    class GradeStage(models.TextChoices):
        PRESCHOOL = 'preschool', _('پیش‌دبستانی')
        ELEMENTARY = 'elementary', _('ابتدایی')
        MIDDLE_SCHOOL = 'middle_school', _('متوسطه اول')
        HIGH_SCHOOL = 'high_school', _('متوسطه دوم')
        UNIVERSITY = 'university', _('دانشگاهی')
        OTHER = 'other', _('سایر')

    stage = models.CharField(
        _('مقطع تحصیلی'),
        max_length=20,
        choices=GradeStage.choices,
        default=GradeStage.OTHER,
        db_index=True
    )
    
    is_active = models.BooleanField(_('فعال'), default=True)
    
    class Meta:
        db_table = 'grade_levels'
        verbose_name = _('پایه تحصیلی')
        verbose_name_plural = _('پایه‌های تحصیلی')
        ordering = ['order']

    def __str__(self):
        return self.name

class StudentProfile(TimeStampedModel):
    """
    Extended profile for students
    """
    class EducationLevel(models.TextChoices):
        ELEMENTARY = 'elementary', _('ابتدایی')
        MIDDLE_SCHOOL = 'middle_school', _('راهنمایی')
        HIGH_SCHOOL = 'high_school', _('دبیرستان')
        DIPLOMA = 'diploma', _('دیپلم')
        ASSOCIATE = 'associate', _('کاردانی')
        BACHELOR = 'bachelor', _('کارشناسی')
        MASTER = 'master', _('کارشناسی ارشد')
        PHD = 'phd', _('دکترا')

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_('کاربر')
    )
    
    # Emergency Contact
    emergency_contact_name = models.CharField(
        _('نام تماس اضطراری'),
        max_length=100,
        null=True,
        blank=True
    )
    emergency_contact_phone = models.CharField(
        _('شماره تماس اضطراری'),
        max_length=11,
        null=True,
        blank=True
    )
    emergency_contact_relation = models.CharField(
        _('نسبت'),
        max_length=50,
        null=True,
        blank=True
    )
    grade_level = models.ForeignKey(
        GradeLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name=_('پایه تحصیلی')
    )
    # Guardian Info (for minors)
    guardian_name = models.CharField(_('نام ولی'), max_length=100, null=True, blank=True)
    guardian_mobile = models.CharField(_('موبایل ولی'), max_length=11, null=True, blank=True)
    guardian_national_code = models.CharField(
        _('کد ملی ولی'),
        max_length=10,
        null=True,
        blank=True
    )
    
    # Education
    education_level = models.CharField(
        _('مقطع تحصیلی'),
        max_length=20,
        choices=EducationLevel.choices,
        null=True,
        blank=True
    )
    school_name = models.CharField(_('نام مدرسه/دانشگاه'), max_length=200, null=True, blank=True)
    field_of_study = models.CharField(_('رشته تحصیلی'), max_length=100, null=True, blank=True)
    
    # Medical Info
    medical_conditions = models.TextField(_('وضعیت پزشکی'), null=True, blank=True)
    allergies = models.TextField(_('آلرژی‌ها'), null=True, blank=True)
    
    # Documents
    id_card_image = models.ImageField(
        _('تصویر کارت ملی'),
        upload_to='students/documents/',
        null=True,
        blank=True
    )
    birth_certificate_image = models.ImageField(
        _('تصویر شناسنامه'),
        upload_to='students/documents/',
        null=True,
        blank=True
    )
    
    # Registration
    registration_date = models.DateField(_('تاریخ ثبت نام'), auto_now_add=True)
    student_number = models.CharField(
        _('شماره دانشجویی'),
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )
    
    # Status
    is_active_student = models.BooleanField(_('دانش آموز فعال'), default=True)
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'student_profiles'
        verbose_name = _('پروفایل دانش آموز')
        verbose_name_plural = _('پروفایل‌های دانش آموز')

    def __str__(self):
        return f"پروفایل {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.student_number:
            # Generate student number
            from django.utils import timezone
            year = timezone.now().year
            count = StudentProfile.objects.filter(
                registration_date__year=year
            ).count() + 1
            self.student_number = f"{year}{count:05d}"
        super().save(*args, **kwargs)


class TeacherProfile(TimeStampedModel):
    """
    Extended profile for teachers
    """
    class TeacherStatus(models.TextChoices):
        ACTIVE = 'active', _('فعال')
        INACTIVE = 'inactive', _('غیرفعال')
        ON_LEAVE = 'on_leave', _('مرخصی')
        SUSPENDED = 'suspended', _('معلق')

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_('کاربر')
    )
    
    # Professional Info
    expertise = models.TextField(_('تخصص‌ها'))
    experience_years = models.PositiveIntegerField(_('سال‌های تجربه'), default=0)
    education_degree = models.CharField(_('مدرک تحصیلی'), max_length=100)
    university = models.CharField(_('دانشگاه'), max_length=200, null=True, blank=True)
    
    # Bio
    bio = models.TextField(_('بیوگرافی'), null=True, blank=True)
    specialties = models.TextField(_('تخصص‌های ویژه'), null=True, blank=True)
    
    # Rating
    rating = models.DecimalField(
        _('امتیاز'),
        max_digits=3,
        decimal_places=2,
        default=0,
        help_text='از 0 تا 5'
    )
    total_reviews = models.PositiveIntegerField(_('تعداد نظرات'), default=0)
    
    # Employment
    employment_date = models.DateField(_('تاریخ استخدام'), null=True, blank=True)
    employee_code = models.CharField(
        _('کد کارمندی'),
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )
    contract_type = models.CharField(
        _('نوع قرارداد'),
        max_length=50,
        null=True,
        blank=True,
        help_text='تمام وقت، پاره وقت، پیمانی'
    )
    
    # Financial
    hourly_rate = models.DecimalField(
        _('نرخ ساعتی'),
        max_digits=10,
        decimal_places=0,
        default=0
    )
    base_salary = models.DecimalField(
        _('حقوق پایه'),
        max_digits=12,
        decimal_places=0,
        default=0,
        null=True,
        blank=True
    )
    commission_rate = models.DecimalField(
        _('نرخ کمیسیون'),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='درصد'
    )
    
    # Documents
    resume = models.FileField(
        _('رزومه'),
        upload_to='teachers/resumes/',
        null=True,
        blank=True
    )
    certificates = models.FileField(
        _('مدارک'),
        upload_to='teachers/certificates/',
        null=True,
        blank=True
    )
    contract_file = models.FileField(
        _('فایل قرارداد'),
        upload_to='teachers/contracts/',
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=TeacherStatus.choices,
        default=TeacherStatus.ACTIVE
    )
    can_teach_online = models.BooleanField(_('امکان تدریس آنلاین'), default=True)
    max_students_per_class = models.PositiveIntegerField(
        _('حداکثر دانش آموز در کلاس'),
        default=20
    )
    
    # Social
    website = models.URLField(_('وب‌سایت'), null=True, blank=True)
    linkedin = models.URLField(_('لینکدین'), null=True, blank=True)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'teacher_profiles'
        verbose_name = _('پروفایل معلم')
        verbose_name_plural = _('پروفایل‌های معلم')

    def __str__(self):
        return f"معلم: {self.user.get_full_name()}"

    def update_rating(self):
        """Calculate and update teacher rating"""
        from django.db.models import Avg
        from apps.courses.models import TeacherReview
        
        avg_rating = TeacherReview.objects.filter(
            teacher=self.user,
            is_approved=True
        ).aggregate(Avg('rating'))['rating__avg']
        
        if avg_rating:
            self.rating = round(avg_rating, 2)
            self.total_reviews = TeacherReview.objects.filter(
                teacher=self.user,
                is_approved=True
            ).count()
            self.save()


class LoginHistory(TimeStampedModel):
    """
    Track user login history
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name=_('کاربر')
    )
    
    ip_address = models.GenericIPAddressField(_('IP'))
    user_agent = models.TextField(_('User Agent'))
    device_type = models.CharField(_('نوع دستگاه'), max_length=50, null=True, blank=True)
    browser = models.CharField(_('مرورگر'), max_length=50, null=True, blank=True)
    os = models.CharField(_('سیستم عامل'), max_length=50, null=True, blank=True)
    
    login_successful = models.BooleanField(_('ورود موفق'), default=True)
    logout_at = models.DateTimeField(_('خروج'), null=True, blank=True)
    
    location = models.CharField(_('موقعیت'), max_length=200, null=True, blank=True)
    country = models.CharField(_('کشور'), max_length=100, null=True, blank=True)
    city = models.CharField(_('شهر'), max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'login_history'
        verbose_name = _('تاریخچه ورود')
        verbose_name_plural = _('تاریخچه‌های ورود')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.mobile} - {self.created_at}"
    
    

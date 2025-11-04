from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import User


class Branch(TimeStampedModel, SoftDeleteModel):
    """
    Branch Model
    """
    class BranchStatus(models.TextChoices):
        ACTIVE = 'active', _('فعال')
        INACTIVE = 'inactive', _('غیرفعال')
        UNDER_CONSTRUCTION = 'under_construction', _('در حال ساخت')

    name = models.CharField(_('نام شعبه'), max_length=200)
    code = models.CharField(_('کد شعبه'), max_length=20, unique=True)
    
    # Manager
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branches',
        verbose_name=_('مدیر شعبه'),
        limit_choices_to={'role': User.UserRole.BRANCH_MANAGER}
    )
    
    # Contact Info
    phone = models.CharField(_('تلفن'), max_length=11)
    email = models.EmailField(_('ایمیل'), null=True, blank=True)
    
    # Address
    province = models.CharField(_('استان'), max_length=100)
    city = models.CharField(_('شهر'), max_length=100)
    address = models.TextField(_('آدرس'))
    postal_code = models.CharField(_('کد پستی'), max_length=10, null=True, blank=True)
    
    # Location
    latitude = models.DecimalField(
        _('عرض جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        _('طول جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Capacity
    total_capacity = models.PositiveIntegerField(
        _('ظرفیت کل'),
        default=100,
        validators=[MinValueValidator(1)]
    )
    
    # Working Hours
    working_hours_start = models.TimeField(_('ساعت شروع کار'), null=True, blank=True)
    working_hours_end = models.TimeField(_('ساعت پایان کار'), null=True, blank=True)
    working_days = models.CharField(
        _('روزهای کاری'),
        max_length=200,
        default='شنبه تا پنجشنبه',
        help_text='مثال: شنبه تا پنجشنبه'
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=BranchStatus.choices,
        default=BranchStatus.ACTIVE
    )
    
    # Images
    image = models.ImageField(
        _('تصویر'),
        upload_to='branches/',
        null=True,
        blank=True
    )
    
    # Description
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    facilities = models.TextField(
        _('امکانات'),
        null=True,
        blank=True,
        help_text='امکانات موجود در شعبه'
    )
    
    # Metadata
    established_date = models.DateField(_('تاریخ تاسیس'), null=True, blank=True)

    class Meta:
        db_table = 'branches'
        verbose_name = _('شعبه')
        verbose_name_plural = _('شعب')
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['city']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def active_classrooms_count(self):
        return self.classrooms.filter(is_active=True).count()

    @property
    def current_students_count(self):
        # این قسمت بعداً با enrollments کامل می‌شود
        return 0

    @property
    def is_active(self):
        return self.status == self.BranchStatus.ACTIVE


class Classroom(TimeStampedModel, SoftDeleteModel):
    """
    Physical Classroom Model
    """
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name=_('شعبه')
    )
    
    name = models.CharField(_('نام کلاس'), max_length=100)
    room_number = models.CharField(_('شماره اتاق'), max_length=20)
    
    # Capacity
    capacity = models.PositiveIntegerField(
        _('ظرفیت'),
        validators=[MinValueValidator(1)]
    )
    
    # Facilities
    has_projector = models.BooleanField(_('دارای پروژکتور'), default=False)
    has_whiteboard = models.BooleanField(_('دارای وایت برد'), default=True)
    has_smartboard = models.BooleanField(_('دارای اسمارت برد'), default=False)
    has_ac = models.BooleanField(_('دارای کولر'), default=False)
    has_computer = models.BooleanField(_('دارای کامپیوتر'), default=False)
    
    # Status
    is_active = models.BooleanField(_('فعال'), default=True)
    
    # Description
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    equipment = models.TextField(_('تجهیزات'), null=True, blank=True)
    
    # Image
    image = models.ImageField(
        _('تصویر'),
        upload_to='classrooms/',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'classrooms'
        verbose_name = _('کلاس فیزیکی')
        verbose_name_plural = _('کلاس‌های فیزیکی')
        ordering = ['branch', 'room_number']
        unique_together = ['branch', 'room_number']
        indexes = [
            models.Index(fields=['branch', 'is_active']),
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.name} ({self.room_number})"


class BranchStaff(TimeStampedModel):
    """
    Staff assigned to branches
    """
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='staff',
        verbose_name=_('شعبه')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='branch_assignments',
        verbose_name=_('کاربر')
    )
    
    position = models.CharField(_('سمت'), max_length=100)
    is_active = models.BooleanField(_('فعال'), default=True)
    assigned_date = models.DateField(_('تاریخ تخصیص'), auto_now_add=True)
    end_date = models.DateField(_('تاریخ پایان'), null=True, blank=True)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'branch_staff'
        verbose_name = _('کارمند شعبه')
        verbose_name_plural = _('کارمندان شعبه')
        unique_together = ['branch', 'user']
        indexes = [
            models.Index(fields=['branch', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.branch.name}"
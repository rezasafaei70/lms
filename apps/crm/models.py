from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import User
from apps.branches.models import Branch
from apps.courses.models import Course


class Lead(TimeStampedModel, SoftDeleteModel):
    """
    Lead Model (مشتری بالقوه)
    """
    class LeadStatus(models.TextChoices):
        NEW = 'new', _('جدید')
        CONTACTED = 'contacted', _('تماس گرفته شده')
        QUALIFIED = 'qualified', _('واجد شرایط')
        CONVERTED = 'converted', _('تبدیل شده')
        LOST = 'lost', _('از دست رفته')

    class LeadSource(models.TextChoices):
        WEBSITE = 'website', _('وب‌سایت')
        PHONE = 'phone', _('تلفن')
        REFERRAL = 'referral', _('معرفی')
        SOCIAL_MEDIA = 'social_media', _('شبکه‌های اجتماعی')
        WALK_IN = 'walk_in', _('مراجعه حضوری')
        ADVERTISEMENT = 'advertisement', _('تبلیغات')
        OTHER = 'other', _('سایر')

    # Phone validator
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره موبایل باید به فرمت 09xxxxxxxxx باشد"
    )

    # Basic Info
    first_name = models.CharField(_('نام'), max_length=50)
    last_name = models.CharField(_('نام خانوادگی'), max_length=50)
    mobile = models.CharField(
        _('شماره موبایل'),
        max_length=11,
        validators=[phone_regex]
    )
    email = models.EmailField(_('ایمیل'), null=True, blank=True)
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW
    )
    
    # Source
    source = models.CharField(
        _('منبع'),
        max_length=20,
        choices=LeadSource.choices
    )
    source_details = models.CharField(
        _('جزئیات منبع'),
        max_length=255,
        null=True,
        blank=True
    )
    
    # Interest
    interested_course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interested_leads',
        verbose_name=_('دوره مورد علاقه')
    )
    
    preferred_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
        verbose_name=_('شعبه ترجیحی')
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        verbose_name=_('اختصاص داده شده به')
    )
    
    # Conversion
    converted_to_student = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_conversion',
        verbose_name=_('تبدیل به دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    converted_at = models.DateTimeField(_('تاریخ تبدیل'), null=True, blank=True)
    
    # Score
    score = models.PositiveIntegerField(
        _('امتیاز'),
        default=0,
        help_text='امتیاز کیفیت لید (0-100)'
    )
    
    # Notes
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)
    
    # Last contact
    last_contact_date = models.DateTimeField(_('آخرین تماس'), null=True, blank=True)
    next_follow_up_date = models.DateTimeField(_('پیگیری بعدی'), null=True, blank=True)

    class Meta:
        db_table = 'crm_leads'
        verbose_name = _('لید')
        verbose_name_plural = _('لیدها')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile']),
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['source']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.mobile}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class LeadActivity(TimeStampedModel):
    """
    Lead Activity Log
    """
    class ActivityType(models.TextChoices):
        CALL = 'call', _('تماس')
        EMAIL = 'email', _('ایمیل')
        SMS = 'sms', _('پیامک')
        MEETING = 'meeting', _('جلسه')
        NOTE = 'note', _('یادداشت')
        STATUS_CHANGE = 'status_change', _('تغییر وضعیت')

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name=_('لید')
    )
    
    activity_type = models.CharField(
        _('نوع فعالیت'),
        max_length=20,
        choices=ActivityType.choices
    )
    
    subject = models.CharField(_('موضوع'), max_length=255)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    # User who performed the activity
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lead_activities',
        verbose_name=_('انجام دهنده')
    )
    
    # Activity date/time
    activity_date = models.DateTimeField(_('تاریخ فعالیت'), auto_now_add=True)
    
    # Duration (for calls, meetings)
    duration_minutes = models.PositiveIntegerField(
        _('مدت زمان (دقیقه)'),
        null=True,
        blank=True
    )
    
    # Outcome
    outcome = models.TextField(_('نتیجه'), null=True, blank=True)

    class Meta:
        db_table = 'crm_lead_activities'
        verbose_name = _('فعالیت لید')
        verbose_name_plural = _('فعالیت‌های لید')
        ordering = ['-activity_date']

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.lead.full_name}"


class Campaign(TimeStampedModel, SoftDeleteModel):
    """
    Marketing Campaign Model
    """
    class CampaignType(models.TextChoices):
        EMAIL = 'email', _('ایمیل')
        SMS = 'sms', _('پیامک')
        SOCIAL_MEDIA = 'social_media', _('شبکه اجتماعی')
        PHONE = 'phone', _('تماس تلفنی')
        EVENT = 'event', _('رویداد')
        OTHER = 'other', _('سایر')

    class CampaignStatus(models.TextChoices):
        DRAFT = 'draft', _('پیش‌نویس')
        SCHEDULED = 'scheduled', _('زمان‌بندی شده')
        ACTIVE = 'active', _('فعال')
        COMPLETED = 'completed', _('تکمیل شده')
        CANCELLED = 'cancelled', _('لغو شده')

    name = models.CharField(_('نام کمپین'), max_length=255)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    campaign_type = models.CharField(
        _('نوع کمپین'),
        max_length=20,
        choices=CampaignType.choices
    )
    
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT
    )
    
    # Dates
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    
    # Target
    target_course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name=_('دوره هدف')
    )
    
    target_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name=_('شعبه هدف')
    )
    
    # Budget
    budget = models.DecimalField(
        _('بودجه'),
        max_digits=12,
        decimal_places=0,
        default=0
    )
    
    spent = models.DecimalField(
        _('هزینه شده'),
        max_digits=12,
        decimal_places=0,
        default=0
    )
    
    # Content
    message_template = models.TextField(
        _('قالب پیام'),
        null=True,
        blank=True
    )
    
    # Results
    total_sent = models.PositiveIntegerField(_('تعداد ارسال'), default=0)
    total_delivered = models.PositiveIntegerField(_('تعداد تحویل'), default=0)
    total_opened = models.PositiveIntegerField(_('تعداد بازشده'), default=0)
    total_clicked = models.PositiveIntegerField(_('تعداد کلیک'), default=0)
    total_conversions = models.PositiveIntegerField(_('تعداد تبدیل'), default=0)
    
    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_campaigns',
        verbose_name=_('ایجاد کننده')
    )

    class Meta:
        db_table = 'crm_campaigns'
        verbose_name = _('کمپین')
        verbose_name_plural = _('کمپین‌ها')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def conversion_rate(self):
        if self.total_sent > 0:
            return (self.total_conversions / self.total_sent) * 100
        return 0

    @property
    def roi(self):
        """Return on Investment"""
        if self.spent > 0:
            # Calculate based on conversions
            # This is simplified - should calculate actual revenue
            return ((self.total_conversions * 1000000 - self.spent) / self.spent) * 100
        return 0


class CampaignLead(TimeStampedModel):
    """
    Campaign-Lead Relationship
    """
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='campaign_leads',
        verbose_name=_('کمپین')
    )
    
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='campaigns',
        verbose_name=_('لید')
    )
    
    # Tracking
    sent_at = models.DateTimeField(_('زمان ارسال'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('زمان تحویل'), null=True, blank=True)
    opened_at = models.DateTimeField(_('زمان بازشدن'), null=True, blank=True)
    clicked_at = models.DateTimeField(_('زمان کلیک'), null=True, blank=True)
    converted_at = models.DateTimeField(_('زمان تبدیل'), null=True, blank=True)
    
    # Response
    response = models.TextField(_('پاسخ'), null=True, blank=True)

    class Meta:
        db_table = 'crm_campaign_leads'
        verbose_name = _('لید کمپین')
        verbose_name_plural = _('لیدهای کمپین')
        unique_together = ['campaign', 'lead']

    def __str__(self):
        return f"{self.campaign.name} - {self.lead.full_name}"


class CustomerFeedback(TimeStampedModel):
    """
    Customer Feedback Model
    """
    class FeedbackType(models.TextChoices):
        COMPLAINT = 'complaint', _('شکایت')
        SUGGESTION = 'suggestion', _('پیشنهاد')
        PRAISE = 'praise', _('تقدیر')
        QUESTION = 'question', _('سوال')
        OTHER = 'other', _('سایر')

    class FeedbackStatus(models.TextChoices):
        NEW = 'new', _('جدید')
        IN_PROGRESS = 'in_progress', _('در حال بررسی')
        RESOLVED = 'resolved', _('حل شده')
        CLOSED = 'closed', _('بسته شده')

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        verbose_name=_('مشتری')
    )
    
    feedback_type = models.CharField(
        _('نوع بازخورد'),
        max_length=20,
        choices=FeedbackType.choices
    )
    
    subject = models.CharField(_('موضوع'), max_length=255)
    message = models.TextField(_('پیام'))
    
    # Related objects
    related_class = models.ForeignKey(
        'courses.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedbacks',
        verbose_name=_('کلاس مرتبط')
    )
    
    related_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_feedbacks',
        verbose_name=_('معلم مرتبط'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.NEW
    )
    
    # Priority
    priority = models.PositiveSmallIntegerField(
        _('اولویت'),
        default=3,
        help_text='1=بالا, 3=متوسط, 5=پایین'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_feedbacks',
        verbose_name=_('مسئول رسیدگی')
    )
    
    # Resolution
    resolution = models.TextField(_('راه حل'), null=True, blank=True)
    resolved_at = models.DateTimeField(_('تاریخ حل'), null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_feedbacks',
        verbose_name=_('حل کننده')
    )
    
    # Customer satisfaction
    satisfaction_rating = models.PositiveSmallIntegerField(
        _('امتیاز رضایت'),
        null=True,
        blank=True,
        help_text='1-5'
    )

    class Meta:
        db_table = 'crm_customer_feedbacks'
        verbose_name = _('بازخورد مشتری')
        verbose_name_plural = _('بازخوردهای مشتری')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.customer.get_full_name()}"


class LoyaltyProgram(TimeStampedModel):
    """
    Loyalty Program Model
    """
    name = models.CharField(_('نام برنامه'), max_length=255)
    description = models.TextField(_('توضیحات'))
    
    # Status
    is_active = models.BooleanField(_('فعال'), default=True)
    
    # Dates
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'), null=True, blank=True)
    
    # Points
    points_per_enrollment = models.PositiveIntegerField(
        _('امتیاز به ازای هر ثبت‌نام'),
        default=100
    )
    points_per_referral = models.PositiveIntegerField(
        _('امتیاز به ازای هر معرفی'),
        default=200
    )
    points_per_1000_toman = models.PositiveIntegerField(
        _('امتیاز به ازای هر 1000 تومان'),
        default=1
    )
    
    # Rewards
    rewards = models.JSONField(
        _('پاداش‌ها'),
        default=list,
        help_text='لیست پاداش‌ها و امتیاز مورد نیاز'
    )

    class Meta:
        db_table = 'crm_loyalty_programs'
        verbose_name = _('برنامه وفاداری')
        verbose_name_plural = _('برنامه‌های وفاداری')

    def __str__(self):
        return self.name


class CustomerLoyaltyPoints(TimeStampedModel):
    """
    Customer Loyalty Points
    """
    class TransactionType(models.TextChoices):
        EARNED = 'earned', _('کسب شده')
        REDEEMED = 'redeemed', _('استفاده شده')
        EXPIRED = 'expired', _('منقضی شده')
        ADJUSTED = 'adjusted', _('تعدیل شده')

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='loyalty_points',
        verbose_name=_('مشتری')
    )
    
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='customer_points',
        verbose_name=_('برنامه وفاداری')
    )
    
    transaction_type = models.CharField(
        _('نوع تراکنش'),
        max_length=20,
        choices=TransactionType.choices
    )
    
    points = models.IntegerField(_('امتیاز'))
    balance_after = models.IntegerField(_('موجودی بعد از تراکنش'))
    
    # Reference
    reference_type = models.CharField(
        _('نوع مرجع'),
        max_length=50,
        null=True,
        blank=True
    )
    reference_id = models.CharField(
        _('شناسه مرجع'),
        max_length=50,
        null=True,
        blank=True
    )
    
    description = models.CharField(_('توضیحات'), max_length=255)
    
    # Expiration
    expires_at = models.DateField(_('تاریخ انقضا'), null=True, blank=True)

    class Meta:
        db_table = 'crm_customer_loyalty_points'
        verbose_name = _('امتیاز وفاداری')
        verbose_name_plural = _('امتیازات وفاداری')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.points} امتیاز"


class Referral(TimeStampedModel):
    """
    Student Referral Model
    """
    class ReferralStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        REGISTERED = 'registered', _('ثبت‌نام شده')
        ENROLLED = 'enrolled', _('کلاس گرفته')
        REWARDED = 'rewarded', _('پاداش داده شده')

    referrer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referrals_made',
        verbose_name=_('معرف')
    )
    
    referred_name = models.CharField(_('نام معرفی شده'), max_length=100)
    referred_mobile = models.CharField(_('موبایل معرفی شده'), max_length=11)
    
    # Converted user
    referred_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_by',
        verbose_name=_('کاربر معرفی شده')
    )
    
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=ReferralStatus.choices,
        default=ReferralStatus.PENDING
    )
    
    # Reward
    reward_given = models.BooleanField(_('پاداش داده شده'), default=False)
    reward_type = models.CharField(
        _('نوع پاداش'),
        max_length=50,
        null=True,
        blank=True
    )
    reward_value = models.DecimalField(
        _('مقدار پاداش'),
        max_digits=12,
        decimal_places=0,
        default=0
    )
    rewarded_at = models.DateTimeField(_('تاریخ پاداش'), null=True, blank=True)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'crm_referrals'
        verbose_name = _('معرفی')
        verbose_name_plural = _('معرفی‌ها')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.referrer.get_full_name()} -> {self.referred_name}"
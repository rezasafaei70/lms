from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import User
from apps.enrollments.models import Enrollment
from apps.branches.models import Branch
import uuid


class Invoice(TimeStampedModel, SoftDeleteModel):
    """
    Invoice Model
    """
    class InvoiceType(models.TextChoices):
        TUITION = 'tuition', _('شهریه')
        REGISTRATION = 'registration', _('ثبت‌نام')
        BOOK = 'book', _('کتاب')
        EXAM = 'exam', _('آزمون')
        CERTIFICATE = 'certificate', _('گواهینامه')
        OTHER = 'other', _('سایر')

    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', _('پیش‌نویس')
        PENDING = 'pending', _('در انتظار پرداخت')
        PAID = 'paid', _('پرداخت شده')
        PARTIALLY_PAID = 'partially_paid', _('پرداخت جزئی')
        CANCELLED = 'cancelled', _('لغو شده')
        REFUNDED = 'refunded', _('بازگشت داده شده')

    # Invoice Info
    invoice_number = models.CharField(
        _('شماره فاکتور'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_('دانش‌آموز'),
        limit_choices_to={'role': User.UserRole.STUDENT}
    )
    
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name=_('ثبت‌نام')
    )
    
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_('شعبه')
    )
    
    # Type
    invoice_type = models.CharField(
        _('نوع فاکتور'),
        max_length=20,
        choices=InvoiceType.choices,
        default=InvoiceType.TUITION
    )
    
    # Amounts
    subtotal = models.DecimalField(
        _('جمع جزء'),
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
    
    tax_amount = models.DecimalField(
        _('مالیات'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    total_amount = models.DecimalField(
        _('مبلغ کل'),
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
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
    
    # Dates
    issue_date = models.DateField(_('تاریخ صدور'))
    due_date = models.DateField(_('سررسید'))
    paid_date = models.DateField(_('تاریخ پرداخت'), null=True, blank=True)
    
    # Description
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)
    
    # Created by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices',
        verbose_name=_('ایجاد کننده')
    )

    class Meta:
        db_table = 'invoices'
        verbose_name = _('فاکتور')
        verbose_name_plural = _('فاکتورها')
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['branch', 'issue_date']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.student.get_full_name()}"

    def save(self, *args, **kwargs):
        # Generate invoice number
        if not self.invoice_number:
            from django.utils import timezone
            year = timezone.now().year
            count = Invoice.objects.filter(
                issue_date__year=year
            ).count() + 1
            self.invoice_number = f"INV{year}{count:06d}"
        
        # Calculate total
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        
        # Update status based on payment
        if self.paid_amount == 0:
            self.status = self.InvoiceStatus.PENDING
        elif self.paid_amount >= self.total_amount:
            self.status = self.InvoiceStatus.PAID
            if not self.paid_date:
                from django.utils import timezone
                self.paid_date = timezone.now().date()
        elif self.paid_amount > 0:
            self.status = self.InvoiceStatus.PARTIALLY_PAID
        
        super().save(*args, **kwargs)

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def is_paid(self):
        return self.paid_amount >= self.total_amount

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status in [self.InvoiceStatus.PAID, self.InvoiceStatus.CANCELLED]:
            return False
        return timezone.now().date() > self.due_date


class InvoiceItem(TimeStampedModel):
    """
    Invoice Line Item
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('فاکتور')
    )
    
    description = models.CharField(_('شرح'), max_length=500)
    quantity = models.PositiveIntegerField(_('تعداد'), default=1)
    unit_price = models.DecimalField(
        _('قیمت واحد'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    discount = models.DecimalField(
        _('تخفیف'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        _('جمع'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        db_table = 'invoice_items'
        verbose_name = _('آیتم فاکتور')
        verbose_name_plural = _('آیتم‌های فاکتور')
        ordering = ['id']

    def __str__(self):
        return f"{self.description} - {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price) - self.discount
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    """
    Payment Model
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', _('نقدی')
        CARD = 'card', _('کارت خوان')
        BANK_TRANSFER = 'bank_transfer', _('واریز بانکی')
        ONLINE = 'online', _('پرداخت آنلاین')
        CHEQUE = 'cheque', _('چک')
        INSTALLMENT = 'installment', _('اقساط')
        CREDIT = 'credit', _('اعتبار داخلی')
        
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        PROCESSING = 'processing', _('در حال پردازش')
        COMPLETED = 'completed', _('تکمیل شده')
        FAILED = 'failed', _('ناموفق')
        CANCELLED = 'cancelled', _('لغو شده')
        REFUNDED = 'refunded', _('بازگشت داده شده')

    # Payment Info
    payment_number = models.CharField(
        _('شماره پرداخت'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('فاکتور')
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('دانش‌آموز')
    )
    
    # Amount
    amount = models.DecimalField(
        _('مبلغ'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    # Method
    payment_method = models.CharField(
        _('روش پرداخت'),
        max_length=20,
        choices=PaymentMethod.choices
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Online Payment Details
    gateway_transaction_id = models.CharField(
        _('شناسه تراکنش درگاه'),
        max_length=255,
        null=True,
        blank=True
    )
    gateway_reference_id = models.CharField(
        _('شماره پیگیری'),
        max_length=255,
        null=True,
        blank=True
    )
    card_number = models.CharField(
        _('شماره کارت'),
        max_length=16,
        null=True,
        blank=True
    )
    
    # Bank Transfer Details
    bank_name = models.CharField(_('نام بانک'), max_length=100, null=True, blank=True)
    account_number = models.CharField(
        _('شماره حساب'),
        max_length=50,
        null=True,
        blank=True
    )
    tracking_code = models.CharField(
        _('کد پیگیری'),
        max_length=100,
        null=True,
        blank=True
    )
    
    # Cheque Details
    cheque_number = models.CharField(
        _('شماره چک'),
        max_length=50,
        null=True,
        blank=True
    )
    cheque_date = models.DateField(_('تاریخ چک'), null=True, blank=True)
    
    # Dates
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), auto_now_add=True)
    verified_date = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)
    
    # Receipt
    receipt_file = models.FileField(
        _('فایل رسید'),
        upload_to='payments/receipts/',
        null=True,
        blank=True
    )
    
    # Verification
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        verbose_name=_('تایید کننده')
    )
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'payments'
        verbose_name = _('پرداخت')
        verbose_name_plural = _('پرداخت‌ها')
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['invoice', 'status']),
            models.Index(fields=['student', 'payment_date']),
            models.Index(fields=['gateway_transaction_id']),
        ]

    def __str__(self):
        return f"{self.payment_number} - {self.amount}"

    def save(self, *args, **kwargs):
        # Generate payment number
        if not self.payment_number:
            from django.utils import timezone
            year = timezone.now().year
            count = Payment.objects.filter(
                payment_date__year=year
            ).count() + 1
            self.payment_number = f"PAY{year}{count:06d}"
        
        super().save(*args, **kwargs)
        
        # Update invoice paid amount
        if self.status == self.PaymentStatus.COMPLETED:
            self.invoice.paid_amount = self.invoice.payments.filter(
                status=self.PaymentStatus.COMPLETED
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            self.invoice.save()


class DiscountCoupon(TimeStampedModel):
    """
    Discount Coupon Model
    """
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', _('درصدی')
        FIXED = 'fixed', _('مبلغ ثابت')

    code = models.CharField(_('کد تخفیف'), max_length=50, unique=True)
    name = models.CharField(_('نام'), max_length=200)
    description = models.TextField(_('توضیحات'), null=True, blank=True)
    
    # Discount
    discount_type = models.CharField(
        _('نوع تخفیف'),
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    
    discount_value = models.DecimalField(
        _('مقدار تخفیف'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    max_discount_amount = models.DecimalField(
        _('حداکثر مبلغ تخفیف'),
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Usage Limits
    max_uses = models.PositiveIntegerField(
        _('حداکثر استفاده'),
        null=True,
        blank=True
    )
    max_uses_per_user = models.PositiveIntegerField(
        _('حداکثر استفاده هر کاربر'),
        default=1
    )
    current_uses = models.PositiveIntegerField(_('استفاده‌های فعلی'), default=0)
    
    # Minimum Amount
    min_purchase_amount = models.DecimalField(
        _('حداقل مبلغ خرید'),
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Validity
    valid_from = models.DateTimeField(_('معتبر از'))
    valid_until = models.DateTimeField(_('معتبر تا'))
    
    # Restrictions
    applicable_courses = models.ManyToManyField(
        'courses.Course',
        blank=True,
        related_name='discount_coupons',
        verbose_name=_('دوره‌های قابل اعمال')
    )
    applicable_branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name='discount_coupons',
        verbose_name=_('شعب قابل اعمال')
    )
    
    # Status
    is_active = models.BooleanField(_('فعال'), default=True)
    
    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_coupons',
        verbose_name=_('ایجاد کننده')
    )

    class Meta:
        db_table = 'discount_coupons'
        verbose_name = _('کد تخفیف')
        verbose_name_plural = _('کدهای تخفیف')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def is_valid(self):
        """Check if coupon is valid"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if now < self.valid_from or now > self.valid_until:
            return False
        
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        
        return True

    def can_use(self, user):
        """Check if user can use this coupon"""
        if not self.is_valid():
            return False
        
        # Check user usage
        user_usage = CouponUsage.objects.filter(
            coupon=self,
            user=user
        ).count()
        
        if user_usage >= self.max_uses_per_user:
            return False
        
        return True

    def calculate_discount(self, amount):
        """Calculate discount amount"""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = (amount * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount_value
        
        return min(discount, amount)


class CouponUsage(TimeStampedModel):
    """
    Coupon Usage Tracking
    """
    coupon = models.ForeignKey(
        DiscountCoupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name=_('کد تخفیف')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name=_('کاربر')
    )
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name=_('فاکتور')
    )
    
    discount_amount = models.DecimalField(
        _('مبلغ تخفیف'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    used_at = models.DateTimeField(_('تاریخ استفاده'), auto_now_add=True)

    class Meta:
        db_table = 'coupon_usages'
        verbose_name = _('استفاده از کد تخفیف')
        verbose_name_plural = _('استفاده‌های کد تخفیف')
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.coupon.code} - {self.user.get_full_name()}"


class Installment(TimeStampedModel):
    """
    Payment Installment Model
    """
    class InstallmentStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        PAID = 'paid', _('پرداخت شده')
        OVERDUE = 'overdue', _('سررسید گذشته')
        CANCELLED = 'cancelled', _('لغو شده')

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='installments',
        verbose_name=_('فاکتور')
    )
    
    installment_number = models.PositiveIntegerField(_('شماره قسط'))
    
    amount = models.DecimalField(
        _('مبلغ قسط'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    due_date = models.DateField(_('سررسید'))
    
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=InstallmentStatus.choices,
        default=InstallmentStatus.PENDING
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installments',
        verbose_name=_('پرداخت')
    )
    
    paid_date = models.DateField(_('تاریخ پرداخت'), null=True, blank=True)
    
    penalty_amount = models.DecimalField(
        _('جریمه'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'installments'
        verbose_name = _('قسط')
        verbose_name_plural = _('اقساط')
        ordering = ['invoice', 'installment_number']
        unique_together = ['invoice', 'installment_number']

    def __str__(self):
        return f"{self.invoice.invoice_number} - قسط {self.installment_number}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status == self.InstallmentStatus.PAID:
            return False
        return timezone.now().date() > self.due_date


class Transaction(TimeStampedModel):
    """
    Financial Transaction Model
    """
    class TransactionType(models.TextChoices):
        INCOME = 'income', _('درآمد')
        EXPENSE = 'expense', _('هزینه')

    class TransactionCategory(models.TextChoices):
        TUITION = 'tuition', _('شهریه')
        SALARY = 'salary', _('حقوق')
        RENT = 'rent', _('اجاره')
        UTILITIES = 'utilities', _('آب و برق')
        MAINTENANCE = 'maintenance', _('تعمیرات')
        SUPPLIES = 'supplies', _('لوازم')
        MARKETING = 'marketing', _('بازاریابی')
        OTHER = 'other', _('سایر')

    transaction_number = models.CharField(
        _('شماره تراکنش'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name=_('شعبه')
    )
    
    transaction_type = models.CharField(
        _('نوع تراکنش'),
        max_length=20,
        choices=TransactionType.choices
    )
    
    category = models.CharField(
        _('دسته‌بندی'),
        max_length=20,
        choices=TransactionCategory.choices
    )
    
    amount = models.DecimalField(
        _('مبلغ'),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    date = models.DateField(_('تاریخ'))
    
    description = models.TextField(_('شرح'))
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name=_('پرداخت')
    )
    
    reference = models.CharField(_('مرجع'), max_length=255, null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions',
        verbose_name=_('ایجاد کننده')
    )
    
    receipt_file = models.FileField(
        _('فایل رسید'),
        upload_to='transactions/receipts/',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'transactions'
        verbose_name = _('تراکنش مالی')
        verbose_name_plural = _('تراکنش‌های مالی')
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['branch', 'date']),
            models.Index(fields=['transaction_type', 'category']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            from django.utils import timezone
            year = timezone.now().year
            count = Transaction.objects.filter(
                date__year=year
            ).count() + 1
            self.transaction_number = f"TRX{year}{count:06d}"
        
        super().save(*args, **kwargs)


class TeacherPayment(TimeStampedModel):
    """
    Teacher Salary/Payment Model
    """
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        APPROVED = 'approved', _('تایید شده')
        PAID = 'paid', _('پرداخت شده')
        REJECTED = 'rejected', _('رد شده')

    teacher = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='teacher_payments',
        verbose_name=_('معلم'),
        limit_choices_to={'role': User.UserRole.TEACHER}
    )
    
    payment_number = models.CharField(
        _('شماره پرداخت'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    # Period
    from_date = models.DateField(_('از تاریخ'))
    to_date = models.DateField(_('تا تاریخ'))
    
    # Teaching Hours
    total_hours = models.DecimalField(
        _('کل ساعات تدریس'),
        max_digits=6,
        decimal_places=2,
        default=0
    )
    
    hourly_rate = models.DecimalField(
        _('نرخ ساعتی'),
        max_digits=12,
        decimal_places=0
    )
    
    # Amounts
    base_amount = models.DecimalField(
        _('مبلغ پایه'),
        max_digits=12,
        decimal_places=0
    )
    
    bonus = models.DecimalField(
        _('پاداش'),
        max_digits=12,
        decimal_places=0,
        default=0
    )
    
    deductions = models.DecimalField(
        _('کسورات'),
        max_digits=12,
        decimal_places=0,
        default=0
    )
    
    total_amount = models.DecimalField(
        _('مبلغ کل'),
        max_digits=12,
        decimal_places=0
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_teacher_payments',
        verbose_name=_('تایید کننده')
    )
    approved_date = models.DateTimeField(_('تاریخ تایید'), null=True, blank=True)
    
    # Payment
    payment_date = models.DateField(_('تاریخ پرداخت'), null=True, blank=True)
    payment_method = models.CharField(
        _('روش پرداخت'),
        max_length=50,
        null=True,
        blank=True
    )
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_payments',
        verbose_name=_('تراکنش')
    )
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'teacher_payments'
        verbose_name = _('پرداخت معلم')
        verbose_name_plural = _('پرداخت‌های معلمان')
        ordering = ['-from_date']

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.from_date} تا {self.to_date}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            from django.utils import timezone
            year = timezone.now().year
            count = TeacherPayment.objects.filter(
                from_date__year=year
            ).count() + 1
            self.payment_number = f"TP{year}{count:06d}"
        
        # Calculate total
        self.total_amount = self.base_amount + self.bonus - self.deductions
        
        super().save(*args, **kwargs)

    def calculate_teaching_hours(self):
        """Calculate total teaching hours for period"""
        from apps.courses.models import ClassSession
        from apps.attendance.models import AttendanceReport
        
        sessions = ClassSession.objects.filter(
            class_obj__teacher=self.teacher,
            date__gte=self.from_date,
            date__lte=self.to_date,
            status=ClassSession.SessionStatus.COMPLETED
        )
        
        total_hours = 0
        for session in sessions:
            # Calculate duration in hours
            from datetime import datetime, timedelta
            start = datetime.combine(session.date, session.start_time)
            end = datetime.combine(session.date, session.end_time)
            duration = (end - start).total_seconds() / 3600
            total_hours += duration
        
        self.total_hours = total_hours
        self.base_amount = self.total_hours * float(self.hourly_rate)
        self.save()
        
class CreditNote(TimeStampedModel):
    """
    مدل برای مدیریت اعتبار دانش‌آموزان (کیف پول)
    """
    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='credit_note',
        verbose_name=_('دانش‌آموز')
    )
    
    balance = models.DecimalField(
        _('موجودی اعتبار'),
        max_digits=12,
        decimal_places=0,
        default=0
    )

    class Meta:
        db_table = 'credit_notes'
        verbose_name = _('اعتبار دانش‌آموز')
        verbose_name_plural = _('اعتبارات دانش‌آموزان')

    def __str__(self):
        return f"اعتبار {self.student.get_full_name()}: {self.balance:,}"

class CreditTransaction(TimeStampedModel):
    """
    تاریخچه تراکنش‌های اعتبار
    """
    class TransactionType(models.TextChoices):
        REFUND = 'refund', _('بازگشت وجه')
        PAYMENT = 'payment', _('استفاده برای پرداخت')
        ADJUSTMENT = 'adjustment', _('تعدیل دستی')

    credit_note = models.ForeignKey(
        CreditNote,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('اعتبار')
    )
    
    transaction_type = models.CharField(
        _('نوع تراکنش'),
        max_length=20,
        choices=TransactionType.choices
    )
    
    amount = models.DecimalField(
        _('مبلغ'),
        max_digits=12,
        decimal_places=0
    )
    
    balance_after = models.DecimalField(
        _('موجودی بعد از تراکنش'),
        max_digits=12,
        decimal_places=0
    )
    
    description = models.CharField(_('توضیحات'), max_length=255)
    
    # منبع تراکنش
    source_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('فاکتور مبدا/مقصد')
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('ایجاد کننده')
    )

    class Meta:
        db_table = 'credit_transactions'
        verbose_name = _('تراکنش اعتبار')
        verbose_name_plural = _('تراکنش‌های اعتبار')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}"


class RefundRequest(TimeStampedModel):
    """
    درخواست بازگشت وجه (برای واریز به حساب)
    """
    class RequestStatus(models.TextChoices):
        PENDING = 'pending', _('در انتظار')
        PROCESSING = 'processing', _('در حال پردازش')
        COMPLETED = 'completed', _('انجام شده')
        REJECTED = 'rejected', _('رد شده')

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='refund_requests',
        verbose_name=_('دانش‌آموز')
    )
    
    amount = models.DecimalField(
        _('مبلغ درخواستی'),
        max_digits=12,
        decimal_places=0
    )
    
    reason = models.TextField(_('دلیل درخواست'))
    
    # اطلاعات حساب بانکی
    bank_name = models.CharField(_('نام بانک'), max_length=100)
    card_number = models.CharField(_('شماره کارت'), max_length=16)
    iban = models.CharField(_('شماره شبا'), max_length=26, unique=True)
    
    status = models.CharField(
        _('وضعیت'),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds',
        verbose_name=_('پردازش کننده')
    )
    processed_at = models.DateTimeField(_('تاریخ پردازش'), null=True, blank=True)
    transaction_receipt = models.FileField(
        _('رسید تراکنش'),
        upload_to='refunds/',
        null=True,
        blank=True
    )
    
    admin_notes = models.TextField(_('یادداشت مدیر'), null=True, blank=True)

    class Meta:
        db_table = 'refund_requests'
        verbose_name = _('درخواست بازگشت وجه')
        verbose_name_plural = _('درخواست‌های بازگشت وجه')
        ordering = ['-created_at']
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    'created_at' and 'updated_at' fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeleteModel(models.Model):
    """
    An abstract base class model that provides soft delete functionality.
    """
    is_deleted = models.BooleanField(_('حذف شده'), default=False)
    deleted_at = models.DateTimeField(_('تاریخ حذف'), null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()
        
class SystemSettings(TimeStampedModel):
    """
    System-wide Settings
    """
    class SettingType(models.TextChoices):
        FINANCIAL = 'financial', _('مالی')
        ACADEMIC = 'academic', _('آموزشی')
        GENERAL = 'general', _('عمومی')

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
        db_table = 'system_settings'
        verbose_name = _('تنظیمات سیستم')
        verbose_name_plural = _('تنظیمات سیستم')

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_value(cls, key, default=None):
        """دریافت مقدار تنظیمات"""
        try:
            setting = cls.objects.get(key=key, is_active=True)
            return setting.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_annual_registration_fee(cls):
        """دریافت هزینه ثبت‌نام سالانه"""
        value = cls.get_value('annual_registration_fee', '2000000')
        return int(value)

    @classmethod
    def get_private_class_prices(cls):
        """دریافت قیمت‌های کلاس خصوصی"""
        return {
            'private': int(cls.get_value('private_class_price_per_session', '500000')),
            'semi_private_2': int(cls.get_value('semi_private_2_price_per_session', '350000')),
            'semi_private_3': int(cls.get_value('semi_private_3_price_per_session', '300000')),
            'semi_private_4': int(cls.get_value('semi_private_4_price_per_session', '250000')),
        }
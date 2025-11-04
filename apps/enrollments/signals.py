from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from apps.courses.models import Class
from apps.financial.models import Payment, Invoice
from .models import AnnualRegistration, Enrollment
from django.db import transaction



@receiver(post_save, sender=Payment)
def update_annual_registration_on_payment(sender, instance, created, **kwargs):
    """
    وقتی پرداخت تکمیل شد، وضعیت ثبت‌نام را بروز کن
    """
    # فقط برای پرداخت‌های تکمیل شده
    if instance.status != Payment.PaymentStatus.COMPLETED:
        return
    
    # پیدا کردن ثبت‌نام سالانه مرتبط
    try:
        registration = AnnualRegistration.objects.select_related('invoice').get(
            invoice=instance.invoice
        )
        
        # بروزرسانی کش پرداخت
        registration.update_payment_cache()
        
        # اگر فاکتور کامل پرداخت شده
        if instance.invoice.is_paid:
            # تغییر وضعیت به در انتظار تایید مدارک
            if registration.status == AnnualRegistration.RegistrationStatus.PENDING_PAYMENT:
                registration.status = AnnualRegistration.RegistrationStatus.PENDING_VERIFICATION
                registration.save(update_fields=['status'])
            
            # بررسی و فعال‌سازی خودکار
            if registration.check_and_activate():
                # ارسال نوتیفیکیشن
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=registration.student,
                    title='ثبت‌نام سالانه فعال شد',
                    message=f'ثبت‌نام سالانه شما برای {registration.academic_year} فعال شد.',
                    notification_type=Notification.NotificationType.SUCCESS,
                    category=Notification.NotificationCategory.ENROLLMENT
                )
                
    except AnnualRegistration.DoesNotExist:
        pass


@receiver(post_save, sender=Invoice)
def update_registration_payment_cache_on_invoice_change(sender, instance, **kwargs):
    """
    وقتی Invoice تغییر کرد، کش را بروز کن
    """
    try:
        registration = AnnualRegistration.objects.get(invoice=instance)
        old_cached = registration.is_paid_cached
        new_cached = instance.is_paid
        
        # فقط اگر تغییر کرده باشد
        if old_cached != new_cached:
            registration.update_payment_cache()
    except AnnualRegistration.DoesNotExist:
        pass
    
@receiver(post_save, sender=Payment)
def activate_enrollment_on_payment(sender, instance, created, **kwargs):
    """
    وقتی پرداخت تکمیل شد، ثبت‌نام را فعال و شمارنده کلاس را بروز کن
    """
    if instance.status != Payment.PaymentStatus.COMPLETED:
        return
    
    # پیدا کردن ثبت‌نام مرتبط
    try:
        enrollment = Enrollment.objects.select_related('class_obj').get(
            invoice=instance.invoice
        )
        
        # اگر پرداخت کامل بود و وضعیت در انتظار پرداخت بود
        if (
            instance.invoice.is_paid and
            enrollment.status == Enrollment.EnrollmentStatus.PENDING
        ):
            with transaction.atomic():
                # ✅ بروزرسانی شمارنده کلاس (به صورت اتمیک)
                Class.objects.filter(id=enrollment.class_obj.id).update(
                    current_enrollments=F('current_enrollments') + 1
                )
                
                # ✅ فعال‌سازی ثبت‌نام
                enrollment.status = Enrollment.EnrollmentStatus.ACTIVE
                enrollment.save(update_fields=['status'])
                
                # ارسال نوتیفیکیشن
                from apps.notifications.tasks import send_enrollment_approved_notification
                send_enrollment_approved_notification.delay(str(enrollment.id))
                
    except Enrollment.DoesNotExist:
        pass
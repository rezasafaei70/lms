from celery import shared_task
from django.utils import timezone
from .models import AnnualRegistration


@shared_task
def expire_old_registrations():
    """
    روزانه ثبت‌نام‌های گذشته را منقضی کن
    """
    today = timezone.now().date()
    
    expired_count = 0
    registrations = AnnualRegistration.objects.filter(
        status=AnnualRegistration.RegistrationStatus.ACTIVE,
        end_date__lt=today
    )
    
    for registration in registrations:
        if registration.expire_if_needed():
            expired_count += 1
    
    return f"{expired_count} ثبت‌نام منقضی شد"


@shared_task
def send_registration_expiry_reminders():
    """
    یادآوری انقضا (30 روز قبل)
    """
    from datetime import timedelta
    from apps.notifications.models import Notification
    
    reminder_date = timezone.now().date() + timedelta(days=30)
    
    registrations = AnnualRegistration.objects.filter(
        status=AnnualRegistration.RegistrationStatus.ACTIVE,
        end_date=reminder_date
    )
    
    for registration in registrations:
        Notification.objects.create(
            recipient=registration.student,
            title='یادآوری انقضا ثبت‌نام',
            message=f'ثبت‌نام سالانه شما تا 30 روز دیگر منقضی می‌شود. لطفاً برای تمدید اقدام کنید.',
            notification_type=Notification.NotificationType.WARNING,
            category=Notification.NotificationCategory.ENROLLMENT
        )
    
    return f"{registrations.count()} یادآوری ارسال شد"
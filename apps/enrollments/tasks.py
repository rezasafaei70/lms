from celery import shared_task
from django.utils import timezone

from apps.notifications.models import Notification
from .models import AnnualRegistration, WaitingList


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

@shared_task
def check_waiting_list(class_id):
    """
    بررسی لیست انتظار و اطلاع‌رسانی در صورت وجود ظرفیت
    """
    from apps.courses.models import Class
    
    try:
        class_obj = Class.objects.get(id=class_id)
        if not class_obj.is_full:
            # پیدا کردن نفر اول در لیست انتظار
            waiting = WaitingList.objects.filter(
                class_obj=class_obj,
                status=WaitingList.WaitingStatus.WAITING
            ).order_by('created_at').first()
            
            if waiting:
                # اطلاع‌رسانی
                waiting.status = WaitingList.WaitingStatus.NOTIFIED
                waiting.notified_at = timezone.now()
                waiting.notification_expires_at = timezone.now() + timezone.timedelta(hours=24)
                waiting.save()
                
                Notification.objects.create(
                    recipient=waiting.student,
                    title=f'ظرفیت آزاد در کلاس {class_obj.name}',
                    message='یک ظرفیت در کلاس مورد نظر شما آزاد شده است. برای ثبت‌نام تا 24 ساعت آینده اقدام کنید.',
                    action_url=f'/classes/{class_obj.id}/'
                )
    except Class.DoesNotExist:
        pass
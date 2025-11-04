from celery import shared_task
from django.utils import timezone
from .models import Notification, SMSLog, Announcement
from apps.accounts.models import User
from utils.sms import send_sms


@shared_task
def send_notification_task(notification_id):
    """
    Send notification via configured channels
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        settings = notification.recipient.notification_settings
        
        # Check quiet hours
        now = timezone.now().time()
        if settings.quiet_hours_start and settings.quiet_hours_end:
            if settings.quiet_hours_start <= now <= settings.quiet_hours_end:
                # Reschedule for later
                return
        
        # Send via SMS
        if settings.enable_sms and notification.recipient.mobile:
            send_sms_notification.delay(notification_id)
        
        # Send via Email
        if settings.enable_email and notification.recipient.email:
            send_email_notification.delay(notification_id)
        
        # Send via Push
        if settings.enable_push:
            send_push_notification.delay(notification_id)
        
    except Notification.DoesNotExist:
        pass


@shared_task
def send_sms_notification(notification_id):
    """
    Send SMS notification
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        mobile = notification.recipient.mobile
        
        message = f"{notification.title}\n{notification.message}"
        
        # Create SMS log
        sms_log = SMSLog.objects.create(
            recipient=notification.recipient,
            mobile=mobile,
            message=message
        )
        
        # Send SMS
        success = send_sms(mobile, message)
        
        if success:
            sms_log.status = SMSLog.SMSStatus.SENT
            sms_log.sent_at = timezone.now()
            notification.sent_via_sms = True
        else:
            sms_log.status = SMSLog.SMSStatus.FAILED
            sms_log.error_message = 'خطا در ارسال SMS'
        
        sms_log.save()
        notification.save()
        
    except Notification.DoesNotExist:
        pass


@shared_task
def send_email_notification(notification_id):
    """
    Send email notification
    """
    try:
        from utils.helpers import send_email
        
        notification = Notification.objects.get(id=notification_id)
        email = notification.recipient.email
        
        success = send_email(
            subject=notification.title,
            message=notification.message,
            recipient_list=[email]
        )
        
        if success:
            notification.sent_via_email = True
            notification.save()
        
    except Notification.DoesNotExist:
        pass


@shared_task
def send_push_notification(notification_id):
    """
    Send push notification
    """
    # Implement push notification logic
    pass


@shared_task
def send_enrollment_approved_notification(enrollment_id):
    """
    Send notification when enrollment is approved
    """
    from apps.enrollments.models import Enrollment
    
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id)
        
        Notification.objects.create(
            recipient=enrollment.student,
            title='ثبت‌نام تایید شد',
            message=f'ثبت‌نام شما در کلاس {enrollment.class_obj.name} تایید شد.',
            notification_type=Notification.NotificationType.SUCCESS,
            category=Notification.NotificationCategory.ENROLLMENT,
            action_url=f'/enrollments/{enrollment.id}/'
        )
    except Enrollment.DoesNotExist:
        pass


@shared_task
def send_enrollment_rejected_notification(enrollment_id, reason):
    """
    Send notification when enrollment is rejected
    """
    from apps.enrollments.models import Enrollment
    
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id)
        
        Notification.objects.create(
            recipient=enrollment.student,
            title='ثبت‌نام رد شد',
            message=f'ثبت‌نام شما در کلاس {enrollment.class_obj.name} رد شد.\nدلیل: {reason}',
            notification_type=Notification.NotificationType.ERROR,
            category=Notification.NotificationCategory.ENROLLMENT
        )
    except Enrollment.DoesNotExist:
        pass


@shared_task
def send_class_reminder(class_id, hours_before=2):
    """
    Send class reminder to enrolled students
    """
    from apps.courses.models import Class
    from apps.enrollments.models import Enrollment
    
    try:
        class_obj = Class.objects.get(id=class_id)
        enrollments = Enrollment.objects.filter(
            class_obj=class_obj,
            status=Enrollment.EnrollmentStatus.ACTIVE
        )
        
        for enrollment in enrollments:
            Notification.objects.create(
                recipient=enrollment.student,
                title='یادآوری کلاس',
                message=f'کلاس {class_obj.name} {hours_before} ساعت دیگر شروع می‌شود.',
                notification_type=Notification.NotificationType.REMINDER,
                category=Notification.NotificationCategory.CLASS,
                action_url=f'/classes/{class_obj.id}/'
            )
    except Class.DoesNotExist:
        pass


@shared_task
def send_payment_reminder(invoice_id):
    """
    Send payment reminder
    """
    from apps.financial.models import Invoice
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        if invoice.remaining_amount > 0:
            Notification.objects.create(
                recipient=invoice.student,
                title='یادآوری پرداخت',
                message=f'مبلغ {invoice.remaining_amount:,} تومان از فاکتور {invoice.invoice_number} پرداخت نشده است.',
                notification_type=Notification.NotificationType.REMINDER,
                category=Notification.NotificationCategory.PAYMENT,
                action_url=f'/invoices/{invoice.id}/'
            )
    except Invoice.DoesNotExist:
        pass


@shared_task
def send_low_attendance_alerts(class_id):
    """
    Send low attendance alert to students
    """
    from apps.enrollments.models import Enrollment
    
    enrollments = Enrollment.objects.filter(
        class_obj_id=class_id,
        status=Enrollment.EnrollmentStatus.ACTIVE,
        attendance_rate__lt=75
    )
    
    for enrollment in enrollments:
        Notification.objects.create(
            recipient=enrollment.student,
            title='هشدار حضور پایین',
            message=f'نرخ حضور شما ({enrollment.attendance_rate}%) کمتر از حد مجاز است.',
            notification_type=Notification.NotificationType.WARNING,
            category=Notification.NotificationCategory.ATTENDANCE
        )


@shared_task
def send_placement_test_result_notification(test_id):
    """
    Send placement test result notification
    """
    from apps.enrollments.models import PlacementTest
    
    try:
        test = PlacementTest.objects.get(id=test_id)
        
        Notification.objects.create(
            recipient=test.student,
            title='نتیجه آزمون تعیین سطح',
            message=f'نتیجه آزمون تعیین سطح شما: {test.get_determined_level_display()}\nنمره: {test.score}',
            notification_type=Notification.NotificationType.SUCCESS,
            category=Notification.NotificationCategory.EXAM,
            action_url=f'/placement-tests/{test.id}/'
        )
    except PlacementTest.DoesNotExist:
        pass


@shared_task
def send_waiting_list_notification(waiting_id):
    """
    Send waiting list notification
    """
    from apps.enrollments.models import WaitingList
    
    try:
        waiting = WaitingList.objects.get(id=waiting_id)
        
        Notification.objects.create(
            recipient=waiting.student,
            title='ظرفیت آزاد شد',
            message=f'در کلاس {waiting.class_obj.name} ظرفیت آزاد شد. برای ثبت‌نام تا 24 ساعت آینده اقدام کنید.',
            notification_type=Notification.NotificationType.INFO,
            category=Notification.NotificationCategory.ENROLLMENT,
            action_url=f'/classes/{waiting.class_obj.id}/'
        )
    except WaitingList.DoesNotExist:
        pass
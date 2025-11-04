import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('academy')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'send-payment-reminders-daily': {
        'task': 'apps.financial.tasks.send_overdue_payment_reminders',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
    'send-class-reminders': {
        'task': 'apps.notifications.tasks.send_class_reminders',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

app.conf.beat_schedule = {
    'expire-old-registrations': {
        'task': 'apps.enrollments.tasks.expire_old_registrations',
        'schedule': crontab(hour=1, minute=0),  # هر روز ساعت 1 صبح
    },
    'send-registration-expiry-reminders': {
        'task': 'apps.enrollments.tasks.send_registration_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),  # هر روز ساعت 9 صبح
    },
}
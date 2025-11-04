from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet, NotificationTemplateViewSet,
    UserNotificationSettingsViewSet, SMSLogViewSet, AnnouncementViewSet
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'templates', NotificationTemplateViewSet, basename='templates')
router.register(r'settings', UserNotificationSettingsViewSet, basename='settings')
router.register(r'sms-logs', SMSLogViewSet, basename='sms-logs')
router.register(r'announcements', AnnouncementViewSet, basename='announcements')

urlpatterns = [
    path('', include(router.urls)),
]
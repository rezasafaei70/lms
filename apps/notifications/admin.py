from django.contrib import admin
from .models import (
    Notification, NotificationTemplate, UserNotificationSettings,
    SMSLog, Announcement
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'recipient', 'notification_type', 'category',
        'is_read', 'created_at'
    ]
    list_filter = ['notification_type', 'category', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__first_name']
    readonly_fields = ['created_at', 'read_at']
    ordering = ['-created_at']


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'content']


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'enable_sms', 'enable_email',
        'enable_push', 'digest_mode'
    ]
    list_filter = ['enable_sms', 'enable_email', 'enable_push', 'digest_mode']
    search_fields = ['user__first_name', 'user__last_name']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = [
        'mobile', 'recipient', 'status', 'sent_at', 'cost'
    ]
    list_filter = ['status', 'sent_at']
    search_fields = ['mobile', 'message', 'gateway_message_id']
    readonly_fields = ['created_at', 'sent_at', 'delivered_at']
    ordering = ['-created_at']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'announcement_type', 'target_audience',
        'is_published', 'publish_date', 'view_count'
    ]
    list_filter = [
        'announcement_type', 'target_audience',
        'is_published', 'is_pinned', 'publish_date'
    ]
    search_fields = ['title', 'content']
    filter_horizontal = ['specific_users', 'specific_branches']
    readonly_fields = ['view_count', 'created_at']
    ordering = ['-publish_date']
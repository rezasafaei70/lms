from rest_framework import serializers
from .models import (
    Notification, NotificationTemplate, UserNotificationSettings,
    SMSLog, Announcement
)
from apps.accounts.serializers import UserSerializer


class NotificationSerializer(serializers.ModelSerializer):
    """
    Notification Serializer
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'is_read',
            'read_at', 'sent_via_sms', 'sent_via_email', 'sent_via_push'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Simplified Notification List Serializer
    """
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type',
            'category', 'is_read', 'created_at', 'action_url'
        ]


class BulkNotificationSerializer(serializers.Serializer):
    """
    Bulk Notification Serializer
    """
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices
    )
    category = serializers.ChoiceField(
        choices=Notification.NotificationCategory.choices
    )
    recipients = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    send_sms = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=False)
    action_url = serializers.CharField(required=False, allow_blank=True)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Notification Template Serializer
    """
    template_type_display = serializers.CharField(
        source='get_template_type_display',
        read_only=True
    )
    
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """
    User Notification Settings Serializer
    """
    class Meta:
        model = UserNotificationSettings
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']


class SMSLogSerializer(serializers.ModelSerializer):
    """
    SMS Log Serializer
    """
    recipient_name = serializers.CharField(
        source='recipient.get_full_name',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = SMSLog
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'sent_at',
            'delivered_at', 'gateway_message_id'
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    """
    Announcement Serializer
    """
    announcement_type_display = serializers.CharField(
        source='get_announcement_type_display',
        read_only=True
    )
    target_audience_display = serializers.CharField(
        source='get_target_audience_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 'view_count'
        ]


class SendAnnouncementNotificationSerializer(serializers.Serializer):
    """
    Send Announcement Notification Serializer
    """
    announcement_id = serializers.UUIDField()
    send_sms = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=False)
    send_push = serializers.BooleanField(default=False)
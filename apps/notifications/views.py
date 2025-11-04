from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Count
from django.db import transaction

from .models import (
    Notification, NotificationTemplate, UserNotificationSettings,
    SMSLog, Announcement
)
from .serializers import (
    NotificationSerializer, NotificationListSerializer, BulkNotificationSerializer,
    NotificationTemplateSerializer, UserNotificationSettingsSerializer,
    SMSLogSerializer, AnnouncementSerializer, SendAnnouncementNotificationSerializer
)
from .tasks import send_notification_task
from utils.permissions import IsSuperAdmin, IsBranchManager
from utils.pagination import StandardResultsSetPagination


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Notification ViewSet
    """
    queryset = Notification.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'category', 'is_read']
    ordering_fields = ['created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        elif self.action == 'send_bulk':
            return BulkNotificationSerializer
        return NotificationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Users see only their notifications
        if not user.is_superuser:
            queryset = queryset.filter(recipient=user)
        
        # Filter expired notifications
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now())
        )
        
        return queryset.select_related('recipient')

    @action(detail=False, methods=['get'], url_path='my-notifications')
    def my_notifications(self, request):
        """
        Get current user's notifications
        GET /api/v1/notifications/notifications/my-notifications/
        """
        notifications = self.get_queryset().filter(recipient=request.user)
        
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='unread')
    def unread_notifications(self, request):
        """
        Get unread notifications
        GET /api/v1/notifications/notifications/unread/
        """
        notifications = self.get_queryset().filter(
            recipient=request.user,
            is_read=False
        )
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        Get unread notifications count
        GET /api/v1/notifications/notifications/unread-count/
        """
        count = self.get_queryset().filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """
        Mark notification as read
        POST /api/v1/notifications/notifications/{id}/mark-read/
        """
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'message': 'اعلان به عنوان خوانده شده علامت زد'
        })

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """
        Mark all notifications as read
        POST /api/v1/notifications/notifications/mark-all-read/
        """
        self.get_queryset().filter(
            recipient=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': 'تمام اعلان‌ها به عنوان خوانده شده علامت زدند'
        })

    @action(detail=False, methods=['post'], url_path='send-bulk', permission_classes=[IsSuperAdmin])
    def send_bulk(self, request):
        """
        Send bulk notification
        POST /api/v1/notifications/notifications/send-bulk/
        {
            "title": "اطلاعیه مهم",
            "message": "متن اطلاعیه",
            "notification_type": "info",
            "category": "announcement",
            "recipients": ["user_id_1", "user_id_2"],
            "send_sms": true
        }
        """
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.accounts.models import User
        
        recipients = User.objects.filter(
            id__in=serializer.validated_data['recipients']
        )
        
        notifications = []
        for recipient in recipients:
            notification = Notification.objects.create(
                recipient=recipient,
                title=serializer.validated_data['title'],
                message=serializer.validated_data['message'],
                notification_type=serializer.validated_data['notification_type'],
                category=serializer.validated_data['category'],
                action_url=serializer.validated_data.get('action_url', '')
            )
            notifications.append(notification)
            
            # Send via configured channels
            if serializer.validated_data.get('send_sms') or serializer.validated_data.get('send_email'):
                send_notification_task.delay(str(notification.id))
        
        return Response({
            'message': f'{len(notifications)} اعلان ارسال شد',
            'count': len(notifications)
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        """
        Clear all notifications
        DELETE /api/v1/notifications/notifications/clear-all/
        """
        self.get_queryset().filter(recipient=request.user).delete()
        
        return Response({
            'message': 'تمام اعلان‌ها پاک شدند'
        })


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    Notification Template ViewSet
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='render')
    def render_template(self, request, pk=None):
        """
        Render template with context
        POST /api/v1/notifications/templates/{id}/render/
        {
            "context": {
                "student_name": "علی احمدی",
                "class_name": "انگلیسی مقدماتی"
            }
        }
        """
        template = self.get_object()
        context = request.data.get('context', {})
        
        rendered_content = template.render(context)
        
        return Response({
            'rendered': rendered_content
        })


class UserNotificationSettingsViewSet(viewsets.ModelViewSet):
    """
    User Notification Settings ViewSet
    """
    queryset = UserNotificationSettings.objects.all()
    serializer_class = UserNotificationSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Users see only their settings
        if not user.is_superuser:
            queryset = queryset.filter(user=user)
        
        return queryset

    @action(detail=False, methods=['get'], url_path='my-settings')
    def my_settings(self, request):
        """
        Get current user's notification settings
        GET /api/v1/notifications/settings/my-settings/
        """
        settings, created = UserNotificationSettings.objects.get_or_create(
            user=request.user
        )
        
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], url_path='update-my-settings')
    def update_my_settings(self, request):
        """
        Update current user's notification settings
        PUT/PATCH /api/v1/notifications/settings/update-my-settings/
        """
        settings, created = UserNotificationSettings.objects.get_or_create(
            user=request.user
        )
        
        serializer = self.get_serializer(
            settings,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'تنظیمات بروزرسانی شد',
            'settings': serializer.data
        })


class SMSLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    SMS Log ViewSet (Read-only)
    """
    queryset = SMSLog.objects.all()
    serializer_class = SMSLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'mobile']
    ordering_fields = ['created_at', 'sent_at']

    def get_permissions(self):
        # Only admins can view SMS logs
        return [IsSuperAdmin()]

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get SMS statistics
        GET /api/v1/notifications/sms-logs/statistics/
        """
        total = self.get_queryset().count()
        
        stats = {
            'total_sms': total,
            'sent': self.get_queryset().filter(
                status=SMSLog.SMSStatus.SENT
            ).count(),
            'delivered': self.get_queryset().filter(
                status=SMSLog.SMSStatus.DELIVERED
            ).count(),
            'failed': self.get_queryset().filter(
                status=SMSLog.SMSStatus.FAILED
            ).count(),
            'total_cost': self.get_queryset().aggregate(
                total=models.Sum('cost')
            )['total'] or 0
        }
        
        return Response(stats)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    Announcement ViewSet
    """
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['announcement_type', 'target_audience', 'is_published']
    search_fields = ['title', 'content']
    ordering_fields = ['publish_date', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsBranchManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Non-admin users see only published announcements
        if user.role not in [user.UserRole.SUPER_ADMIN, user.UserRole.BRANCH_MANAGER]:
            queryset = queryset.filter(
                is_published=True,
                publish_date__lte=timezone.now()
            ).filter(
                Q(expire_date__isnull=True) | Q(expire_date__gte=timezone.now())
            )
            
            # Filter by target audience
            queryset = queryset.filter(
                Q(target_audience=Announcement.TargetAudience.ALL) |
                Q(target_audience=Announcement.TargetAudience.STUDENTS, 
                  recipient__role=user.UserRole.STUDENT) |
                Q(target_audience=Announcement.TargetAudience.TEACHERS,
                  recipient__role=user.UserRole.TEACHER) |
                Q(specific_users=user)
            )
        
        return queryset.select_related('created_by').prefetch_related(
            'specific_users', 'specific_branches'
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """
        Publish announcement
        POST /api/v1/notifications/announcements/{id}/publish/
        """
        announcement = self.get_object()
        
        announcement.is_published = True
        announcement.publish_date = timezone.now()
        announcement.save()
        
        return Response({
            'message': 'اطلاعیه منتشر شد'
        })

    @action(detail=True, methods=['post'], url_path='unpublish')
    def unpublish(self, request, pk=None):
        """
        Unpublish announcement
        POST /api/v1/notifications/announcements/{id}/unpublish/
        """
        announcement = self.get_object()
        
        announcement.is_published = False
        announcement.save()
        
        return Response({
            'message': 'اطلاعیه از انتشار خارج شد'
        })

    @action(detail=True, methods=['post'], url_path='send-notification')
    def send_notification(self, request, pk=None):
        """
        Send notification to announcement recipients
        POST /api/v1/notifications/announcements/{id}/send-notification/
        {
            "send_sms": true,
            "send_email": false,
            "send_push": true
        }
        """
        announcement = self.get_object()
        recipients = announcement.get_recipients()
        
        send_sms = request.data.get('send_sms', False)
        send_email = request.data.get('send_email', False)
        
        notifications_created = 0
        for recipient in recipients:
            notification = Notification.objects.create(
                recipient=recipient,
                title=announcement.title,
                message=announcement.content,
                notification_type=Notification.NotificationType.INFO,
                category=Notification.NotificationCategory.ANNOUNCEMENT,
                action_url=f'/announcements/{announcement.id}/'
            )
            
            if send_sms or send_email:
                send_notification_task.delay(str(notification.id))
            
            notifications_created += 1
        
        return Response({
            'message': f'اعلان به {notifications_created} کاربر ارسال شد',
            'count': notifications_created
        })

    @action(detail=True, methods=['post'], url_path='increment-view')
    def increment_view(self, request, pk=None):
        """
        Increment view count
        POST /api/v1/notifications/announcements/{id}/increment-view/
        """
        announcement = self.get_object()
        announcement.view_count += 1
        announcement.save()
        
        return Response({'view_count': announcement.view_count})

    @action(detail=False, methods=['get'], url_path='active')
    def active_announcements(self, request):
        """
        Get active announcements
        GET /api/v1/notifications/announcements/active/
        """
        announcements = self.get_queryset().filter(
            is_published=True
        )
        
        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pinned')
    def pinned_announcements(self, request):
        """
        Get pinned announcements
        GET /api/v1/notifications/announcements/pinned/
        """
        announcements = self.get_queryset().filter(
            is_published=True,
            is_pinned=True
        )
        
        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)
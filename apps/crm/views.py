from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.db import transaction as db_transaction

from .models import (
    Lead, LeadActivity, Campaign, CampaignLead,
    CustomerFeedback, LoyaltyProgram, CustomerLoyaltyPoints, Referral
)
from .serializers import (
    LeadSerializer, LeadActivitySerializer, CampaignSerializer,
    CampaignLeadSerializer, CustomerFeedbackSerializer,
    LoyaltyProgramSerializer, CustomerLoyaltyPointsSerializer,
    ReferralSerializer
)
from utils.permissions import IsSuperAdmin, IsBranchManager
from utils.pagination import StandardResultsSetPagination


class LeadViewSet(viewsets.ModelViewSet):
    """
    Lead ViewSet
    """
    queryset = Lead.objects.filter(is_deleted=False)
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'source', 'assigned_to', 'preferred_branch']
    search_fields = ['first_name', 'last_name', 'mobile', 'email']
    ordering_fields = ['created_at', 'score', 'last_contact_date']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsBranchManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'assigned_to', 'interested_course', 'preferred_branch',
            'converted_to_student'
        ).prefetch_related('activities')
        
        # Branch managers see their branch leads
        if user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(
                Q(assigned_to=user) | Q(preferred_branch__manager=user)
            )
        
        return queryset

    @action(detail=True, methods=['post'], url_path='add-activity')
    def add_activity(self, request, pk=None):
        """
        Add activity to lead
        POST /api/v1/crm/leads/{id}/add-activity/
        {
            "activity_type": "call",
            "subject": "تماس اول",
            "description": "توضیحات",
            "duration_minutes": 10,
            "outcome": "علاقمند به ثبت‌نام"
        }
        """
        lead = self.get_object()
        
        data = request.data.copy()
        data['lead'] = lead.id
        data['performed_by'] = request.user.id
        
        serializer = LeadActivitySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        
        # Update lead last contact
        lead.last_contact_date = timezone.now()
        lead.save()
        
        return Response({
            'message': 'فعالیت ثبت شد',
            'activity': LeadActivitySerializer(activity).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        """
        Change lead status
        POST /api/v1/crm/leads/{id}/change-status/
        {
            "status": "qualified",
            "notes": "دلیل تغییر وضعیت"
        }
        """
        lead = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        old_status = lead.status
        lead.status = new_status
        if notes:
            lead.notes = f"{lead.notes or ''}\n{timezone.now()}: {notes}"
        lead.save()
        
        # Log activity
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
            subject=f'تغییر وضعیت از {old_status} به {new_status}',
            description=notes,
            performed_by=request.user
        )
        
        return Response({
            'message': 'وضعیت تغییر کرد',
            'lead': LeadSerializer(lead).data
        })

    @action(detail=True, methods=['post'], url_path='convert')
    def convert_to_student(self, request, pk=None):
        """
        Convert lead to student
        POST /api/v1/crm/leads/{id}/convert/
        {
            "email": "student@example.com",
            "password": "password123"
        }
        """
        lead = self.get_object()
        
        if lead.status == Lead.LeadStatus.CONVERTED:
            return Response({
                'error': 'این لید قبلاً تبدیل شده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.accounts.models import User, StudentProfile
        
        with db_transaction.atomic():
            # Create user
            user = User.objects.create_user(
                mobile=lead.mobile,
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=request.data.get('email', lead.email),
                role=User.UserRole.STUDENT
            )
            
            if request.data.get('password'):
                user.set_password(request.data['password'])
                user.save()
            
            # Create student profile
            StudentProfile.objects.create(user=user)
            
            # Update lead
            lead.status = Lead.LeadStatus.CONVERTED
            lead.converted_to_student = user
            lead.converted_at = timezone.now()
            lead.save()
            
            # Log activity
            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.NOTE,
                subject='تبدیل به دانش‌آموز',
                description=f'لید به دانش‌آموز با شناسه {user.id} تبدیل شد',
                performed_by=request.user
            )
        
        return Response({
            'message': 'لید به دانش‌آموز تبدیل شد',
            'user_id': str(user.id)
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_lead(self, request, pk=None):
        """
        Assign lead to user
        POST /api/v1/crm/leads/{id}/assign/
        {
            "assigned_to": "user_id"
        }
        """
        lead = self.get_object()
        user_id = request.data.get('assigned_to')
        
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'کاربر یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        lead.assigned_to = user
        lead.save()
        
        # Log activity
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.NOTE,
            subject='اختصاص لید',
            description=f'لید به {user.get_full_name()} اختصاص داده شد',
            performed_by=request.user
        )
        
        return Response({
            'message': f'لید به {user.get_full_name()} اختصاص داده شد'
        })

    @action(detail=False, methods=['get'], url_path='my-leads')
    def my_leads(self, request):
        """
        Get leads assigned to current user
        GET /api/v1/crm/leads/my-leads/
        """
        leads = self.get_queryset().filter(assigned_to=request.user)
        
        serializer = self.get_serializer(leads, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get lead statistics
        GET /api/v1/crm/leads/statistics/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'by_status': dict(queryset.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')),
            'by_source': dict(queryset.values('source').annotate(
                count=Count('id')
            ).values_list('source', 'count')),
            'converted': queryset.filter(
                status=Lead.LeadStatus.CONVERTED
            ).count(),
            'conversion_rate': 0,
            'average_score': queryset.aggregate(Avg('score'))['score__avg'] or 0,
        }
        
        if stats['total'] > 0:
            stats['conversion_rate'] = (stats['converted'] / stats['total']) * 100
        
        return Response(stats)


class LeadActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lead Activity ViewSet (Read-only)
    """
    queryset = LeadActivity.objects.all()
    serializer_class = LeadActivitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['lead', 'activity_type', 'performed_by']
    ordering_fields = ['activity_date']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'lead', 'performed_by'
        ).order_by('-activity_date')


class CampaignViewSet(viewsets.ModelViewSet):
    """
    Campaign ViewSet
    """
    queryset = Campaign.objects.filter(is_deleted=False)
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['campaign_type', 'status', 'target_branch']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsBranchManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='add-leads')
    def add_leads(self, request, pk=None):
        """
        Add leads to campaign
        POST /api/v1/crm/campaigns/{id}/add-leads/
        {
            "leads": ["lead_id_1", "lead_id_2"]
        }
        """
        campaign = self.get_object()
        lead_ids = request.data.get('leads', [])
        
        added = 0
        for lead_id in lead_ids:
            try:
                lead = Lead.objects.get(id=lead_id)
                CampaignLead.objects.get_or_create(
                    campaign=campaign,
                    lead=lead
                )
                added += 1
            except Lead.DoesNotExist:
                continue
        
        return Response({
            'message': f'{added} لید به کمپین اضافه شد',
            'added': added
        })

    @action(detail=True, methods=['post'], url_path='launch')
    def launch_campaign(self, request, pk=None):
        """
        Launch campaign
        POST /api/v1/crm/campaigns/{id}/launch/
        """
        campaign = self.get_object()
        
        if campaign.status != Campaign.CampaignStatus.SCHEDULED:
            return Response({
                'error': 'فقط کمپین‌های زمان‌بندی شده قابل اجرا هستند'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        campaign.status = Campaign.CampaignStatus.ACTIVE
        campaign.save()
        
        # Execute campaign (send messages, etc.)
        from .tasks import execute_campaign
        execute_campaign.delay(str(campaign.id))
        
        return Response({
            'message': 'کمپین راه‌اندازی شد'
        })

    @action(detail=True, methods=['get'], url_path='report')
    def campaign_report(self, request, pk=None):
        """
        Get campaign report
        GET /api/v1/crm/campaigns/{id}/report/
        """
        campaign = self.get_object()
        
        report = {
            'campaign': CampaignSerializer(campaign).data,
            'total_leads': campaign.campaign_leads.count(),
            'sent': campaign.total_sent,
            'delivered': campaign.total_delivered,
            'opened': campaign.total_opened,
            'clicked': campaign.total_clicked,
            'converted': campaign.total_conversions,
            'conversion_rate': campaign.conversion_rate,
            'roi': campaign.roi,
            'budget': float(campaign.budget),
            'spent': float(campaign.spent),
        }
        
        return Response(report)

    @action(detail=False, methods=['get'], url_path='active')
    def active_campaigns(self, request):
        """
        Get active campaigns
        GET /api/v1/crm/campaigns/active/
        """
        campaigns = self.get_queryset().filter(
            status=Campaign.CampaignStatus.ACTIVE
        )
        
        serializer = self.get_serializer(campaigns, many=True)
        return Response(serializer.data)


class CustomerFeedbackViewSet(viewsets.ModelViewSet):
    """
    Customer Feedback ViewSet
    """
    queryset = CustomerFeedback.objects.all()
    serializer_class = CustomerFeedbackSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['feedback_type', 'status', 'priority', 'customer']
    search_fields = ['subject', 'message']
    ordering_fields = ['created_at', 'priority']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'customer', 'assigned_to', 'resolved_by',
            'related_class', 'related_teacher'
        )
        
        # Students see only their feedback
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(customer=user)
        # Teachers see feedback about them
        elif user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(
                Q(assigned_to=user) | Q(related_teacher=user)
            )
        
        return queryset

    def perform_create(self, serializer):
        # Students can only create feedback for themselves
        if self.request.user.role == self.request.user.UserRole.STUDENT:
            serializer.save(customer=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_feedback(self, request, pk=None):
        """
        Assign feedback to user
        POST /api/v1/crm/feedbacks/{id}/assign/
        {
            "assigned_to": "user_id"
        }
        """
        feedback = self.get_object()
        user_id = request.data.get('assigned_to')
        
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'کاربر یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        feedback.assigned_to = user
        feedback.status = CustomerFeedback.FeedbackStatus.IN_PROGRESS
        feedback.save()
        
        return Response({
            'message': f'بازخورد به {user.get_full_name()} اختصاص داده شد'
        })

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve_feedback(self, request, pk=None):
        """
        Resolve feedback
        POST /api/v1/crm/feedbacks/{id}/resolve/
        {
            "resolution": "راه حل"
        }
        """
        feedback = self.get_object()
        
        feedback.resolution = request.data.get('resolution', '')
        feedback.status = CustomerFeedback.FeedbackStatus.RESOLVED
        feedback.resolved_by = request.user
        feedback.resolved_at = timezone.now()
        feedback.save()
        
        # Send notification to customer
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=feedback.customer,
            title='بازخورد شما پاسخ داده شد',
            message=f'بازخورد "{feedback.subject}" پاسخ داده شد.',
            notification_type=Notification.NotificationType.INFO,
            category=Notification.NotificationCategory.SYSTEM,
            action_url=f'/feedbacks/{feedback.id}/'
        )
        
        return Response({
            'message': 'بازخورد حل شد'
        })

    @action(detail=False, methods=['get'], url_path='my-feedbacks')
    def my_feedbacks(self, request):
        """
        Get current user's feedbacks
        GET /api/v1/crm/feedbacks/my-feedbacks/
        """
        feedbacks = self.get_queryset().filter(customer=request.user)
        
        serializer = self.get_serializer(feedbacks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_feedbacks(self, request):
        """
        Get pending feedbacks
        GET /api/v1/crm/feedbacks/pending/
        """
        feedbacks = self.get_queryset().filter(
            status__in=[
                CustomerFeedback.FeedbackStatus.NEW,
                CustomerFeedback.FeedbackStatus.IN_PROGRESS
            ]
        ).order_by('priority', '-created_at')
        
        serializer = self.get_serializer(feedbacks, many=True)
        return Response(serializer.data)


class LoyaltyProgramViewSet(viewsets.ModelViewSet):
    """
    Loyalty Program ViewSet
    """
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['created_at', 'start_date']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='active')
    def active_program(self, request):
        """
        Get active loyalty program
        GET /api/v1/crm/loyalty-programs/active/
        """
        today = timezone.now().date()
        program = self.get_queryset().filter(
            is_active=True,
            start_date__lte=today
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).first()
        
        if not program:
            return Response({
                'error': 'برنامه وفاداری فعالی یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(program)
        return Response(serializer.data)


class CustomerLoyaltyPointsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Customer Loyalty Points ViewSet (Read-only)
    """
    queryset = CustomerLoyaltyPoints.objects.all()
    serializer_class = CustomerLoyaltyPointsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['customer', 'program', 'transaction_type']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Students see only their points
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(customer=user)
        
        return queryset.select_related('customer', 'program')

    @action(detail=False, methods=['get'], url_path='my-balance')
    def my_balance(self, request):
        """
        Get current user's loyalty points balance
        GET /api/v1/crm/loyalty-points/my-balance/
        """
        latest = self.get_queryset().filter(
            customer=request.user
        ).order_by('-created_at').first()
        
        balance = latest.balance_after if latest else 0
        
        # Get breakdown
        breakdown = self.get_queryset().filter(
            customer=request.user
        ).values('transaction_type').annotate(
            total=Sum('points')
        )
        
        return Response({
            'balance': balance,
            'breakdown': list(breakdown)
        })


class ReferralViewSet(viewsets.ModelViewSet):
    """
    Referral ViewSet
    """
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['referrer', 'status', 'reward_given']
    search_fields = ['referred_name', 'referred_mobile']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Users see only their referrals
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(referrer=user)
        
        return queryset.select_related('referrer', 'referred_user')

    def perform_create(self, serializer):
        # Students can only create referrals for themselves
        if self.request.user.role == self.request.user.UserRole.STUDENT:
            serializer.save(referrer=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='mark-registered')
    def mark_registered(self, request, pk=None):
        """
        Mark referral as registered
        POST /api/v1/crm/referrals/{id}/mark-registered/
        {
            "referred_user": "user_id"
        }
        """
        referral = self.get_object()
        user_id = request.data.get('referred_user')
        
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=user_id, mobile=referral.referred_mobile)
        except User.DoesNotExist:
            return Response({
                'error': 'کاربر یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        referral.referred_user = user
        referral.status = Referral.ReferralStatus.REGISTERED
        referral.save()
        
        return Response({
            'message': 'معرفی به عنوان ثبت‌نام شده علامت زد'
        })

    @action(detail=True, methods=['post'], url_path='give-reward')
    def give_reward(self, request, pk=None):
        """
        Give reward to referrer
        POST /api/v1/crm/referrals/{id}/give-reward/
        {
            "reward_type": "discount",
            "reward_value": 100000
        }
        """
        referral = self.get_object()
        
        if referral.reward_given:
            return Response({
                'error': 'پاداش قبلاً داده شده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        referral.reward_type = request.data.get('reward_type')
        referral.reward_value = request.data.get('reward_value', 0)
        referral.reward_given = True
        referral.rewarded_at = timezone.now()
        referral.save()
        
        # Add loyalty points
        try:
            program = LoyaltyProgram.objects.filter(is_active=True).first()
            if program:
                last_point = CustomerLoyaltyPoints.objects.filter(
                    customer=referral.referrer,
                    program=program
                ).order_by('-created_at').first()
                
                balance = last_point.balance_after if last_point else 0
                
                CustomerLoyaltyPoints.objects.create(
                    customer=referral.referrer,
                    program=program,
                    transaction_type=CustomerLoyaltyPoints.TransactionType.EARNED,
                    points=program.points_per_referral,
                    balance_after=balance + program.points_per_referral,
                    description=f'معرفی {referral.referred_name}',
                    reference_type='referral',
                    reference_id=str(referral.id)
                )
        except:
            pass
        
        # Send notification
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=referral.referrer,
            title='پاداش معرفی',
            message=f'پاداش معرفی {referral.referred_name} برای شما ثبت شد.',
            notification_type=Notification.NotificationType.SUCCESS,
            category=Notification.NotificationCategory.SYSTEM
        )
        
        return Response({
            'message': 'پاداش داده شد'
        })

    @action(detail=False, methods=['get'], url_path='my-referrals')
    def my_referrals(self, request):
        """
        Get current user's referrals
        GET /api/v1/crm/referrals/my-referrals/
        """
        referrals = self.get_queryset().filter(referrer=request.user)
        
        serializer = self.get_serializer(referrals, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get referral statistics
        GET /api/v1/crm/referrals/statistics/
        """
        user = request.user
        referrals = self.get_queryset().filter(referrer=user)
        
        stats = {
            'total': referrals.count(),
            'registered': referrals.filter(
                status__in=[
                    Referral.ReferralStatus.REGISTERED,
                    Referral.ReferralStatus.ENROLLED,
                    Referral.ReferralStatus.REWARDED
                ]
            ).count(),
            'enrolled': referrals.filter(
                status__in=[
                    Referral.ReferralStatus.ENROLLED,
                    Referral.ReferralStatus.REWARDED
                ]
            ).count(),
            'pending_reward': referrals.filter(
                status=Referral.ReferralStatus.ENROLLED,
                reward_given=False
            ).count(),
            'total_rewards': referrals.filter(
                reward_given=True
            ).aggregate(Sum('reward_value'))['reward_value__sum'] or 0
        }
        
        return Response(stats)
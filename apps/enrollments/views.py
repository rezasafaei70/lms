from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.db import transaction

from .models import (
    Enrollment, PlacementTest, WaitingList, EnrollmentTransfer,
    AnnualRegistration, EnrollmentDocument
)
from .serializers import (
    EnrollmentSerializer, EnrollmentListSerializer, PlacementTestSerializer,
    WaitingListSerializer, EnrollmentTransferSerializer,
    AnnualRegistrationSerializer, EnrollmentDocumentSerializer
)
from utils.permissions import IsSuperAdmin, IsStudent, IsBranchManager
from utils.pagination import StandardResultsSetPagination


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    Enrollment ViewSet
    """
    queryset = Enrollment.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'class_obj', 'term', 'status']
    search_fields = [
        'enrollment_number', 'student__first_name',
        'student__last_name', 'class_obj__name'
    ]
    ordering_fields = ['enrollment_date', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return EnrollmentListSerializer
        return EnrollmentSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'student', 'class_obj', 'class_obj__course',
            'class_obj__branch', 'term'
        )
        
        # Students see only their enrollments
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Branch managers see their branch enrollments
        elif user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(class_obj__branch__manager=user)
        
        return queryset

    def perform_create(self, serializer):
        # Students can only enroll themselves
        if self.request.user.role == self.request.user.UserRole.STUDENT:
            serializer.save(student=self.request.user)
        else:
            serializer.save()

    @action(detail=False, methods=['post'], url_path='enroll')
    def enroll(self, request):
        """
        Quick enrollment
        POST /api/v1/enrollments/enrollments/enroll/
        {
            "class_obj": "class_id",
            "discount_code": "CODE123" (optional)
        }
        """
        data = request.data.copy()
        data['student'] = request.user.id
        
        # Apply discount code if provided
        discount_code = data.pop('discount_code', None)
        discount_amount = 0
        
        if discount_code:
            from apps.financial.models import DiscountCoupon
            try:
                coupon = DiscountCoupon.objects.get(
                    code=discount_code,
                    is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_until__gte=timezone.now()
                )
                if coupon.can_use(request.user):
                    discount_amount = coupon.calculate_discount(data['class_obj'])
                    data['discount_amount'] = discount_amount
            except DiscountCoupon.DoesNotExist:
                pass
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save()
        
        return Response({
            'message': 'ثبت‌نام با موفقیت انجام شد',
            'enrollment': EnrollmentSerializer(enrollment).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Approve enrollment
        POST /api/v1/enrollments/enrollments/{id}/approve/
        """
        enrollment = self.get_object()
        
        enrollment.status = Enrollment.EnrollmentStatus.APPROVED
        enrollment.approved_by = request.user
        enrollment.approved_date = timezone.now()
        enrollment.save()
        
        # Send notification
        from apps.notifications.tasks import send_enrollment_approved_notification
        send_enrollment_approved_notification.delay(enrollment.id)
        
        return Response({
            'message': 'ثبت‌نام تایید شد'
        })

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Reject enrollment
        POST /api/v1/enrollments/enrollments/{id}/reject/
        {
            "reason": "دلیل رد"
        }
        """
        enrollment = self.get_object()
        reason = request.data.get('reason', '')
        
        enrollment.status = Enrollment.EnrollmentStatus.REJECTED
        enrollment.notes = f"رد شده: {reason}\n\n{enrollment.notes or ''}"
        enrollment.save()
        
        # Decrement class enrollments
        enrollment.class_obj.current_enrollments -= 1
        enrollment.class_obj.save()
        
        # Send notification
        from apps.notifications.tasks import send_enrollment_rejected_notification
        send_enrollment_rejected_notification.delay(enrollment.id, reason)
        
        return Response({
            'message': 'ثبت‌نام رد شد'
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel enrollment
        POST /api/v1/enrollments/enrollments/{id}/cancel/
        {
            "reason": "دلیل لغو"
        }
        """
        enrollment = self.get_object()
        reason = request.data.get('reason', '')
        
        # Check if user can cancel
        if request.user != enrollment.student and not request.user.is_superuser:
            return Response({
                'error': 'شما مجاز به لغو این ثبت‌نام نیستید'
            }, status=status.HTTP_403_FORBIDDEN)
        
        enrollment.status = Enrollment.EnrollmentStatus.CANCELLED
        enrollment.cancellation_reason = reason
        enrollment.save()
        
        # Decrement class enrollments
        enrollment.class_obj.current_enrollments -= 1
        enrollment.class_obj.save()
        
        # Refund logic (بعداً با financial کامل می‌شود)
        
        return Response({
            'message': 'ثبت‌نام لغو شد'
        })

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        """
        Withdraw from enrollment
        POST /api/v1/enrollments/enrollments/{id}/withdraw/
        """
        enrollment = self.get_object()
        
        enrollment.status = Enrollment.EnrollmentStatus.WITHDRAWN
        enrollment.save()
        
        return Response({
            'message': 'انصراف با موفقیت ثبت شد'
        })

    @action(detail=True, methods=['post'], url_path='issue-certificate')
    def issue_certificate(self, request, pk=None):
        """
        Issue certificate
        POST /api/v1/enrollments/enrollments/{id}/issue-certificate/
        """
        enrollment = self.get_object()
        
        # Check if eligible
        if enrollment.status != Enrollment.EnrollmentStatus.COMPLETED:
            return Response({
                'error': 'دوره هنوز تکمیل نشده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if enrollment.attendance_rate < 75:
            return Response({
                'error': 'حضور کافی نیست (حداقل 75% مورد نیاز است)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate certificate
        from apps.lms.utils import generate_certificate
        certificate_file = generate_certificate(enrollment)
        
        # Generate certificate number
        import random
        enrollment.certificate_number = f"CERT{timezone.now().year}{random.randint(100000, 999999)}"
        enrollment.certificate_issued = True
        enrollment.certificate_issue_date = timezone.now().date()
        enrollment.save()
        
        return Response({
            'message': 'گواهینامه صادر شد',
            'certificate_number': enrollment.certificate_number,
            'certificate_url': certificate_file
        })

    @action(detail=False, methods=['get'], url_path='my-enrollments')
    def my_enrollments(self, request):
        """
        Get current user enrollments
        GET /api/v1/enrollments/enrollments/my-enrollments/
        """
        enrollments = self.get_queryset().filter(student=request.user)
        
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get enrollment statistics
        GET /api/v1/enrollments/enrollments/statistics/
        """
        total = self.get_queryset().count()
        
        stats = {
            'total_enrollments': total,
            'pending': self.get_queryset().filter(
                status=Enrollment.EnrollmentStatus.PENDING
            ).count(),
            'active': self.get_queryset().filter(
                status=Enrollment.EnrollmentStatus.ACTIVE
            ).count(),
            'completed': self.get_queryset().filter(
                status=Enrollment.EnrollmentStatus.COMPLETED
            ).count(),
            'cancelled': self.get_queryset().filter(
                status=Enrollment.EnrollmentStatus.CANCELLED
            ).count(),
            'total_revenue': self.get_queryset().aggregate(
                total=Sum('paid_amount')
            )['total'] or 0,
            'certificates_issued': self.get_queryset().filter(
                certificate_issued=True
            ).count(),
        }
        
        return Response(stats)


class PlacementTestViewSet(viewsets.ModelViewSet):
    """
    Placement Test ViewSet
    """
    queryset = PlacementTest.objects.all()
    serializer_class = PlacementTestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'course', 'status', 'determined_level']
    ordering_fields = ['test_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Students see only their tests
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Teachers see tests they evaluated
        elif user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(evaluated_by=user)
        
        return queryset.select_related('student', 'course', 'evaluated_by')

    @action(detail=True, methods=['post'], url_path='submit-result')
    def submit_result(self, request, pk=None):
        """
        Submit test result
        POST /api/v1/enrollments/placement-tests/{id}/submit-result/
        {
            "score": 85,
            "determined_level": "intermediate",
            "feedback": "عالی بود"
        }
        """
        test = self.get_object()
        
        test.score = request.data.get('score')
        test.determined_level = request.data.get('determined_level')
        test.feedback = request.data.get('feedback', '')
        test.recommendations = request.data.get('recommendations', '')
        test.status = PlacementTest.TestStatus.COMPLETED
        test.evaluated_by = request.user
        test.evaluated_at = timezone.now()
        test.save()
        
        # Send notification
        from apps.notifications.tasks import send_placement_test_result_notification
        send_placement_test_result_notification.delay(test.id)
        
        return Response({
            'message': 'نتیجه آزمون ثبت شد',
            'test': PlacementTestSerializer(test).data
        })

    @action(detail=False, methods=['get'], url_path='my-tests')
    def my_tests(self, request):
        """
        Get current user placement tests
        GET /api/v1/enrollments/placement-tests/my-tests/
        """
        tests = self.get_queryset().filter(student=request.user)
        
        serializer = self.get_serializer(tests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_tests(self, request):
        """
        Get pending tests for evaluation
        GET /api/v1/enrollments/placement-tests/pending/
        """
        tests = self.get_queryset().filter(
            status=PlacementTest.TestStatus.COMPLETED,
            score__isnull=True
        )
        
        serializer = self.get_serializer(tests, many=True)
        return Response(serializer.data)


class WaitingListViewSet(viewsets.ModelViewSet):
    """
    Waiting List ViewSet
    """
    queryset = WaitingList.objects.all()
    serializer_class = WaitingListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'class_obj', 'status']
    ordering_fields = ['created_at', 'position']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Students see only their waiting lists
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        
        return queryset.select_related('student', 'class_obj')

    def perform_create(self, serializer):
        if self.request.user.role == self.request.user.UserRole.STUDENT:
            serializer.save(student=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='notify')
    def notify(self, request, pk=None):
        """
        Notify student about available seat
        POST /api/v1/enrollments/waiting-lists/{id}/notify/
        """
        waiting = self.get_object()
        
        waiting.status = WaitingList.WaitingStatus.NOTIFIED
        waiting.notified_at = timezone.now()
        waiting.notification_expires_at = timezone.now() + timezone.timedelta(hours=24)
        waiting.save()
        
        # Send notification
        from apps.notifications.tasks import send_waiting_list_notification
        send_waiting_list_notification.delay(waiting.id)
        
        return Response({
            'message': 'اطلاع‌رسانی انجام شد'
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel waiting list entry
        POST /api/v1/enrollments/waiting-lists/{id}/cancel/
        """
        waiting = self.get_object()
        
        waiting.status = WaitingList.WaitingStatus.CANCELLED
        waiting.save()
        
        return Response({
            'message': 'لیست انتظار لغو شد'
        })

    @action(detail=False, methods=['get'], url_path='my-waiting-lists')
    def my_waiting_lists(self, request):
        """
        Get current user waiting lists
        GET /api/v1/enrollments/waiting-lists/my-waiting-lists/
        """
        waiting_lists = self.get_queryset().filter(
            student=request.user,
            status=WaitingList.WaitingStatus.WAITING
        )
        
        serializer = self.get_serializer(waiting_lists, many=True)
        return Response(serializer.data)


class EnrollmentTransferViewSet(viewsets.ModelViewSet):
    """
    Enrollment Transfer ViewSet
    """
    queryset = EnrollmentTransfer.objects.all()
    serializer_class = EnrollmentTransferSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enrollment', 'status']
    ordering_fields = ['request_date']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Students see only their transfers
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(enrollment__student=user)
        
        return queryset.select_related(
            'enrollment', 'from_class', 'to_class',
            'requested_by', 'approved_by'
        )

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Approve transfer
        POST /api/v1/enrollments/transfers/{id}/approve/
        """
        transfer = self.get_object()
        
        with transaction.atomic():
            # Update enrollment
            enrollment = transfer.enrollment
            enrollment.class_obj = transfer.to_class
            enrollment.total_amount = transfer.to_class.price
            enrollment.save()
            
            # Update class enrollments
            transfer.from_class.current_enrollments -= 1
            transfer.from_class.save()
            
            transfer.to_class.current_enrollments += 1
            transfer.to_class.save()
            
            # Update transfer
            transfer.status = EnrollmentTransfer.TransferStatus.APPROVED
            transfer.approved_by = request.user
            transfer.approved_date = timezone.now()
            transfer.save()
        
        return Response({
            'message': 'انتقال تایید شد'
        })

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Reject transfer
        POST /api/v1/enrollments/transfers/{id}/reject/
        {
            "reason": "دلیل رد"
        }
        """
        transfer = self.get_object()
        reason = request.data.get('reason', '')
        
        transfer.status = EnrollmentTransfer.TransferStatus.REJECTED
        transfer.admin_notes = reason
        transfer.save()
        
        return Response({
            'message': 'انتقال رد شد'
        })

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_transfers(self, request):
        """
        Get pending transfers
        GET /api/v1/enrollments/transfers/pending/
        """
        transfers = self.get_queryset().filter(
            status=EnrollmentTransfer.TransferStatus.PENDING
        )
        
        serializer = self.get_serializer(transfers, many=True)
        return Response(serializer.data)


class AnnualRegistrationViewSet(viewsets.ModelViewSet):
    """
    Annual Registration ViewSet
    """
    queryset = AnnualRegistration.objects.all()
    serializer_class = AnnualRegistrationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'branch', 'academic_year', 'status']
    ordering_fields = ['registration_date']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Students see only their registrations
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Branch managers see their branch registrations
        elif user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(branch__manager=user)
        
        return queryset.select_related('student', 'branch')

    def perform_create(self, serializer):
        if self.request.user.role == self.request.user.UserRole.STUDENT:
            serializer.save(student=self.request.user)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='my-registrations')
    def my_registrations(self, request):
        """
        Get current user annual registrations
        GET /api/v1/enrollments/annual-registrations/my-registrations/
        """
        registrations = self.get_queryset().filter(student=request.user)
        
        serializer = self.get_serializer(registrations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """
        Activate annual registration
        POST /api/v1/enrollments/annual-registrations/{id}/activate/
        """
        registration = self.get_object()
        
        if not registration.is_paid:
            return Response({
                'error': 'شهریه پرداخت نشده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not registration.documents_verified:
            return Response({
                'error': 'مدارک تایید نشده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        registration.status = AnnualRegistration.RegistrationStatus.ACTIVE
        registration.save()
        
        return Response({
            'message': 'ثبت‌نام سالانه فعال شد'
        })


class EnrollmentDocumentViewSet(viewsets.ModelViewSet):
    """
    Enrollment Document ViewSet
    """
    queryset = EnrollmentDocument.objects.all()
    serializer_class = EnrollmentDocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enrollment', 'document_type', 'is_verified']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Students see only their documents
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(enrollment__student=user)
        
        return queryset.select_related('enrollment', 'verified_by')

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        """
        Verify document
        POST /api/v1/enrollments/documents/{id}/verify/
        """
        document = self.get_object()
        
        document.is_verified = True
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.save()
        
        return Response({
            'message': 'مدرک تایید شد'
        })

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_documents(self, request):
        """
        Get pending documents for verification
        GET /api/v1/enrollments/documents/pending/
        """
        documents = self.get_queryset().filter(is_verified=False)
        
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
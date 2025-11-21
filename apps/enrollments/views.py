from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.db import transaction

from apps.core.models import SystemSettings
from apps.courses.models import Class
from apps.financial.models import Invoice, InvoiceItem

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
        شروع فرآیند ثبت‌نام معمولی
        POST /api/v1/enrollments/enrollments/enroll/
        {
            "class_obj": "class_id",
            "discount_code": "CODE123" // optional
        }
        """
        class_id = request.data.get('class_obj')
        student = request.user
        
        # ... (کد بررسی ظرفیت و ثبت‌نام قبلی)
        from apps.courses.models import Class
        with transaction.atomic():
            # ✅ قفل کردن رکورد کلاس
            try:
                class_obj = Class.objects.select_for_update().get(id=class_id)
            except Class.DoesNotExist:
                return Response({'error': 'کلاس یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

            # ✅ دوباره چک کردن ظرفیت داخل تراکنش قفل شده
            if class_obj.is_full:
                return Response({'error': 'ظرفیت کلاس در همین لحظه پر شد'}, status=status.HTTP_400_BAD_REQUEST)

        
        # ...
        
        with transaction.atomic():
            # 1. ایجاد ثبت‌نام با وضعیت در انتظار پرداخت
            enrollment = Enrollment.objects.create(
                student=student,
                class_obj=class_obj,
                status=Enrollment.EnrollmentStatus.PENDING,
                total_amount=class_obj.price, # قیمت پایه
                # سایر فیلدها...
            )
            
            # 2. ایجاد فاکتور
            # ... (کد تخفیف و محاسبه قیمت نهایی)
            
            invoice = Invoice.objects.create(
                student=student,
                branch=class_obj.branch,
                invoice_type=Invoice.InvoiceType.TUITION,
                subtotal=class_obj.price,
                # discount_amount=discount_amount,
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=1),
                created_by=request.user,
                description=f'شهریه کلاس {class_obj.name}'
            )
            
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f'شهریه کلاس {class_obj.name}',
                quantity=1,
                unit_price=class_obj.price,
            )
            
            # 3. اتصال فاکتور به ثبت‌نام
            enrollment.invoice = invoice
            enrollment.save()
            
        return Response({
            'message': 'ثبت‌نام اولیه انجام شد. لطفاً فاکتور را پرداخت کنید.',
            'enrollment_id': str(enrollment.id),
            'invoice_id': str(invoice.id),
            'payment_url': f'/api/v1/financial/invoices/{invoice.id}/pay/'
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
        لغو ثبت‌نام
        """
        enrollment = self.get_object()
        reason = request.data.get('reason', 'لغو توسط کاربر')
        
        # فقط ثبت‌نام‌های فعال یا در انتظار قابل لغو هستند
        if enrollment.status not in [
            Enrollment.EnrollmentStatus.ACTIVE,
            Enrollment.EnrollmentStatus.PENDING_PAYMENT
        ]:
            return Response({'error': 'این ثبت‌نام قابل لغو نیست'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # اگر ثبت‌نام فعال بود، شمارنده را کم کن
            if enrollment.status == Enrollment.EnrollmentStatus.ACTIVE:
                Class.objects.filter(id=enrollment.class_obj.id).update(
                    current_enrollments=F('current_enrollments') - 1
                )

            # بروزرسانی وضعیت
            enrollment.status = Enrollment.EnrollmentStatus.CANCELLED
            enrollment.cancellation_reason = reason
            enrollment.save()
            
            # ✅ اطلاع به لیست انتظار
            from .tasks import check_waiting_list
            check_waiting_list.delay(enrollment.class_obj.id)
            
            # ⚠️ فرآیند بازگشت وجه باید اینجا شروع شود
            # می‌توانید یک Transaction یا CreditNote در سیستم مالی ایجاد کنید
            
        return Response({'message': 'ثبت‌نام با موفقیت لغو شد'})

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
        تایید انتقال - مرحله اول: بررسی مالی
        """
        transfer = self.get_object()
        
        # محاسبه اختلاف قیمت
        price_difference = transfer.to_class.price - transfer.from_class.price
        transfer.price_difference = price_difference
        
        with db_transaction.atomic():
            if price_difference > 0:
                # ✅ باید مابه‌التفاوت پرداخت شود
                invoice = Invoice.objects.create(
                    student=transfer.enrollment.student,
                    branch=transfer.to_class.branch,
                    invoice_type=Invoice.InvoiceType.OTHER,
                    subtotal=price_difference,
                    issue_date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=3),
                    created_by=request.user,
                    description=f'مابه‌التفاوت انتقال از کلاس {transfer.from_class.name} به {transfer.to_class.name}'
                )
                
                transfer.status = 'pending_payment'  # وضعیت جدید برای مدل Transfer
                transfer.save()
                
                return Response({
                    'message': 'انتقال تایید شد. لطفاً مابه‌التفاوت را پرداخت کنید.',
                    'invoice_id': str(invoice.id),
                    'amount_to_pay': price_difference
                })
            
            elif price_difference < 0:
                # ✅ باید مبلغی بازگردانده شود
                from apps.financial.models import Transaction
                Transaction.objects.create(
                    branch=transfer.from_class.branch,
                    transaction_type=Transaction.TransactionType.EXPENSE,
                    category=Transaction.TransactionCategory.OTHER,
                    amount=abs(price_difference),
                    date=timezone.now().date(),
                    description=f'بازگشت وجه انتقال {transfer.enrollment.student.get_full_name()}',
                    created_by=request.user
                )
                self._complete_transfer(transfer, request.user)
                
                return Response({
                    'message': 'انتقال با موفقیت انجام شد و مبلغ اضافه بازگردانده شد.'
                })
            
            else:
                # ✅ بدون اختلاف قیمت
                self._complete_transfer(transfer, request.user)
                
                return Response({
                    'message': 'انتقال با موفقیت انجام شد.'
                })
    def _complete_transfer(self, transfer, user):
        """متد کمکی برای نهایی کردن انتقال"""
        with transaction.atomic():
            # بروزرسانی ثبت‌نام
            enrollment = transfer.enrollment
            old_class = enrollment.class_obj
            enrollment.class_obj = transfer.to_class
            enrollment.save()
            
            # بروزرسانی شمارنده‌ها
            old_class.current_enrollments = F('current_enrollments') - 1
            old_class.save()
            
            transfer.to_class.current_enrollments = F('current_enrollments') + 1
            transfer.to_class.save()
            
            # بروزرسانی انتقال
            transfer.status = EnrollmentTransfer.TransferStatus.COMPLETED
            transfer.approved_by = user
            transfer.approved_date = timezone.now()
            transfer.save()
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
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'student', 'branch', 'invoice'
        )
        
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        elif user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(branch__manager=user)
        
        return queryset

    @action(detail=False, methods=['post'], url_path='register')
    def create_registration(self, request):
        """
        ثبت‌نام سالانه جدید
        POST /api/v1/enrollments/annual-registrations/register/
        {
            "branch": "branch_id",
            "academic_year": "1403-1404"  // optional - auto-detected
        }
        """
        from apps.financial.models import Invoice, InvoiceItem
        from apps.core.models import SystemSettings
        
        # دریافت سال تحصیلی
        academic_year = request.data.get('academic_year')
        if not academic_year:
            import jdatetime
            current_year = jdatetime.datetime.now().year
            academic_year = f"{current_year}-{current_year + 1}"
        
        # بررسی ثبت‌نام قبلی
        if AnnualRegistration.objects.filter(
            student=request.user,
            academic_year=academic_year
        ).exists():
            return Response({
                'error': 'شما قبلاً برای این سال ثبت‌نام کرده‌اید'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # دریافت شعبه
        try:
            from apps.branches.models import Branch
            branch = Branch.objects.get(id=request.data.get('branch'))
        except Branch.DoesNotExist:
            return Response({
                'error': 'شعبه یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # دریافت هزینه ثبت‌نام از تنظیمات
        registration_fee = SystemSettings.get_annual_registration_fee()
        
        # محاسبه تاریخ شروع و پایان
        import jdatetime
        year = int(academic_year.split('-')[0])
        start_date = jdatetime.date(year, 7, 1).togregorian()  # 1 مهر
        end_date = jdatetime.date(year + 1, 6, 31).togregorian()  # 31 شهریور
        
        with db_transaction.atomic():
            # ایجاد ثبت‌نام
            registration = AnnualRegistration.objects.create(
                student=request.user,
                branch=branch,
                academic_year=academic_year,
                start_date=start_date,
                end_date=end_date,
                registration_fee_setting=registration_fee,
                status=AnnualRegistration.RegistrationStatus.DRAFT
            )
            
            # ✅ ایجاد فاکتور
            invoice = Invoice.objects.create(
                student=request.user,
                branch=branch,
                invoice_type=Invoice.InvoiceType.REGISTRATION,
                subtotal=registration_fee,
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=7),
                created_by=request.user,
                description=f'ثبت‌نام سالانه {academic_year}'
            )
            
            # ایجاد آیتم فاکتور
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f'شهریه ثبت‌نام سالانه {academic_year}',
                quantity=1,
                unit_price=registration_fee
            )
            
            # اتصال فاکتور به ثبت‌نام
            registration.invoice = invoice
            registration.status = AnnualRegistration.RegistrationStatus.PENDING_PAYMENT
            registration.save()
        
        return Response({
            'message': 'ثبت‌نام ایجاد شد. لطفاً فاکتور را پرداخت کنید.',
            'registration_id': str(registration.id),
            'invoice_id': str(invoice.id),
            'amount': registration_fee,
            'due_date': invoice.due_date
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='verify-documents')
    def verify_documents(self, request, pk=None):
        """
        تایید مدارک ثبت‌نام
        POST /api/v1/enrollments/annual-registrations/{id}/verify-documents/
        """
        registration = self.get_object()
        
        if not registration.documents_submitted:
            return Response({
                'error': 'مدارک هنوز ارسال نشده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        registration.documents_verified = True
        registration.verified_by = request.user
        registration.verified_at = timezone.now()
        
        # اگر پرداخت هم انجام شده، وضعیت را تغییر بده
        if registration.is_paid:
            registration.status = AnnualRegistration.RegistrationStatus.PENDING_VERIFICATION
        
        registration.save()
        
        # اگر همه شرایط فراهم باشد، خودکار فعال کن
        if registration.can_activate:
            registration.status = AnnualRegistration.RegistrationStatus.ACTIVE
            registration.activated_by = request.user
            registration.activated_at = timezone.now()
            registration.save()
            
            # ارسال نوتیفیکیشن
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=registration.student,
                title='ثبت‌نام سالانه فعال شد',
                message=f'ثبت‌نام سالانه شما برای {registration.academic_year} فعال شد.',
                notification_type=Notification.NotificationType.SUCCESS,
                category=Notification.NotificationCategory.ENROLLMENT
            )
        
        return Response({
            'message': 'مدارک تایید شد',
            'registration_activated': registration.status == AnnualRegistration.RegistrationStatus.ACTIVE
        })

    @action(detail=False, methods=['get'], url_path='my-registration')
    def my_current_registration(self, request):
        """
        دریافت ثبت‌نام فعلی کاربر
        GET /api/v1/enrollments/annual-registrations/my-registration/
        """
        import jdatetime
        current_year = jdatetime.datetime.now().year
        academic_year = f"{current_year}-{current_year + 1}"
        
        try:
            registration = AnnualRegistration.objects.select_related(
                'invoice', 'branch'
            ).get(
                student=request.user,
                academic_year=academic_year
            )
            
            serializer = self.get_serializer(registration)
            data = serializer.data
            
            # اضافه کردن اطلاعات مالی از Invoice
            if registration.invoice:
                data['payment_info'] = {
                    'invoice_id': str(registration.invoice.id),
                    'total_amount': registration.invoice.total_amount,
                    'paid_amount': registration.invoice.paid_amount,
                    'remaining': registration.invoice.remaining_amount,
                    'status': registration.invoice.status,
                    'due_date': registration.invoice.due_date,
                    'is_paid': registration.invoice.is_paid,
                }
            
            return Response(data)
            
        except AnnualRegistration.DoesNotExist:
            return Response({
                'registered': False,
                'academic_year': academic_year,
                'registration_fee': SystemSettings.get_annual_registration_fee(),
                'message': 'شما هنوز برای این سال ثبت‌نام نکرده‌اید'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='payment-url')
    def get_payment_url(self, request, pk=None):
        """
        دریافت لینک پرداخت
        GET /api/v1/enrollments/annual-registrations/{id}/payment-url/
        """
        registration = self.get_object()
        
        if not registration.invoice:
            return Response({
                'error': 'فاکتوری یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if registration.invoice.is_paid:
            return Response({
                'error': 'این فاکتور قبلاً پرداخت شده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ایجاد لینک پرداخت
        # این بخش در financial views است
        return Response({
            'invoice_id': str(registration.invoice.id),
            'payment_url': f'/api/v1/financial/invoices/{registration.invoice.id}/pay/',
            'amount': registration.invoice.total_amount
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
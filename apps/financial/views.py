from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db import transaction as db_transaction

from .models import (
    Invoice, InvoiceItem, Payment, DiscountCoupon, CouponUsage,
    Installment, Transaction, TeacherPayment
)
from .serializers import (
    InvoiceSerializer, InvoiceListSerializer, CreateInvoiceSerializer,
    PaymentSerializer, VerifyPaymentSerializer,
    DiscountCouponSerializer, ValidateCouponSerializer,
    InstallmentSerializer, CreateInstallmentPlanSerializer,
    TransactionSerializer, TeacherPaymentSerializer,
    FinancialReportSerializer
)
from utils.permissions import IsSuperAdmin, IsStudent, IsBranchManager
from utils.pagination import StandardResultsSetPagination
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Invoice ViewSet
    """
    queryset = Invoice.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'branch', 'invoice_type', 'status']
    search_fields = ['invoice_number', 'student__first_name', 'student__last_name']
    ordering_fields = ['issue_date', 'total_amount', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create_invoice':
            return CreateInvoiceSerializer
        return InvoiceSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'student', 'enrollment', 'branch', 'created_by'
        ).prefetch_related('items', 'payments')
        
        # Students see only their invoices
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Branch managers see their branch invoices
        elif user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(branch__manager=user)
        
        return queryset

    @action(detail=False, methods=['post'], url_path='create-invoice')
    def create_invoice(self, request):
        """
        Create invoice with items
        POST /api/v1/financial/invoices/create-invoice/
        """
        serializer = CreateInvoiceSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        
        return Response({
            'message': 'فاکتور ایجاد شد',
            'invoice': InvoiceSerializer(invoice).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        """
        Download invoice as PDF
        GET /api/v1/financial/invoices/{id}/download-pdf/
        """
        invoice = self.get_object()
        
        # Generate PDF
        from utils.pdf_generator import generate_invoice_pdf
        pdf_file = generate_invoice_pdf(invoice)
        
        from django.http import FileResponse
        return FileResponse(
            pdf_file,
            as_attachment=True,
            filename=f'invoice_{invoice.invoice_number}.pdf'
        )

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_invoice(self, request, pk=None):
        """
        Cancel invoice
        POST /api/v1/financial/invoices/{id}/cancel/
        """
        invoice = self.get_object()
        
        if invoice.status == Invoice.InvoiceStatus.PAID:
            return Response({
                'error': 'فاکتور پرداخت شده قابل لغو نیست'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.status = Invoice.InvoiceStatus.CANCELLED
        invoice.save()
        
        return Response({
            'message': 'فاکتور لغو شد'
        })

    @action(detail=False, methods=['get'], url_path='my-invoices')
    def my_invoices(self, request):
        """
        Get current user's invoices
        GET /api/v1/financial/invoices/my-invoices/
        """
        invoices = self.get_queryset().filter(student=request.user)
        
        page = self.paginate_queryset(invoices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue_invoices(self, request):
        """
        Get overdue invoices
        GET /api/v1/financial/invoices/overdue/
        """
        today = timezone.now().date()
        invoices = self.get_queryset().filter(
            status__in=[
                Invoice.InvoiceStatus.PENDING,
                Invoice.InvoiceStatus.PARTIALLY_PAID
            ],
            due_date__lt=today
        )
        
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get invoice statistics
        GET /api/v1/financial/invoices/statistics/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_invoices': queryset.count(),
            'paid_invoices': queryset.filter(
                status=Invoice.InvoiceStatus.PAID
            ).count(),
            'pending_invoices': queryset.filter(
                status=Invoice.InvoiceStatus.PENDING
            ).count(),
            'cancelled_invoices': queryset.filter(
                status=Invoice.InvoiceStatus.CANCELLED
            ).count(),
            'total_amount': queryset.aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'paid_amount': queryset.aggregate(
                total=Sum('paid_amount')
            )['total'] or 0,
            'outstanding_amount': queryset.filter(
                status__in=[
                    Invoice.InvoiceStatus.PENDING,
                    Invoice.InvoiceStatus.PARTIALLY_PAID
                ]
            ).aggregate(
                total=Sum('total_amount') - Sum('paid_amount')
            )['total'] or 0,
        }
        
        return Response(stats)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment ViewSet
    """
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['invoice', 'student', 'payment_method', 'status']
    search_fields = [
        'payment_number', 'gateway_transaction_id',
        'gateway_reference_id', 'student__first_name'
    ]
    ordering_fields = ['payment_date', 'amount']

    def get_serializer_class(self):
        if self.action == 'verify_payment':
            return VerifyPaymentSerializer
        return PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'invoice', 'student', 'verified_by'
        )
        
        # Students see only their payments
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        
        return queryset

    @action(detail=False, methods=['post'], url_path='verify')
    def verify_payment(self, request):
        """
        Verify payment
        POST /api/v1/financial/payments/verify/
        """
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment = Payment.objects.get(id=serializer.validated_data['payment_id'])
        
        payment.status = Payment.PaymentStatus.COMPLETED
        payment.verified_by = request.user
        payment.verified_date = timezone.now()
        payment.tracking_code = serializer.validated_data.get('tracking_code', '')
        payment.notes = serializer.validated_data.get('notes', '')
        payment.save()
        
        return Response({
            'message': 'پرداخت تایید شد',
            'payment': PaymentSerializer(payment).data
        })

    @action(detail=True, methods=['post'], url_path='refund')
    def refund_payment(self, request, pk=None):
        """
        Refund payment
        POST /api/v1/financial/payments/{id}/refund/
        """
        payment = self.get_object()
        
        if payment.status != Payment.PaymentStatus.COMPLETED:
            return Response({
                'error': 'فقط پرداخت‌های تکمیل شده قابل بازگشت هستند'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payment.status = Payment.PaymentStatus.REFUNDED
        payment.save()
        
        # Update invoice
        payment.invoice.paid_amount -= payment.amount
        payment.invoice.save()
        
        return Response({
            'message': 'بازگشت وجه انجام شد'
        })

    @action(detail=False, methods=['get'], url_path='my-payments')
    def my_payments(self, request):
        """
        Get current user's payments
        GET /api/v1/financial/payments/my-payments/
        """
        payments = self.get_queryset().filter(student=request.user)
        
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)


class DiscountCouponViewSet(viewsets.ModelViewSet):
    """
    Discount Coupon ViewSet
    """
    queryset = DiscountCoupon.objects.all()
    serializer_class = DiscountCouponSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'discount_type']
    search_fields = ['code', 'name']
    ordering_fields = ['created_at', 'valid_from', 'valid_until']

    def get_permissions(self):
        if self.action in ['validate_coupon']:
            return [IsAuthenticated()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_coupon(self, request):
        """
        Validate discount coupon
        POST /api/v1/financial/coupons/validate/
        {
            "code": "DISCOUNT20",
            "user_id": "user_id",
            "amount": 1000000
        }
        """
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response({
            'valid': True,
            'code': serializer.validated_data['code'],
            'discount_amount': serializer.validated_data['discount_amount'],
            'coupon': DiscountCouponSerializer(
                serializer.validated_data['coupon']
            ).data
        })

    @action(detail=False, methods=['get'], url_path='active')
    def active_coupons(self, request):
        """
        Get active coupons
        GET /api/v1/financial/coupons/active/
        """
        now = timezone.now()
        coupons = self.get_queryset().filter(
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now
        )
        
        serializer = self.get_serializer(coupons, many=True)
        return Response(serializer.data)


class InstallmentViewSet(viewsets.ModelViewSet):
    """
    Installment ViewSet
    """
    queryset = Installment.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['invoice', 'status']
    ordering_fields = ['due_date', 'installment_number']

    def get_serializer_class(self):
        if self.action == 'create_plan':
            return CreateInstallmentPlanSerializer
        return InstallmentSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related('invoice', 'payment')
        
        # Students see only their installments
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(invoice__student=user)
        
        return queryset

    @action(detail=False, methods=['post'], url_path='create-plan')
    def create_plan(self, request):
        """
        Create installment plan
        POST /api/v1/financial/installments/create-plan/
        """
        serializer = CreateInstallmentPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        installments = serializer.save()
        
        return Response({
            'message': f'{len(installments)} قسط ایجاد شد',
            'installments': InstallmentSerializer(installments, many=True).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='pay')
    def pay_installment(self, request, pk=None):
        """
        Pay installment
        POST /api/v1/financial/installments/{id}/pay/
        """
        installment = self.get_object()
        
        if installment.status == Installment.InstallmentStatus.PAID:
            return Response({
                'error': 'این قسط قبلاً پرداخت شده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create payment
        payment = Payment.objects.create(
            invoice=installment.invoice,
            student=installment.invoice.student,
            amount=installment.amount + installment.penalty_amount,
            payment_method=request.data.get('payment_method', 'cash'),
            status=Payment.PaymentStatus.PENDING
        )
        
        installment.payment = payment
        installment.status = Installment.InstallmentStatus.PAID
        installment.paid_date = timezone.now().date()
        installment.save()
        
        return Response({
            'message': 'قسط پرداخت شد',
            'payment': PaymentSerializer(payment).data
        })

    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue_installments(self, request):
        """
        Get overdue installments
        GET /api/v1/financial/installments/overdue/
        """
        today = timezone.now().date()
        installments = self.get_queryset().filter(
            status=Installment.InstallmentStatus.PENDING,
            due_date__lt=today
        )
        
        serializer = self.get_serializer(installments, many=True)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    Transaction ViewSet
    """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['branch', 'transaction_type', 'category']
    search_fields = ['transaction_number', 'description', 'reference']
    ordering_fields = ['date', 'amount', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsBranchManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related('branch', 'created_by')
        
        # Branch managers see their branch transactions
        if user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(branch__manager=user)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Get transaction summary
        GET /api/v1/financial/transactions/summary/
        """
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        branch = request.query_params.get('branch')
        
        queryset = self.get_queryset()
        
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
        if branch:
            queryset = queryset.filter(branch_id=branch)
        
        income = queryset.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense = queryset.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_income': income,
            'total_expense': expense,
            'net_profit': income - expense,
            'transaction_count': queryset.count()
        })


class TeacherPaymentViewSet(viewsets.ModelViewSet):
    """
    Teacher Payment ViewSet
    """
    queryset = TeacherPayment.objects.all()
    serializer_class = TeacherPaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['teacher', 'status']
    ordering_fields = ['from_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'teacher', 'approved_by', 'transaction'
        )
        
        # Teachers see only their payments
        if user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(teacher=user)
        
        return queryset

    @action(detail=True, methods=['post'], url_path='calculate-hours')
    def calculate_hours(self, request, pk=None):
        """
        Calculate teaching hours
        POST /api/v1/financial/teacher-payments/{id}/calculate-hours/
        """
        payment = self.get_object()
        payment.calculate_teaching_hours()
        
        return Response({
            'message': 'ساعات تدریس محاسبه شد',
            'payment': TeacherPaymentSerializer(payment).data
        })

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_payment(self, request, pk=None):
        """
        Approve teacher payment
        POST /api/v1/financial/teacher-payments/{id}/approve/
        """
        payment = self.get_object()
        
        payment.status = TeacherPayment.PaymentStatus.APPROVED
        payment.approved_by = request.user
        payment.approved_date = timezone.now()
        payment.save()
        
        return Response({
            'message': 'پرداخت تایید شد'
        })

    @action(detail=False, methods=['get'], url_path='my-payments')
    def my_payments(self, request):
        """
        Get current teacher's payments
        GET /api/v1/financial/teacher-payments/my-payments/
        """
        if request.user.role != request.user.UserRole.TEACHER:
            return Response({
                'error': 'فقط معلمان می‌توانند به این بخش دسترسی داشته باشند'
            }, status=status.HTTP_403_FORBIDDEN)
        
        payments = self.get_queryset().filter(teacher=request.user)
        
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)


class FinancialReportViewSet(viewsets.ViewSet):
    """
    Financial Report ViewSet
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        Get financial dashboard data
        GET /api/v1/financial/reports/dashboard/
        """
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        # Invoices
        invoices = Invoice.objects.all()
        if from_date:
            invoices = invoices.filter(issue_date__gte=from_date)
        if to_date:
            invoices = invoices.filter(issue_date__lte=to_date)
        
        # Transactions
        transactions = Transaction.objects.all()
        if from_date:
            transactions = transactions.filter(date__gte=from_date)
        if to_date:
            transactions = transactions.filter(date__lte=to_date)
        
        income = transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense = transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        report_data = {
            'total_income': income,
            'total_expense': expense,
            'net_profit': income - expense,
            'total_invoices': invoices.count(),
            'paid_invoices': invoices.filter(
                status=Invoice.InvoiceStatus.PAID
            ).count(),
            'pending_invoices': invoices.filter(
                status=Invoice.InvoiceStatus.PENDING
            ).count(),
            'total_payments': Payment.objects.filter(
                status=Payment.PaymentStatus.COMPLETED
            ).count(),
            'overdue_invoices': invoices.filter(
                status__in=[
                    Invoice.InvoiceStatus.PENDING,
                    Invoice.InvoiceStatus.PARTIALLY_PAID
                ],
                due_date__lt=timezone.now().date()
            ).count(),
            'total_outstanding': invoices.filter(
                status__in=[
                    Invoice.InvoiceStatus.PENDING,
                    Invoice.InvoiceStatus.PARTIALLY_PAID
                ]
            ).aggregate(
                total=Sum('total_amount') - Sum('paid_amount')
            )['total'] or 0,
        }
        
        serializer = FinancialReportSerializer(report_data)
        return Response(serializer.data)
    
class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # دریافت داده‌ها از بانک
        transaction_id = request.data.get('id')
        order_id = request.data.get('order_id') # همان payment_number شما

        try:
            payment = Payment.objects.get(payment_number=order_id)
        except Payment.DoesNotExist:
            return Response({'error': 'پرداخت یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

        # استعلام از وب‌سرویس بانک (این بخش باید طبق مستندات بانک نوشته شود)
        is_successful, tracking_code = verify_bank_payment(transaction_id, payment.amount)

        if is_successful:
            with db_transaction.atomic():
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.gateway_transaction_id = transaction_id
                payment.gateway_reference_id = tracking_code
                payment.verified_date = timezone.now()
                payment.save() # این save، سیگنال post_save را فعال می‌کند

            return Response({'message': 'پرداخت با موفقیت تایید شد'})
        else:
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()
            return Response({'error': 'پرداخت ناموفق بود'}, status=status.HTTP_400_BAD_REQUEST)
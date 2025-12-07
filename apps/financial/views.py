from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db import transaction as db_transaction

from apps.financial.services import add_credit_to_student, use_credit_for_payment

from .models import (
    CreditNote, Invoice, InvoiceItem, Payment, DiscountCoupon, CouponUsage,
    Installment, Transaction, TeacherPayment
)
from .serializers import (
    CreditNoteSerializer, CreditTransactionSerializer, InvoiceSerializer, InvoiceListSerializer, CreateInvoiceSerializer,
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

        # استعلام از وب‌سرویس بانک
        from .payment_gateway import verify_sadad_payment
        verify_result = verify_sadad_payment(transaction_id, payment.invoice)

        if verify_result.get('success'):
            with db_transaction.atomic():
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.gateway_transaction_id = transaction_id
                payment.gateway_reference_id = verify_result.get('reference_number')
                payment.verified_date = timezone.now()
                payment.save()

            return Response({'message': 'پرداخت با موفقیت تایید شد'})
        else:
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()
            return Response({'error': verify_result.get('error', 'پرداخت ناموفق بود')}, status=status.HTTP_400_BAD_REQUEST)


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class SadadPaymentView(APIView):
    """
    Sadad Payment Gateway Views
    """
    # اجازه دسترسی به همه - بررسی احراز هویت در هر متد جداگانه انجام می‌شود
    permission_classes = [AllowAny]
    # احراز هویت فعال باشد تا توکن JWT پردازش شود
    # authentication_classes پیش‌فرض استفاده می‌شود

    def get(self, request, action=None, *args, **kwargs):
        """Handle GET requests for payment simulation and verification"""
        if action == 'simulate':
            return self.simulate_payment_page(request)
        elif action == 'verify':
            return self.verify_payment_status(request, kwargs.get('invoice_id'))
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, action=None, *args, **kwargs):
        """Handle POST requests for initiating payments and callbacks"""
        if action == 'initiate':
            return self.initiate_payment(request)
        elif action == 'callback':
            return self.payment_callback(request)
        elif action == 'simulate-confirm':
            # این اکشن از فرم HTML فراخوانی می‌شود و نیاز به احراز هویت ندارد
            return self.simulate_confirm_payment(request)
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

    def initiate_payment(self, request):
        """
        Initiate a payment for an invoice
        POST /api/v1/financial/payment/initiate/
        """
        # بررسی احراز هویت برای شروع پرداخت
        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'برای پرداخت باید وارد شوید'}, status=status.HTTP_401_UNAUTHORIZED)
        
        from .payment_gateway import initiate_sadad_payment
        
        invoice_id = request.data.get('invoice_id')
        if not invoice_id:
            return Response({'error': 'شناسه فاکتور الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'error': 'فاکتور یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already paid
        if invoice.status == Invoice.InvoiceStatus.PAID:
            return Response({'error': 'این فاکتور قبلاً پرداخت شده است'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Build callback URL
        callback_url = request.build_absolute_uri('/api/v1/financial/payment/callback/')
        
        # Initiate payment
        result = initiate_sadad_payment(invoice, callback_url)
        
        if result['success']:
            # تبدیل URL نسبی به URL مطلق برای جلوگیری از مشکل پورت
            payment_url = result['payment_url']
            if payment_url.startswith('/'):
                # استفاده از تنظیمات API_BASE_URL برای ساخت URL کامل
                from django.conf import settings
                api_base_url = getattr(settings, 'API_BASE_URL', None)
                if api_base_url:
                    payment_url = f"{api_base_url.rstrip('/')}{payment_url}"
                else:
                    payment_url = request.build_absolute_uri(payment_url)
            
            return Response({
                'success': True,
                'payment_url': payment_url,
                'token': result['token'],
                'order_id': result['order_id'],
                'amount': int(invoice.total_amount),
                'invoice_number': invoice.invoice_number,
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'خطا در ایجاد درخواست پرداخت')
            }, status=status.HTTP_400_BAD_REQUEST)

    def simulate_payment_page(self, request):
        """Simulate payment page for testing"""
        token = request.query_params.get('token', '')
        amount = request.query_params.get('amount', '0')
        invoice_id = request.query_params.get('invoice_id', '')
        callback = request.query_params.get('callback', '')
        
        # تبدیل مبلغ به عدد
        try:
            amount_int = int(amount) if amount else 0
            amount_toman = amount_int // 10
        except (ValueError, TypeError):
            amount_int = 0
            amount_toman = 0
        
        # فرمت کردن مبلغ با جداکننده هزارگان
        amount_formatted = f"{amount_int:,}"
        amount_toman_formatted = f"{amount_toman:,}"
        
        html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>درگاه پرداخت سداد - بانک ملی</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Tahoma; background: linear-gradient(135deg, #1a237e, #0d47a1); min-height: 100vh; display: flex; flex-direction: column; }}
        .header {{ background: #0d47a1; padding: 15px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 3px solid #ffc107; color: white; }}
        .logo {{ display: flex; align-items: center; gap: 12px; }}
        .logo-icon {{ width: 45px; height: 45px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #0d47a1; }}
        .main {{ flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; }}
        .card {{ background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 420px; width: 100%; overflow: hidden; }}
        .card-header {{ background: linear-gradient(90deg, #1565c0, #0d47a1); color: white; padding: 20px; text-align: center; }}
        .card-body {{ padding: 25px; }}
        .amount-box {{ background: linear-gradient(135deg, #e3f2fd, #bbdefb); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 2px solid #90caf9; }}
        .amount-value {{ font-size: 28px; font-weight: bold; color: #0d47a1; }}
        .amount-toman {{ font-size: 13px; color: #666; margin-top: 5px; }}
        .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed #e0e0e0; font-size: 13px; }}
        .form-group {{ margin-bottom: 12px; }}
        .form-label {{ display: block; font-size: 12px; color: #666; margin-bottom: 5px; }}
        .form-input {{ width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; text-align: center; direction: ltr; }}
        .btn-group {{ display: flex; gap: 10px; margin-top: 15px; }}
        .btn {{ flex: 1; padding: 14px; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; }}
        .btn-pay {{ background: linear-gradient(135deg, #43a047, #2e7d32); color: white; }}
        .btn-pay:hover {{ opacity: 0.9; }}
        .btn-cancel {{ background: #f5f5f5; color: #666; border: 2px solid #e0e0e0; }}
        .btn-cancel:hover {{ background: #ffebee; border-color: #ef5350; color: #d32f2f; }}
        .test-banner {{ background: linear-gradient(90deg, #ff9800, #f57c00); color: white; padding: 8px; text-align: center; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-icon">🏦</div>
            <div><strong>سداد - بانک ملی ایران</strong><br><small>درگاه پرداخت امن</small></div>
        </div>
        <div>🔒 SSL</div>
    </div>
    <div class="test-banner">⚠️ حالت آزمایشی - شبیه‌ساز درگاه پرداخت</div>
    <div class="main">
        <div class="card">
            <div class="card-header"><h2>پرداخت امن اینترنتی</h2></div>
            <div class="card-body">
                <div class="amount-box">
                    <div style="font-size:13px;color:#1565c0;margin-bottom:5px;">مبلغ قابل پرداخت</div>
                    <div class="amount-value">{amount_formatted} ریال</div>
                    <div class="amount-toman">معادل {amount_toman_formatted} تومان</div>
                </div>
                <div class="info-row"><span>پذیرنده:</span><span>آموزشگاه کنکور پزشکی</span></div>
                <div class="info-row"><span>شماره سفارش:</span><span style="direction:ltr;">{str(invoice_id)[:8]}...</span></div>
                <form method="POST" action="/api/v1/financial/payment/simulate-confirm/" style="margin-top:15px;" id="paymentForm">
                    <input type="hidden" name="token" value="{token}">
                    <input type="hidden" name="invoice_id" value="{invoice_id}">
                    <div class="form-group"><label class="form-label">شماره کارت</label><input type="text" class="form-input" value="6037-9911-****-5678" readonly></div>
                    <div style="display:flex;gap:10px;">
                        <div class="form-group" style="flex:1;"><label class="form-label">CVV2</label><input type="text" class="form-input" value="***" readonly></div>
                        <div class="form-group" style="flex:1;"><label class="form-label">انقضا</label><input type="text" class="form-input" value="12/28" readonly></div>
                    </div>
                    <div class="form-group"><label class="form-label">رمز دوم پویا</label><input type="text" class="form-input" value="******" readonly></div>
                    <div class="btn-group">
                        <button type="submit" name="status" value="success" class="btn btn-pay">✓ تأیید پرداخت</button>
                        <button type="submit" name="status" value="failed" class="btn btn-cancel">✗ انصراف</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</body>
</html>'''
        from django.http import HttpResponse
        return HttpResponse(html, content_type='text/html; charset=utf-8')

    def simulate_confirm_payment(self, request):
        """Handle simulated payment confirmation"""
        from .payment_gateway import process_sadad_callback
        from django.conf import settings
        
        token = request.data.get('token') or request.POST.get('token')
        invoice_id = request.data.get('invoice_id') or request.POST.get('invoice_id')
        status_value = request.data.get('status') or request.POST.get('status')
        
        result = process_sadad_callback(
            token=token,
            status=status_value,
            invoice_id=invoice_id,
            reference_number=f"TEST_REF_{str(invoice_id)[:8]}" if status_value == 'success' else None,
            card_number='6037****1234' if status_value == 'success' else None
        )
        
        # استفاده از تنظیمات فرانت‌اند یا پیش‌فرض
        frontend_base = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:3000')
        frontend_url = f"{frontend_base}/student/payments"
        
        if result['success']:
            redirect_url = f"{frontend_url}?payment=success&reference={result.get('reference_number', '')}"
        else:
            error_msg = result.get('error', 'خطا')
            # URL encode the error message
            from urllib.parse import quote
            redirect_url = f"{frontend_url}?payment=failed&error={quote(error_msg)}"
        
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(redirect_url)

    def payment_callback(self, request):
        """Handle payment callback from gateway"""
        from .payment_gateway import process_sadad_callback
        
        token = request.data.get('token')
        invoice_id = request.data.get('invoice_id') or request.data.get('OrderId')
        status_value = 'success' if request.data.get('ResCode') == 0 else 'failed'
        reference_number = request.data.get('RetrivalRefNo')
        card_number = request.data.get('CardNo')
        
        result = process_sadad_callback(
            token=token,
            status=status_value,
            invoice_id=invoice_id,
            reference_number=reference_number,
            card_number=card_number
        )
        
        return Response(result)

    def verify_payment_status(self, request, invoice_id):
        """Verify payment status for an invoice"""
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'error': 'فاکتور یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'invoice_id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'status': invoice.status,
            'is_paid': invoice.is_paid,
            'total_amount': float(invoice.total_amount),
            'paid_amount': float(invoice.paid_amount),
            'remaining_amount': float(invoice.remaining_amount),
        })
        
class CreditNoteViewSet(viewsets.GenericViewSet):
    """
    مدیریت کیف پول و اعتبار دانش‌آموزان
    """
    queryset = CreditNote.objects.all()
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related('student').prefetch_related('transactions')
        
        # دانش‌آموزان فقط کیف پول خود را می‌بینند
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # مدیران می‌توانند همه را ببینند
        elif user.role not in [user.UserRole.SUPER_ADMIN, user.UserRole.BRANCH_MANAGER]:
            queryset = queryset.none()
        
        return queryset

    @action(detail=False, methods=['get'], url_path='my-credit')
    def my_credit_details(self, request):
        """
        دریافت اطلاعات کامل کیف پول کاربر جاری
        GET /api/v1/financial/credit/my-credit/
        """
        credit_note, created = CreditNote.objects.get_or_create(student=request.user)
        serializer = self.get_serializer(credit_note)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-balance')
    def my_balance(self, request):
        """
        دریافت موجودی فعلی اعتبار (سریع)
        GET /api/v1/financial/credit/my-balance/
        """
        credit_note, created = CreditNote.objects.get_or_create(student=request.user)
        return Response({'balance': credit_note.balance})

    @action(detail=False, methods=['get'], url_path='my-transactions')
    def my_transactions(self, request):
        """
        دریافت تاریخچه تراکنش‌های اعتبار کاربر جاری
        GET /api/v1/financial/credit/my-transactions/
        """
        credit_note, created = CreditNote.objects.get_or_create(student=request.user)
        
        # استفاده از pagination
        paginator = StandardResultsSetPagination()
        transactions = credit_note.transactions.all().order_by('-created_at')
        page = paginator.paginate_queryset(transactions, request)
        
        serializer = CreditTransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['post'], url_path='pay-with-credit', permission_classes=[IsStudent])
    def pay_with_credit(self, request):
        """
        پرداخت بخشی یا تمام یک فاکتور با استفاده از اعتبار
        POST /api/v1/financial/credit/pay-with-credit/
        {
            "invoice_id": "uuid-of-invoice",
            "amount": 50000  // مبلغی که می‌خواهد از اعتبار پرداخت کند
        }
        """
        invoice_id = request.data.get('invoice_id')
        try:
            amount = Decimal(request.data.get('amount'))
        except (TypeError, ValueError):
            return Response({'error': 'مبلغ نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not invoice_id or amount <= 0:
            return Response({'error': 'شناسه فاکتور و مبلغ الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invoice = Invoice.objects.get(id=invoice_id, student=request.user)
        except Invoice.DoesNotExist:
            return Response({'error': 'فاکتور یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        
        if invoice.is_paid:
            return Response({'error': 'این فاکتور قبلاً پرداخت شده است.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # اگر مبلغ درخواستی بیشتر از باقی‌مانده فاکتور بود، آن را محدود کن
        if amount > invoice.remaining_amount:
            amount = invoice.remaining_amount
            
        try:
            # فراخوانی سرویس برای انجام عملیات
            use_credit_for_payment(
                student=request.user, 
                amount=amount, 
                invoice=invoice
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # دریافت مجدد اطلاعات بروز شده
        invoice.refresh_from_db()
        credit_note = CreditNote.objects.get(student=request.user)
        
        return Response({
            'message': f'مبلغ {amount:,} تومان با موفقیت از اعتبار شما برای پرداخت فاکتور استفاده شد.',
            'invoice_status': invoice.status,
            'invoice_remaining_amount': invoice.remaining_amount,
            'new_credit_balance': credit_note.balance
        })

    @action(detail=False, methods=['post'], url_path='add-manual-credit', permission_classes=[IsSuperAdmin])
    def add_manual_credit(self, request):
        """
        اضافه کردن اعتبار به صورت دستی توسط ادمین
        POST /api/v1/financial/credit/add-manual-credit/
        {
            "student_id": "uuid-of-student",
            "amount": 100000,
            "description": "پاداش دانش‌آموز ممتاز"
        }
        """
        student_id = request.data.get('student_id')
        amount = Decimal(request.data.get('amount', 0))
        description = request.data.get('description')

        if not all([student_id, amount > 0, description]):
            return Response({'error': 'اطلاعات کامل نیست.'}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.accounts.models import User
        try:
            student = User.objects.get(id=student_id, role=User.UserRole.STUDENT)
        except User.DoesNotExist:
            return Response({'error': 'دانش‌آموز یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            credit_note = add_credit_to_student(
                student=student,
                amount=amount,
                description=description,
                created_by=request.user
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({
            'message': f'مبلغ {amount:,} تومان با موفقیت به اعتبار {student.get_full_name()} اضافه شد.',
            'new_balance': credit_note.balance
        })

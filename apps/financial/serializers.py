from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    CreditNote, CreditTransaction, Invoice, InvoiceItem, Payment, DiscountCoupon, CouponUsage,
    Installment, Transaction, TeacherPayment
)
from apps.accounts.serializers import UserSerializer
from apps.enrollments.serializers import AnnualRegistrationSerializer, EnrollmentListSerializer
from utils.fields import S3DocumentField


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Invoice Item Serializer
    """
    class Meta:
        model = InvoiceItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'total']


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Invoice Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    class_enrollment_details = EnrollmentListSerializer(
        source='class_enrollment', 
        read_only=True
    )
    annual_registration_details = AnnualRegistrationSerializer(
        source='annual_registration_source', 
        read_only=True
    )
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    items = InvoiceItemSerializer(many=True, read_only=True)
    
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'invoice_number',
            'total_amount', 'paid_amount', 'paid_date', 'created_by'
        ]

    def validate(self, attrs):
        # Validate dates
        issue_date = attrs.get('issue_date')
        due_date = attrs.get('due_date')
        
        if issue_date and due_date and due_date < issue_date:
            raise serializers.ValidationError({
                'due_date': 'سررسید نمی‌تواند قبل از تاریخ صدور باشد'
            })
        
        return attrs


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Simplified Invoice List Serializer
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'student_name', 'branch_name',
            'invoice_type', 'total_amount', 'paid_amount', 'status',
            'status_display', 'issue_date', 'due_date', 'is_paid', 'is_overdue'
        ]


class CreateInvoiceSerializer(serializers.Serializer):
    """
    Create Invoice with Items Serializer
    """
    student = serializers.UUIDField()
    enrollment = serializers.UUIDField(required=False, allow_null=True)
    branch = serializers.UUIDField()
    invoice_type = serializers.ChoiceField(choices=Invoice.InvoiceType.choices)
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True)
    
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    discount_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """
        Validate items list
        Expected format:
        [
            {
                "description": "شهریه دوره مقدماتی",
                "quantity": 1,
                "unit_price": 5000000
            }
        ]
        """
        for item in value:
            if 'description' not in item or 'quantity' not in item or 'unit_price' not in item:
                raise serializers.ValidationError(
                    'هر آیتم باید شامل description، quantity و unit_price باشد'
                )
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        from apps.accounts.models import User
        from apps.enrollments.models import Enrollment
        from apps.branches.models import Branch
        
        items_data = validated_data.pop('items')
        discount_code = validated_data.pop('discount_code', None)
        
        # Get related objects
        student = User.objects.get(id=validated_data.pop('student'))
        branch = Branch.objects.get(id=validated_data.pop('branch'))
        enrollment_id = validated_data.pop('enrollment', None)
        enrollment = Enrollment.objects.get(id=enrollment_id) if enrollment_id else None
        
        # Calculate subtotal
        subtotal = sum(
            item['quantity'] * item['unit_price'] 
            for item in items_data
        )
        
        # Apply discount
        discount_amount = 0
        if discount_code:
            try:
                coupon = DiscountCoupon.objects.get(
                    code=discount_code,
                    is_active=True
                )
                if coupon.is_valid() and coupon.can_use(student):
                    discount_amount = coupon.calculate_discount(subtotal)
            except DiscountCoupon.DoesNotExist:
                pass
        
        # Create invoice
        invoice = Invoice.objects.create(
            student=student,
            enrollment=enrollment,
            branch=branch,
            subtotal=subtotal,
            discount_amount=discount_amount,
            created_by=self.context.get('request').user,
            **validated_data
        )
        
        # Create items
        for item_data in items_data:
            InvoiceItem.objects.create(
                invoice=invoice,
                **item_data
            )
        
        # Record coupon usage
        if discount_code and discount_amount > 0:
            coupon = DiscountCoupon.objects.get(code=discount_code)
            CouponUsage.objects.create(
                coupon=coupon,
                user=student,
                invoice=invoice,
                discount_amount=discount_amount
            )
            coupon.current_uses += 1
            coupon.save()
        
        return invoice


class PaymentSerializer(serializers.ModelSerializer):
    """
    Payment Serializer
    
    Supports S3 upload for receipt_file:
    - Use receipt_file_id from multipart upload
    """
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # S3 file URL
    receipt_file_url = serializers.SerializerMethodField()
    
    # S3 file reference
    receipt_file_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'payment_number',
            'payment_date', 'verified_date', 'verified_by'
        ]
    
    def get_receipt_file_url(self, obj):
        if obj.receipt_file:
            try:
                from utils.storage import get_s3_upload_manager
                manager = get_s3_upload_manager()
                return manager.get_file_url(obj.receipt_file.name)
            except Exception:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.receipt_file.url)
        return None
    
    def validate(self, attrs):
        from apps.core.models import UploadedFile
        
        receipt_file_id = attrs.pop('receipt_file_id', None)
        if receipt_file_id:
            try:
                uploaded_file = UploadedFile.objects.get(id=receipt_file_id)
                attrs['receipt_file'] = uploaded_file.s3_key
                uploaded_file.is_temp = False
                uploaded_file.save()
            except UploadedFile.DoesNotExist:
                raise serializers.ValidationError({'receipt_file_id': 'فایل پیدا نشد'})
        
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    """
    Verify Payment Serializer
    """
    payment_id = serializers.UUIDField()
    tracking_code = serializers.CharField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class DiscountCouponSerializer(serializers.ModelSerializer):
    """
    Discount Coupon Serializer
    """
    discount_type_display = serializers.CharField(
        source='get_discount_type_display',
        read_only=True
    )
    is_valid_now = serializers.SerializerMethodField()
    remaining_uses = serializers.SerializerMethodField()
    
    class Meta:
        model = DiscountCoupon
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_uses', 'created_by']
    
    def get_is_valid_now(self, obj):
        return obj.is_valid()
    
    def get_remaining_uses(self, obj):
        if obj.max_uses:
            return obj.max_uses - obj.current_uses
        return None


class ValidateCouponSerializer(serializers.Serializer):
    """
    Validate Coupon Serializer
    """
    code = serializers.CharField()
    user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    
    def validate(self, attrs):
        from apps.accounts.models import User
        
        try:
            coupon = DiscountCoupon.objects.get(
                code=attrs['code'],
                is_active=True
            )
        except DiscountCoupon.DoesNotExist:
            raise serializers.ValidationError({'code': 'کد تخفیف نامعتبر است'})
        
        if not coupon.is_valid():
            raise serializers.ValidationError({'code': 'کد تخفیف منقضی شده است'})
        
        try:
            user = User.objects.get(id=attrs['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'user_id': 'کاربر یافت نشد'})
        
        if not coupon.can_use(user):
            raise serializers.ValidationError({
                'code': 'شما قبلاً از این کد استفاده کرده‌اید'
            })
        
        amount = attrs['amount']
        if coupon.min_purchase_amount and amount < coupon.min_purchase_amount:
            raise serializers.ValidationError({
                'amount': f'حداقل مبلغ خرید {coupon.min_purchase_amount} تومان است'
            })
        
        attrs['coupon'] = coupon
        attrs['discount_amount'] = coupon.calculate_discount(amount)
        
        return attrs


class InstallmentSerializer(serializers.ModelSerializer):
    """
    Installment Serializer
    """
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Installment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'paid_date']


class CreateInstallmentPlanSerializer(serializers.Serializer):
    """
    Create Installment Plan Serializer
    """
    invoice = serializers.UUIDField()
    number_of_installments = serializers.IntegerField(min_value=2, max_value=12)
    first_installment_date = serializers.DateField()
    installment_interval_days = serializers.IntegerField(default=30, min_value=1)
    
    @transaction.atomic
    def create(self, validated_data):
        from datetime import timedelta
        
        invoice = Invoice.objects.get(id=validated_data['invoice'])
        num_installments = validated_data['number_of_installments']
        first_date = validated_data['first_installment_date']
        interval = validated_data['installment_interval_days']
        
        # Delete existing installments
        invoice.installments.all().delete()
        
        # Calculate installment amount
        amount_per_installment = invoice.total_amount / num_installments
        
        installments = []
        for i in range(num_installments):
            due_date = first_date + timedelta(days=interval * i)
            
            installment = Installment.objects.create(
                invoice=invoice,
                installment_number=i + 1,
                amount=amount_per_installment,
                due_date=due_date
            )
            installments.append(installment)
        
        return installments


class TransactionSerializer(serializers.ModelSerializer):
    """
    Transaction Serializer
    
    Supports S3 upload for receipt_file:
    - Use receipt_file_id from multipart upload
    """
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    # S3 file URL
    receipt_file_url = serializers.SerializerMethodField()
    
    # S3 file reference
    receipt_file_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'transaction_number']
    
    def get_receipt_file_url(self, obj):
        if obj.receipt_file:
            try:
                from utils.storage import get_s3_upload_manager
                manager = get_s3_upload_manager()
                return manager.get_file_url(obj.receipt_file.name)
            except Exception:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.receipt_file.url)
        return None
    
    def validate(self, attrs):
        from apps.core.models import UploadedFile
        
        receipt_file_id = attrs.pop('receipt_file_id', None)
        if receipt_file_id:
            try:
                uploaded_file = UploadedFile.objects.get(id=receipt_file_id)
                attrs['receipt_file'] = uploaded_file.s3_key
                uploaded_file.is_temp = False
                uploaded_file.save()
            except UploadedFile.DoesNotExist:
                raise serializers.ValidationError({'receipt_file_id': 'فایل پیدا نشد'})
        
        return attrs


class TeacherPaymentSerializer(serializers.ModelSerializer):
    """
    Teacher Payment Serializer
    """
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TeacherPayment
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'payment_number',
            'total_amount', 'approved_by', 'approved_date'
        ]


class FinancialReportSerializer(serializers.Serializer):
    """
    Financial Report Serializer
    """
    total_income = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=0)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    pending_invoices = serializers.IntegerField()
    total_payments = serializers.IntegerField()
    overdue_invoices = serializers.IntegerField()
    total_outstanding = serializers.DecimalField(max_digits=12, decimal_places=0)
    
    
class CreditTransactionSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای تاریخچه تراکنش‌های اعتبار
    """
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    source_invoice_number = serializers.CharField(
        source='source_invoice.invoice_number',
        read_only=True
    )

    class Meta:
        model = CreditTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display',
            'amount', 'balance_after', 'description',
            'source_invoice', 'source_invoice_number',
            'created_by', 'created_by_name',
            'created_at'
        ]
        read_only_fields = fields


class CreditNoteSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای نمایش اعتبار و تاریخچه آن
    """
    student_details = UserSerializer(source='student', read_only=True)
    transactions = CreditTransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = CreditNote
        fields = [
            'id', 'student', 'student_details', 'balance', 'transactions', 'updated_at'
        ]
        read_only_fields = fields
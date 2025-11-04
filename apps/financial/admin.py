from django.contrib import admin
from .models import (
    Invoice, InvoiceItem, Payment, DiscountCoupon, CouponUsage,
    Installment, Transaction, TeacherPayment
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ['total']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'student', 'branch', 'invoice_type',
        'total_amount', 'paid_amount', 'status', 'issue_date', 'is_paid'
    ]
    list_filter = ['invoice_type', 'status', 'issue_date', 'branch']
    search_fields = [
        'invoice_number', 'student__first_name',
        'student__last_name', 'description'
    ]
    readonly_fields = ['invoice_number', 'total_amount', 'paid_date']
    ordering = ['-issue_date']
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('invoice_number', 'student', 'enrollment', 'branch', 'invoice_type')
        }),
        ('مبالغ', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount')
        }),
        ('تاریخ‌ها', {
            'fields': ('issue_date', 'due_date', 'paid_date')
        }),
        ('وضعیت', {
            'fields': ('status',)
        }),
        ('توضیحات', {
            'fields': ('description', 'notes')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_number', 'invoice', 'student', 'amount',
        'payment_method', 'status', 'payment_date'
    ]
    list_filter = ['payment_method', 'status', 'payment_date']
    search_fields = [
        'payment_number', 'gateway_transaction_id',
        'gateway_reference_id', 'student__first_name'
    ]
    readonly_fields = ['payment_number', 'payment_date', 'verified_date']
    ordering = ['-payment_date']


@admin.register(DiscountCoupon)
class DiscountCouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'discount_type', 'discount_value',
        'current_uses', 'max_uses', 'is_active', 'valid_from', 'valid_until'
    ]
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'name', 'description']
    filter_horizontal = ['applicable_courses', 'applicable_branches']
    ordering = ['-created_at']


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = [
        'coupon', 'user', 'invoice', 'discount_amount', 'used_at'
    ]
    list_filter = ['used_at']
    search_fields = ['coupon__code', 'user__first_name', 'invoice__invoice_number']
    ordering = ['-used_at']


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice', 'installment_number', 'amount',
        'due_date', 'status', 'paid_date'
    ]
    list_filter = ['status', 'due_date']
    search_fields = ['invoice__invoice_number']
    ordering = ['invoice', 'installment_number']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_number', 'branch', 'transaction_type',
        'category', 'amount', 'date'
    ]
    list_filter = ['transaction_type', 'category', 'branch', 'date']
    search_fields = ['transaction_number', 'description', 'reference']
    readonly_fields = ['transaction_number']
    ordering = ['-date']


@admin.register(TeacherPayment)
class TeacherPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_number', 'teacher', 'from_date', 'to_date',
        'total_hours', 'total_amount', 'status'
    ]
    list_filter = ['status', 'from_date', 'to_date']
    search_fields = ['payment_number', 'teacher__first_name', 'teacher__last_name']
    readonly_fields = ['payment_number', 'total_amount']
    ordering = ['-from_date']
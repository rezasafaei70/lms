from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InvoiceViewSet, PaymentViewSet, DiscountCouponViewSet,
    InstallmentViewSet, TransactionViewSet, TeacherPaymentViewSet,
    FinancialReportViewSet
)

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoices')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'coupons', DiscountCouponViewSet, basename='coupons')
router.register(r'installments', InstallmentViewSet, basename='installments')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'teacher-payments', TeacherPaymentViewSet, basename='teacher-payments')
router.register(r'reports', FinancialReportViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]
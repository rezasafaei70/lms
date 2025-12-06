from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CreditNoteViewSet, InvoiceViewSet, PaymentViewSet, DiscountCouponViewSet,
    InstallmentViewSet, TransactionViewSet, TeacherPaymentViewSet,
    FinancialReportViewSet, SadadPaymentView
)

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoices')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'coupons', DiscountCouponViewSet, basename='coupons')
router.register(r'installments', InstallmentViewSet, basename='installments')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'teacher-payments', TeacherPaymentViewSet, basename='teacher-payments')
router.register(r'reports', FinancialReportViewSet, basename='reports')
router.register(r'credit', CreditNoteViewSet, basename='credit') 

# Sadad Payment Gateway URLs
sadad_view = SadadPaymentView.as_view()

urlpatterns = [
    path('', include(router.urls)),
    # Sadad Payment Gateway
    path('payment/initiate/', sadad_view, {'action': 'initiate'}, name='payment-initiate'),
    path('payment/simulate/', sadad_view, {'action': 'simulate'}, name='payment-simulate'),
    path('payment/simulate-confirm/', sadad_view, {'action': 'simulate-confirm'}, name='payment-simulate-confirm'),
    path('payment/callback/', sadad_view, {'action': 'callback'}, name='payment-callback'),
    path('payment/verify/<uuid:invoice_id>/', sadad_view, {'action': 'verify'}, name='payment-verify'),
]
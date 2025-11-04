from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeadViewSet, LeadActivityViewSet, CampaignViewSet,
    CustomerFeedbackViewSet, LoyaltyProgramViewSet,
    CustomerLoyaltyPointsViewSet, ReferralViewSet
)

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='leads')
router.register(r'lead-activities', LeadActivityViewSet, basename='lead-activities')
router.register(r'campaigns', CampaignViewSet, basename='campaigns')
router.register(r'feedbacks', CustomerFeedbackViewSet, basename='feedbacks')
router.register(r'loyalty-programs', LoyaltyProgramViewSet, basename='loyalty-programs')
router.register(r'loyalty-points', CustomerLoyaltyPointsViewSet, basename='loyalty-points')
router.register(r'referrals', ReferralViewSet, basename='referrals')

urlpatterns = [
    path('', include(router.urls)),
]
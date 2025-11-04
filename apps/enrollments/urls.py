from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnrollmentViewSet, PlacementTestViewSet, WaitingListViewSet,
    EnrollmentTransferViewSet, AnnualRegistrationViewSet,
    EnrollmentDocumentViewSet
)

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet, basename='enrollments')
router.register(r'placement-tests', PlacementTestViewSet, basename='placement-tests')
router.register(r'waiting-lists', WaitingListViewSet, basename='waiting-lists')
router.register(r'transfers', EnrollmentTransferViewSet, basename='transfers')
router.register(r'annual-registrations', AnnualRegistrationViewSet, basename='annual-registrations')
router.register(r'documents', EnrollmentDocumentViewSet, basename='documents')

urlpatterns = [
    path('', include(router.urls)),
]
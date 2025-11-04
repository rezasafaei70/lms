from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceViewSet, AttendanceReportViewSet

router = DefaultRouter()
router.register(r'attendances', AttendanceViewSet, basename='attendances')
router.register(r'reports', AttendanceReportViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]
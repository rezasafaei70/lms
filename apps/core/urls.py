"""
Core App URLs - File Upload API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileUploadViewSet

router = DefaultRouter()
router.register(r'files', FileUploadViewSet, basename='files')

urlpatterns = [
    path('', include(router.urls)),
]


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BranchViewSet, ClassroomViewSet, BranchStaffViewSet

router = DefaultRouter()
router.register(r'branches', BranchViewSet, basename='branches')
router.register(r'classrooms', ClassroomViewSet, basename='classrooms')
router.register(r'staff', BranchStaffViewSet, basename='staff')

urlpatterns = [
    path('', include(router.urls)),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, UserViewSet, StudentProfileViewSet,
    TeacherProfileViewSet, LoginHistoryViewSet
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'students', StudentProfileViewSet, basename='students')
router.register(r'teachers', TeacherProfileViewSet, basename='teachers')
router.register(r'login-history', LoginHistoryViewSet, basename='login-history')

urlpatterns = [
    path('', include(router.urls)),
]
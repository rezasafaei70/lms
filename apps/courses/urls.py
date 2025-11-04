from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, ClassViewSet, ClassSessionViewSet,
    TermViewSet, TeacherReviewViewSet
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='courses')
router.register(r'classes', ClassViewSet, basename='classes')
router.register(r'sessions', ClassSessionViewSet, basename='sessions')
router.register(r'terms', TermViewSet, basename='terms')
router.register(r'reviews', TeacherReviewViewSet, basename='reviews')

urlpatterns = [
    path('', include(router.urls)),
]
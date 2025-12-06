from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, ClassViewSet, ClassSessionViewSet, PrivateClassPricingViewSet, PrivateClassRequestViewSet,
    SubjectViewSet, TermViewSet, TeacherReviewViewSet
)

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subjects')
router.register(r'courses', CourseViewSet, basename='courses')
router.register(r'classes', ClassViewSet, basename='classes')
router.register(r'sessions', ClassSessionViewSet, basename='sessions')
router.register(r'terms', TermViewSet, basename='terms')
router.register(r'reviews', TeacherReviewViewSet, basename='reviews')
router.register(r'private-requests', PrivateClassRequestViewSet, basename='private-requests')
router.register(r'private-pricing', PrivateClassPricingViewSet, basename='private-pricing')

urlpatterns = [
    path('', include(router.urls)),
]
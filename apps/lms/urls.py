from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseMaterialViewSet, AssignmentViewSet, AssignmentSubmissionViewSet,
    OnlineSessionViewSet
)

router = DefaultRouter()
router.register(r'materials', CourseMaterialViewSet, basename='materials')
router.register(r'assignments', AssignmentViewSet, basename='assignments')
router.register(r'submissions', AssignmentSubmissionViewSet, basename='submissions')
router.register(r'online-sessions', OnlineSessionViewSet, basename='online-sessions')

urlpatterns = [
    path('', include(router.urls)),
]
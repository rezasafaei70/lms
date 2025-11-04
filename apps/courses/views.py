from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Avg, F

from .models import Course, Class, ClassSession, Term, TeacherReview
from .serializers import (
    CourseSerializer, CourseListSerializer, ClassSerializer,
    ClassListSerializer, ClassSessionSerializer, TermSerializer,
    TeacherReviewSerializer, CourseStatisticsSerializer
)
from utils.permissions import IsSuperAdmin, IsTeacher, IsStudent
from utils.pagination import StandardResultsSetPagination


class CourseViewSet(viewsets.ModelViewSet):
    """
    Course ViewSet
    """
    queryset = Course.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'status', 'is_featured', 'provides_certificate']
    search_fields = ['name', 'code', 'description', 'short_description']
    ordering_fields = ['name', 'created_at', 'base_price', 'average_rating', 'total_enrollments']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter active courses for non-admin users
        user = self.request.user
        if not user.is_authenticated or user.role not in [
            user.UserRole.SUPER_ADMIN,
            user.UserRole.BRANCH_MANAGER
        ]:
            queryset = queryset.filter(status=Course.CourseStatus.ACTIVE)
        
        return queryset

    @action(detail=False, methods=['get'], url_path='featured')
    def featured_courses(self, request):
        """
        Get featured courses
        GET /api/v1/courses/courses/featured/
        """
        courses = self.get_queryset().filter(
            is_featured=True,
            status=Course.CourseStatus.ACTIVE
        ).order_by('-average_rating')[:10]
        
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='popular')
    def popular_courses(self, request):
        """
        Get popular courses
        GET /api/v1/courses/courses/popular/
        """
        courses = self.get_queryset().filter(
            status=Course.CourseStatus.ACTIVE
        ).order_by('-total_enrollments', '-average_rating')[:10]
        
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='classes')
    def get_classes(self, request, slug=None):
        """
        Get all classes for a course
        GET /api/v1/courses/courses/{slug}/classes/
        """
        course = self.get_object()
        classes = Class.objects.filter(
            course=course,
            is_deleted=False
        ).select_related('branch', 'teacher', 'classroom')
        
        # Filter parameters
        branch = request.query_params.get('branch')
        class_type = request.query_params.get('type')
        available_only = request.query_params.get('available', 'false').lower() == 'true'
        
        if branch:
            classes = classes.filter(branch_id=branch)
        if class_type:
            classes = classes.filter(class_type=class_type)
        if available_only:
            classes = classes.filter(
                is_registration_open=True,
                status=Class.ClassStatus.SCHEDULED,
                current_enrollments__lt=F('capacity')
            )
        
        serializer = ClassListSerializer(classes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='reviews')
    def get_reviews(self, request, slug=None):
        """
        Get course reviews
        GET /api/v1/courses/courses/{slug}/reviews/
        """
        course = self.get_object()
        
        # Get reviews from all classes of this course
        reviews = TeacherReview.objects.filter(
            class_obj__course=course,
            is_approved=True
        ).select_related('student', 'teacher', 'class_obj')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = TeacherReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TeacherReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get course statistics
        GET /api/v1/courses/courses/statistics/
        """
        stats = {
            'total_courses': Course.objects.count(),
            'active_courses': Course.objects.filter(
                status=Course.CourseStatus.ACTIVE
            ).count(),
            'total_classes': Class.objects.count(),
            'ongoing_classes': Class.objects.filter(
                status=Class.ClassStatus.ONGOING
            ).count(),
            'total_enrollments': Course.objects.aggregate(
                total=Count('classes__enrollments')
            )['total'] or 0,
            'popular_courses': CourseListSerializer(
                Course.objects.filter(
                    status=Course.CourseStatus.ACTIVE
                ).order_by('-total_enrollments')[:5],
                many=True
            ).data
        }
        
        serializer = CourseStatisticsSerializer(stats)
        return Response(serializer.data)


class ClassViewSet(viewsets.ModelViewSet):
    """
    Class ViewSet
    """
    queryset = Class.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'course', 'branch', 'teacher', 'class_type',
        'status', 'is_registration_open'
    ]
    search_fields = ['name', 'code', 'course__name']
    ordering_fields = ['start_date', 'created_at', 'price']

    def get_serializer_class(self):
        if self.action == 'list':
            return ClassListSerializer
        return ClassSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'course', 'branch', 'teacher', 'classroom'
        )
        
        user = self.request.user
        
        # Teachers see their classes
        if user.is_authenticated and user.role == user.UserRole.TEACHER:
            if self.action not in ['list', 'retrieve']:
                queryset = queryset.filter(teacher=user)
        
        return queryset

    @action(detail=True, methods=['get'], url_path='sessions')
    def get_sessions(self, request, pk=None):
        """
        Get all sessions of a class
        GET /api/v1/courses/classes/{id}/sessions/
        """
        class_obj = self.get_object()
        sessions = class_obj.sessions.all()
        
        serializer = ClassSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='generate-sessions')
    def generate_sessions(self, request, pk=None):
        """
        Auto-generate sessions for a class
        POST /api/v1/courses/classes/{id}/generate-sessions/
        """
        class_obj = self.get_object()
        
        # Delete existing sessions
        class_obj.sessions.all().delete()
        
        # Generate sessions based on schedule
        from datetime import datetime, timedelta
        from apps.courses.utils import generate_class_sessions
        
        sessions = generate_class_sessions(class_obj)
        
        return Response({
            'message': f'{len(sessions)} جلسه با موفقیت ایجاد شد',
            'sessions': ClassSessionSerializer(sessions, many=True).data
        })

    @action(detail=True, methods=['get'], url_path='bbb-join-url')
    def get_bbb_join_url(self, request, pk=None):
        """
        Get BigBlueButton join URL
        GET /api/v1/courses/classes/{id}/bbb-join-url/
        """
        class_obj = self.get_object()
        user = request.user
        
        if not class_obj.is_online:
            return Response({
                'error': 'این کلاس آنلاین نیست'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate BBB join URL
        from apps.lms.utils import get_bbb_join_url
        
        is_moderator = user == class_obj.teacher or user.is_superuser
        join_url = get_bbb_join_url(
            class_obj,
            user,
            is_moderator=is_moderator
        )
        
        return Response({
            'join_url': join_url,
            'meeting_id': class_obj.bbb_meeting_id,
            'is_moderator': is_moderator
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_class(self, request, pk=None):
        """
        Cancel a class
        POST /api/v1/courses/classes/{id}/cancel/
        {
            "reason": "دلیل لغو"
        }
        """
        class_obj = self.get_object()
        reason = request.data.get('reason', '')
        
        class_obj.status = Class.ClassStatus.CANCELLED
        class_obj.description = f"لغو شده: {reason}\n\n{class_obj.description or ''}"
        class_obj.save()
        
        # Send notification to students
        # این قسمت بعداً با notification کامل می‌شود
        
        return Response({
            'message': 'کلاس با موفقیت لغو شد'
        })

    @action(detail=False, methods=['get'], url_path='my-classes')
    def my_classes(self, request):
        """
        Get classes of current user (teacher or student)
        GET /api/v1/courses/classes/my-classes/
        """
        user = request.user
        
        if user.role == user.UserRole.TEACHER:
            classes = self.get_queryset().filter(teacher=user)
        elif user.role == user.UserRole.STUDENT:
            # بعداً با enrollment کامل می‌شود
            classes = Class.objects.none()
        else:
            return Response({
                'error': 'شما دسترسی به این بخش ندارید'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(classes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='available')
    def available_classes(self, request):
        """
        Get available classes for enrollment
        GET /api/v1/courses/classes/available/
        """
        classes = self.get_queryset().filter(
            status=Class.ClassStatus.SCHEDULED,
            is_registration_open=True,
            current_enrollments__lt=F('capacity'),
            start_date__gte=timezone.now().date()
        )
        
        serializer = self.get_serializer(classes, many=True)
        return Response(serializer.data)
    @action(detail=True, methods=['get'], url_path='materials')
    def class_materials(self, request, pk=None):
        """
        Get class materials
        GET /api/v1/courses/classes/{id}/materials/
        """
        from apps.lms.serializers import CourseMaterialSerializer
        
        class_obj = self.get_object()
        materials = class_obj.course_materials.filter(is_deleted=False).order_by('order')
        
        serializer = CourseMaterialSerializer(materials, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='assignments')
    def class_assignments(self, request, pk=None):
        """
        Get class assignments
        GET /api/v1/courses/classes/{id}/assignments/
        """
        from apps.lms.serializers import AssignmentSerializer
        
        class_obj = self.get_object()
        assignments = class_obj.class_assignments.filter(
            is_deleted=False,
            is_published=True
        ).order_by('-due_date')
        
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

class ClassSessionViewSet(viewsets.ModelViewSet):
    """
    Class Session ViewSet
    """
    queryset = ClassSession.objects.all()
    serializer_class = ClassSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['class_obj', 'status', 'attendance_taken']
    ordering_fields = ['date', 'session_number']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsTeacher()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='start')
    def start_session(self, request, pk=None):
        """
        Start a session
        POST /api/v1/courses/sessions/{id}/start/
        """
        session = self.get_object()
        
        session.status = ClassSession.SessionStatus.IN_PROGRESS
        session.bbb_started_at = timezone.now()
        session.save()
        
        return Response({
            'message': 'جلسه شروع شد'
        })

    @action(detail=True, methods=['post'], url_path='end')
    def end_session(self, request, pk=None):
        """
        End a session
        POST /api/v1/courses/sessions/{id}/end/
        """
        session = self.get_object()
        
        session.status = ClassSession.SessionStatus.COMPLETED
        session.bbb_ended_at = timezone.now()
        session.save()
        
        return Response({
            'message': 'جلسه به پایان رسید'
        })


class TermViewSet(viewsets.ModelViewSet):
    """
    Term ViewSet
    """
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'code']
    ordering_fields = ['start_date', 'created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='current')
    def current_term(self, request):
        """
        Get current active term
        GET /api/v1/courses/terms/current/
        """
        today = timezone.now().date()
        term = Term.objects.filter(
            status=Term.TermStatus.ACTIVE,
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if not term:
            return Response({
                'error': 'ترم فعالی یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(term)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming_terms(self, request):
        """
        Get upcoming terms
        GET /api/v1/courses/terms/upcoming/
        """
        terms = self.get_queryset().filter(
            status=Term.TermStatus.UPCOMING
        ).order_by('start_date')
        
        serializer = self.get_serializer(terms, many=True)
        return Response(serializer.data)


class TeacherReviewViewSet(viewsets.ModelViewSet):
    """
    Teacher Review ViewSet
    """
    queryset = TeacherReview.objects.all()
    serializer_class = TeacherReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['teacher', 'is_approved', 'rating']
    ordering_fields = ['created_at', 'rating']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students see their own reviews
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Teachers see reviews about them
        elif user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(teacher=user, is_approved=True)
        # Others see approved reviews only
        elif user.role not in [user.UserRole.SUPER_ADMIN, user.UserRole.BRANCH_MANAGER]:
            queryset = queryset.filter(is_approved=True)
        
        return queryset.select_related('student', 'teacher', 'class_obj')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve', permission_classes=[IsSuperAdmin])
    def approve_review(self, request, pk=None):
        """
        Approve a review
        POST /api/v1/courses/reviews/{id}/approve/
        """
        review = self.get_object()
        
        review.is_approved = True
        review.approved_by = request.user
        review.approved_at = timezone.now()
        review.save()
        
        return Response({
            'message': 'نظر تایید شد'
        })

    @action(detail=True, methods=['post'], url_path='reject', permission_classes=[IsSuperAdmin])
    def reject_review(self, request, pk=None):
        """
        Reject a review
        POST /api/v1/courses/reviews/{id}/reject/
        """
        review = self.get_object()
        review.delete()
        
        return Response({
            'message': 'نظر رد شد'
        })

    @action(detail=False, methods=['get'], url_path='pending', permission_classes=[IsSuperAdmin])
    def pending_reviews(self, request):
        """
        Get pending reviews
        GET /api/v1/courses/reviews/pending/
        """
        reviews = self.get_queryset().filter(is_approved=False)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
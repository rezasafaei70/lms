from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models, transaction as db_transaction
from django.db.models import Q, Count, Avg, F
from datetime import datetime, timedelta

from .models import Course, Class, ClassSession, PrivateClassPricing, PrivateClassRequest, Subject, Term, TeacherReview
from .serializers import (
    ApprovePrivateClassSerializer, CourseSerializer, CourseListSerializer, ClassSerializer,
    ClassListSerializer, ClassSessionSerializer, CreateClassFromRequestSerializer, PrivateClassPricingSerializer, PrivateClassRequestListSerializer, PrivateClassRequestSerializer, SubjectSerializer, TermSerializer,
    TeacherReviewSerializer, CourseStatisticsSerializer
)
from utils.permissions import IsSuperAdmin, IsTeacher, IsStudent
from utils.pagination import StandardResultsSetPagination


class SubjectViewSet(viewsets.ModelViewSet):
    """
    Subject (درس) ViewSet
    """
    queryset = Subject.objects.filter(is_deleted=False)
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grade_level', 'is_active']
    search_fields = ['title', 'code', 'description']
    ordering_fields = ['title', 'created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='active')
    def active_subjects(self, request):
        """
        Get active subjects
        GET /api/v1/courses/subjects/active/
        """
        subjects = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(subjects, many=True)
        return Response(serializer.data)


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

    @action(detail=True, methods=['get'], url_path='students')
    def get_students(self, request, pk=None):
        """
        Get all students enrolled in a class
        GET /api/v1/courses/classes/{id}/students/
        """
        from apps.enrollments.models import Enrollment
        from apps.accounts.serializers import UserSerializer
        
        class_obj = self.get_object()
        enrollments = Enrollment.objects.filter(
            class_obj=class_obj,
            status__in=[
                Enrollment.EnrollmentStatus.ACTIVE,
                Enrollment.EnrollmentStatus.APPROVED,
                Enrollment.EnrollmentStatus.COMPLETED
            ]
        ).select_related('student')
        
        students = []
        for enrollment in enrollments:
            student_data = UserSerializer(enrollment.student).data
            # Add student_name for frontend compatibility
            student_data['student_name'] = enrollment.student.get_full_name() or enrollment.student.mobile
            student_data['student_number'] = enrollment.student.national_code or enrollment.student.mobile
            student_data['enrollment_id'] = str(enrollment.id)
            student_data['enrollment_status'] = enrollment.status
            student_data['enrollment_date'] = enrollment.enrollment_date
            student_data['paid_amount'] = float(enrollment.paid_amount)
            student_data['is_paid'] = enrollment.is_paid
            students.append(student_data)
        
        return Response(students)

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
        {
            "max_sessions": 10  // اختیاری - تعداد جلسات (اگر نباشد از تعداد جلسات دوره استفاده می‌شود)
        }
        """
        class_obj = self.get_object()
        
        # دریافت حداکثر تعداد جلسات از درخواست
        max_sessions = request.data.get('max_sessions')
        if max_sessions:
            try:
                max_sessions = int(max_sessions)
            except (ValueError, TypeError):
                max_sessions = None
        
        # Delete existing sessions
        class_obj.sessions.all().delete()
        
        # Generate sessions based on schedule
        from apps.courses.utils import generate_class_sessions
        
        sessions = generate_class_sessions(class_obj, max_sessions=max_sessions)
        
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
    

class PrivateClassPricingViewSet(viewsets.ModelViewSet):
    """
    مدیریت قیمت‌گذاری کلاس‌های خصوصی
    """
    queryset = PrivateClassPricing.objects.all()
    serializer_class = PrivateClassPricingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['class_type', 'is_active']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'calculate']:
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    @action(detail=False, methods=['get'], url_path='active')
    def active_pricing(self, request):
        """
        دریافت قیمت‌های فعال
        GET /api/v1/courses/private-pricing/active/
        """
        pricing = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(pricing, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate_price(self, request):
        """
        محاسبه قیمت
        POST /api/v1/courses/private-pricing/calculate/
        {
            "class_type": "private",
            "total_sessions": 24
        }
        """
        class_type = request.data.get('class_type')
        total_sessions = int(request.data.get('total_sessions', 24))
        
        try:
            pricing = PrivateClassPricing.objects.get(
                class_type=class_type,
                is_active=True
            )
        except PrivateClassPricing.DoesNotExist:
            return Response({
                'error': 'قیمت‌گذاری برای این نوع کلاس یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        result = pricing.calculate_total(total_sessions)
        result['class_type'] = class_type
        result['class_type_display'] = pricing.get_class_type_display()
        result['price_per_session'] = pricing.price_per_session
        result['total_sessions'] = total_sessions
        
        return Response(result)


class PrivateClassRequestViewSet(viewsets.ModelViewSet):
    """
    مدیریت درخواست‌های کلاس خصوصی
    """
    queryset = PrivateClassRequest.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'class_type', 'branch', 'course']
    search_fields = [
        'request_number', 'primary_student__first_name',
        'primary_student__last_name'
    ]
    ordering_fields = ['created_at', 'preferred_start_date', 'status']

    def get_serializer_class(self):
        if self.action == 'list':
            return PrivateClassRequestListSerializer
        elif self.action == 'approve':
            return ApprovePrivateClassSerializer
        elif self.action == 'create_class':
            return CreateClassFromRequestSerializer
        return PrivateClassRequestSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'primary_student', 'course', 'branch',
            'preferred_teacher', 'assigned_teacher', 'created_class'
        ).prefetch_related('additional_students')
        
        # دانش‌آموزان فقط درخواست‌های خود
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(
                Q(primary_student=user) | 
                Q(additional_students=user)
            )
        # مدیران شعبه فقط شعبه خود
        elif user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(branch__manager=user)
        
        return queryset

    def perform_create(self, serializer):
        # دانش‌آموزان فقط می‌توانند برای خود درخواست بدهند
        if self.request.user.role == self.request.user.UserRole.STUDENT:
            serializer.save(primary_student=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        تایید درخواست کلاس خصوصی
        POST /api/v1/courses/private-requests/{id}/approve/
        {
            "teacher": "teacher_id",
            "custom_price_per_session": 600000,  // optional
            "discount_percent": 5,  // optional
            "admin_notes": "..."  // optional
        }
        """
        private_request = self.get_object()
        
        if private_request.status != PrivateClassRequest.RequestStatus.PENDING:
            return Response({
                'error': 'فقط درخواست‌های در انتظار قابل تایید هستند'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ApprovePrivateClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # دریافت معلم
        from apps.accounts.models import User
        try:
            teacher = User.objects.get(
                id=serializer.validated_data['teacher'],
                role=User.UserRole.TEACHER
            )
        except User.DoesNotExist:
            return Response({
                'error': 'معلم یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # محاسبه قیمت
        custom_price = serializer.validated_data.get('custom_price_per_session')
        discount_percent = serializer.validated_data.get('discount_percent', 0)
        
        if custom_price:
            # استفاده از قیمت سفارشی
            price_per_session = custom_price
        else:
            # استفاده از جدول قیمت
            try:
                pricing = PrivateClassPricing.objects.get(
                    class_type=private_request.class_type,
                    is_active=True
                )
                price_calculation = pricing.calculate_total(private_request.total_sessions)
                price_per_session = pricing.price_per_session
                # اعمال تخفیف خودکار
                if discount_percent == 0:
                    discount_percent = price_calculation['discount_percent']
            except PrivateClassPricing.DoesNotExist:
                return Response({
                    'error': 'قیمت‌گذاری یافت نشد. لطفاً قیمت سفارشی وارد کنید'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # محاسبه مبالغ
        subtotal = price_per_session * private_request.total_sessions
        discount_amount = (subtotal * discount_percent) / 100
        final_amount = subtotal - discount_amount
        
        with db_transaction.atomic():
            # بروزرسانی درخواست
            private_request.assigned_teacher = teacher
            private_request.status = PrivateClassRequest.RequestStatus.APPROVED
            private_request.approved_by = request.user
            private_request.approved_at = timezone.now()
            private_request.admin_notes = serializer.validated_data.get('admin_notes', '')
            private_request.save()
            
            # ایجاد فاکتور
            from apps.financial.models import Invoice, InvoiceItem
            
            invoice = Invoice.objects.create(
                student=private_request.primary_student,
                branch=private_request.branch,
                invoice_type=Invoice.InvoiceType.TUITION,
                subtotal=subtotal,
                discount_amount=discount_amount,
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=7),
                created_by=request.user,
                description=f'کلاس خصوصی {private_request.course.name} - {private_request.get_class_type_display()}'
            )
            
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f'کلاس خصوصی {private_request.course.name}',
                quantity=private_request.total_sessions,
                unit_price=price_per_session,
                discount=discount_amount
            )
            
            # ارسال نوتیفیکیشن
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=private_request.primary_student,
                title='تایید درخواست کلاس خصوصی',
                message=f'درخواست کلاس خصوصی شما تایید شد. مبلغ قابل پرداخت: {final_amount:,} تومان',
                notification_type=Notification.NotificationType.SUCCESS,
                category=Notification.NotificationCategory.ENROLLMENT,
                action_url=f'/invoices/{invoice.id}/'
            )
        
        return Response({
            'message': 'درخواست تایید شد',
            'invoice_id': str(invoice.id),
            'total_amount': final_amount,
            'request': PrivateClassRequestSerializer(private_request).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        رد درخواست
        POST /api/v1/courses/private-requests/{id}/reject/
        {
            "rejection_reason": "دلیل رد"
        }
        """
        private_request = self.get_object()
        
        private_request.status = PrivateClassRequest.RequestStatus.REJECTED
        private_request.rejection_reason = request.data.get('rejection_reason', '')
        private_request.save()
        
        # ارسال نوتیفیکیشن
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=private_request.primary_student,
            title='رد درخواست کلاس خصوصی',
            message=f'متاسفانه درخواست کلاس خصوصی شما رد شد.\nدلیل: {private_request.rejection_reason}',
            notification_type=Notification.NotificationType.ERROR,
            category=Notification.NotificationCategory.ENROLLMENT
        )
        
        return Response({
            'message': 'درخواست رد شد'
        })

    @action(detail=True, methods=['post'], url_path='create-class')
    def create_class(self, request, pk=None):
        """
        ایجاد کلاس از درخواست تایید شده
        POST /api/v1/courses/private-requests/{id}/create-class/
        {
            "start_date": "2024-01-15",
            "schedule_days": ["saturday", "monday"],
            "start_time": "10:00",
            "classroom": "classroom_id"  // optional
        }
        """
        private_request = self.get_object()
        
        # بررسی وضعیت
        if private_request.status != PrivateClassRequest.RequestStatus.APPROVED:
            return Response({
                'error': 'فقط درخواست‌های تایید شده قابل ایجاد کلاس هستند'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # بررسی پرداخت
        try:
            invoice = Invoice.objects.get(
                student=private_request.primary_student,
                description__contains=f'کلاس خصوصی {private_request.course.name}'
            )
            if not invoice.is_paid:
                return Response({
                    'error': 'ابتدا باید شهریه پرداخت شود',
                    'invoice_id': str(invoice.id)
                }, status=status.HTTP_400_BAD_REQUEST)
        except Invoice.DoesNotExist:
            return Response({
                'error': 'فاکتور یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateClassFromRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # محاسبه تاریخ پایان
        start_date = serializer.validated_data['start_date']
        sessions_per_week = private_request.sessions_per_week
        total_weeks = private_request.total_sessions / sessions_per_week
        end_date = start_date + timedelta(weeks=int(total_weeks) + 1)
        
        # محاسبه ساعت پایان
        start_time = serializer.validated_data['start_time']
        start_datetime = datetime.combine(datetime.today(), start_time)
        end_datetime = start_datetime + timedelta(minutes=private_request.session_duration)
        end_time = end_datetime.time()
        
        with db_transaction.atomic():
            # ایجاد کلاس
            import secrets
            new_class = Class.objects.create(
                course=private_request.course,
                branch=private_request.branch,
                teacher=private_request.assigned_teacher,
                classroom_id=serializer.validated_data.get('classroom'),
                name=f"کلاس خصوصی {private_request.course.name} - {private_request.primary_student.get_full_name()}",
                code=f"PVT{secrets.token_hex(4).upper()}",
                class_type=(
                    Class.ClassType.PRIVATE 
                    if private_request.class_type == PrivateClassRequest.ClassType.PRIVATE 
                    else Class.ClassType.SEMI_PRIVATE
                ),
                start_date=start_date,
                end_date=end_date,
                schedule_days=serializer.validated_data['schedule_days'],
                start_time=start_time,
                end_time=end_time,
                capacity=private_request.student_count,
                current_enrollments=0,
                price=invoice.total_amount,
                registration_start=timezone.now(),
                registration_end=timezone.now(),
                is_registration_open=False,
                status=Class.ClassStatus.SCHEDULED
            )
            
            # ایجاد ثبت‌نام برای دانش‌آموز اصلی
            from apps.enrollments.models import Enrollment
            
            Enrollment.objects.create(
                student=private_request.primary_student,
                class_obj=new_class,
                status=Enrollment.EnrollmentStatus.ACTIVE,
                total_amount=invoice.total_amount,
                final_amount=invoice.total_amount,
                paid_amount=invoice.paid_amount
            )
            new_class.current_enrollments += 1
            
            # ایجاد ثبت‌نام برای دانش‌آموزان اضافی
            for student in private_request.additional_students.all():
                Enrollment.objects.create(
                    student=student,
                    class_obj=new_class,
                    status=Enrollment.EnrollmentStatus.ACTIVE,
                    total_amount=0,
                    final_amount=0,
                    paid_amount=0
                )
                new_class.current_enrollments += 1
            
            new_class.save()
            
            # بروزرسانی درخواست
            private_request.created_class = new_class
            private_request.status = PrivateClassRequest.RequestStatus.SCHEDULED
            private_request.save()
            
            # ایجاد جلسات
            from apps.courses.utils import generate_class_sessions
            sessions = generate_class_sessions(new_class)
            
            # ارسال نوتیفیکیشن
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=private_request.primary_student,
                title='کلاس خصوصی شما آماده است',
                message=f'کلاس خصوصی شما با موفقیت ایجاد شد. تاریخ شروع: {start_date}',
                notification_type=Notification.NotificationType.SUCCESS,
                category=Notification.NotificationCategory.CLASS,
                action_url=f'/classes/{new_class.id}/'
            )
        
        return Response({
            'message': 'کلاس با موفقیت ایجاد شد',
            'class_id': str(new_class.id),
            'total_sessions': len(sessions),
            'class': ClassSerializer(new_class).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-requests')
    def my_requests(self, request):
        """
        درخواست‌های کاربر جاری
        GET /api/v1/courses/private-requests/my-requests/
        """
        user = request.user
        requests_qs = self.get_queryset().filter(
            models.Q(primary_student=user) | 
            models.Q(additional_students=user)
        )
        
        serializer = self.get_serializer(requests_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_requests(self, request):
        """
        درخواست‌های در انتظار تایید
        GET /api/v1/courses/private-requests/pending/
        """
        requests_qs = self.get_queryset().filter(
            status=PrivateClassRequest.RequestStatus.PENDING
        ).order_by('created_at')
        
        serializer = self.get_serializer(requests_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        آمار درخواست‌های کلاس خصوصی
        GET /api/v1/courses/private-requests/statistics/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(
                status=PrivateClassRequest.RequestStatus.PENDING
            ).count(),
            'approved': queryset.filter(
                status=PrivateClassRequest.RequestStatus.APPROVED
            ).count(),
            'scheduled': queryset.filter(
                status=PrivateClassRequest.RequestStatus.SCHEDULED
            ).count(),
            'rejected': queryset.filter(
                status=PrivateClassRequest.RequestStatus.REJECTED
            ).count(),
            'by_class_type': dict(
                queryset.values('class_type').annotate(
                    count=Count('id')
                ).values_list('class_type', 'count')
            ),
        }
        
        return Response(stats)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        لغو درخواست توسط دانش‌آموز
        POST /api/v1/courses/private-requests/{id}/cancel/
        """
        private_request = self.get_object()
        
        # فقط دانش‌آموز اصلی می‌تواند لغو کند
        if request.user != private_request.primary_student:
            return Response({
                'error': 'فقط دانش‌آموز اصلی می‌تواند درخواست را لغو کند'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # فقط در وضعیت pending و approved
        if private_request.status not in [
            PrivateClassRequest.RequestStatus.PENDING,
            PrivateClassRequest.RequestStatus.APPROVED
        ]:
            return Response({
                'error': 'این درخواست قابل لغو نیست'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        private_request.status = PrivateClassRequest.RequestStatus.CANCELLED
        private_request.save()
        
        return Response({
            'message': 'درخواست لغو شد'
        })
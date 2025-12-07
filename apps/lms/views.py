from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Count, Avg, Exists, OuterRef, Subquery
from django.http import FileResponse, Http404

from .models import (
    CourseMaterial, Assignment, AssignmentSubmission,
    OnlineSession, OnlineSessionParticipant
)
from .serializers import (
    CourseMaterialSerializer, AssignmentSerializer,
    AssignmentSubmissionSerializer, GradeSubmissionSerializer,
    OnlineSessionSerializer, OnlineSessionParticipantSerializer,
    CreateOnlineSessionSerializer, JoinSessionSerializer
)
from utils.permissions import IsSuperAdmin, IsTeacher, IsStudent
from utils.pagination import StandardResultsSetPagination


class CourseMaterialViewSet(viewsets.ModelViewSet):
    """
    Course Material ViewSet
    """
    queryset = CourseMaterial.objects.filter(is_deleted=False)
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['class_obj', 'session', 'material_type']
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'created_at', 'title']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacher() or IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'class_obj', 'session', 'uploaded_by'
        )
        
        # Check availability
        now = timezone.now()
        queryset = queryset.filter(
            Q(available_from__isnull=True) | Q(available_from__lte=now)
        ).filter(
            Q(available_until__isnull=True) | Q(available_until__gte=now)
        )
        
        # Students see only their class materials
        if user.role == user.UserRole.STUDENT:
            from apps.enrollments.models import Enrollment
            enrolled_classes = Enrollment.objects.filter(
                student=user,
                status=Enrollment.EnrollmentStatus.ACTIVE
            ).values_list('class_obj_id', flat=True)
            
            queryset = queryset.filter(
                Q(class_obj_id__in=enrolled_classes) | Q(is_public=True)
            )
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Download material file
        GET /api/v1/lms/materials/{id}/download/
        """
        material = self.get_object()
        
        if not material.file:
            return Response({
                'error': 'فایلی برای دانلود وجود ندارد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Increment download count
        material.download_count += 1
        material.save()
        
        # Return file
        return FileResponse(
            material.file.open('rb'),
            as_attachment=True,
            filename=material.file.name
        )

    @action(detail=True, methods=['post'], url_path='increment-view')
    def increment_view(self, request, pk=None):
        """
        Increment view count
        POST /api/v1/lms/materials/{id}/increment-view/
        """
        material = self.get_object()
        material.view_count += 1
        material.save()
        
        return Response({'view_count': material.view_count})

    @action(detail=False, methods=['get'], url_path='class/(?P<class_id>[^/.]+)')
    def by_class(self, request, class_id=None):
        """
        Get materials for a specific class
        GET /api/v1/lms/materials/class/{class_id}/
        """
        materials = self.get_queryset().filter(class_obj_id=class_id)
        
        serializer = self.get_serializer(materials, many=True)
        return Response(serializer.data)


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    Assignment ViewSet
    """
    queryset = Assignment.objects.filter(is_deleted=False)
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['class_obj', 'assignment_type', 'is_published']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacher() or IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'class_obj', 'session', 'created_by'
        )
        
        # Students see only published assignments
        if user.role == user.UserRole.STUDENT:
            from apps.enrollments.models import Enrollment
            enrolled_classes = Enrollment.objects.filter(
                student=user,
                status=Enrollment.EnrollmentStatus.ACTIVE
            ).values_list('class_obj_id', flat=True)
            
            queryset = queryset.filter(
                class_obj_id__in=enrolled_classes,
                is_published=True
            )
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='submissions')
    def get_submissions(self, request, pk=None):
        """
        Get all submissions for an assignment
        GET /api/v1/lms/assignments/{id}/submissions/
        """
        assignment = self.get_object()
        submissions = assignment.submissions.all().select_related('student', 'graded_by')
        
        serializer = AssignmentSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='statistics')
    def statistics(self, request, pk=None):
        """
        Get assignment statistics
        GET /api/v1/lms/assignments/{id}/statistics/
        """
        assignment = self.get_object()
        submissions = assignment.submissions.all()
        
        stats = {
            'total_students': assignment.class_obj.current_enrollments,
            'submitted_count': submissions.count(),
            'graded_count': submissions.filter(
                status=AssignmentSubmission.SubmissionStatus.GRADED
            ).count(),
            'pending_count': submissions.filter(
                status=AssignmentSubmission.SubmissionStatus.SUBMITTED
            ).count(),
            'late_count': submissions.filter(is_late=True).count(),
            'average_score': submissions.filter(
                score__isnull=False
            ).aggregate(avg=Avg('score'))['avg'] or 0,
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'], url_path='my-assignments')
    def my_assignments(self, request):
        """
        Get assignments for current student
        GET /api/v1/lms/assignments/my-assignments/
        """
        if request.user.role != request.user.UserRole.STUDENT:
            return Response({
                'error': 'فقط دانش‌آموزان می‌توانند به این بخش دسترسی داشته باشند'
            }, status=status.HTTP_403_FORBIDDEN)
        
        assignments = self.get_queryset()
        
        # Annotate with submission info
        submissions = AssignmentSubmission.objects.filter(
            assignment=OuterRef('pk'),
            student=request.user
        )
        
        assignments = assignments.annotate(
            has_submitted=Exists(submissions),
            submission_status=Subquery(
                submissions.values('status')[:1]
            ),
            submission_score=Subquery(
                submissions.values('score')[:1]
            )
        )
        
        serializer = self.get_serializer(assignments, many=True)
        data = serializer.data
        
        # Add status based on submission for each assignment
        for i, assignment in enumerate(assignments):
            class_obj = assignment.class_obj
            data[i]['class_name'] = class_obj.name if class_obj else None
            data[i]['has_submitted'] = assignment.has_submitted
            
            # Determine status for frontend
            if assignment.submission_status == 'graded':
                data[i]['status'] = 'graded'
                data[i]['score'] = float(assignment.submission_score) if assignment.submission_score else None
            elif assignment.has_submitted:
                data[i]['status'] = 'submitted'
            else:
                data[i]['status'] = 'pending'
        
        return Response(data)

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming_assignments(self, request):
        """
        Get upcoming assignments
        GET /api/v1/lms/assignments/upcoming/
        """
        assignments = self.get_queryset().filter(
            due_date__gte=timezone.now(),
            is_published=True
        ).order_by('due_date')[:10]
        
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    """
    Assignment Submission ViewSet
    """
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['assignment', 'student', 'status']
    ordering_fields = ['submitted_at', 'score']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'assignment', 'student', 'enrollment', 'graded_by'
        )
        
        # Students see only their submissions
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Teachers see submissions for their classes
        elif user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(assignment__class_obj__teacher=user)
        
        return queryset

    def perform_create(self, serializer):
        from apps.enrollments.models import Enrollment
        
        # Get student's enrollment
        assignment = serializer.validated_data['assignment']
        enrollment = Enrollment.objects.get(
            student=self.request.user,
            class_obj=assignment.class_obj,
            status=Enrollment.EnrollmentStatus.ACTIVE
        )
        
        serializer.save(
            student=self.request.user,
            enrollment=enrollment
        )

    @action(detail=True, methods=['post'], url_path='grade')
    def grade_submission(self, request, pk=None):
        """
        Grade a submission
        POST /api/v1/lms/submissions/{id}/grade/
        {
            "score": 85,
            "feedback": "عالی بود"
        }
        """
        submission = self.get_object()
        
        serializer = GradeSubmissionSerializer(data={
            'submission_id': submission.id,
            'score': request.data.get('score'),
            'feedback': request.data.get('feedback', '')
        })
        serializer.is_valid(raise_exception=True)
        
        submission.score = serializer.validated_data['score']
        submission.feedback = serializer.validated_data.get('feedback', '')
        submission.status = AssignmentSubmission.SubmissionStatus.GRADED
        submission.graded_by = request.user
        submission.graded_at = timezone.now()
        submission.save()
        
        # Send notification
        try:
            from apps.notifications.tasks import send_notification_task
            from apps.notifications.models import Notification
            
            notification = Notification.objects.create(
                recipient=submission.student,
                title='نمره تکلیف',
                message=f'تکلیف {submission.assignment.title} شما نمره‌دهی شد. نمره: {submission.score}',
                notification_type=Notification.NotificationType.SUCCESS,
                category=Notification.NotificationCategory.EXAM
            )
            send_notification_task.delay(str(notification.id))
        except Exception as e:
            # اگر Redis در دسترس نیست، نوتیفیکیشن ذخیره شده ولی ارسال نمی‌شود
            import logging
            logging.warning(f"Could not send notification via Celery: {e}")
        
        return Response({
            'message': 'نمره ثبت شد',
            'submission': AssignmentSubmissionSerializer(submission).data
        })

    @action(detail=False, methods=['get'], url_path='my-submissions')
    def my_submissions(self, request):
        """
        Get current student's submissions
        GET /api/v1/lms/submissions/my-submissions/
        """
        submissions = self.get_queryset().filter(student=request.user)
        
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-grading')
    def pending_grading(self, request):
        """
        Get submissions pending grading
        GET /api/v1/lms/submissions/pending-grading/
        """
        submissions = self.get_queryset().filter(
            status=AssignmentSubmission.SubmissionStatus.SUBMITTED
        )
        
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)


class OnlineSessionViewSet(viewsets.ModelViewSet):
    """
    Online Session ViewSet
    """
    queryset = OnlineSession.objects.all()
    serializer_class = OnlineSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['class_session', 'status']
    ordering_fields = ['created_at', 'started_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacher() or IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='create-session')
    def create_session(self, request):
        """
        Create BBB session
        POST /api/v1/lms/online-sessions/create-session/
        """
        from apps.courses.models import ClassSession
        from .utils import create_bbb_meeting
        
        serializer = CreateOnlineSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        class_session = ClassSession.objects.get(
            id=serializer.validated_data['class_session_id']
        )
        
        # Create BBB meeting
        meeting_info = create_bbb_meeting(
            class_session=class_session,
            max_participants=serializer.validated_data.get('max_participants', 100),
            is_recorded=serializer.validated_data.get('is_recorded', True)
        )
        
        # Create online session record
        online_session = OnlineSession.objects.create(
            class_session=class_session,
            meeting_id=meeting_info['meeting_id'],
            moderator_password=meeting_info['moderator_password'],
            attendee_password=meeting_info['attendee_password'],
            max_participants=serializer.validated_data.get('max_participants', 100),
            is_recorded=serializer.validated_data.get('is_recorded', True),
            allow_chat=serializer.validated_data.get('allow_chat', True),
            allow_webcam=serializer.validated_data.get('allow_webcam', True),
            allow_microphone=serializer.validated_data.get('allow_microphone', True),
            allow_screen_share=serializer.validated_data.get('allow_screen_share', False)
        )
        
        return Response({
            'message': 'جلسه آنلاین ایجاد شد',
            'session': OnlineSessionSerializer(online_session).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='join')
    def join_session(self, request, pk=None):
        """
        Get join URL for session
        POST /api/v1/lms/online-sessions/{id}/join/
        """
        from .utils import get_bbb_join_url
        
        online_session = self.get_object()
        user = request.user
        
        # Check if user is moderator (teacher)
        is_moderator = (
            user == online_session.class_session.class_obj.teacher or
            user.is_superuser
        )
        
        join_url = get_bbb_join_url(
            online_session=online_session,
            user=user,
            is_moderator=is_moderator
        )
        
        # Log participant
        OnlineSessionParticipant.objects.create(
            online_session=online_session,
            user=user,
            joined_at=timezone.now(),
            is_moderator=is_moderator
        )
        
        return Response({
            'join_url': join_url,
            'is_moderator': is_moderator
        })

    @action(detail=True, methods=['post'], url_path='end')
    def end_session(self, request, pk=None):
        """
        End BBB session
        POST /api/v1/lms/online-sessions/{id}/end/
        """
        from .utils import end_bbb_meeting
        
        online_session = self.get_object()
        
        # End BBB meeting
        end_bbb_meeting(online_session.meeting_id)
        
        # Update session
        online_session.status = OnlineSession.SessionStatus.ENDED
        online_session.ended_at = timezone.now()
        online_session.save()
        
        return Response({
            'message': 'جلسه پایان یافت'
        })

    @action(detail=True, methods=['get'], url_path='participants')
    def get_participants(self, request, pk=None):
        """
        Get session participants
        GET /api/v1/lms/online-sessions/{id}/participants/
        """
        online_session = self.get_object()
        participants = online_session.participants.all().select_related('user')
        
        serializer = OnlineSessionParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='recordings')
    def get_recordings(self, request, pk=None):
        """
        Get session recordings
        GET /api/v1/lms/online-sessions/{id}/recordings/
        """
        from .utils import get_bbb_recordings
        
        online_session = self.get_object()
        recordings = get_bbb_recordings(online_session.meeting_id)
        
        return Response(recordings)
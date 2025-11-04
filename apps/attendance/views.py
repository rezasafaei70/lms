from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.db.models import Q, Count, Avg

from .models import Attendance, AttendanceReport
from .serializers import (
    AttendanceSerializer, AttendanceListSerializer, BulkAttendanceSerializer,
    AttendanceReportSerializer, StudentAttendanceSummarySerializer
)
from apps.courses.models import ClassSession
from apps.enrollments.models import Enrollment
from utils.permissions import IsSuperAdmin, IsTeacher, IsStudent
from utils.pagination import StandardResultsSetPagination


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Attendance ViewSet
    """
    queryset = Attendance.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enrollment', 'session', 'status']
    ordering_fields = ['created_at', 'check_in_time']

    def get_serializer_class(self):
        if self.action == 'list':
            return AttendanceListSerializer
        elif self.action == 'bulk_record':
            return BulkAttendanceSerializer
        return AttendanceSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'enrollment', 'enrollment__student', 'session',
            'session__class_obj', 'recorded_by'
        )
        
        # Students see only their attendance
        if user.role == user.UserRole.STUDENT:
            queryset = queryset.filter(enrollment__student=user)
        # Teachers see their classes' attendance
        elif user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(session__class_obj__teacher=user)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(
            recorded_by=self.request.user,
            check_in_time=timezone.now() if serializer.validated_data['status'] != 'absent' else None
        )

    @action(detail=False, methods=['post'], url_path='bulk-record')
    def bulk_record(self, request):
        """
        Record attendance for multiple students
        POST /api/v1/attendance/attendances/bulk-record/
        {
            "session": "session_id",
            "attendances": [
                {
                    "enrollment": "enrollment_id",
                    "status": "present"
                },
                {
                    "enrollment": "enrollment_id",
                    "status": "absent",
                    "excuse_reason": "مریضی"
                }
            ]
        }
        """
        serializer = BulkAttendanceSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        attendances = serializer.save()
        
        return Response({
            'message': f'{len(attendances)} مورد حضور و غیاب ثبت شد',
            'attendances': AttendanceListSerializer(attendances, many=True).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='session/(?P<session_id>[^/.]+)')
    def by_session(self, request, session_id=None):
        """
        Get attendance for a specific session
        GET /api/v1/attendance/attendances/session/{session_id}/
        """
        try:
            session = ClassSession.objects.get(id=session_id)
        except ClassSession.DoesNotExist:
            return Response({
                'error': 'جلسه یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        attendances = self.get_queryset().filter(session=session)
        serializer = self.get_serializer(attendances, many=True)
        
        return Response({
            'session': {
                'id': str(session.id),
                'title': session.title,
                'date': session.date,
                'attendance_taken': session.attendance_taken
            },
            'attendances': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='my-attendance')
    def my_attendance(self, request):
        """
        Get current user's attendance records
        GET /api/v1/attendance/attendances/my-attendance/
        """
        attendances = self.get_queryset().filter(
            enrollment__student=request.user
        ).order_by('-session__date')
        
        page = self.paginate_queryset(attendances)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(attendances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-summary')
    def my_summary(self, request):
        """
        Get attendance summary for current user
        GET /api/v1/attendance/attendances/my-summary/
        """
        enrollment_id = request.query_params.get('enrollment')
        
        if not enrollment_id:
            return Response({
                'error': 'شناسه ثبت‌نام الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            enrollment = Enrollment.objects.get(
                id=enrollment_id,
                student=request.user
            )
        except Enrollment.DoesNotExist:
            return Response({
                'error': 'ثبت‌نام یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        attendances = Attendance.objects.filter(enrollment=enrollment)
        
        summary = {
            'total_sessions': attendances.count(),
            'attended_sessions': attendances.filter(
                status__in=[
                    Attendance.AttendanceStatus.PRESENT,
                    Attendance.AttendanceStatus.LATE
                ]
            ).count(),
            'absent_sessions': attendances.filter(
                status=Attendance.AttendanceStatus.ABSENT
            ).count(),
            'late_sessions': attendances.filter(
                status=Attendance.AttendanceStatus.LATE
            ).count(),
            'excused_sessions': attendances.filter(
                status=Attendance.AttendanceStatus.EXCUSED
            ).count(),
            'attendance_rate': enrollment.attendance_rate,
            'recent_attendances': AttendanceListSerializer(
                attendances.order_by('-created_at')[:10],
                many=True
            ).data
        }
        
        serializer = StudentAttendanceSummarySerializer(summary)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-excused')
    def mark_excused(self, request, pk=None):
        """
        Mark absence as excused
        POST /api/v1/attendance/attendances/{id}/mark-excused/
        {
            "excuse_reason": "دلیل غیبت"
        }
        """
        attendance = self.get_object()
        excuse_reason = request.data.get('excuse_reason', '')
        
        attendance.status = Attendance.AttendanceStatus.EXCUSED
        attendance.excuse_reason = excuse_reason
        attendance.save()
        
        return Response({
            'message': 'غیبت به عنوان موجه ثبت شد'
        })

    @action(detail=False, methods=['post'], url_path='auto-record-online')
    def auto_record_online(self, request):
        """
        Auto-record attendance for online class (from BBB)
        POST /api/v1/attendance/attendances/auto-record-online/
        {
            "session": "session_id",
            "attendees": [
                {
                    "user_id": "user_id",
                    "join_time": "2024-01-01T10:00:00Z",
                    "leave_time": "2024-01-01T11:30:00Z"
                }
            ]
        }
        """
        from django.db import transaction
        
        session_id = request.data.get('session')
        attendees = request.data.get('attendees', [])
        
        try:
            session = ClassSession.objects.get(id=session_id)
        except ClassSession.DoesNotExist:
            return Response({
                'error': 'جلسه یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        with transaction.atomic():
            for attendee in attendees:
                try:
                    enrollment = Enrollment.objects.get(
                        student_id=attendee['user_id'],
                        class_obj=session.class_obj
                    )
                    
                    Attendance.objects.update_or_create(
                        enrollment=enrollment,
                        session=session,
                        defaults={
                            'status': Attendance.AttendanceStatus.PRESENT,
                            'check_in_time': attendee.get('join_time'),
                            'check_out_time': attendee.get('leave_time'),
                            'is_auto_recorded': True
                        }
                    )
                except Enrollment.DoesNotExist:
                    continue
            
            session.attendance_taken = True
            session.save()
        
        return Response({
            'message': 'حضور و غیاب خودکار ثبت شد'
        })


class AttendanceReportViewSet(viewsets.ModelViewSet):
    """
    Attendance Report ViewSet
    """
    queryset = AttendanceReport.objects.all()
    serializer_class = AttendanceReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['session', 'teacher', 'is_finalized']
    ordering_fields = ['submitted_at', 'attendance_rate']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'session', 'session__class_obj', 'teacher'
        )
        
        # Teachers see their reports
        if user.role == user.UserRole.TEACHER:
            queryset = queryset.filter(teacher=user)
        
        return queryset

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """
        Finalize attendance report
        POST /api/v1/attendance/reports/{id}/finalize/
        """
        report = self.get_object()
        
        report.is_finalized = True
        report.save()
        
        # Send notifications to students with low attendance
        from apps.notifications.tasks import send_low_attendance_alerts
        send_low_attendance_alerts.delay(report.session.class_obj.id)
        
        return Response({
            'message': 'گزارش نهایی شد'
        })

    @action(detail=False, methods=['get'], url_path='class-summary/(?P<class_id>[^/.]+)')
    def class_summary(self, request, class_id=None):
        """
        Get attendance summary for a class
        GET /api/v1/attendance/reports/class-summary/{class_id}/
        """
        from apps.courses.models import Class
        
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            return Response({
                'error': 'کلاس یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        reports = self.get_queryset().filter(session__class_obj=class_obj)
        
        summary = {
            'class_name': class_obj.name,
            'total_sessions': reports.count(),
            'average_attendance_rate': reports.aggregate(
                avg=Avg('attendance_rate')
            )['avg'] or 0,
            'total_students': class_obj.current_enrollments,
            'reports': self.get_serializer(reports, many=True).data
        }
        
        return Response(summary)
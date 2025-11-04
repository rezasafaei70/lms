from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from django.http import FileResponse
from django.db.models import Count, Sum, Avg, Q
import io

from .models import Report, ReportTemplate
from .serializers import (
    ReportSerializer, ReportTemplateSerializer, GenerateReportSerializer
)
from utils.permissions import IsSuperAdmin, IsBranchManager
from utils.pagination import StandardResultsSetPagination


class ReportViewSet(viewsets.ModelViewSet):
    """
    Report ViewSet
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'file_format', 'branch', 'is_generated']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'generated_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Users see only their reports
        if user.role not in [user.UserRole.SUPER_ADMIN]:
            queryset = queryset.filter(created_by=user)
        
        # Branch managers see their branch reports
        if user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(
                Q(created_by=user) | Q(branch__manager=user)
            )
        
        return queryset.select_related('created_by', 'branch')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        """
        Generate a new report
        POST /api/v1/reports/reports/generate/
        """
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from .utils import generate_report
        
        report = generate_report(
            report_type=serializer.validated_data['report_type'],
            title=serializer.validated_data['title'],
            file_format=serializer.validated_data['file_format'],
            parameters=serializer.validated_data.get('parameters', {}),
            branch_id=serializer.validated_data.get('branch'),
            user=request.user
        )
        
        return Response({
            'message': 'گزارش در حال تولید است',
            'report': ReportSerializer(report, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Download report file
        GET /api/v1/reports/reports/{id}/download/
        """
        report = self.get_object()
        
        if not report.file:
            return Response({
                'error': 'فایل گزارش هنوز تولید نشده است'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return FileResponse(
            report.file.open('rb'),
            as_attachment=True,
            filename=f"{report.title}.{report.file_format}"
        )

    @action(detail=False, methods=['get'], url_path='financial-summary')
    def financial_summary(self, request):
        """
        Get financial summary report
        GET /api/v1/reports/reports/financial-summary/
        """
        from apps.financial.models import Invoice, Payment, Transaction
        from datetime import datetime, timedelta
        
        # Get date range from query params
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        branch_id = request.query_params.get('branch')
        
        # Default to last 30 days
        if not from_date:
            from_date = (timezone.now() - timedelta(days=30)).date()
        if not to_date:
            to_date = timezone.now().date()
        
        # Filter data
        invoices = Invoice.objects.filter(
            issue_date__gte=from_date,
            issue_date__lte=to_date
        )
        
        payments = Payment.objects.filter(
            payment_date__gte=from_date,
            payment_date__lte=to_date,
            status=Payment.PaymentStatus.COMPLETED
        )
        
        transactions = Transaction.objects.filter(
            date__gte=from_date,
            date__lte=to_date
        )
        
        if branch_id:
            invoices = invoices.filter(branch_id=branch_id)
            transactions = transactions.filter(branch_id=branch_id)
        
        # Calculate totals
        summary = {
            'period': {
                'from': from_date,
                'to': to_date
            },
            'invoices': {
                'total': invoices.count(),
                'paid': invoices.filter(status=Invoice.InvoiceStatus.PAID).count(),
                'pending': invoices.filter(status=Invoice.InvoiceStatus.PENDING).count(),
                'total_amount': invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                'paid_amount': invoices.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
            },
            'payments': {
                'total': payments.count(),
                'total_amount': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
                'by_method': list(payments.values('payment_method').annotate(
                    count=Count('id'),
                    total=Sum('amount')
                ))
            },
            'transactions': {
                'income': transactions.filter(
                    transaction_type=Transaction.TransactionType.INCOME
                ).aggregate(Sum('amount'))['amount__sum'] or 0,
                'expense': transactions.filter(
                    transaction_type=Transaction.TransactionType.EXPENSE
                ).aggregate(Sum('amount'))['amount__sum'] or 0,
            }
        }
        
        summary['transactions']['net'] = (
            summary['transactions']['income'] - 
            summary['transactions']['expense']
        )
        
        return Response(summary)

    @action(detail=False, methods=['get'], url_path='enrollment-summary')
    def enrollment_summary(self, request):
        """
        Get enrollment summary report
        GET /api/v1/reports/reports/enrollment-summary/
        """
        from apps.enrollments.models import Enrollment
        from apps.courses.models import Class
        
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        branch_id = request.query_params.get('branch')
        
        enrollments = Enrollment.objects.all()
        classes = Class.objects.all()
        
        if from_date:
            enrollments = enrollments.filter(enrollment_date__gte=from_date)
        if to_date:
            enrollments = enrollments.filter(enrollment_date__lte=to_date)
        if branch_id:
            enrollments = enrollments.filter(class_obj__branch_id=branch_id)
            classes = classes.filter(branch_id=branch_id)
        
        summary = {
            'total_enrollments': enrollments.count(),
            'by_status': list(enrollments.values('status').annotate(
                count=Count('id')
            )),
            'total_classes': classes.count(),
            'active_classes': classes.filter(
                status=Class.ClassStatus.SCHEDULED
            ).count(),
            'total_students': enrollments.values('student').distinct().count(),
            'average_attendance_rate': enrollments.aggregate(
                Avg('attendance_rate')
            )['attendance_rate__avg'] or 0,
        }
        
        return Response(summary)

    @action(detail=False, methods=['get'], url_path='attendance-summary')
    def attendance_summary(self, request):
        """
        Get attendance summary report
        GET /api/v1/reports/reports/attendance-summary/
        """
        from apps.attendance.models import Attendance, AttendanceReport
        
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        class_id = request.query_params.get('class')
        
        attendances = Attendance.objects.all()
        
        if from_date:
            attendances = attendances.filter(session__date__gte=from_date)
        if to_date:
            attendances = attendances.filter(session__date__lte=to_date)
        if class_id:
            attendances = attendances.filter(session__class_obj_id=class_id)
        
        summary = {
            'total_sessions': attendances.values('session').distinct().count(),
            'total_attendances': attendances.count(),
            'by_status': list(attendances.values('status').annotate(
                count=Count('id')
            )),
            'present_count': attendances.filter(
                status=Attendance.AttendanceStatus.PRESENT
            ).count(),
            'absent_count': attendances.filter(
                status=Attendance.AttendanceStatus.ABSENT
            ).count(),
            'late_count': attendances.filter(
                status=Attendance.AttendanceStatus.LATE
            ).count(),
        }
        
        if summary['total_attendances'] > 0:
            summary['attendance_rate'] = (
                summary['present_count'] / summary['total_attendances']
            ) * 100
        else:
            summary['attendance_rate'] = 0
        
        return Response(summary)

    @action(detail=False, methods=['get'], url_path='teacher-performance')
    def teacher_performance(self, request):
        """
        Get teacher performance report
        GET /api/v1/reports/reports/teacher-performance/
        """
        from apps.accounts.models import User, TeacherProfile
        from apps.courses.models import Class, TeacherReview
        
        teacher_id = request.query_params.get('teacher')
        
        teachers = User.objects.filter(role=User.UserRole.TEACHER)
        
        if teacher_id:
            teachers = teachers.filter(id=teacher_id)
        
        data = []
        for teacher in teachers:
            try:
                profile = teacher.teacher_profile
            except:
                continue
            
            classes = Class.objects.filter(teacher=teacher)
            reviews = TeacherReview.objects.filter(
                teacher=teacher,
                is_approved=True
            )
            
            data.append({
                'teacher': {
                    'id': str(teacher.id),
                    'name': teacher.get_full_name(),
                    'employee_code': profile.employee_code,
                },
                'classes': {
                    'total': classes.count(),
                    'active': classes.filter(
                        status=Class.ClassStatus.SCHEDULED
                    ).count(),
                },
                'students': classes.aggregate(
                    Sum('current_enrollments')
                )['current_enrollments__sum'] or 0,
                'rating': profile.rating,
                'total_reviews': reviews.count(),
                'experience_years': profile.experience_years,
            })
        
        return Response(data)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """
    Report Template ViewSet
    """
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'is_active', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='active')
    def active_templates(self, request):
        """
        Get active templates
        GET /api/v1/reports/templates/active/
        """
        templates = self.get_queryset().filter(is_active=True)
        
        # Filter by user role
        user = request.user
        if user.role != user.UserRole.SUPER_ADMIN:
            templates = templates.filter(
                Q(is_public=True) | 
                Q(allowed_roles__contains=[user.role])
            )
        
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)
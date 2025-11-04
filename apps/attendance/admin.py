from django.contrib import admin
from .models import Attendance, AttendanceReport


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'enrollment', 'session', 'status', 'check_in_time',
        'late_minutes', 'is_auto_recorded'
    ]
    list_filter = ['status', 'is_auto_recorded', 'created_at']
    search_fields = [
        'enrollment__student__first_name',
        'enrollment__student__last_name',
        'session__title'
    ]
    ordering = ['-created_at']
    readonly_fields = ['late_minutes']


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'teacher', 'total_students', 'present_count',
        'absent_count', 'attendance_rate', 'is_finalized'
    ]
    list_filter = ['is_finalized', 'submitted_at']
    search_fields = ['session__title', 'teacher__first_name']
    ordering = ['-submitted_at']
    readonly_fields = [
        'total_students', 'present_count', 'absent_count',
        'late_count', 'excused_count', 'attendance_rate'
    ]
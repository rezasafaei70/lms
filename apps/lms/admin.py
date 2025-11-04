from django.contrib import admin
from .models import (
    CourseMaterial, Assignment, AssignmentSubmission,
    OnlineSession, OnlineSessionParticipant
)


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'class_obj', 'material_type',
        'is_public', 'download_count', 'view_count', 'created_at'
    ]
    list_filter = ['material_type', 'is_public', 'created_at']
    search_fields = ['title', 'description', 'class_obj__name']
    ordering = ['-created_at']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'class_obj', 'assignment_type',
        'max_score', 'due_date', 'is_published'
    ]
    list_filter = ['assignment_type', 'is_published', 'due_date']
    search_fields = ['title', 'description', 'class_obj__name']
    ordering = ['-due_date']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'assignment', 'student', 'submitted_at',
        'score', 'status', 'is_late'
    ]
    list_filter = ['status', 'is_late', 'submitted_at']
    search_fields = [
        'assignment__title', 'student__first_name', 'student__last_name'
    ]
    ordering = ['-submitted_at']


@admin.register(OnlineSession)
class OnlineSessionAdmin(admin.ModelAdmin):
    list_display = [
        'class_session', 'meeting_id', 'status',
        'started_at', 'ended_at', 'is_recorded'
    ]
    list_filter = ['status', 'is_recorded', 'created_at']
    search_fields = ['meeting_id', 'class_session__title']
    ordering = ['-created_at']


@admin.register(OnlineSessionParticipant)
class OnlineSessionParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'online_session', 'user', 'joined_at',
        'left_at', 'duration_seconds', 'is_moderator'
    ]
    list_filter = ['is_moderator', 'joined_at']
    search_fields = ['user__first_name', 'user__last_name']
    ordering = ['-joined_at']
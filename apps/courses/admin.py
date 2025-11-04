from django.contrib import admin
from .models import Course, Class, ClassSession, Term, TeacherReview


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'level', 'duration_hours', 'sessions_count',
        'base_price', 'status', 'is_featured', 'average_rating'
    ]
    list_filter = ['level', 'status', 'is_featured', 'provides_certificate']
    search_fields = ['name', 'code', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['prerequisites']
    ordering = ['-created_at']


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'course', 'branch', 'teacher',
        'class_type', 'start_date', 'capacity', 'current_enrollments', 'status'
    ]
    list_filter = ['class_type', 'status', 'branch', 'is_registration_open']
    search_fields = ['name', 'code', 'course__name', 'teacher__first_name']
    ordering = ['-start_date']


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = [
        'class_obj', 'session_number', 'date', 'start_time',
        'end_time', 'status', 'attendance_taken'
    ]
    list_filter = ['status', 'attendance_taken', 'date']
    search_fields = ['class_obj__name', 'title']
    ordering = ['date', 'start_time']


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'start_date', 'end_date',
        'registration_start', 'registration_end', 'status'
    ]
    list_filter = ['status']
    search_fields = ['name', 'code']
    ordering = ['-start_date']


@admin.register(TeacherReview)
class TeacherReviewAdmin(admin.ModelAdmin):
    list_display = [
        'teacher', 'student', 'class_obj', 'rating',
        'is_approved', 'created_at'
    ]
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['teacher__first_name', 'student__first_name', 'comment']
    ordering = ['-created_at']
    
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            is_approved=True,
            approved_by=request.user,
            approved_at=timezone.now()
        )
    approve_reviews.short_description = 'تایید نظرات انتخاب شده'
    
    def reject_reviews(self, request, queryset):
        queryset.delete()
    reject_reviews.short_description = 'حذف نظرات انتخاب شده'
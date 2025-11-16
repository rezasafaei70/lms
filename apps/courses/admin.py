from django.contrib import admin
from .models import Course, Class, ClassSession, PrivateClassPricing, PrivateClassRequest, Subject, Term, TeacherReview
from django.utils import timezone

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['title']
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
    
    

@admin.register(PrivateClassPricing)
class PrivateClassPricingAdmin(admin.ModelAdmin):
    list_display = [
        'class_type', 'price_per_session', 'discount_24_sessions',
        'discount_36_sessions', 'discount_48_sessions', 'is_active'
    ]
    list_filter = ['class_type', 'is_active']
    ordering = ['class_type']
    
    fieldsets = (
        ('نوع کلاس', {
            'fields': ('class_type', 'is_active')
        }),
        ('قیمت‌گذاری', {
            'fields': ('price_per_session',)
        }),
        ('تخفیفات', {
            'fields': (
                'discount_24_sessions',
                'discount_36_sessions',
                'discount_48_sessions'
            )
        }),
    )


@admin.register(PrivateClassRequest)
class PrivateClassRequestAdmin(admin.ModelAdmin):
    list_display = [
        'request_number', 'primary_student', 'course', 'class_type',
        'total_sessions', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'class_type', 'branch', 'preferred_location',
        'created_at'
    ]
    search_fields = [
        'request_number', 'primary_student__first_name',
        'primary_student__last_name', 'primary_student__mobile'
    ]
    readonly_fields = [
        'request_number', 'created_at', 'updated_at',
        'approved_by', 'approved_at', 'student_count_display'
    ]
    ordering = ['-created_at']
    
    filter_horizontal = ['additional_students']
    
    fieldsets = (
        ('اطلاعات درخواست', {
            'fields': (
                'request_number', 'status', 'primary_student',
                'additional_students', 'student_count_display'
            )
        }),
        ('دوره و شعبه', {
            'fields': ('course', 'branch')
        }),
        ('نوع و تنظیمات کلاس', {
            'fields': (
                'class_type', 'sessions_per_week', 'total_sessions',
                'session_duration'
            )
        }),
        ('ترجیحات', {
            'fields': (
                'preferred_teacher', 'preferred_days',
                'preferred_time_slot', 'preferred_location',
                'preferred_start_date'
            )
        }),
        ('اختصاص و تایید', {
            'fields': (
                'assigned_teacher', 'created_class',
                'approved_by', 'approved_at'
            )
        }),
        ('یادداشت‌ها', {
            'fields': ('student_notes', 'admin_notes', 'rejection_reason')
        }),
    )
    
    def student_count_display(self, obj):
        return obj.student_count
    student_count_display.short_description = 'تعداد دانش‌آموزان'
    
    actions = ['approve_selected', 'reject_selected']
    
    def approve_selected(self, request, queryset):
        count = queryset.filter(
            status=PrivateClassRequest.RequestStatus.PENDING
        ).update(
            status=PrivateClassRequest.RequestStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{count} درخواست تایید شد')
    approve_selected.short_description = 'تایید درخواست‌های انتخاب شده'
    
    def reject_selected(self, request, queryset):
        count = queryset.filter(
            status=PrivateClassRequest.RequestStatus.PENDING
        ).update(
            status=PrivateClassRequest.RequestStatus.REJECTED
        )
        self.message_user(request, f'{count} درخواست رد شد')
    reject_selected.short_description = 'رد درخواست‌های انتخاب شده'
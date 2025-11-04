from django.contrib import admin
from .models import (
    Enrollment, PlacementTest, WaitingList, EnrollmentTransfer,
    AnnualRegistration, EnrollmentDocument
)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'enrollment_number', 'student', 'class_obj', 'status',
        'enrollment_date', 'final_amount', 'is_paid', 'attendance_rate'
    ]
    list_filter = ['status', 'enrollment_date', 'certificate_issued']
    search_fields = [
        'enrollment_number', 'student__first_name',
        'student__last_name', 'class_obj__name'
    ]
    readonly_fields = ['enrollment_number', 'enrollment_date']
    ordering = ['-enrollment_date']


@admin.register(PlacementTest)
class PlacementTestAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'course', 'test_date', 'score',
        'determined_level', 'status'
    ]
    list_filter = ['status', 'determined_level', 'test_date', 'is_online']
    search_fields = ['student__first_name', 'student__last_name', 'course__name']
    ordering = ['-test_date']


@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'class_obj', 'position', 'status',
        'created_at', 'is_priority'
    ]
    list_filter = ['status', 'is_priority', 'created_at']
    search_fields = ['student__first_name', 'student__last_name', 'class_obj__name']
    ordering = ['is_priority', 'created_at']


@admin.register(EnrollmentTransfer)
class EnrollmentTransferAdmin(admin.ModelAdmin):
    list_display = [
        'enrollment', 'from_class', 'to_class',
        'status', 'request_date', 'price_difference'
    ]
    list_filter = ['status', 'request_date']
    search_fields = [
        'enrollment__enrollment_number',
        'enrollment__student__first_name'
    ]
    ordering = ['-request_date']


@admin.register(AnnualRegistration)
class AnnualRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'branch', 'academic_year', 'status',
        'registration_date', 'is_paid'
    ]
    list_filter = ['status', 'academic_year', 'is_paid', 'documents_verified']
    search_fields = ['student__first_name', 'student__last_name', 'academic_year']
    ordering = ['-registration_date']


@admin.register(EnrollmentDocument)
class EnrollmentDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'enrollment', 'document_type', 'title',
        'is_verified', 'created_at'
    ]
    list_filter = ['document_type', 'is_verified', 'created_at']
    search_fields = [
        'enrollment__enrollment_number',
        'enrollment__student__first_name', 'title'
    ]
    ordering = ['-created_at']
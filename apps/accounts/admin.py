from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import GradeLevel, User, StudentProfile, TeacherProfile, OTP, LoginHistory



@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'stage', 'order', 'is_active']
    list_filter = ['stage', 'is_active']
    search_fields = ['name']
    ordering = ['order']

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User Admin
    """
    list_display = ['mobile', 'get_full_name', 'email', 'role', 'is_active', 'is_verified', 'created_at']
    list_filter = ['role', 'is_active', 'is_verified', 'gender', 'created_at']
    search_fields = ['mobile', 'email', 'first_name', 'last_name', 'national_code']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('mobile', 'password')}),
        (_('اطلاعات شخصی'), {
            'fields': ('first_name', 'last_name', 'national_code', 'email', 
                      'gender', 'birth_date', 'profile_picture')
        }),
        (_('اطلاعات تماس'), {
            'fields': ('phone', 'address', 'city', 'province', 'postal_code')
        }),
        (_('دسترسی‌ها'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 
                      'is_verified', 'groups', 'user_permissions')
        }),
        (_('تاریخ‌ها'), {
            'fields': ('last_login', 'email_verified_at', 'mobile_verified_at', 
                      'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'نام کامل'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """
    Student Profile Admin
    """
    list_display = ['user', 'student_number', 'education_level','grade_level', 'is_active_student', 'registration_date']
    list_filter = ['education_level','grade_level', 'is_active_student', 'registration_date']
    search_fields = ['user__first_name', 'user__last_name', 'student_number', 'school_name']
    ordering = ['-registration_date']
    
    fieldsets = (
        (_('کاربر'), {'fields': ('user',)}),
        (_('اطلاعات تحصیلی'), {
            'fields': ('education_level', 'school_name','grade_level', 'field_of_study', 'student_number')
        }),
        (_('اطلاعات ولی'), {
            'fields': ('guardian_name', 'guardian_mobile', 'guardian_national_code')
        }),
        (_('تماس اضطراری'), {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 
                      'emergency_contact_relation')
        }),
        (_('اطلاعات پزشکی'), {
            'fields': ('medical_conditions', 'allergies')
        }),
        (_('مدارک'), {
            'fields': ('id_card_image', 'birth_certificate_image')
        }),
        (_('سایر'), {
            'fields': ('is_active_student', 'notes')
        }),
    )
    autocomplete_fields = ['user', 'grade_level']
    readonly_fields = ['student_number', 'registration_date']


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    """
    Teacher Profile Admin
    """
    list_display = ['user', 'employee_code', 'status', 'rating', 'experience_years', 'hourly_rate']
    list_filter = ['status', 'can_teach_online', 'employment_date']
    search_fields = ['user__first_name', 'user__last_name', 'employee_code', 'expertise']
    ordering = ['-created_at']
    
    fieldsets = (
        (_('کاربر'), {'fields': ('user',)}),
        (_('اطلاعات حرفه‌ای'), {
            'fields': ('expertise', 'experience_years', 'education_degree', 
                      'university', 'bio', 'specialties')
        }),
        (_('اطلاعات استخدامی'), {
            'fields': ('employment_date', 'employee_code', 'contract_type', 'status')
        }),
        (_('اطلاعات مالی'), {
            'fields': ('hourly_rate', 'base_salary', 'commission_rate')
        }),
        (_('تنظیمات تدریس'), {
            'fields': ('can_teach_online', 'max_students_per_class')
        }),
        (_('مدارک'), {
            'fields': ('resume', 'certificates', 'contract_file')
        }),
        (_('امتیازدهی'), {
            'fields': ('rating', 'total_reviews')
        }),
        (_('شبکه‌های اجتماعی'), {
            'fields': ('website', 'linkedin')
        }),
        (_('سایر'), {
            'fields': ('notes',)
        }),
    )

    readonly_fields = ['employee_code', 'rating', 'total_reviews']


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """
    OTP Admin
    """
    list_display = ['mobile', 'code', 'purpose', 'is_used', 'is_expired', 'created_at', 'expires_at']
    list_filter = ['purpose', 'is_used', 'is_expired', 'created_at']
    search_fields = ['mobile', 'code']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'verified_at']


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """
    Login History Admin
    """
    list_display = ['user', 'ip_address', 'device_type', 'browser', 'login_successful', 'created_at']
    list_filter = ['login_successful', 'device_type', 'browser', 'os', 'created_at']
    search_fields = ['user__mobile', 'user__first_name', 'user__last_name', 'ip_address']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'logout_at']
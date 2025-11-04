from django.contrib import admin
from .models import Branch, Classroom, BranchStaff


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'manager', 'status', 'total_capacity', 'created_at']
    list_filter = ['status', 'city', 'province', 'created_at']
    search_fields = ['name', 'code', 'city', 'address']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'code', 'manager', 'status')
        }),
        ('اطلاعات تماس', {
            'fields': ('phone', 'email')
        }),
        ('آدرس', {
            'fields': ('province', 'city', 'address', 'postal_code', 'latitude', 'longitude')
        }),
        ('ظرفیت و ساعات کاری', {
            'fields': ('total_capacity', 'working_hours_start', 'working_hours_end', 'working_days')
        }),
        ('سایر', {
            'fields': ('description', 'facilities', 'image', 'established_date')
        }),
    )


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch', 'room_number', 'capacity', 'is_active']
    list_filter = ['branch', 'is_active', 'has_projector', 'has_smartboard']
    search_fields = ['name', 'room_number', 'branch__name']
    ordering = ['branch', 'room_number']


@admin.register(BranchStaff)
class BranchStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'branch', 'position', 'is_active', 'assigned_date']
    list_filter = ['branch', 'is_active', 'assigned_date']
    search_fields = ['user__first_name', 'user__last_name', 'position']
    ordering = ['-assigned_date']
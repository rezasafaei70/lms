from django.contrib import admin
from .models import Report, ReportTemplate


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'report_type', 'file_format', 'branch',
        'is_generated', 'created_by', 'created_at'
    ]
    list_filter = ['report_type', 'file_format', 'is_generated', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'generated_at', 'file_size']
    ordering = ['-created_at']


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'report_type', 'is_active', 'is_public', 'created_at'
    ]
    list_filter = ['report_type', 'is_active', 'is_public']
    search_fields = ['name', 'description']
    ordering = ['name']
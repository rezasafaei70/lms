from rest_framework import serializers
from .models import Report, ReportTemplate
from apps.accounts.serializers import UserSerializer


class ReportSerializer(serializers.ModelSerializer):
    """
    Report Serializer
    """
    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    file_format_display = serializers.CharField(
        source='get_file_format_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'is_generated', 'generated_at', 'file_size'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


class ReportTemplateSerializer(serializers.ModelSerializer):
    """
    Report Template Serializer
    """
    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = ReportTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class GenerateReportSerializer(serializers.Serializer):
    """
    Generate Report Serializer
    """
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    title = serializers.CharField(max_length=255)
    file_format = serializers.ChoiceField(
        choices=Report.ReportFormat.choices,
        default=Report.ReportFormat.PDF
    )
    parameters = serializers.JSONField(default=dict)
    branch = serializers.UUIDField(required=False, allow_null=True)
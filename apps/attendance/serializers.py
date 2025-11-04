from rest_framework import serializers
from django.utils import timezone
from .models import Attendance, AttendanceReport
from apps.accounts.serializers import UserSerializer
from apps.enrollments.serializers import EnrollmentListSerializer


class AttendanceSerializer(serializers.ModelSerializer):
    """
    Attendance Serializer
    """
    enrollment_details = EnrollmentListSerializer(source='enrollment', read_only=True)
    student_name = serializers.CharField(
        source='enrollment.student.get_full_name',
        read_only=True
    )
    session_title = serializers.CharField(source='session.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'recorded_by',
            'late_minutes', 'is_auto_recorded'
        ]

    def validate(self, attrs):
        enrollment = attrs.get('enrollment')
        session = attrs.get('session')
        
        # Check if enrollment belongs to the session's class
        if enrollment.class_obj != session.class_obj:
            raise serializers.ValidationError(
                'ثبت‌نام و جلسه متعلق به یک کلاس نیستند'
            )
        
        return attrs


class AttendanceListSerializer(serializers.ModelSerializer):
    """
    Simplified Attendance List Serializer
    """
    student_name = serializers.CharField(
        source='enrollment.student.get_full_name',
        read_only=True
    )
    student_id = serializers.UUIDField(
        source='enrollment.student.id',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'student_id', 'student_name', 'status',
            'status_display', 'check_in_time', 'late_minutes', 'notes'
        ]


class BulkAttendanceSerializer(serializers.Serializer):
    """
    Bulk Attendance Serializer
    """
    session = serializers.UUIDField()
    attendances = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
    
    def validate_attendances(self, value):
        """
        Validate attendances list
        Expected format:
        [
            {"enrollment": "uuid", "status": "present"},
            {"enrollment": "uuid", "status": "absent", "excuse_reason": "..."},
            ...
        ]
        """
        if not value:
            raise serializers.ValidationError('لیست حضور و غیاب خالی است')
        
        for item in value:
            if 'enrollment' not in item or 'status' not in item:
                raise serializers.ValidationError(
                    'هر مورد باید شامل enrollment و status باشد'
                )
            
            if item['status'] not in dict(Attendance.AttendanceStatus.choices):
                raise serializers.ValidationError(f"وضعیت {item['status']} نامعتبر است")
        
        return value
    
    def create(self, validated_data):
        from apps.courses.models import ClassSession
        from apps.enrollments.models import Enrollment
        from django.db import transaction
        
        session_id = validated_data['session']
        attendances_data = validated_data['attendances']
        
        try:
            session = ClassSession.objects.get(id=session_id)
        except ClassSession.DoesNotExist:
            raise serializers.ValidationError('جلسه یافت نشد')
        
        created_attendances = []
        
        with transaction.atomic():
            for item in attendances_data:
                try:
                    enrollment = Enrollment.objects.get(id=item['enrollment'])
                except Enrollment.DoesNotExist:
                    continue
                
                attendance, created = Attendance.objects.update_or_create(
                    enrollment=enrollment,
                    session=session,
                    defaults={
                        'status': item['status'],
                        'notes': item.get('notes', ''),
                        'excuse_reason': item.get('excuse_reason', ''),
                        'recorded_by': self.context.get('request').user,
                        'check_in_time': timezone.now() if item['status'] != 'absent' else None
                    }
                )
                created_attendances.append(attendance)
            
            # Mark session as attendance taken
            session.attendance_taken = True
            session.save()
            
            # Create or update attendance report
            report, _ = AttendanceReport.objects.get_or_create(
                session=session,
                defaults={'teacher': session.class_obj.teacher}
            )
            report.calculate_statistics()
        
        return created_attendances


class AttendanceReportSerializer(serializers.ModelSerializer):
    """
    Attendance Report Serializer
    """
    session_title = serializers.CharField(source='session.title', read_only=True)
    session_date = serializers.DateField(source='session.date', read_only=True)
    class_name = serializers.CharField(source='session.class_obj.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    
    class Meta:
        model = AttendanceReport
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'submitted_at',
            'total_students', 'present_count', 'absent_count',
            'late_count', 'excused_count', 'attendance_rate'
        ]


class StudentAttendanceSummarySerializer(serializers.Serializer):
    """
    Student Attendance Summary Serializer
    """
    total_sessions = serializers.IntegerField()
    attended_sessions = serializers.IntegerField()
    absent_sessions = serializers.IntegerField()
    late_sessions = serializers.IntegerField()
    excused_sessions = serializers.IntegerField()
    attendance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    recent_attendances = AttendanceListSerializer(many=True)
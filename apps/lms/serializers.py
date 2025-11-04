from rest_framework import serializers
from django.utils import timezone
from .models import (
    CourseMaterial, Assignment, AssignmentSubmission,
    OnlineSession, OnlineSessionParticipant
)
from apps.accounts.serializers import UserSerializer


class CourseMaterialSerializer(serializers.ModelSerializer):
    """
    Course Material Serializer
    """
    material_type_display = serializers.CharField(
        source='get_material_type_display',
        read_only=True
    )
    uploaded_by_name = serializers.CharField(
        source='uploaded_by.get_full_name',
        read_only=True
    )
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseMaterial
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'uploaded_by',
            'file_size', 'download_count', 'view_count'
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


class AssignmentSerializer(serializers.ModelSerializer):
    """
    Assignment Serializer
    """
    assignment_type_display = serializers.CharField(
        source='get_assignment_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    submission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 'assigned_date'
        ]
    
    def get_submission_count(self, obj):
        return obj.submissions.count()
    
    def validate(self, attrs):
        # Validate due date
        assigned_date = timezone.now()
        due_date = attrs.get('due_date')
        
        if due_date and due_date <= assigned_date:
            raise serializers.ValidationError({
                'due_date': 'مهلت ارسال باید در آینده باشد'
            })
        
        return attrs


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """
    Assignment Submission Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    graded_by_name = serializers.CharField(
        source='graded_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = AssignmentSubmission
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'submitted_at',
            'is_late', 'graded_by', 'graded_at', 'resubmission_count'
        ]
    
    def validate(self, attrs):
        assignment = attrs.get('assignment')
        student = attrs.get('student', self.context.get('request').user)
        
        # Check if already submitted
        if not self.instance:  # Creating new submission
            if AssignmentSubmission.objects.filter(
                assignment=assignment,
                student=student
            ).exists():
                raise serializers.ValidationError(
                    'شما قبلاً پاسخ خود را ارسال کرده‌اید'
                )
        
        # Check if assignment is still accepting submissions
        if not assignment.late_submission_allowed and timezone.now() > assignment.due_date:
            raise serializers.ValidationError(
                'مهلت ارسال تکلیف به پایان رسیده است'
            )
        
        return attrs


class GradeSubmissionSerializer(serializers.Serializer):
    """
    Grade Submission Serializer
    """
    submission_id = serializers.UUIDField()
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)
    
    def validate_score(self, value):
        submission_id = self.initial_data.get('submission_id')
        try:
            submission = AssignmentSubmission.objects.get(id=submission_id)
            if value > submission.assignment.max_score:
                raise serializers.ValidationError(
                    f'نمره نمی‌تواند بیشتر از {submission.assignment.max_score} باشد'
                )
        except AssignmentSubmission.DoesNotExist:
            pass
        
        return value


class OnlineSessionSerializer(serializers.ModelSerializer):
    """
    Online Session Serializer
    """
    class_session_title = serializers.CharField(
        source='class_session.title',
        read_only=True
    )
    class_name = serializers.CharField(
        source='class_session.class_obj.name',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineSession
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'meeting_id',
            'moderator_password', 'attendee_password',
            'started_at', 'ended_at', 'recording_url', 'recording_size'
        ]
    
    def get_duration_minutes(self, obj):
        if obj.started_at and obj.ended_at:
            delta = obj.ended_at - obj.started_at
            return int(delta.total_seconds() / 60)
        return None
    
    def get_participant_count(self, obj):
        return obj.participants.count()


class OnlineSessionParticipantSerializer(serializers.ModelSerializer):
    """
    Online Session Participant Serializer
    """
    user_details = UserSerializer(source='user', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineSessionParticipant
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'duration_seconds']
    
    def get_duration_minutes(self, obj):
        return round(obj.duration_seconds / 60, 2)


class CreateOnlineSessionSerializer(serializers.Serializer):
    """
    Create Online Session Serializer
    """
    class_session_id = serializers.UUIDField()
    max_participants = serializers.IntegerField(default=100)
    is_recorded = serializers.BooleanField(default=True)
    allow_chat = serializers.BooleanField(default=True)
    allow_webcam = serializers.BooleanField(default=True)
    allow_microphone = serializers.BooleanField(default=True)
    allow_screen_share = serializers.BooleanField(default=False)


class JoinSessionSerializer(serializers.Serializer):
    """
    Join Session Serializer
    """
    session_id = serializers.UUIDField()
    full_name = serializers.CharField(max_length=255)
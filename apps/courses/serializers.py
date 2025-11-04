from rest_framework import serializers
from django.utils import timezone
from django.db.models import Avg, Count

from apps.lms.serializers import AssignmentSerializer, CourseMaterialSerializer
from .models import Course, Class, ClassSession, Term, TeacherReview
from apps.accounts.serializers import UserSerializer
from apps.branches.serializers import BranchSerializer, ClassroomSerializer


class CourseSerializer(serializers.ModelSerializer):
    """
    Course Serializer
    """
    prerequisites_details = serializers.SerializerMethodField()
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    active_classes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_enrollments', 
                           'average_rating', 'total_reviews']

    def get_prerequisites_details(self, obj):
        if obj.prerequisites.exists():
            return CourseListSerializer(obj.prerequisites.all(), many=True).data
        return []

    def get_active_classes_count(self, obj):
        return obj.classes.filter(
            status=Class.ClassStatus.SCHEDULED,
            is_registration_open=True
        ).count()


class CourseListSerializer(serializers.ModelSerializer):
    """
    Simplified Course List Serializer
    """
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'code', 'slug', 'short_description',
            'level', 'level_display', 'duration_hours', 'sessions_count',
            'base_price', 'thumbnail', 'is_featured', 'average_rating',
            'total_reviews', 'status'
        ]


class ClassSessionSerializer(serializers.ModelSerializer):
    """
    Class Session Serializer
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ClassSession
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClassSerializer(serializers.ModelSerializer):
    """
    Class Serializer
    """
    course_details = CourseListSerializer(source='course', read_only=True)
    branch_details = BranchSerializer(source='branch', read_only=True)
    classroom_details = ClassroomSerializer(source='classroom', read_only=True)
    teacher_details = UserSerializer(source='teacher', read_only=True)
    
    sessions = ClassSessionSerializer(many=True, read_only=True)
    
    # اضافه کردن این فیلدها:
    course_materials = CourseMaterialSerializer(many=True, read_only=True)
    class_assignments = AssignmentSerializer(many=True, read_only=True)
    
    class_type_display = serializers.CharField(source='get_class_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    is_full = serializers.BooleanField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'code', 'current_enrollments',
            'bbb_meeting_id', 'bbb_moderator_password', 'bbb_attendee_password'
        ]

    def validate(self, attrs):
        # Validate dates
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد'
            })

        # Validate times
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                'end_time': 'ساعت پایان باید بعد از ساعت شروع باشد'
            })

        # Validate registration period
        registration_start = attrs.get('registration_start')
        registration_end = attrs.get('registration_end')
        if registration_start and registration_end:
            if registration_end < registration_start:
                raise serializers.ValidationError({
                    'registration_end': 'پایان ثبت‌نام نمی‌تواند قبل از شروع آن باشد'
                })

        # Validate capacity
        capacity = attrs.get('capacity')
        course = attrs.get('course')
        if capacity and course:
            if capacity < course.min_students:
                raise serializers.ValidationError({
                    'capacity': f'ظرفیت نمی‌تواند کمتر از {course.min_students} باشد'
                })
            if capacity > course.max_students:
                raise serializers.ValidationError({
                    'capacity': f'ظرفیت نمی‌تواند بیشتر از {course.max_students} باشد'
                })

        # Validate classroom for in-person classes
        class_type = attrs.get('class_type')
        classroom = attrs.get('classroom')
        if class_type == Class.ClassType.IN_PERSON and not classroom:
            raise serializers.ValidationError({
                'classroom': 'برای کلاس حضوری باید کلاس فیزیکی مشخص شود'
            })

        return attrs


class ClassListSerializer(serializers.ModelSerializer):
    """
    Simplified Class List Serializer
    """
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_level = serializers.CharField(source='course.get_level_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    
    available_seats = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Class
        fields = [
            'id', 'name', 'code', 'course_name', 'course_level',
            'branch_name', 'teacher_name', 'class_type', 'start_date',
            'end_date', 'start_time', 'end_time', 'capacity',
            'current_enrollments', 'available_seats', 'is_full',
            'price', 'status', 'is_registration_open'
        ]


class TermSerializer(serializers.ModelSerializer):
    """
    Term Serializer
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    is_registration_open = serializers.SerializerMethodField()
    classes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Term
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_active(self, obj):
        return obj.status == Term.TermStatus.ACTIVE

    def get_is_registration_open(self, obj):
        today = timezone.now().date()
        return obj.registration_start <= today <= obj.registration_end

    def get_classes_count(self, obj):
        # بعداً با enrollment کامل می‌شود
        return 0

    def validate(self, attrs):
        # Validate term dates
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد'
            })

        # Validate registration dates
        reg_start = attrs.get('registration_start')
        reg_end = attrs.get('registration_end')
        if reg_start and reg_end:
            if reg_end < reg_start:
                raise serializers.ValidationError({
                    'registration_end': 'پایان ثبت‌نام نمی‌تواند قبل از شروع آن باشد'
            })
            if start_date and reg_end > start_date:
                raise serializers.ValidationError({
                    'registration_end': 'ثبت‌نام باید قبل از شروع ترم تمام شود'
                })

        # Validate early registration
        early_deadline = attrs.get('early_registration_deadline')
        if early_deadline and reg_start and early_deadline < reg_start:
            raise serializers.ValidationError({
                'early_registration_deadline': 'مهلت ثبت‌نام زودهنگام نمی‌تواند قبل از شروع ثبت‌نام باشد'
            })

        return attrs


class TeacherReviewSerializer(serializers.ModelSerializer):
    """
    Teacher Review Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    
    class Meta:
        model = TeacherReview
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'is_approved',
            'approved_by', 'approved_at'
        ]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('امتیاز باید بین 1 تا 5 باشد')
        return value

    def validate(self, attrs):
        student = attrs.get('student', self.context.get('request').user)
        teacher = attrs.get('teacher')
        class_obj = attrs.get('class_obj')

        # Check if student is enrolled in the class
        # این قسمت بعداً با enrollment کامل می‌شود
        
        # Check if already reviewed
        if TeacherReview.objects.filter(
            student=student,
            teacher=teacher,
            class_obj=class_obj
        ).exists():
            raise serializers.ValidationError('شما قبلاً نظر خود را ثبت کرده‌اید')

        return attrs


class CourseStatisticsSerializer(serializers.Serializer):
    """
    Course Statistics Serializer
    """
    total_courses = serializers.IntegerField()
    active_courses = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    ongoing_classes = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    popular_courses = CourseListSerializer(many=True)
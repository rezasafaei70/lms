from rest_framework import serializers
from django.utils import timezone
from django.db.models import Avg, Count

from apps.lms.serializers import AssignmentSerializer, CourseMaterialSerializer
from .models import Course, Class, ClassSession, PrivateClassPricing, PrivateClassRequest, Term, TeacherReview
from apps.accounts.serializers import UserSerializer
from apps.branches.serializers import BranchSerializer, ClassroomSerializer
from django.core.validators import MinValueValidator, MaxValueValidator

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
    
    
    
class PrivateClassPricingSerializer(serializers.ModelSerializer):
    """
    قیمت‌گذاری کلاس خصوصی
    """
    class_type_display = serializers.CharField(
        source='get_class_type_display',
        read_only=True
    )
    
    class Meta:
        model = PrivateClassPricing
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrivateClassRequestSerializer(serializers.ModelSerializer):
    """
    درخواست کلاس خصوصی - Serializer کامل
    """
    # Related objects
    primary_student_details = UserSerializer(source='primary_student', read_only=True)
    additional_students_details = UserSerializer(
        source='additional_students',
        many=True,
        read_only=True
    )
    course_details = CourseListSerializer(source='course', read_only=True)
    branch_details = BranchSerializer(source='branch', read_only=True)
    preferred_teacher_details = UserSerializer(source='preferred_teacher', read_only=True)
    assigned_teacher_details = UserSerializer(source='assigned_teacher', read_only=True)
    
    # Display fields
    class_type_display = serializers.CharField(
        source='get_class_type_display',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    preferred_time_slot_display = serializers.CharField(
        source='get_preferred_time_slot_display',
        read_only=True
    )
    preferred_location_display = serializers.CharField(
        source='get_preferred_location_display',
        read_only=True
    )
    
    # Calculated fields
    student_count = serializers.IntegerField(read_only=True)
    estimated_pricing = serializers.SerializerMethodField()
    
    # Created class info
    created_class_details = ClassListSerializer(source='created_class', read_only=True)
    
    class Meta:
        model = PrivateClassRequest
        fields = [
            'id', 'request_number', 
            'primary_student', 'primary_student_details',
            'additional_students', 'additional_students_details',
            'course', 'course_details',
            'branch', 'branch_details',
            'class_type', 'class_type_display',
            'preferred_teacher', 'preferred_teacher_details',
            'preferred_days', 'preferred_time_slot', 'preferred_time_slot_display',
            'preferred_location', 'preferred_location_display',
            'sessions_per_week', 'total_sessions', 'session_duration',
            'preferred_start_date',
            'status', 'status_display',
            'assigned_teacher', 'assigned_teacher_details',
            'created_class', 'created_class_details',
            'approved_by', 'approved_at',
            'student_notes', 'admin_notes', 'rejection_reason',
            'student_count', 'estimated_pricing',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'request_number',
            'assigned_teacher', 'created_class', 'approved_by', 'approved_at'
        ]

    def get_estimated_pricing(self, obj):
        """محاسبه قیمت تخمینی"""
        return obj.calculate_estimated_price()

    def validate(self, attrs):
        # بررسی تعداد دانش‌آموزان اضافی
        class_type = attrs.get('class_type')
        additional_students = attrs.get('additional_students', [])
        
        max_additional = {
            PrivateClassRequest.ClassType.PRIVATE: 0,
            PrivateClassRequest.ClassType.SEMI_PRIVATE_2: 1,
            PrivateClassRequest.ClassType.SEMI_PRIVATE_3: 2,
            PrivateClassRequest.ClassType.SEMI_PRIVATE_4: 4,
        }
        
        max_allowed = max_additional.get(class_type, 0)
        if len(additional_students) > max_allowed:
            raise serializers.ValidationError({
                'additional_students': f'برای {class_type} حداکثر {max_allowed} دانش‌آموز اضافی مجاز است'
            })
        
        # بررسی تاریخ شروع
        preferred_start_date = attrs.get('preferred_start_date')
        if preferred_start_date:
            from django.utils import timezone
            if preferred_start_date < timezone.now().date():
                raise serializers.ValidationError({
                    'preferred_start_date': 'تاریخ شروع نمی‌تواند در گذشته باشد'
                })
        
        return attrs


class PrivateClassRequestListSerializer(serializers.ModelSerializer):
    """
    لیست درخواست‌های کلاس خصوصی - ساده شده
    """
    student_name = serializers.CharField(
        source='primary_student.get_full_name',
        read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PrivateClassRequest
        fields = [
            'id', 'request_number', 'student_name', 'course_name',
            'branch_name', 'class_type', 'status', 'status_display',
            'total_sessions', 'student_count', 'preferred_start_date',
            'created_at'
        ]


class ApprovePrivateClassSerializer(serializers.Serializer):
    """
    تایید درخواست کلاس خصوصی
    """
    teacher = serializers.UUIDField(required=True)
    custom_price_per_session = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        required=False,
        allow_null=True,
        help_text='قیمت سفارشی - اگر خالی باشد از جدول قیمت استفاده می‌شود'
    )
    discount_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    admin_notes = serializers.CharField(required=False, allow_blank=True)


class CreateClassFromRequestSerializer(serializers.Serializer):
    """
    ایجاد کلاس از درخواست
    """
    start_date = serializers.DateField()
    schedule_days = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        help_text='["saturday", "monday", "wednesday"]'
    )
    start_time = serializers.TimeField()
    classroom = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_schedule_days(self, value):
        valid_days = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for day in value:
            if day not in valid_days:
                raise serializers.ValidationError(f'روز {day} معتبر نیست')
        return value

    def validate_start_date(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError('تاریخ شروع نمی‌تواند در گذشته باشد')
        return value
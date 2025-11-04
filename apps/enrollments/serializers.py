from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    Enrollment, PlacementTest, WaitingList, EnrollmentTransfer,
    AnnualRegistration, EnrollmentDocument
)
from apps.accounts.serializers import UserSerializer
from apps.courses.serializers import ClassSerializer, ClassListSerializer, CourseListSerializer


class EnrollmentDocumentSerializer(serializers.ModelSerializer):
    """
    Enrollment Document Serializer
    """
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    
    class Meta:
        model = EnrollmentDocument
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'is_verified', 'verified_by', 'verified_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    class_details = ClassListSerializer(source='class_obj', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    
    documents = EnrollmentDocumentSerializer(many=True, read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        read_only=True
    )
    progress_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'enrollment_number',
            'enrollment_date', 'approved_date', 'approved_by',
            'paid_amount', 'attendance_rate', 'total_sessions_attended',
            'certificate_issued', 'certificate_issue_date', 'certificate_number'
        ]

    def validate(self, attrs):
        student = attrs.get('student', self.context.get('request').user)
        class_obj = attrs.get('class_obj')
        
        # Check if already enrolled
        if Enrollment.objects.filter(
            student=student,
            class_obj=class_obj
        ).exclude(
            status__in=[
                Enrollment.EnrollmentStatus.CANCELLED,
                Enrollment.EnrollmentStatus.REJECTED
            ]
        ).exists():
            raise serializers.ValidationError('شما قبلاً در این کلاس ثبت‌نام کرده‌اید')
        
        # Check class capacity
        if class_obj.is_full:
            raise serializers.ValidationError('این کلاس پر شده است')
        
        # Check registration period
        now = timezone.now()
        if not class_obj.is_registration_open:
            raise serializers.ValidationError('ثبت‌نام در این کلاس بسته است')
        
        if not (class_obj.registration_start <= now <= class_obj.registration_end):
            raise serializers.ValidationError('زمان ثبت‌نام در این کلاس به پایان رسیده است')
        
        # Set total_amount from class price
        if not attrs.get('total_amount'):
            attrs['total_amount'] = class_obj.price
        
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        enrollment = super().create(validated_data)
        
        # Increment class enrollments count
        enrollment.class_obj.current_enrollments += 1
        enrollment.class_obj.save()
        
        # Create invoice (این قسمت بعداً با financial کامل می‌شود)
        
        return enrollment


class EnrollmentListSerializer(serializers.ModelSerializer):
    """
    Simplified Enrollment List Serializer
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    course_name = serializers.CharField(source='class_obj.course.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'enrollment_number', 'student_name', 'class_name',
            'course_name', 'status', 'status_display', 'enrollment_date',
            'final_amount', 'paid_amount', 'is_paid', 'attendance_rate'
        ]


class PlacementTestSerializer(serializers.ModelSerializer):
    """
    Placement Test Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    course_details = CourseListSerializer(source='course', read_only=True)
    evaluator_name = serializers.CharField(
        source='evaluated_by.get_full_name',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    level_display = serializers.CharField(
        source='get_determined_level_display',
        read_only=True
    )
    
    class Meta:
        model = PlacementTest
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'evaluated_by', 'evaluated_at'
        ]


class WaitingListSerializer(serializers.ModelSerializer):
    """
    Waiting List Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    class_details = ClassListSerializer(source='class_obj', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WaitingList
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'position',
            'notified_at', 'notification_expires_at'
        ]

    def validate(self, attrs):
        student = attrs.get('student', self.context.get('request').user)
        class_obj = attrs.get('class_obj')
        
        # Check if already in waiting list
        if WaitingList.objects.filter(
            student=student,
            class_obj=class_obj,
            status=WaitingList.WaitingStatus.WAITING
        ).exists():
            raise serializers.ValidationError('شما قبلاً در لیست انتظار این کلاس هستید')
        
        # Check if already enrolled
        if Enrollment.objects.filter(
            student=student,
            class_obj=class_obj,
            status__in=[
                Enrollment.EnrollmentStatus.ACTIVE,
                Enrollment.EnrollmentStatus.APPROVED
            ]
        ).exists():
            raise serializers.ValidationError('شما در این کلاس ثبت‌نام کرده‌اید')
        
        return attrs


class EnrollmentTransferSerializer(serializers.ModelSerializer):
    """
    Enrollment Transfer Serializer
    """
    enrollment_details = EnrollmentListSerializer(source='enrollment', read_only=True)
    from_class_name = serializers.CharField(source='from_class.name', read_only=True)
    to_class_name = serializers.CharField(source='to_class.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EnrollmentTransfer
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'requested_by',
            'request_date', 'approved_by', 'approved_date', 'price_difference'
        ]

    def validate(self, attrs):
        from_class = attrs.get('from_class')
        to_class = attrs.get('to_class')
        
        # Check if classes are different
        if from_class == to_class:
            raise serializers.ValidationError('کلاس مبدا و مقصد نمی‌توانند یکسان باشند')
        
        # Check if same course
        if from_class.course != to_class.course:
            raise serializers.ValidationError('فقط می‌توان بین کلاس‌های یک دوره انتقال داد')
        
        # Check if to_class is full
        if to_class.is_full:
            raise serializers.ValidationError('کلاس مقصد پر شده است')
        
        # Calculate price difference
        attrs['price_difference'] = to_class.price - from_class.price
        
        return attrs


class AnnualRegistrationSerializer(serializers.ModelSerializer):
    """
    Annual Registration Serializer
    """
    student_details = UserSerializer(source='student', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AnnualRegistration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        student = attrs.get('student', self.context.get('request').user)
        academic_year = attrs.get('academic_year')
        
        # Check if already registered for this year
        if AnnualRegistration.objects.filter(
            student=student,
            academic_year=academic_year,
            status__in=[
                AnnualRegistration.RegistrationStatus.ACTIVE,
                AnnualRegistration.RegistrationStatus.PENDING
            ]
        ).exists():
            raise serializers.ValidationError(
                f'شما قبلاً برای سال تحصیلی {academic_year} ثبت‌نام کرده‌اید'
            )
        
        return attrs
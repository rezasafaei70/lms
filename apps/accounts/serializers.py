from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from .models import GradeLevel, User, StudentProfile, TeacherProfile, OTP, LoginHistory
from utils.validators import validate_iranian_mobile, validate_iranian_national_code
import random
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    """
    Basic User Serializer
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'mobile', 'email', 'first_name', 'last_name', 'full_name',
            'national_code', 'gender', 'birth_date', 'age', 'profile_picture',
            'phone', 'address', 'city', 'province', 'postal_code',
            'role', 'is_active', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'role']

class GradeLevelSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای پایه تحصیلی
    """
    class Meta:
        model = GradeLevel
        fields = ['id', 'name', 'order', 'stage']

class StudentProfileSerializer(serializers.ModelSerializer):
    """
    Student Profile Serializer
    """
    user = UserSerializer(read_only=True)
    grade_level_details = GradeLevelSerializer(source='grade_level', read_only=True)
    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'student_number', 'registration_date']


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    Teacher Profile Serializer
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TeacherProfile
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'employee_code', 'rating', 'total_reviews'
        ]


class RegisterSerializer(serializers.Serializer):
    """
    User Registration Serializer
    """
    mobile = serializers.CharField(max_length=11, validators=[validate_iranian_mobile])
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password]
    )
    role = serializers.ChoiceField(
        choices=User.UserRole.choices,
        default=User.UserRole.STUDENT
    )

    def validate_mobile(self, value):
        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        # Create profile based on role
        if user.role == User.UserRole.STUDENT:
            StudentProfile.objects.create(user=user)
        elif user.role == User.UserRole.TEACHER:
            TeacherProfile.objects.create(user=user)
        
        return user


class SendOTPSerializer(serializers.Serializer):
    """
    Send OTP Serializer
    """
    mobile = serializers.CharField(max_length=11, validators=[validate_iranian_mobile])
    purpose = serializers.ChoiceField(
        choices=OTP.OTPPurpose.choices,
        default=OTP.OTPPurpose.LOGIN
    )

    def validate_mobile(self, value):
        # Check cooldown period
        recent_otp = OTP.objects.filter(
            mobile=value,
            created_at__gte=timezone.now() - timedelta(seconds=settings.OTP_COOLDOWN)
        ).first()
        
        if recent_otp:
            remaining_time = settings.OTP_COOLDOWN - (
                timezone.now() - recent_otp.created_at
            ).seconds
            raise serializers.ValidationError(
                f"لطفاً {remaining_time} ثانیه دیگر مجدداً تلاش کنید"
            )
        
        return value

    def create(self, validated_data):
        mobile = validated_data['mobile']
        purpose = validated_data['purpose']
        
        # Generate OTP code
        code = ''.join([str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH)])
        
        # Get request data
        request = self.context.get('request')
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        # Create OTP
        otp = OTP.objects.create(
            mobile=mobile,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(seconds=settings.OTP_EXPIRE_TIME),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send SMS
        from utils.sms import send_otp_sms
        send_otp_sms(mobile, code)
        
        return otp


class VerifyOTPSerializer(serializers.Serializer):
    """
    Verify OTP Serializer
    """
    mobile = serializers.CharField(max_length=11, validators=[validate_iranian_mobile])
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        mobile = attrs.get('mobile')
        code = attrs.get('code')
        
        # Find OTP
        try:
            otp = OTP.objects.filter(
                mobile=mobile,
                code=code,
                is_used=False,
                is_expired=False
            ).latest('created_at')
        except OTP.DoesNotExist:
            raise serializers.ValidationError("کد وارد شده نامعتبر است")
        
        # Check if OTP is valid
        if not otp.is_valid():
            raise serializers.ValidationError("کد وارد شده منقضی شده است")
        
        # Check attempts
        if otp.attempts >= settings.MAX_OTP_ATTEMPTS:
            otp.is_expired = True
            otp.save()
            raise serializers.ValidationError(
                "تعداد تلاش‌های شما به حداکثر رسیده است. لطفاً کد جدید دریافت کنید"
            )
        
        # Increment attempts
        otp.attempts += 1
        otp.save()
        
        attrs['otp'] = otp
        return attrs

    def save(self):
        otp = self.validated_data['otp']
        otp.is_used = True
        otp.verified_at = timezone.now()
        otp.save()
        
        # Get or create user
        user, created = User.objects.get_or_create(
            mobile=otp.mobile,
            defaults={
                'is_active': True,
                'mobile_verified_at': timezone.now()
            }
        )
        
        if not created and not user.mobile_verified_at:
            user.mobile_verified_at = timezone.now()
            user.save()
        
        return user


class LoginSerializer(serializers.Serializer):
    """
    Login with OTP Serializer
    """
    mobile = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        verify_serializer = VerifyOTPSerializer(data=attrs, context=self.context)
        verify_serializer.is_valid(raise_exception=True)
        attrs['user'] = verify_serializer.save()
        return attrs


class PasswordLoginSerializer(serializers.Serializer):
    """
    Login with Mobile and Password (Optional)
    """
    mobile = serializers.CharField(max_length=11)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        mobile = attrs.get('mobile')
        password = attrs.get('password')
        
        user = authenticate(username=mobile, password=password)
        
        if not user:
            raise serializers.ValidationError("شماره موبایل یا رمز عبور اشتباه است")
        
        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری شما غیرفعال است")
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Change Password Serializer
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("رمز عبور فعلی اشتباه است")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "رمز عبور جدید و تکرار آن مطابقت ندارند"
            })
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LoginHistorySerializer(serializers.ModelSerializer):
    """
    Login History Serializer
    """
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LoginHistory
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
        
        

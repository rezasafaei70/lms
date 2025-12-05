from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from .models import GradeLevel, User, StudentProfile, TeacherProfile, OTP, LoginHistory
from utils.validators import validate_iranian_mobile, validate_iranian_national_code
from utils.fields import S3ImageField, S3DocumentField
import random
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    """
    Basic User Serializer
    
    Supports S3 upload for profile_picture:
    - Use profile_picture_id (file_id from multipart upload)
    - Or direct file upload
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    
    # Support S3 file reference
    profile_picture_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'mobile', 'email', 'first_name', 'last_name', 'full_name',
            'national_code', 'gender', 'birth_date', 'age', 'profile_picture',
            'profile_picture_url', 'profile_picture_id',
            'phone', 'address', 'city', 'province', 'postal_code',
            'role', 'is_active', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'role']
    
    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            try:
                from utils.storage import get_s3_upload_manager
                manager = get_s3_upload_manager()
                return manager.get_file_url(obj.profile_picture.name)
            except Exception:
                request = self.context.get('request')
                if request and obj.profile_picture:
                    return request.build_absolute_uri(obj.profile_picture.url)
        return None
    
    def validate(self, attrs):
        # Handle S3 file reference for profile picture
        profile_picture_id = attrs.pop('profile_picture_id', None)
        
        if profile_picture_id:
            from apps.core.models import UploadedFile
            try:
                uploaded_file = UploadedFile.objects.get(id=profile_picture_id)
                attrs['profile_picture'] = uploaded_file.s3_key
                uploaded_file.is_temp = False
                uploaded_file.save()
            except UploadedFile.DoesNotExist:
                raise serializers.ValidationError({'profile_picture_id': 'فایل پیدا نشد'})
        
        return attrs

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
    
    Supports S3 upload for documents:
    - Use id_card_image_id, birth_certificate_image_id from multipart upload
    """
    user = UserSerializer(read_only=True)
    grade_level_details = GradeLevelSerializer(source='grade_level', read_only=True)
    
    # S3 file URLs
    id_card_image_url = serializers.SerializerMethodField()
    birth_certificate_image_url = serializers.SerializerMethodField()
    
    # S3 file references
    id_card_image_id = serializers.UUIDField(write_only=True, required=False)
    birth_certificate_image_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'student_number', 'registration_date']
    
    def _get_s3_url(self, file_field):
        if file_field:
            try:
                from utils.storage import get_s3_upload_manager
                manager = get_s3_upload_manager()
                return manager.get_file_url(file_field.name)
            except Exception:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(file_field.url)
        return None
    
    def get_id_card_image_url(self, obj):
        return self._get_s3_url(obj.id_card_image)
    
    def get_birth_certificate_image_url(self, obj):
        return self._get_s3_url(obj.birth_certificate_image)
    
    def validate(self, attrs):
        from apps.core.models import UploadedFile
        
        file_fields = {
            'id_card_image_id': 'id_card_image',
            'birth_certificate_image_id': 'birth_certificate_image',
        }
        
        for id_field, target_field in file_fields.items():
            file_id = attrs.pop(id_field, None)
            if file_id:
                try:
                    uploaded_file = UploadedFile.objects.get(id=file_id)
                    attrs[target_field] = uploaded_file.s3_key
                    uploaded_file.is_temp = False
                    uploaded_file.save()
                except UploadedFile.DoesNotExist:
                    raise serializers.ValidationError({id_field: 'فایل پیدا نشد'})
        
        return attrs


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    Teacher Profile Serializer
    
    Supports S3 upload for documents (resume, certificates, contract_file):
    - Use resume_id, certificates_id, contract_file_id from multipart upload
    - Or direct file upload
    """
    user = UserSerializer(read_only=True)
    
    # S3 file URLs
    resume_url = serializers.SerializerMethodField()
    certificates_url = serializers.SerializerMethodField()
    contract_file_url = serializers.SerializerMethodField()
    
    # S3 file references
    resume_id = serializers.UUIDField(write_only=True, required=False)
    certificates_id = serializers.UUIDField(write_only=True, required=False)
    contract_file_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = TeacherProfile
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'employee_code', 'rating', 'total_reviews'
        ]
    
    def _get_s3_url(self, file_field):
        if file_field:
            try:
                from utils.storage import get_s3_upload_manager
                manager = get_s3_upload_manager()
                return manager.get_file_url(file_field.name)
            except Exception:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(file_field.url)
        return None
    
    def get_resume_url(self, obj):
        return self._get_s3_url(obj.resume)
    
    def get_certificates_url(self, obj):
        return self._get_s3_url(obj.certificates)
    
    def get_contract_file_url(self, obj):
        return self._get_s3_url(obj.contract_file)
    
    def validate(self, attrs):
        from apps.core.models import UploadedFile
        
        file_fields = {
            'resume_id': 'resume',
            'certificates_id': 'certificates',
            'contract_file_id': 'contract_file',
        }
        
        for id_field, target_field in file_fields.items():
            file_id = attrs.pop(id_field, None)
            if file_id:
                try:
                    uploaded_file = UploadedFile.objects.get(id=file_id)
                    attrs[target_field] = uploaded_file.s3_key
                    uploaded_file.is_temp = False
                    uploaded_file.save()
                except UploadedFile.DoesNotExist:
                    raise serializers.ValidationError({id_field: 'فایل پیدا نشد'})
        
        return attrs


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
    national_code = serializers.CharField(max_length=11)
    purpose = serializers.ChoiceField(
        choices=OTP.OTPPurpose.choices,
        default=OTP.OTPPurpose.LOGIN
    )

    def validate_national_code(self, value):
        user = User.objects.filter(national_code=value).first()
        recent_otp = OTP.objects.filter(
            mobile=user.mobile,
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
        national_code = validated_data['national_code']
        purpose = validated_data['purpose']
        
        # Generate OTP code
        code = ''.join([str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH)])
        
        # Get request data
        request = self.context.get('request')
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        user = User.objects.filter(national_code=national_code).first()
        mobile = user.mobile
        # Create OTP
        otp = OTP.objects.create(
            mobile=user.mobile,
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
    national_code = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        national_code = attrs.get('national_code')
        code = attrs.get('code')
        user = User.objects.filter(national_code=national_code).first()
        # Find OTP
        try:
            otp = OTP.objects.filter(
                mobile=user.mobile,
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
    national_code = serializers.CharField(max_length=10)
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
        
        

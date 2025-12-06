from rest_framework import serializers
from django.conf import settings
from .models import Branch, Classroom, BranchStaff
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from utils.s3_utils import get_s3_url


class ClassroomSerializer(serializers.ModelSerializer):
    """
    Classroom Serializer
    """
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Classroom
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BranchStaffSerializer(serializers.ModelSerializer):
    """
    Branch Staff Serializer
    """
    user_details = UserSerializer(source='user', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = BranchStaff
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'assigned_date']


class BranchSerializer(serializers.ModelSerializer):
    """
    Branch Serializer
    """
    manager_details = UserSerializer(source='manager', read_only=True)
    classrooms = ClassroomSerializer(many=True, read_only=True)
    staff = BranchStaffSerializer(many=True, read_only=True)
    
    active_classrooms_count = serializers.IntegerField(read_only=True)
    current_students_count = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    # S3 image key for upload
    image_s3_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'code': {'required': False, 'allow_blank': True},
            'image': {'required': False, 'write_only': True},  # Hide raw image field, only return image_url
        }
    
    def get_image_url(self, obj):
        if obj.image:
            image_str = str(obj.image)
            return get_s3_url(image_str)
        return None

    def validate(self, attrs):
        # Handle S3 image key
        image_s3_key = attrs.pop('image_s3_key', None)
        if image_s3_key:
            # Store the S3 key in the image field
            attrs['image'] = image_s3_key
        
        # Validate manager role
        manager = attrs.get('manager')
        if manager and hasattr(manager, 'role') and manager.role != 'branch_manager':
            raise serializers.ValidationError({
                'manager': 'کاربر انتخاب شده باید نقش مدیر شعبه داشته باشد'
            })
        return attrs

    def create(self, validated_data):
        # Generate branch code if not provided
        if not validated_data.get('code'):
            import random
            while True:
                code = f"BR{random.randint(1000, 9999)}"
                if not Branch.objects.filter(code=code).exists():
                    validated_data['code'] = code
                    break
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Don't allow changing code after creation
        validated_data.pop('code', None)
        return super().update(instance, validated_data)


class BranchListSerializer(serializers.ModelSerializer):
    """
    Simplified Branch List Serializer
    """
    manager_name = serializers.SerializerMethodField()
    manager_details = UserSerializer(source='manager', read_only=True)
    classrooms_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'code', 'city', 'province', 'phone', 'email',
            'address', 'postal_code', 'manager', 'manager_name', 'manager_details',
            'status', 'classrooms_count', 'is_active', 'total_capacity',
            'working_hours_start', 'working_hours_end', 'working_days',
            'description', 'facilities', 'established_date', 'image_url'  # Removed 'image', only image_url
        ]
    
    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.get_full_name()
        return None
    
    def get_classrooms_count(self, obj):
        return obj.classrooms.filter(is_active=True).count()
    
    def get_image_url(self, obj):
        if obj.image:
            image_str = str(obj.image)
            return get_s3_url(image_str)
        return None
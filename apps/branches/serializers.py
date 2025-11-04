from rest_framework import serializers
from .models import Branch, Classroom, BranchStaff
from apps.accounts.serializers import UserSerializer


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
    
    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'code']

    def validate(self, attrs):
        # Validate manager role
        manager = attrs.get('manager')
        if manager and manager.role != User.UserRole.BRANCH_MANAGER:
            raise serializers.ValidationError({
                'manager': 'کاربر انتخاب شده باید نقش مدیر شعبه داشته باشد'
            })
        return attrs

    def create(self, validated_data):
        # Generate branch code
        if not validated_data.get('code'):
            import random
            validated_data['code'] = f"BR{random.randint(1000, 9999)}"
        return super().create(validated_data)


class BranchListSerializer(serializers.ModelSerializer):
    """
    Simplified Branch List Serializer
    """
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    classrooms_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'code', 'city', 'province', 'phone',
            'manager_name', 'status', 'classrooms_count', 'is_active'
        ]
    
    def get_classrooms_count(self, obj):
        return obj.classrooms.filter(is_active=True).count()
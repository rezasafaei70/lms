from rest_framework import serializers
from .models import (
    Lead, LeadActivity, Campaign, CampaignLead,
    CustomerFeedback, LoyaltyProgram, CustomerLoyaltyPoints, Referral
)
from apps.accounts.serializers import UserSerializer


class LeadActivitySerializer(serializers.ModelSerializer):
    """
    Lead Activity Serializer
    """
    activity_type_display = serializers.CharField(
        source='get_activity_type_display',
        read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = LeadActivity
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'activity_date']


class LeadSerializer(serializers.ModelSerializer):
    """
    Lead Serializer
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    assigned_to_name = serializers.CharField(
        source='assigned_to.get_full_name',
        read_only=True
    )
    interested_course_name = serializers.CharField(
        source='interested_course.name',
        read_only=True
    )
    
    activities = LeadActivitySerializer(many=True, read_only=True)
    recent_activities = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'converted_to_student', 'converted_at'
        ]
    
    def get_recent_activities(self, obj):
        activities = obj.activities.all()[:5]
        return LeadActivitySerializer(activities, many=True).data
    
    def validate_mobile(self, value):
        # Check if lead with this mobile already exists
        if Lead.objects.filter(mobile=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError('لیدی با این شماره موبایل قبلاً ثبت شده است')
        return value


class CampaignLeadSerializer(serializers.ModelSerializer):
    """
    Campaign Lead Serializer
    """
    lead_details = LeadSerializer(source='lead', read_only=True)
    
    class Meta:
        model = CampaignLead
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'sent_at', 'delivered_at',
            'opened_at', 'clicked_at', 'converted_at'
        ]


class CampaignSerializer(serializers.ModelSerializer):
    """
    Campaign Serializer
    """
    campaign_type_display = serializers.CharField(
        source='get_campaign_type_display',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    conversion_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    roi = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    leads_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'total_sent', 'total_delivered', 'total_opened',
            'total_clicked', 'total_conversions'
        ]
    
    def get_leads_count(self, obj):
        return obj.campaign_leads.count()


class CustomerFeedbackSerializer(serializers.ModelSerializer):
    """
    Customer Feedback Serializer
    """
    feedback_type_display = serializers.CharField(
        source='get_feedback_type_display',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    assigned_to_name = serializers.CharField(
        source='assigned_to.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = CustomerFeedback
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'resolved_at', 'resolved_by'
        ]


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    """
    Loyalty Program Serializer
    """
    class Meta:
        model = LoyaltyProgram
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerLoyaltyPointsSerializer(serializers.ModelSerializer):
    """
    Customer Loyalty Points Serializer
    """
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = CustomerLoyaltyPoints
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'balance_after']


class ReferralSerializer(serializers.ModelSerializer):
    """
    Referral Serializer
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    referrer_name = serializers.CharField(
        source='referrer.get_full_name',
        read_only=True
    )
    referred_user_name = serializers.CharField(
        source='referred_user.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Referral
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'referred_user',
            'reward_given', 'rewarded_at'
        ]
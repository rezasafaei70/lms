from django.contrib import admin
from .models import (
    Lead, LeadActivity, Campaign, CampaignLead,
    CustomerFeedback, LoyaltyProgram, CustomerLoyaltyPoints, Referral
)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'mobile', 'status', 'source',
        'assigned_to', 'score', 'created_at'
    ]
    list_filter = ['status', 'source', 'created_at']
    search_fields = ['first_name', 'last_name', 'mobile', 'email']
    ordering = ['-created_at']
    readonly_fields = ['converted_at']


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = [
        'lead', 'activity_type', 'subject',
        'performed_by', 'activity_date'
    ]
    list_filter = ['activity_type', 'activity_date']
    search_fields = ['lead__first_name', 'lead__last_name', 'subject']
    ordering = ['-activity_date']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'campaign_type', 'status', 'start_date',
        'total_sent', 'total_conversions', 'conversion_rate'
    ]
    list_filter = ['campaign_type', 'status', 'start_date']
    search_fields = ['name', 'description']
    ordering = ['-created_at']


@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    list_display = [
        'campaign', 'lead', 'sent_at', 'delivered_at',
        'opened_at', 'converted_at'
    ]
    list_filter = ['campaign', 'sent_at']
    ordering = ['-created_at']


@admin.register(CustomerFeedback)
class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'feedback_type', 'subject', 'status',
        'priority', 'created_at'
    ]
    list_filter = ['feedback_type', 'status', 'priority', 'created_at']
    search_fields = ['customer__first_name', 'subject', 'message']
    ordering = ['-created_at']


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'is_active', 'start_date', 'end_date',
        'points_per_enrollment', 'points_per_referral'
    ]
    list_filter = ['is_active', 'start_date']
    ordering = ['-created_at']


@admin.register(CustomerLoyaltyPoints)
class CustomerLoyaltyPointsAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'program', 'transaction_type',
        'points', 'balance_after', 'created_at'
    ]
    list_filter = ['transaction_type', 'program', 'created_at']
    search_fields = ['customer__first_name', 'customer__last_name']
    ordering = ['-created_at']


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'referrer', 'referred_name', 'referred_mobile',
        'status', 'reward_given', 'created_at'
    ]
    list_filter = ['status', 'reward_given', 'created_at']
    search_fields = [
        'referrer__first_name', 'referred_name', 'referred_mobile'
    ]
    ordering = ['-created_at']
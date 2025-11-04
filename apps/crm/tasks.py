from celery import shared_task
from django.utils import timezone
from .models import Campaign, CampaignLead


@shared_task
def execute_campaign(campaign_id):
    """
    Execute marketing campaign
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        
        if campaign.campaign_type == Campaign.CampaignType.SMS:
            execute_sms_campaign(campaign)
        elif campaign.campaign_type == Campaign.CampaignType.EMAIL:
            execute_email_campaign(campaign)
        
    except Campaign.DoesNotExist:
        pass


def execute_sms_campaign(campaign):
    """
    Execute SMS campaign
    """
    from utils.sms import send_sms
    
    campaign_leads = campaign.campaign_leads.filter(sent_at__isnull=True)
    
    for campaign_lead in campaign_leads:
        # Render message
        message = campaign.message_template
        # You can add variable substitution here
        
        # Send SMS
        success = send_sms(campaign_lead.lead.mobile, message)
        
        if success:
            campaign_lead.sent_at = timezone.now()
            campaign_lead.delivered_at = timezone.now()
            campaign.total_sent += 1
            campaign.total_delivered += 1
        
        campaign_lead.save()
    
    campaign.save()


def execute_email_campaign(campaign):
    """
    Execute email campaign
    """
    from utils.helpers import send_email
    
    campaign_leads = campaign.campaign_leads.filter(sent_at__isnull=True)
    
    for campaign_lead in campaign_leads:
        if not campaign_lead.lead.email:
            continue
        
        message = campaign.message_template
        
        success = send_email(
            subject=campaign.name,
            message=message,
            recipient_list=[campaign_lead.lead.email]
        )
        
        if success:
            campaign_lead.sent_at = timezone.now()
            campaign.total_sent += 1
        
        campaign_lead.save()
    
    campaign.save()
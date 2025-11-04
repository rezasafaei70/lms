"""
LMS Utility Functions
"""
import hashlib
import random
import string
from django.conf import settings
from bigbluebutton_api_python import BigBlueButton


def get_bbb_client():
    """
    Get BigBlueButton API client
    """
    return BigBlueButton(
        settings.BBB_URL,
        settings.BBB_SECRET
    )


def create_bbb_meeting(class_session, max_participants=100, is_recorded=True):
    """
    Create BigBlueButton meeting
    """
    import secrets
    
    # Generate meeting credentials
    meeting_id = f"{class_session.class_obj.code}_{class_session.session_number}_{secrets.token_hex(4)}"
    moderator_password = secrets.token_urlsafe(16)
    attendee_password = secrets.token_urlsafe(16)
    
    bbb = get_bbb_client()
    
    # Create meeting
    try:
        meeting = bbb.create_meeting(
            name=f"{class_session.class_obj.name} - {class_session.title}",
            meeting_id=meeting_id,
            attendee_pw=attendee_password,
            moderator_pw=moderator_password,
            record=is_recorded,
            auto_start_recording=is_recorded,
            allow_start_stop_recording=True,
            max_participants=max_participants,
            welcome_msg=f"به کلاس {class_session.class_obj.name} خوش آمدید",
            logout_url=settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else '/',
        )
        
        return {
            'meeting_id': meeting_id,
            'moderator_password': moderator_password,
            'attendee_password': attendee_password,
            'success': True
        }
    except Exception as e:
        print(f"Error creating BBB meeting: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_bbb_join_url(online_session, user, is_moderator=False):
    """
    Get BigBlueButton join URL
    """
    bbb = get_bbb_client()
    
    password = (
        online_session.moderator_password if is_moderator
        else online_session.attendee_password
    )
    
    try:
        join_url = bbb.get_join_meeting_url(
            name=user.get_full_name(),
            meeting_id=online_session.meeting_id,
            password=password,
            user_id=str(user.id),
            avatar_url=user.profile_picture.url if user.profile_picture else None
        )
        
        return join_url
    except Exception as e:
        print(f"Error getting join URL: {e}")
        return None


def end_bbb_meeting(meeting_id):
    """
    End BigBlueButton meeting
    """
    bbb = get_bbb_client()
    
    try:
        # Get meeting info to get moderator password
        from .models import OnlineSession
        online_session = OnlineSession.objects.get(meeting_id=meeting_id)
        
        bbb.end_meeting(
            meeting_id=meeting_id,
            password=online_session.moderator_password
        )
        
        return True
    except Exception as e:
        print(f"Error ending meeting: {e}")
        return False


def get_bbb_recordings(meeting_id):
    """
    Get BigBlueButton recordings
    """
    bbb = get_bbb_client()
    
    try:
        recordings = bbb.get_recordings(meeting_id=meeting_id)
        
        recordings_list = []
        if recordings and 'recordings' in recordings:
            for recording in recordings['recordings']:
                recordings_list.append({
                    'record_id': recording.get('recordID'),
                    'meeting_id': recording.get('meetingID'),
                    'name': recording.get('name'),
                    'published': recording.get('published'),
                    'start_time': recording.get('startTime'),
                    'end_time': recording.get('endTime'),
                    'playback_url': recording.get('playback', {}).get('format', {}).get('url'),
                    'size': recording.get('size', 0)
                })
        
        return recordings_list
    except Exception as e:
        print(f"Error getting recordings: {e}")
        return []


def is_meeting_running(meeting_id):
    """
    Check if BBB meeting is running
    """
    bbb = get_bbb_client()
    
    try:
        return bbb.is_meeting_running(meeting_id)
    except Exception as e:
        print(f"Error checking meeting status: {e}")
        return False


def get_meeting_info(meeting_id, moderator_password):
    """
    Get BigBlueButton meeting info
    """
    bbb = get_bbb_client()
    
    try:
        info = bbb.get_meeting_info(
            meeting_id=meeting_id,
            password=moderator_password
        )
        
        return {
            'participant_count': info.get('participantCount', 0),
            'moderator_count': info.get('moderatorCount', 0),
            'listener_count': info.get('listenerCount', 0),
            'voice_participant_count': info.get('voiceParticipantCount', 0),
            'video_count': info.get('videoCount', 0),
            'is_recording': info.get('recording', False),
            'has_user_joined': info.get('hasUserJoined', False),
            'start_time': info.get('startTime'),
            'end_time': info.get('endTime')
        }
    except Exception as e:
        print(f"Error getting meeting info: {e}")
        return None


def generate_certificate(enrollment):
    """
    Generate PDF certificate for completed enrollment
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from io import BytesIO
    import jdatetime
    
    buffer = BytesIO()
    
    # Create PDF
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Add border
    p.setLineWidth(3)
    p.rect(1*cm, 1*cm, width-2*cm, height-2*cm)
    
    # Add title
    p.setFont("Helvetica-Bold", 36)
    p.drawCentredString(width/2, height-4*cm, "Certificate of Completion")
    
    # Add subtitle
    p.setFont("Helvetica", 18)
    p.drawCentredString(width/2, height-6*cm, "This is to certify that")
    
    # Add student name
    p.setFont("Helvetica-Bold", 28)
    p.drawCentredString(width/2, height-8*cm, enrollment.student.get_full_name())
    
    # Add course info
    p.setFont("Helvetica", 18)
    p.drawCentredString(
        width/2,
        height-10*cm,
        f"has successfully completed the course"
    )
    
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width/2, height-12*cm, enrollment.class_obj.course.name)
    
    # Add date
    p.setFont("Helvetica", 14)
    jalali_date = jdatetime.date.today().strftime("%Y/%m/%d")
    p.drawCentredString(width/2, height-15*cm, f"Date: {jalali_date}")
    
    # Add certificate number
    p.drawCentredString(
        width/2,
        height-16*cm,
        f"Certificate No: {enrollment.certificate_number}"
    )
    
    # Save PDF
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer
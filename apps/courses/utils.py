from datetime import datetime, timedelta
from .models import ClassSession


def generate_class_sessions(class_obj):
    """
    Generate class sessions based on class schedule
    """
    sessions = []
    current_date = class_obj.start_date
    session_number = 1
    
    # Map weekday names to numbers
    weekday_map = {
        'saturday': 5,
        'sunday': 6,
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
    }
    
    schedule_days = [weekday_map[day] for day in class_obj.schedule_days]
    
    while current_date <= class_obj.end_date:
        if current_date.weekday() in schedule_days:
            session = ClassSession.objects.create(
                class_obj=class_obj,
                session_number=session_number,
                title=f"جلسه {session_number}",
                date=current_date,
                start_time=class_obj.start_time,
                end_time=class_obj.end_time,
                status=ClassSession.SessionStatus.SCHEDULED
            )
            sessions.append(session)
            session_number += 1
        
        current_date += timedelta(days=1)
    
    return sessions
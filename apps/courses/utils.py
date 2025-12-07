from datetime import datetime, timedelta
from .models import ClassSession


def generate_class_sessions(class_obj, max_sessions=None):
    """
    Generate class sessions based on class schedule
    
    Args:
        class_obj: Class instance
        max_sessions: Maximum number of sessions to generate (optional)
                     If None, uses course.sessions_count or generates until end_date
    """
    sessions = []
    current_date = class_obj.start_date
    session_number = 1
    
    # Map weekday names to numbers (Python weekday: Monday=0, Sunday=6)
    weekday_map = {
        'saturday': 5,
        'sunday': 6,
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
    }
    
    # تعیین حداکثر تعداد جلسات
    if max_sessions is None:
        # اگر دوره تعداد جلسات دارد، از آن استفاده کن
        if class_obj.course and class_obj.course.sessions_count:
            max_sessions = class_obj.course.sessions_count
        else:
            max_sessions = 999  # بدون محدودیت (تا تاریخ پایان)
    
    schedule_days = [weekday_map[day] for day in class_obj.schedule_days]
    
    if not schedule_days:
        return sessions  # اگر روزی انتخاب نشده، جلسه‌ای نساز
    
    while current_date <= class_obj.end_date and session_number <= max_sessions:
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
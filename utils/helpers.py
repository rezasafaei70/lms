import random
import string
from django.core.mail import send_mail
from django.conf import settings
import jdatetime


def generate_random_code(length=6, use_digits=True, use_letters=False):
    """
    Generate random code
    """
    characters = ''
    if use_digits:
        characters += string.digits
    if use_letters:
        characters += string.ascii_uppercase
    
    return ''.join(random.choice(characters) for _ in range(length))


def send_email(subject, message, recipient_list):
    """
    Send email
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def jalali_to_gregorian(jalali_date):
    """
    Convert Jalali date to Gregorian
    """
    if isinstance(jalali_date, str):
        # Parse string date (format: 1402/01/01 or 1402-01-01)
        parts = jalali_date.replace('/', '-').split('-')
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        jalali_date = jdatetime.date(year, month, day)
    
    return jalali_date.togregorian()


def gregorian_to_jalali(gregorian_date):
    """
    Convert Gregorian date to Jalali
    """
    return jdatetime.date.fromgregorian(date=gregorian_date)


def format_price(price):
    """
    Format price with thousand separator
    """
    return f"{price:,.0f} تومان"


def calculate_age(birth_date):
    """
    Calculate age from birth date
    """
    from django.utils import timezone
    today = timezone.now().date()
    age = today.year - birth_date.year
    
    if today.month < birth_date.month or (
        today.month == birth_date.month and today.day < birth_date.day
    ):
        age -= 1
    
    return age
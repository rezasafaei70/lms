from django.core.exceptions import ValidationError
import re


def validate_iranian_mobile(value):
    """
    Validate Iranian mobile number format
    """
    pattern = r'^09\d{9}$'
    if not re.match(pattern, value):
        raise ValidationError(
            'شماره موبایل باید به فرمت 09xxxxxxxxx باشد'
        )


def validate_iranian_national_code(value):
    """
    Validate Iranian national code
    """
    if not value or len(value) != 10:
        raise ValidationError('کد ملی باید 10 رقم باشد')
    
    if not value.isdigit():
        raise ValidationError('کد ملی باید فقط شامل اعداد باشد')
    
    # Check algorithm
    check = int(value[9])
    s = sum(int(value[i]) * (10 - i) for i in range(9)) % 11
    
    if not ((s < 2 and check == s) or (s >= 2 and check + s == 11)):
        raise ValidationError('کد ملی نامعتبر است')


def validate_file_size(file, max_size_mb=10):
    """
    Validate uploaded file size
    """
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            f'حجم فایل نباید بیشتر از {max_size_mb} مگابایت باشد'
        )


def validate_file_extension(file, allowed_extensions):
    """
    Validate uploaded file extension
    """
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f'فرمت فایل مجاز نیست. فرمت‌های مجاز: {", ".join(allowed_extensions)}'
        )
from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException


def send_sms(mobile, message):
    """
    Send SMS using Kavenegar
    """
    try:
        api = KavenegarAPI(settings.KAVENEGAR_API_KEY)
        params = {
            'sender': settings.SMS_SENDER,
            'receptor': mobile,
            'message': message
        }
        response = api.sms_send(params)
        return True
    except APIException as e:
        print(f"API Exception: {e}")
        return False
    except HTTPException as e:
        print(f"HTTP Exception: {e}")
        return False


def send_otp_sms(mobile, code):
    """
    Send OTP SMS
    """
    message = f"کد تایید شما: {code}\nاین کد به مدت 2 دقیقه معتبر است."
    return send_sms(mobile, message)


def send_bulk_sms(recipients, message):
    """
    Send bulk SMS
    """
    try:
        api = KavenegarAPI(settings.KAVENEGAR_API_KEY)
        params = {
            'sender': settings.SMS_SENDER,
            'receptor': recipients,  # List of mobiles
            'message': message
        }
        response = api.sms_sendarray(params)
        return True
    except Exception as e:
        print(f"Bulk SMS error: {e}")
        return False
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'error': True,
            'message': get_error_message(response.data),
            'details': response.data,
            'status_code': response.status_code
        }
        response.data = custom_response_data
    
    return response


def get_error_message(error_data):
    """
    Extract error message from error data
    """
    if isinstance(error_data, dict):
        # Get first error message
        for key, value in error_data.items():
            if isinstance(value, list):
                return value[0] if value else 'خطایی رخ داده است'
            elif isinstance(value, str):
                return value
            elif isinstance(value, dict):
                return get_error_message(value)
    elif isinstance(error_data, list):
        return error_data[0] if error_data else 'خطایی رخ داده است'
    elif isinstance(error_data, str):
        return error_data
    
    return 'خطایی رخ داده است'
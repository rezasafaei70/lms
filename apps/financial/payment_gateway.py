"""
Sadad Payment Gateway Integration

This module provides integration with Sadad (سداد) payment gateway.
Based on official Sadad PHP SDK.

Production URLs:
- Payment Request: https://sadad.shaparak.ir/vpg/api/v0/Request/PaymentRequest
- Payment Page: https://sadad.shaparak.ir/VPG/Purchase?Token=...
- Verify: https://sadad.shaparak.ir/vpg/api/v0/Advice/Verify
"""

import requests
import base64
import hashlib
from datetime import datetime
from django.conf import settings
from django.db import transaction
from .models import Payment, Invoice

# برای رمزنگاری Triple DES - فقط در حالت Production نیاز است
try:
    from Crypto.Cipher import DES3  # type: ignore
    CRYPTO_AVAILABLE = True
except ImportError:
    DES3 = None  # type: ignore
    CRYPTO_AVAILABLE = False


class SadadPaymentGateway:
    """
    Sadad (سداد) Payment Gateway integration class
    
    طبق مستندات رسمی سداد و نمونه کد PHP
    """
    
    # تنظیمات از settings.py
    TERMINAL_ID = getattr(settings, 'SADAD_TERMINAL_ID', '5tlQRAWNSIZKMNO5XwJqE5Oq5yDxUD2M')
    MERCHANT_ID = getattr(settings, 'SADAD_MERCHANT_ID', '000000140334793')
    MERCHANT_KEY = getattr(settings, 'SADAD_MERCHANT_KEY', '24091377')
    
    # حالت تست
    TEST_MODE = getattr(settings, 'SADAD_TEST_MODE', False)
    
    # آدرس‌های API سداد (Production)
    REQUEST_URL = 'https://sadad.shaparak.ir/vpg/api/v0/Request/PaymentRequest'
    VERIFY_URL = 'https://sadad.shaparak.ir/vpg/api/v0/Advice/Verify'
    PAYMENT_PAGE_URL = 'https://sadad.shaparak.ir/VPG/Purchase'
    
    @classmethod
    def encrypt_pkcs7(cls, data: str, key: str) -> str:
        """
        رمزنگاری با Triple DES (DES-EDE3) - مطابق با تابع PHP
        
        PHP equivalent:
        function encrypt_pkcs7($str, $key) {
            $key = base64_decode($key);
            $ciphertext = OpenSSL_encrypt($str, "DES-EDE3", $key, OPENSSL_RAW_DATA);
            return base64_encode($ciphertext);
        }
        """
        # اگر pycryptodome نصب نیست، از روش ساده استفاده کن (فقط برای تست)
        if not CRYPTO_AVAILABLE:
            return base64.b64encode(
                hashlib.sha256(f"{data}{key}".encode()).digest()
            ).decode('utf-8')
        
        try:
            # دیکد کردن کلید از Base64
            key_bytes = base64.b64decode(key)
            
            # اطمینان از اینکه کلید 24 بایت است (برای Triple DES)
            if len(key_bytes) < 24:
                key_bytes = key_bytes + key_bytes[:24 - len(key_bytes)]
            elif len(key_bytes) > 24:
                key_bytes = key_bytes[:24]
            
            # تبدیل داده به بایت
            data_bytes = data.encode('utf-8')
            
            # Padding با PKCS7
            block_size = 8  # DES block size
            padding_length = block_size - (len(data_bytes) % block_size)
            data_bytes += bytes([padding_length] * padding_length)
            
            # رمزنگاری با Triple DES در حالت ECB
            cipher = DES3.new(key_bytes, DES3.MODE_ECB)
            encrypted = cipher.encrypt(data_bytes)
            
            # برگرداندن به صورت Base64
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"Encryption error: {e}")
            # در صورت خطا، از روش ساده استفاده می‌کنیم
            return base64.b64encode(
                hashlib.sha256(f"{data}{key}".encode()).digest()
            ).decode('utf-8')
    
    @classmethod
    def generate_sign_data(cls, terminal_id: str, order_id: str, amount: int) -> str:
        """
        تولید SignData برای درخواست پرداخت
        
        فرمت: TerminalId;OrderId;Amount
        """
        data_to_sign = f"{terminal_id};{order_id};{amount}"
        return cls.encrypt_pkcs7(data_to_sign, cls.MERCHANT_KEY)
    
    @classmethod
    def generate_verify_sign_data(cls, token: str) -> str:
        """
        تولید SignData برای تأیید پرداخت
        
        فرمت: فقط Token
        """
        return cls.encrypt_pkcs7(token, cls.MERCHANT_KEY)
    
    @classmethod
    def create_payment_request(cls, invoice, callback_url):
        """
        ایجاد درخواست پرداخت به درگاه سداد
        
        Args:
            invoice: مدل فاکتور
            callback_url: آدرس بازگشت بعد از پرداخت
            
        Returns:
            dict با token و payment_url یا error
        """
        # شناسه سفارش - حداکثر 20 کاراکتر
        order_id = str(invoice.id).replace('-', '')[:20]
        # مبلغ به ریال
        amount = int(invoice.total_amount)
        
        # حالت تست - شبیه‌سازی درگاه
        if cls.TEST_MODE:
            test_token = f"TEST_TOKEN_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return {
                'success': True,
                'token': test_token,
                'order_id': order_id,
                'payment_url': f"/api/v1/financial/payment/simulate/?token={test_token}&amount={amount}&invoice_id={invoice.id}&callback={callback_url}",
            }
        
        # حالت Production - اتصال واقعی به سداد
        # بررسی نصب بودن pycryptodome
        if not CRYPTO_AVAILABLE:
            return {
                'success': False,
                'error': 'برای اتصال به درگاه واقعی، پکیج pycryptodome باید نصب شود: pip install pycryptodome',
            }
        sign_data = cls.generate_sign_data(cls.TERMINAL_ID, order_id, amount)
        
        payload = {
            'TerminalId': cls.TERMINAL_ID,
            'MerchantId': cls.MERCHANT_ID,
            'Amount': amount,
            'SignData': sign_data,
            'ReturnUrl': callback_url,
            'LocalDateTime': datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'),
            'OrderId': order_id,
        }
        
        try:
            response = requests.post(
                cls.REQUEST_URL,
                json=payload,
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=30
            )
            data = response.json()
            
            if data.get('ResCode') == 0:
                token = data['Token']
                return {
                    'success': True,
                    'token': token,
                    'order_id': order_id,
                    'payment_url': f"{cls.PAYMENT_PAGE_URL}?Token={token}",
                }
            else:
                return {
                    'success': False,
                    'error': data.get('Description', 'خطا در ایجاد درخواست پرداخت'),
                    'error_code': data.get('ResCode'),
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'خطا در اتصال به درگاه پرداخت: {str(e)}',
            }
    
    @classmethod
    def verify_payment(cls, token, invoice):
        """
        تأیید پرداخت (Verify)
        
        Args:
            token: توکن پرداخت از callback
            invoice: مدل فاکتور
            
        Returns:
            dict با نتیجه تأیید
        """
        # حالت تست
        if cls.TEST_MODE:
            if token.startswith('TEST_TOKEN_'):
                return {
                    'success': True,
                    'reference_number': f"REF_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    'system_trace_no': f"SYS_{datetime.now().strftime('%H%M%S')}",
                    'card_number': '6037****1234',
                    'message': 'پرداخت با موفقیت انجام شد',
                }
            else:
                return {
                    'success': False,
                    'error': 'توکن نامعتبر است',
                }
        
        # حالت Production
        sign_data = cls.generate_verify_sign_data(token)
        
        payload = {
            'Token': token,
            'SignData': sign_data,
        }
        
        try:
            response = requests.post(
                cls.VERIFY_URL,
                json=payload,
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=30
            )
            data = response.json()
            
            # بررسی موفقیت - ResCode باید 0 باشد
            if data.get('ResCode') == 0:
                return {
                    'success': True,
                    'reference_number': data.get('RetrivalRefNo'),
                    'system_trace_no': data.get('SystemTraceNo'),
                    'card_number': data.get('CardNo'),
                    'order_id': data.get('OrderId'),
                    'message': 'پرداخت با موفقیت تایید شد',
                }
            else:
                return {
                    'success': False,
                    'error': data.get('Description', 'خطا در تایید پرداخت'),
                    'error_code': data.get('ResCode'),
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'خطا در تأیید پرداخت: {str(e)}',
            }
    
    @classmethod
    @transaction.atomic
    def process_callback(cls, token, status, invoice_id, reference_number=None, card_number=None):
        """
        پردازش callback از درگاه و بروزرسانی دیتابیس
        
        Args:
            token: توکن پرداخت
            status: وضعیت پرداخت ('success' یا 'failed')
            invoice_id: شناسه فاکتور
            reference_number: شماره مرجع بانک (اختیاری)
            card_number: شماره کارت (اختیاری)
            
        Returns:
            dict با نتیجه
        """
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            
            if status == 'success':
                # تأیید پرداخت
                verify_result = cls.verify_payment(token, invoice)
                
                if verify_result['success']:
                    # ایجاد رکورد پرداخت
                    payment = Payment.objects.create(
                        invoice=invoice,
                        student=invoice.student,
                        amount=invoice.total_amount - invoice.paid_amount,
                        payment_method=Payment.PaymentMethod.ONLINE,
                        status=Payment.PaymentStatus.COMPLETED,
                        gateway_transaction_id=token,
                        gateway_reference_id=verify_result.get('reference_number', reference_number),
                        card_number=verify_result.get('card_number', card_number),
                    )
                    
                    # بروزرسانی فاکتور
                    invoice.paid_amount = invoice.total_amount
                    invoice.status = Invoice.InvoiceStatus.PAID
                    invoice.save()
                    
                    return {
                        'success': True,
                        'payment_id': str(payment.id),
                        'message': 'پرداخت با موفقیت انجام شد',
                        'reference_number': payment.gateway_reference_id,
                        'system_trace_no': verify_result.get('system_trace_no'),
                    }
                else:
                    return verify_result
            else:
                # پرداخت ناموفق
                return {
                    'success': False,
                    'error': 'پرداخت توسط کاربر لغو شد یا با خطا مواجه شد',
                }
                
        except Invoice.DoesNotExist:
            return {
                'success': False,
                'error': 'فاکتور یافت نشد',
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }


# توابع کمکی برای views
def initiate_sadad_payment(invoice, callback_url):
    """شروع پرداخت با درگاه سداد"""
    return SadadPaymentGateway.create_payment_request(invoice, callback_url)

def verify_sadad_payment(token, invoice):
    """تأیید پرداخت سداد"""
    return SadadPaymentGateway.verify_payment(token, invoice)

def process_sadad_callback(token, status, invoice_id, reference_number=None, card_number=None):
    """پردازش callback سداد"""
    return SadadPaymentGateway.process_callback(token, status, invoice_id, reference_number, card_number)

"""
Sadad Payment Gateway Integration

This module provides integration with Sadad (سداد) payment gateway.
For testing purposes, it uses the Sadad sandbox/test environment.

Sadad Test Environment:
- Terminal ID: 1234567
- Merchant ID: 1234567
- Public Key: (generated for testing)
- URL: https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest (Production)
- Test URL: https://sandbox.sadad.ir/api/v0/Request/PaymentRequest (Sandbox)
"""

import requests
import hashlib
import base64
import json
from datetime import datetime
from django.conf import settings
from django.db import transaction
from .models import Payment, Invoice


class SadadPaymentGateway:
    """
    Sadad (سداد) Payment Gateway integration class
    
    For testing, we'll simulate the Sadad API responses.
    In production, replace with actual API calls.
    """
    
    # Test credentials - Replace with actual credentials in production
    TERMINAL_ID = getattr(settings, 'SADAD_TERMINAL_ID', 'TEST001')
    MERCHANT_ID = getattr(settings, 'SADAD_MERCHANT_ID', 'TEST001')
    MERCHANT_KEY = getattr(settings, 'SADAD_MERCHANT_KEY', 'TEST_KEY_12345678')
    
    # API URLs
    TEST_MODE = getattr(settings, 'SADAD_TEST_MODE', True)
    REQUEST_URL = 'https://sandbox.sadad.ir/api/v0/Request/PaymentRequest' if TEST_MODE else 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest'
    VERIFY_URL = 'https://sandbox.sadad.ir/api/v0/Advice/Verify' if TEST_MODE else 'https://sadad.shaparak.ir/VPG/api/v0/Advice/Verify'
    PAYMENT_PAGE_URL = 'https://sandbox.sadad.ir/VPG/Purchase' if TEST_MODE else 'https://sadad.shaparak.ir/VPG/Purchase'
    
    @classmethod
    def generate_sign_data(cls, terminal_id, order_id, amount):
        """Generate SignData using Triple DES encryption (simplified for testing)"""
        # In production, use actual TripleDES encryption with the MerchantKey
        data_to_sign = f"{terminal_id};{order_id};{amount}"
        sign = hashlib.sha256(f"{data_to_sign}{cls.MERCHANT_KEY}".encode()).hexdigest()
        return sign
    
    @classmethod
    def create_payment_request(cls, invoice, callback_url):
        """
        Create a payment request to Sadad gateway
        
        Args:
            invoice: Invoice model instance
            callback_url: URL to redirect after payment
            
        Returns:
            dict with token and payment_url or error
        """
        order_id = str(invoice.id).replace('-', '')[:20]  # Sadad requires max 20 chars
        amount = int(invoice.total_amount)  # Amount in Rials
        
        # For test mode, simulate successful token generation
        if cls.TEST_MODE:
            # Generate a test token
            test_token = f"TEST_TOKEN_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return {
                'success': True,
                'token': test_token,
                'order_id': order_id,
                'payment_url': f"/api/v1/financial/payment/simulate?token={test_token}&amount={amount}&invoice_id={invoice.id}&callback={callback_url}",
            }
        
        # Production mode - actual API call
        sign_data = cls.generate_sign_data(cls.TERMINAL_ID, order_id, amount)
        
        payload = {
            'TerminalId': cls.TERMINAL_ID,
            'MerchantId': cls.MERCHANT_ID,
            'Amount': amount,
            'OrderId': order_id,
            'LocalDateTime': datetime.now().strftime('%m/%d/%Y %H:%M:%S'),
            'ReturnUrl': callback_url,
            'SignData': sign_data,
        }
        
        try:
            response = requests.post(
                cls.REQUEST_URL,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            data = response.json()
            
            if data.get('ResCode') == 0:
                return {
                    'success': True,
                    'token': data['Token'],
                    'order_id': order_id,
                    'payment_url': f"{cls.PAYMENT_PAGE_URL}?Token={data['Token']}",
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
                'error': str(e),
            }
    
    @classmethod
    def verify_payment(cls, token, invoice):
        """
        Verify a completed payment
        
        Args:
            token: Payment token from callback
            invoice: Invoice model instance
            
        Returns:
            dict with verification result
        """
        # For test mode, simulate successful verification
        if cls.TEST_MODE:
            if token.startswith('TEST_TOKEN_'):
                return {
                    'success': True,
                    'reference_number': f"REF_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    'card_number': '6037****1234',
                    'message': 'پرداخت با موفقیت انجام شد',
                }
            else:
                return {
                    'success': False,
                    'error': 'توکن نامعتبر است',
                }
        
        # Production mode
        sign_data = cls.generate_sign_data(cls.TERMINAL_ID, token, '')
        
        payload = {
            'Token': token,
            'SignData': sign_data,
        }
        
        try:
            response = requests.post(
                cls.VERIFY_URL,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            data = response.json()
            
            if data.get('ResCode') == 0:
                return {
                    'success': True,
                    'reference_number': data.get('RetrivalRefNo'),
                    'system_trace_no': data.get('SystemTraceNo'),
                    'card_number': data.get('CardNo'),
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
                'error': str(e),
            }
    
    @classmethod
    @transaction.atomic
    def process_callback(cls, token, status, invoice_id, reference_number=None, card_number=None):
        """
        Process the payment callback and update database
        
        Args:
            token: Payment token
            status: Payment status ('success' or 'failed')
            invoice_id: Invoice UUID
            reference_number: Bank reference number (optional)
            card_number: Masked card number (optional)
            
        Returns:
            dict with result
        """
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            
            if status == 'success':
                # Verify the payment
                verify_result = cls.verify_payment(token, invoice)
                
                if verify_result['success']:
                    # Create payment record
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
                    
                    # Update invoice
                    invoice.paid_amount = invoice.total_amount
                    invoice.status = Invoice.InvoiceStatus.PAID
                    invoice.save()
                    
                    return {
                        'success': True,
                        'payment_id': str(payment.id),
                        'message': 'پرداخت با موفقیت انجام شد',
                        'reference_number': payment.gateway_reference_id,
                    }
                else:
                    return verify_result
            else:
                # Payment failed
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


# Convenience functions for views
def initiate_sadad_payment(invoice, callback_url):
    """Initiate a payment with Sadad gateway"""
    return SadadPaymentGateway.create_payment_request(invoice, callback_url)

def verify_sadad_payment(token, invoice):
    """Verify a Sadad payment"""
    return SadadPaymentGateway.verify_payment(token, invoice)

def process_sadad_callback(token, status, invoice_id, reference_number=None, card_number=None):
    """Process Sadad payment callback"""
    return SadadPaymentGateway.process_callback(token, status, invoice_id, reference_number, card_number)


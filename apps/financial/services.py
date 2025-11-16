from django.db import transaction
from .models import CreditNote, CreditTransaction
from apps.accounts.models import User

def add_credit_to_student(student: User, amount: float, description: str, source_invoice=None, created_by=None):
    """
    اعتبار به کیف پول دانش‌آموز اضافه می‌کند.
    """
    if amount <= 0:
        raise ValueError("مبلغ باید مثبت باشد")
    
    with transaction.atomic():
        credit_note, created = CreditNote.objects.select_for_update().get_or_create(student=student)
        
        new_balance = credit_note.balance + amount
        
        CreditTransaction.objects.create(
            credit_note=credit_note,
            transaction_type=CreditTransaction.TransactionType.REFUND,
            amount=amount,
            balance_after=new_balance,
            description=description,
            source_invoice=source_invoice,
            created_by=created_by
        )
        
        credit_note.balance = new_balance
        credit_note.save()
        
    return credit_note

def use_credit_for_payment(student: User, amount: float, invoice):
    """
    از اعتبار برای پرداخت فاکتور استفاده می‌کند.
    """
    if amount <= 0:
        raise ValueError("مبلغ باید مثبت باشد")
        
    with transaction.atomic():
        credit_note = CreditNote.objects.select_for_update().get(student=student)
        
        if credit_note.balance < amount:
            raise ValueError("موجودی اعتبار کافی نیست")
        
        new_balance = credit_note.balance - amount
        
        CreditTransaction.objects.create(
            credit_note=credit_note,
            transaction_type=CreditTransaction.TransactionType.PAYMENT,
            amount=-amount, # مبلغ منفی برای استفاده
            balance_after=new_balance,
            description=f'پرداخت فاکتور {invoice.invoice_number}',
            source_invoice=invoice,
            created_by=student
        )
        
        credit_note.balance = new_balance
        credit_note.save()
        
        # ایجاد یک پرداخت از نوع "اعتبار"
        from .models import Payment
        Payment.objects.create(
            invoice=invoice,
            student=student,
            amount=amount,
            payment_method=Payment.PaymentMethod.CREDIT, # نوع پرداخت جدید
            status=Payment.PaymentStatus.COMPLETED,
            verified_by=student # خودکار تایید می‌شود
        )
        
    return credit_note
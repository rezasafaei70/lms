import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner, Modal, ModalFooter } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { financialAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const StudentPayments = () => {
  const [searchParams] = useSearchParams();
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [payingInvoice, setPayingInvoice] = useState(null);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [showResultModal, setShowResultModal] = useState(false);
  const [paymentResult, setPaymentResult] = useState(null);
  const [creditBalance, setCreditBalance] = useState(0);

  useEffect(() => {
    fetchInvoices();
    fetchCreditBalance();
    
    // Check for payment result from URL params
    const paymentStatus = searchParams.get('payment');
    if (paymentStatus) {
      setPaymentResult({
        success: paymentStatus === 'success',
        reference: searchParams.get('reference'),
        error: searchParams.get('error'),
      });
      setShowResultModal(true);
      // Clear URL params
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [searchParams]);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const response = await financialAPI.getMyInvoices();
      setInvoices(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCreditBalance = async () => {
    try {
      const response = await financialAPI.getMyBalance();
      setCreditBalance(response.data?.balance || 0);
    } catch (error) {
      console.error('Error fetching credit:', error);
    }
  };

  const handlePayment = async (invoice) => {
    try {
      setPayingInvoice(invoice.id);
      setPaymentLoading(true);
      
      const response = await financialAPI.initiatePayment(invoice.id);
      
      if (response.data.success) {
        // Redirect to payment page
        window.location.href = response.data.payment_url;
      } else {
        alert(response.data.error || 'خطا در ایجاد درخواست پرداخت');
      }
    } catch (error) {
      console.error('Error initiating payment:', error);
      alert(error.response?.data?.error || 'خطا در ایجاد درخواست پرداخت');
    } finally {
      setPaymentLoading(false);
      setPayingInvoice(null);
    }
  };

  const displayData = invoices;
  const totalPaid = displayData.filter(i => i.status === 'paid').reduce((sum, i) => sum + (parseFloat(i.amount || i.total_amount) || 0), 0);
  const totalPending = displayData.filter(i => i.status !== 'paid' && i.status !== 'cancelled').reduce((sum, i) => sum + (parseFloat(i.amount || i.total_amount) || 0), 0);

  const getStatusBadge = (invoice) => {
    if (invoice.status === 'paid') {
      return <Badge variant="success">پرداخت شده</Badge>;
    } else if (invoice.is_overdue || invoice.status === 'overdue') {
      return <Badge variant="error">معوق</Badge>;
    } else if (invoice.status === 'cancelled') {
      return <Badge variant="default">لغو شده</Badge>;
    } else if (invoice.status === 'partially_paid') {
      return <Badge variant="info">پرداخت جزئی</Badge>;
    }
    return <Badge variant="warning">در انتظار</Badge>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        <Card>
          <CardContent style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            padding: '1.5rem'
          }}>
            <div>
              <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>پرداخت شده</span>
              <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>
                {toPersianDigits(Math.round(totalPaid).toLocaleString())} تومان
              </p>
            </div>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: 'var(--radius-md)',
              background: '#d1fae5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--success)'
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            padding: '1.5rem'
          }}>
            <div>
              <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>در انتظار پرداخت</span>
              <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem', fontWeight: 700, color: 'var(--warning)' }}>
                {toPersianDigits(Math.round(totalPending).toLocaleString())} تومان
              </p>
            </div>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: 'var(--radius-md)',
              background: '#fef3c7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--warning)'
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            padding: '1.5rem'
          }}>
            <div>
              <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>موجودی کیف پول</span>
              <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-600)' }}>
                {toPersianDigits(Math.round(creditBalance).toLocaleString())} تومان
              </p>
            </div>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--primary-100)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--primary-600)'
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                <line x1="1" y1="10" x2="23" y2="10" />
              </svg>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>فاکتورها</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>شماره فاکتور</TableHead>
                  <TableHead>شرح</TableHead>
                  <TableHead>مبلغ</TableHead>
                  <TableHead>تاریخ صدور</TableHead>
                  <TableHead>سررسید</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayData.length === 0 ? (
                  <TableEmpty message="فاکتوری یافت نشد" />
                ) : (
                  displayData.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell>
                        <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                          {invoice.number || invoice.invoice_number}
                        </code>
                      </TableCell>
                      <TableCell>
                        <strong>{invoice.description || `فاکتور ${invoice.invoice_type_display || invoice.invoice_type || 'شهریه'}`}</strong>
                      </TableCell>
                      <TableCell>{toPersianDigits(Math.round(parseFloat(invoice.amount || invoice.total_amount) || 0).toLocaleString())} تومان</TableCell>
                      <TableCell>{formatApiDate(invoice.date || invoice.issue_date)}</TableCell>
                      <TableCell>{invoice.dueDate || invoice.due_date ? formatApiDate(invoice.dueDate || invoice.due_date) : '-'}</TableCell>
                      <TableCell>
                        {getStatusBadge(invoice)}
                      </TableCell>
                      <TableCell>
                        {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
                          <Button 
                            size="small" 
                            variant="primary"
                            onClick={() => handlePayment(invoice)}
                            loading={payingInvoice === invoice.id && paymentLoading}
                            disabled={paymentLoading}
                          >
                            {payingInvoice === invoice.id ? 'در حال انتقال...' : 'پرداخت'}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Payment Result Modal */}
      <Modal
        isOpen={showResultModal}
        onClose={() => setShowResultModal(false)}
        title={paymentResult?.success ? 'پرداخت موفق' : 'خطا در پرداخت'}
        size="small"
      >
        <div style={{ textAlign: 'center', padding: '1rem 0' }}>
          <div style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: paymentResult?.success ? '#d1fae5' : '#fee2e2',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.5rem'
          }}>
            {paymentResult?.success ? (
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            ) : (
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            )}
          </div>
          
          {paymentResult?.success ? (
            <>
              <h3 style={{ margin: '0 0 0.5rem', color: 'var(--success)' }}>پرداخت با موفقیت انجام شد!</h3>
              {paymentResult.reference && (
                <p style={{ color: 'var(--gray-600)', margin: '0.5rem 0' }}>
                  شماره پیگیری: <strong>{paymentResult.reference}</strong>
                </p>
              )}
            </>
          ) : (
            <>
              <h3 style={{ margin: '0 0 0.5rem', color: 'var(--error)' }}>پرداخت ناموفق</h3>
              <p style={{ color: 'var(--gray-600)', margin: '0.5rem 0' }}>
                {paymentResult?.error || 'پرداخت با خطا مواجه شد یا توسط شما لغو شد.'}
              </p>
            </>
          )}
        </div>
        <ModalFooter>
          <Button onClick={() => { setShowResultModal(false); fetchInvoices(); }}>
            بستن
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default StudentPayments;

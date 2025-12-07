import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, JalaliDatePicker, FileUpload, AutocompleteSelect } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { financialAPI, usersAPI, branchesAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const StatCard = ({ title, value, color, icon: Icon }) => (
  <Card className={`stat-card stat-card-${color}`} hover>
    <div className="stat-card-content">
      <div className="stat-card-info">
        <span className="stat-card-title">{title}</span>
        <span className="stat-card-value">{toPersianDigits(value?.toLocaleString() || '0')} تومان</span>
      </div>
      <div className="stat-card-icon">
        <Icon />
      </div>
    </div>
  </Card>
);

const Icons = {
  Income: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  ),
  Pending: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  Overdue: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  Discount: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="9" cy="9" r="2" />
      <circle cx="15" cy="15" r="2" />
      <line x1="7" y1="17" x2="17" y2="7" />
      <rect x="3" y="3" width="18" height="18" rx="2" />
    </svg>
  ),
};

const AdminFinancial = () => {
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('invoices');
  const [stats, setStats] = useState({
    totalIncome: 0,
    totalPending: 0,
    totalOverdue: 0,
    totalDiscount: 0,
  });

  // Payment Modal
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentFormData, setPaymentFormData] = useState({
    invoice: '',
    amount: '',
    payment_date: '',
    method: 'online',
    reference_code: '',
  });
  const [paymentAttachment, setPaymentAttachment] = useState(null);
  const [savingPayment, setSavingPayment] = useState(false);

  // Coupon Modal
  const [showCouponModal, setShowCouponModal] = useState(false);
  const [couponFormData, setCouponFormData] = useState({
    code: '',
    discount_type: 'percentage',
    discount_value: '',
    valid_from: '',
    valid_to: '',
    max_uses: '',
    is_active: true,
  });
  const [savingCoupon, setSavingCoupon] = useState(false);

  // Invoice Modal
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [students, setStudents] = useState([]);
  const [branches, setBranches] = useState([]);
  const [invoiceFormData, setInvoiceFormData] = useState({
    student: '',
    branch: '',
    invoice_type: 'tuition',
    subtotal: '',
    discount_amount: '0',
    tax_amount: '0',
    issue_date: '',
    due_date: '',
    description: '',
  });
  const [invoiceItems, setInvoiceItems] = useState([{ description: '', quantity: 1, unit_price: '' }]);
  const [savingInvoice, setSavingInvoice] = useState(false);

  useEffect(() => {
    fetchData();
    fetchStudentsAndBranches();
  }, []);

  const fetchStudentsAndBranches = async () => {
    try {
      const branchesRes = await branchesAPI.list({ page_size: 100 });
      setBranches(branchesRes.data.results || []);
    } catch (error) {
      console.error('Error fetching branches:', error);
    }
  };

  // Search students for autocomplete
  const searchStudents = useCallback(async (query) => {
    console.log('Financial: searchStudents called with query:', query);
    try {
      const response = await usersAPI.searchStudents(query);
      console.log('Financial: API response:', response.data);
      
      // Handle both paginated and non-paginated responses
      const studentsData = response.data.results || response.data || [];
      console.log('Financial: Found', studentsData.length, 'students');
      
      const mappedResults = studentsData.map(student => {
        // Get user data - might be nested or flat
        const user = student.user || student;
        const firstName = user.first_name || '';
        const lastName = user.last_name || '';
        const nationalCode = user.national_code || '';
        const mobile = user.mobile || '';
        
        // Generate display name
        const fullName = `${firstName} ${lastName}`.trim() || 'بدون نام';
        const identifier = nationalCode || mobile || '';
        const displayName = identifier ? `${fullName} (${identifier})` : fullName;
        
        return {
          ...student,
          userId: user.id || student.id,
          displayName
        };
      });
      
      console.log('Financial: Mapped results:', mappedResults);
      return mappedResults;
    } catch (error) {
      console.error('Financial: Error searching students:', error);
      return [];
    }
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [invoicesRes, paymentsRes, couponsRes] = await Promise.all([
        financialAPI.getInvoices(),
        financialAPI.getPayments(),
        financialAPI.getCoupons(),
      ]);
      
      setInvoices(invoicesRes.data.results || []);
      setPayments(paymentsRes.data.results || []);
      setCoupons(couponsRes.data.results || []);

      // Calculate stats - use parseFloat to handle string/decimal values
      const data = invoicesRes.data.results || [];
      const totalIncome = data.filter(i => i.status === 'paid').reduce((sum, i) => sum + (parseFloat(i.total_amount) || 0), 0);
      const totalPending = data.filter(i => i.status === 'pending' || i.status === 'draft').reduce((sum, i) => sum + (parseFloat(i.total_amount) || 0), 0);
      const totalOverdue = data.filter(i => i.is_overdue).reduce((sum, i) => sum + (parseFloat(i.total_amount) || 0), 0);
      const totalDiscount = data.reduce((sum, i) => sum + (parseFloat(i.discount_amount) || 0), 0);

      setStats({ 
        totalIncome: Math.round(totalIncome), 
        totalPending: Math.round(totalPending), 
        totalOverdue: Math.round(totalOverdue), 
        totalDiscount: Math.round(totalDiscount) 
      });
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePayment = async () => {
    try {
      setSavingPayment(true);
      const data = { ...paymentFormData };
      if (data.amount) data.amount = parseInt(data.amount);
      if (paymentAttachment) data.attachment_s3_key = paymentAttachment;
      
      await financialAPI.createPayment(data);
      setShowPaymentModal(false);
      setPaymentFormData({
        invoice: '',
        amount: '',
        payment_date: '',
        method: 'online',
        reference_code: '',
      });
      setPaymentAttachment(null);
      fetchData();
    } catch (error) {
      console.error('Error creating payment:', error);
      alert(error.response?.data?.detail || 'خطا در ثبت پرداخت');
    } finally {
      setSavingPayment(false);
    }
  };

  const handleCreateCoupon = async () => {
    try {
      setSavingCoupon(true);
      const data = { ...couponFormData };
      if (data.discount_value) data.discount_value = parseInt(data.discount_value);
      if (data.max_uses) data.max_uses = parseInt(data.max_uses);
      
      await financialAPI.createCoupon(data);
      setShowCouponModal(false);
      setCouponFormData({
        code: '',
        discount_type: 'percentage',
        discount_value: '',
        valid_from: '',
        valid_to: '',
        max_uses: '',
        is_active: true,
      });
      fetchData();
    } catch (error) {
      console.error('Error creating coupon:', error);
      alert(error.response?.data?.detail || 'خطا در ایجاد کوپن');
    } finally {
      setSavingCoupon(false);
    }
  };

  const handleCreateInvoice = async () => {
    const validItems = invoiceItems.filter(item => item.description && item.unit_price);
    
    if (!invoiceFormData.student || !invoiceFormData.branch || validItems.length === 0 || !invoiceFormData.issue_date || !invoiceFormData.due_date) {
      alert('لطفاً تمام فیلدهای ضروری را پر کنید (دانش‌آموز، شعبه، تاریخ‌ها و حداقل یک آیتم)');
      return;
    }

    try {
      setSavingInvoice(true);
      const data = {
        student: invoiceFormData.student,
        branch: invoiceFormData.branch,
        invoice_type: invoiceFormData.invoice_type,
        issue_date: invoiceFormData.issue_date,
        due_date: invoiceFormData.due_date,
        description: invoiceFormData.description || '',
        items: validItems.map(item => ({
          description: item.description,
          quantity: parseInt(item.quantity || 1),
          unit_price: parseInt(item.unit_price),
        })),
      };
      
      await financialAPI.createInvoice(data);
      setShowInvoiceModal(false);
      setInvoiceFormData({
        student: '',
        branch: '',
        invoice_type: 'tuition',
        subtotal: '',
        discount_amount: '0',
        tax_amount: '0',
        issue_date: '',
        due_date: '',
        description: '',
      });
      setInvoiceItems([{ description: '', quantity: 1, unit_price: '' }]);
      fetchData();
    } catch (error) {
      console.error('Error creating invoice:', error);
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message || 
                       JSON.stringify(error.response?.data) ||
                       'خطا در ایجاد فاکتور';
      alert(errorMsg);
    } finally {
      setSavingInvoice(false);
    }
  };

  const addInvoiceItem = () => {
    setInvoiceItems([...invoiceItems, { description: '', quantity: 1, unit_price: '' }]);
  };

  const updateInvoiceItem = (index, field, value) => {
    const newItems = [...invoiceItems];
    newItems[index][field] = value;
    setInvoiceItems(newItems);
    
    // Auto-calculate subtotal
    const total = newItems.reduce((sum, item) => {
      return sum + (parseInt(item.quantity || 1) * parseInt(item.unit_price || 0));
    }, 0);
    setInvoiceFormData(prev => ({ ...prev, subtotal: total.toString() }));
  };

  const removeInvoiceItem = (index) => {
    if (invoiceItems.length > 1) {
      const newItems = invoiceItems.filter((_, i) => i !== index);
      setInvoiceItems(newItems);
      
      // Recalculate subtotal
      const total = newItems.reduce((sum, item) => {
        return sum + (parseInt(item.quantity || 1) * parseInt(item.unit_price || 0));
      }, 0);
      setInvoiceFormData(prev => ({ ...prev, subtotal: total.toString() }));
    }
  };

  const getStatusVariant = (status) => {
    const variants = {
      paid: 'success',
      pending: 'warning',
      overdue: 'error',
      cancelled: 'default',
      partial: 'info',
    };
    return variants[status] || 'default';
  };

  const getStatusName = (status) => {
    const names = {
      paid: 'پرداخت شده',
      pending: 'در انتظار',
      overdue: 'معوق',
      cancelled: 'لغو شده',
      partial: 'پرداخت ناقص',
    };
    return names[status] || status;
  };

  const getPaymentMethodName = (method) => {
    const names = {
      online: 'آنلاین',
      card: 'کارت به کارت',
      cash: 'نقدی',
      cheque: 'چک',
    };
    return names[method] || method;
  };

  return (
    <div className="financial-page">
      {/* Stats */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '1.5rem' }}>
        <StatCard
          title="درآمد کل"
          value={stats.totalIncome}
          color="green"
          icon={Icons.Income}
        />
        <StatCard
          title="در انتظار پرداخت"
          value={stats.totalPending}
          color="blue"
          icon={Icons.Pending}
        />
        <StatCard
          title="معوقات"
          value={stats.totalOverdue}
          color="red"
          icon={Icons.Overdue}
        />
        <StatCard
          title="مجموع تخفیفات"
          value={stats.totalDiscount}
          color="purple"
          icon={Icons.Discount}
        />
      </div>

      <Card>
        <CardHeader action={
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button onClick={() => setShowInvoiceModal(true)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              فاکتور جدید
            </Button>
            <Button variant="secondary" onClick={() => setShowPaymentModal(true)}>
              ثبت پرداخت
            </Button>
            <Button variant="secondary" onClick={() => setShowCouponModal(true)}>
              کوپن جدید
            </Button>
          </div>
        }>
          <CardTitle>مدیریت مالی</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Tabs */}
          <div style={{ 
            display: 'flex', 
            gap: '0.25rem',
            padding: '0.25rem',
            background: 'var(--gray-100)',
            borderRadius: 'var(--radius-lg)',
            marginBottom: '1.5rem',
            width: 'fit-content'
          }}>
            {[
              { key: 'invoices', label: 'فاکتورها' },
              { key: 'payments', label: 'پرداخت‌ها' },
              { key: 'coupons', label: 'کوپن‌ها' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: activeTab === tab.key ? 'white' : 'transparent',
                  boxShadow: activeTab === tab.key ? 'var(--shadow-sm)' : 'none',
                  color: activeTab === tab.key ? 'var(--primary-600)' : 'var(--gray-600)',
                  fontWeight: activeTab === tab.key ? 500 : 400,
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  transition: 'all var(--transition)'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <>
              {/* Invoices Tab */}
              {activeTab === 'invoices' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>شماره فاکتور</TableHead>
                      <TableHead>دانش‌آموز</TableHead>
                      <TableHead>مبلغ</TableHead>
                      <TableHead>تخفیف</TableHead>
                      <TableHead>تاریخ صدور</TableHead>
                      <TableHead>سررسید</TableHead>
                      <TableHead>وضعیت</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoices.length === 0 ? (
                      <TableEmpty message="فاکتوری یافت نشد" />
                    ) : (
                      invoices.map((invoice) => (
                        <TableRow key={invoice.id}>
                          <TableCell>
                            <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                              {invoice.invoice_number}
                            </code>
                          </TableCell>
                          <TableCell><strong>{invoice.student_name}</strong></TableCell>
                          <TableCell>{toPersianDigits(invoice.total_amount?.toLocaleString() || '0')} تومان</TableCell>
                          <TableCell>
                            {invoice.discount_amount 
                              ? <Badge variant="success">{toPersianDigits(invoice.discount_amount.toLocaleString())} تومان</Badge>
                              : '-'}
                          </TableCell>
                          <TableCell>{formatApiDate(invoice.issue_date)}</TableCell>
                          <TableCell>{formatApiDate(invoice.due_date)}</TableCell>
                          <TableCell>
                            <Badge variant={getStatusVariant(invoice.status)}>
                              {getStatusName(invoice.status)}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}

              {/* Payments Tab */}
              {activeTab === 'payments' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>فاکتور</TableHead>
                      <TableHead>مبلغ</TableHead>
                      <TableHead>روش پرداخت</TableHead>
                      <TableHead>کد پیگیری</TableHead>
                      <TableHead>تاریخ پرداخت</TableHead>
                      <TableHead>وضعیت</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {payments.length === 0 ? (
                      <TableEmpty message="پرداختی یافت نشد" />
                    ) : (
                      payments.map((payment) => (
                        <TableRow key={payment.id}>
                          <TableCell>
                            <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                              {payment.invoice_number}
                            </code>
                          </TableCell>
                          <TableCell>{toPersianDigits(payment.amount?.toLocaleString() || '0')} تومان</TableCell>
                          <TableCell>{getPaymentMethodName(payment.method)}</TableCell>
                          <TableCell>{payment.reference_code || '-'}</TableCell>
                          <TableCell>{formatApiDate(payment.payment_date)}</TableCell>
                          <TableCell>
                            <Badge variant={payment.is_verified ? 'success' : 'warning'}>
                              {payment.is_verified ? 'تأیید شده' : 'در انتظار تأیید'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}

              {/* Coupons Tab */}
              {activeTab === 'coupons' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>کد</TableHead>
                      <TableHead>نوع تخفیف</TableHead>
                      <TableHead>مقدار</TableHead>
                      <TableHead>اعتبار از</TableHead>
                      <TableHead>اعتبار تا</TableHead>
                      <TableHead>تعداد استفاده</TableHead>
                      <TableHead>وضعیت</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {coupons.length === 0 ? (
                      <TableEmpty message="کوپنی یافت نشد" />
                    ) : (
                      coupons.map((coupon) => (
                        <TableRow key={coupon.id}>
                          <TableCell>
                            <code style={{ 
                              background: 'var(--primary-50)', 
                              color: 'var(--primary-600)',
                              padding: '0.25rem 0.5rem', 
                              borderRadius: 'var(--radius)',
                              fontWeight: 600
                            }}>
                              {coupon.code}
                            </code>
                          </TableCell>
                          <TableCell>
                            {coupon.discount_type === 'percentage' ? 'درصدی' : 'مبلغی'}
                          </TableCell>
                          <TableCell>
                            {coupon.discount_type === 'percentage' 
                              ? `${toPersianDigits(coupon.discount_value)}%`
                              : `${toPersianDigits(coupon.discount_value?.toLocaleString() || '0')} تومان`}
                          </TableCell>
                          <TableCell>{formatApiDate(coupon.valid_from)}</TableCell>
                          <TableCell>{formatApiDate(coupon.valid_to)}</TableCell>
                          <TableCell>
                            {toPersianDigits(coupon.current_uses || 0)} / {coupon.max_uses ? toPersianDigits(coupon.max_uses) : '∞'}
                          </TableCell>
                          <TableCell>
                            <Badge variant={coupon.is_active ? 'success' : 'default'}>
                              {coupon.is_active ? 'فعال' : 'غیرفعال'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Payment Modal */}
      <Modal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        title="ثبت پرداخت جدید"
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>فاکتور *</label>
            <select
              value={paymentFormData.invoice}
              onChange={(e) => setPaymentFormData({ ...paymentFormData, invoice: e.target.value })}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                background: 'white'
              }}
            >
              <option value="">انتخاب فاکتور...</option>
              {invoices.filter(i => i.status !== 'paid').map(invoice => (
                <option key={invoice.id} value={invoice.id}>
                  {invoice.invoice_number} - {invoice.student_name} ({toPersianDigits(invoice.total_amount?.toLocaleString())} تومان)
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="مبلغ (تومان) *"
              type="number"
              value={paymentFormData.amount}
              onChange={(e) => setPaymentFormData({ ...paymentFormData, amount: e.target.value })}
            />
            <JalaliDatePicker
              label="تاریخ پرداخت"
              value={paymentFormData.payment_date}
              onChange={(date) => setPaymentFormData({ ...paymentFormData, payment_date: date })}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>روش پرداخت</label>
              <select
                value={paymentFormData.method}
                onChange={(e) => setPaymentFormData({ ...paymentFormData, method: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="online">آنلاین</option>
                <option value="card">کارت به کارت</option>
                <option value="cash">نقدی</option>
                <option value="cheque">چک</option>
              </select>
            </div>
            <Input
              label="کد پیگیری"
              value={paymentFormData.reference_code}
              onChange={(e) => setPaymentFormData({ ...paymentFormData, reference_code: e.target.value })}
              placeholder="مثال: 123456789"
            />
          </div>

          {/* Attachment Upload */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>رسید پرداخت (اختیاری)</label>
            <FileUpload
              accept="image/*,application/pdf"
              maxSize={5 * 1024 * 1024}
              folder="payments"
              targetModel="Payment"
              targetField="attachment"
              preview={true}
              label="آپلود رسید"
              hint="تصویر یا PDF - حداکثر ۵ مگابایت"
              onUploadComplete={(result) => setPaymentAttachment(result.key)}
              onUploadError={(err) => alert(err)}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowPaymentModal(false)}>انصراف</Button>
          <Button onClick={handleCreatePayment} loading={savingPayment}>ثبت پرداخت</Button>
        </ModalFooter>
      </Modal>

      {/* Coupon Modal */}
      <Modal
        isOpen={showCouponModal}
        onClose={() => setShowCouponModal(false)}
        title="ایجاد کوپن تخفیف"
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="کد کوپن *"
              value={couponFormData.code}
              onChange={(e) => setCouponFormData({ ...couponFormData, code: e.target.value.toUpperCase() })}
              placeholder="مثال: SUMMER2024"
            />
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>نوع تخفیف</label>
              <select
                value={couponFormData.discount_type}
                onChange={(e) => setCouponFormData({ ...couponFormData, discount_type: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="percentage">درصدی</option>
                <option value="fixed">مبلغ ثابت</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label={couponFormData.discount_type === 'percentage' ? 'درصد تخفیف *' : 'مبلغ تخفیف (تومان) *'}
              type="number"
              value={couponFormData.discount_value}
              onChange={(e) => setCouponFormData({ ...couponFormData, discount_value: e.target.value })}
              placeholder={couponFormData.discount_type === 'percentage' ? 'مثال: 20' : 'مثال: 100000'}
            />
            <Input
              label="حداکثر استفاده"
              type="number"
              value={couponFormData.max_uses}
              onChange={(e) => setCouponFormData({ ...couponFormData, max_uses: e.target.value })}
              placeholder="خالی = نامحدود"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <JalaliDatePicker
              label="اعتبار از *"
              value={couponFormData.valid_from}
              onChange={(date) => setCouponFormData({ ...couponFormData, valid_from: date })}
            />
            <JalaliDatePicker
              label="اعتبار تا *"
              value={couponFormData.valid_to}
              onChange={(date) => setCouponFormData({ ...couponFormData, valid_to: date })}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={couponFormData.is_active}
                onChange={(e) => setCouponFormData({ ...couponFormData, is_active: e.target.checked })}
              />
              <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>کوپن فعال باشد</span>
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowCouponModal(false)}>انصراف</Button>
          <Button onClick={handleCreateCoupon} loading={savingCoupon}>ایجاد کوپن</Button>
        </ModalFooter>
      </Modal>

      {/* Invoice Modal */}
      <Modal
        isOpen={showInvoiceModal}
        onClose={() => setShowInvoiceModal(false)}
        title="صدور فاکتور جدید"
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxHeight: '70vh', overflowY: 'auto', padding: '0.5rem' }}>
          {/* Student & Branch */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <AutocompleteSelect
              label="دانش‌آموز *"
              value={invoiceFormData.student}
              onChange={(value) => setInvoiceFormData({ ...invoiceFormData, student: value })}
              onSearch={searchStudents}
              displayField="displayName"
              valueField="userId"
              placeholder="نام، کد ملی یا موبایل..."
              minSearchLength={1}
              required
              hint="حداقل ۱ کاراکتر برای جستجو"
            />
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>شعبه *</label>
              <select
                value={invoiceFormData.branch}
                onChange={(e) => setInvoiceFormData({ ...invoiceFormData, branch: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="">انتخاب شعبه...</option>
                {branches.map(branch => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name} ({branch.city})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Invoice Type & Dates */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>نوع فاکتور</label>
              <select
                value={invoiceFormData.invoice_type}
                onChange={(e) => setInvoiceFormData({ ...invoiceFormData, invoice_type: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="tuition">شهریه</option>
                <option value="registration">ثبت‌نام</option>
                <option value="book">کتاب</option>
                <option value="exam">آزمون</option>
                <option value="certificate">گواهینامه</option>
                <option value="other">سایر</option>
              </select>
            </div>
            <JalaliDatePicker
              label="تاریخ صدور *"
              value={invoiceFormData.issue_date}
              onChange={(date) => setInvoiceFormData({ ...invoiceFormData, issue_date: date })}
            />
            <JalaliDatePicker
              label="سررسید *"
              value={invoiceFormData.due_date}
              onChange={(date) => setInvoiceFormData({ ...invoiceFormData, due_date: date })}
            />
          </div>

          {/* Invoice Items */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h4 style={{ margin: 0, color: 'var(--gray-700)', fontSize: '0.9375rem' }}>آیتم‌های فاکتور</h4>
              <Button variant="secondary" onClick={addInvoiceItem} style={{ padding: '0.5rem 1rem' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                افزودن آیتم
              </Button>
            </div>
            {invoiceItems.map((item, index) => (
              <div key={index} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '0.75rem', marginBottom: '0.75rem', alignItems: 'end' }}>
                <Input
                  label={index === 0 ? 'شرح' : ''}
                  value={item.description}
                  onChange={(e) => updateInvoiceItem(index, 'description', e.target.value)}
                  placeholder="شرح آیتم"
                />
                <Input
                  label={index === 0 ? 'تعداد' : ''}
                  type="number"
                  value={item.quantity}
                  onChange={(e) => updateInvoiceItem(index, 'quantity', e.target.value)}
                  min="1"
                />
                <Input
                  label={index === 0 ? 'قیمت واحد (تومان)' : ''}
                  type="number"
                  value={item.unit_price}
                  onChange={(e) => updateInvoiceItem(index, 'unit_price', e.target.value)}
                  placeholder="مثال: 500000"
                />
                {invoiceItems.length > 1 && (
                  <button
                    onClick={() => removeInvoiceItem(index)}
                    style={{
                      padding: '0.5rem',
                      background: '#fee2e2',
                      border: 'none',
                      borderRadius: 'var(--radius)',
                      color: 'var(--error)',
                      cursor: 'pointer',
                      marginBottom: index === 0 ? '0' : '0'
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Amounts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <Input
              label="جمع جزء (تومان) *"
              type="number"
              value={invoiceFormData.subtotal}
              onChange={(e) => setInvoiceFormData({ ...invoiceFormData, subtotal: e.target.value })}
              placeholder="محاسبه خودکار"
            />
            <Input
              label="تخفیف (تومان)"
              type="number"
              value={invoiceFormData.discount_amount}
              onChange={(e) => setInvoiceFormData({ ...invoiceFormData, discount_amount: e.target.value })}
              placeholder="0"
            />
            <Input
              label="مالیات (تومان)"
              type="number"
              value={invoiceFormData.tax_amount}
              onChange={(e) => setInvoiceFormData({ ...invoiceFormData, tax_amount: e.target.value })}
              placeholder="0"
            />
          </div>

          {/* Total Display */}
          <div style={{ 
            padding: '1rem', 
            background: 'var(--primary-50)', 
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ fontWeight: 500, color: 'var(--gray-700)' }}>مبلغ کل قابل پرداخت:</span>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary-600)' }}>
              {toPersianDigits(
                Math.max(0, 
                  (parseInt(invoiceFormData.subtotal) || 0) - 
                  (parseInt(invoiceFormData.discount_amount) || 0) + 
                  (parseInt(invoiceFormData.tax_amount) || 0)
                ).toLocaleString()
              )} تومان
            </span>
          </div>

          {/* Description */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>توضیحات</label>
            <textarea
              value={invoiceFormData.description}
              onChange={(e) => setInvoiceFormData({ ...invoiceFormData, description: e.target.value })}
              placeholder="توضیحات اختیاری برای فاکتور..."
              rows={2}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                resize: 'vertical'
              }}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowInvoiceModal(false)}>انصراف</Button>
          <Button onClick={handleCreateInvoice} loading={savingInvoice}>صدور فاکتور</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminFinancial;

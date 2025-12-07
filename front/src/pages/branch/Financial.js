import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { financialAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const BranchFinancial = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalIncome: 0,
    totalPending: 0,
    totalOverdue: 0,
    thisMonthIncome: 0,
  });
  const [filter, setFilter] = useState('all');

  // Get selected branch from localStorage
  const selectedBranch = JSON.parse(localStorage.getItem('selected_branch') || '{}');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const invoicesRes = await financialAPI.getInvoices({ branch: selectedBranch.id });
      const data = invoicesRes.data.results || [];
      setInvoices(data);
      
      // Calculate stats
      const totalIncome = data.filter(i => i.status === 'paid').reduce((sum, i) => sum + (i.total_amount || 0), 0);
      const totalPending = data.filter(i => i.status === 'pending').reduce((sum, i) => sum + (i.total_amount || 0), 0);
      const totalOverdue = data.filter(i => i.status === 'overdue').reduce((sum, i) => sum + (i.total_amount || 0), 0);
      
      // This month income (simplified - in real app would filter by date)
      const thisMonthIncome = totalIncome;
      
      setStats({ totalIncome, totalPending, totalOverdue, thisMonthIncome });
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusVariant = (status) => {
    const variants = {
      paid: 'success',
      pending: 'warning',
      overdue: 'error',
      cancelled: 'default',
    };
    return variants[status] || 'default';
  };

  const getStatusName = (status) => {
    const names = {
      paid: 'پرداخت شده',
      pending: 'در انتظار',
      overdue: 'معوق',
      cancelled: 'لغو شده',
    };
    return names[status] || status;
  };

  const filteredInvoices = invoices.filter(invoice => {
    if (filter === 'all') return true;
    return invoice.status === filter;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <p style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--success)' }}>
              {toPersianDigits(stats.totalIncome.toLocaleString())}
            </p>
            <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>درآمد کل (تومان)</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <p style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--primary-600)' }}>
              {toPersianDigits(stats.thisMonthIncome.toLocaleString())}
            </p>
            <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>درآمد این ماه (تومان)</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <p style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--warning)' }}>
              {toPersianDigits(stats.totalPending.toLocaleString())}
            </p>
            <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>در انتظار پرداخت (تومان)</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <p style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--error)' }}>
              {toPersianDigits(stats.totalOverdue.toLocaleString())}
            </p>
            <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>معوقات (تومان)</span>
          </CardContent>
        </Card>
      </div>

      {/* Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>فاکتورها - شعبه {selectedBranch?.name}</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filter Tabs */}
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
              { key: 'all', label: 'همه' },
              { key: 'pending', label: 'در انتظار' },
              { key: 'paid', label: 'پرداخت شده' },
              { key: 'overdue', label: 'معوق' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: filter === tab.key ? 'white' : 'transparent',
                  boxShadow: filter === tab.key ? 'var(--shadow-sm)' : 'none',
                  color: filter === tab.key ? 'var(--primary-600)' : 'var(--gray-600)',
                  fontWeight: filter === tab.key ? 500 : 400,
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>شماره فاکتور</TableHead>
                  <TableHead>دانش‌آموز</TableHead>
                  <TableHead>شرح</TableHead>
                  <TableHead>مبلغ</TableHead>
                  <TableHead>تاریخ صدور</TableHead>
                  <TableHead>سررسید</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInvoices.length === 0 ? (
                  <TableEmpty message="فاکتوری یافت نشد" />
                ) : (
                  filteredInvoices.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell>
                        <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                          {invoice.invoice_number}
                        </code>
                      </TableCell>
                      <TableCell><strong>{invoice.student_name}</strong></TableCell>
                      <TableCell>{invoice.description || '-'}</TableCell>
                      <TableCell>{toPersianDigits((invoice.total_amount || 0).toLocaleString())} تومان</TableCell>
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
        </CardContent>
      </Card>
    </div>
  );
};

export default BranchFinancial;

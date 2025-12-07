import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Badge, Spinner, Input } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { enrollmentsAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const BranchEnrollments = () => {
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchEnrollments();
  }, []);

  const fetchEnrollments = async () => {
    try {
      setLoading(true);
      const response = await enrollmentsAPI.list();
      setEnrollments(response.data.results || []);
    } catch (error) {
      console.error('Error fetching enrollments:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusVariant = (status) => {
    const variants = {
      pending: 'warning',
      active: 'success',
      completed: 'info',
      cancelled: 'error',
    };
    return variants[status] || 'default';
  };

  const getStatusName = (status) => {
    const names = {
      pending: 'در انتظار تأیید',
      active: 'فعال',
      completed: 'تکمیل شده',
      cancelled: 'لغو شده',
    };
    return names[status] || status;
  };

  const filteredEnrollments = enrollments.filter(e => {
    const matchesFilter = filter === 'all' || e.status === filter;
    const matchesSearch = search === '' || 
      e.student_name?.toLowerCase().includes(search.toLowerCase()) ||
      e.class_name?.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Stats
  const stats = {
    total: enrollments.length,
    active: enrollments.filter(e => e.status === 'active').length,
    pending: enrollments.filter(e => e.status === 'pending').length,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.25rem' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-600)' }}>{toPersianDigits(stats.total)}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کل ثبت‌نام‌ها</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.25rem' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(stats.active)}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>فعال</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.25rem' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--warning)' }}>{toPersianDigits(stats.pending)}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>در انتظار</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>ثبت‌نام‌ها</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ 
              display: 'flex', 
              gap: '0.25rem',
              padding: '0.25rem',
              background: 'var(--gray-100)',
              borderRadius: 'var(--radius-lg)',
            }}>
              {[
                { key: 'all', label: 'همه' },
                { key: 'pending', label: 'در انتظار' },
                { key: 'active', label: 'فعال' },
                { key: 'completed', label: 'تکمیل شده' },
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key)}
                  style={{
                    padding: '0.5rem 0.75rem',
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
            <div style={{ flex: 1, maxWidth: '300px' }}>
              <Input
                placeholder="جستجو..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>شماره</TableHead>
                  <TableHead>دانش‌آموز</TableHead>
                  <TableHead>کلاس</TableHead>
                  <TableHead>تاریخ ثبت‌نام</TableHead>
                  <TableHead>مبلغ</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEnrollments.length === 0 ? (
                  <TableEmpty message="ثبت‌نامی یافت نشد" />
                ) : (
                  filteredEnrollments.map((enrollment) => (
                    <TableRow key={enrollment.id}>
                      <TableCell>
                        <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                          {enrollment.enrollment_number}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <div style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontWeight: 600,
                            fontSize: '0.8125rem'
                          }}>
                            {enrollment.student_name?.charAt(0) || '?'}
                          </div>
                          <strong>{enrollment.student_name}</strong>
                        </div>
                      </TableCell>
                      <TableCell>{enrollment.class_name}</TableCell>
                      <TableCell>{formatApiDate(enrollment.enrollment_date)}</TableCell>
                      <TableCell>
                        {enrollment.final_price 
                          ? `${toPersianDigits(enrollment.final_price.toLocaleString())} تومان`
                          : '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(enrollment.status)}>
                          {getStatusName(enrollment.status)}
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

export default BranchEnrollments;

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner, Modal, ModalFooter } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { enrollmentsAPI, financialAPI, attendanceAPI, usersAPI, branchesAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const AdminReports = () => {
  const [showReportModal, setShowReportModal] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportData, setReportData] = useState([]);
  const [loadingReport, setLoadingReport] = useState(false);
  const [stats, setStats] = useState({});

  const reports = [
    { id: 'enrollments', title: 'گزارش ثبت‌نام‌ها', description: 'لیست کامل ثبت‌نام‌ها به تفکیک شعبه و دوره', icon: '📊' },
    { id: 'financial', title: 'گزارش مالی', description: 'درآمد، هزینه و سود به تفکیک ماه', icon: '💰' },
    { id: 'attendance', title: 'گزارش حضور و غیاب', description: 'آمار حضور و غیاب دانش‌آموزان', icon: '📅' },
    { id: 'teachers', title: 'گزارش معلمان', description: 'عملکرد و ساعات تدریس معلمان', icon: '👨‍🏫' },
    { id: 'students', title: 'گزارش دانش‌آموزان', description: 'پیشرفت تحصیلی و نمرات', icon: '🎓' },
    { id: 'branches', title: 'گزارش شعب', description: 'آمار و عملکرد شعب', icon: '🏢' },
  ];

  const handleViewReport = async (report) => {
    setSelectedReport(report);
    setShowReportModal(true);
    setLoadingReport(true);
    setReportData([]);
    setStats({});

    try {
      let response;
      switch (report.id) {
        case 'enrollments':
          response = await enrollmentsAPI.list({ page_size: 100 });
          setReportData(response.data.results || []);
          const enrollments = response.data.results || [];
          setStats({
            total: enrollments.length,
            active: enrollments.filter(e => e.status === 'active').length,
            pending: enrollments.filter(e => e.status === 'pending').length,
            completed: enrollments.filter(e => e.status === 'completed').length,
          });
          break;
        case 'financial':
          response = await financialAPI.getInvoices({ page_size: 100 });
          setReportData(response.data.results || []);
          const invoices = response.data.results || [];
          const totalIncome = invoices.filter(i => i.status === 'paid').reduce((sum, i) => sum + (parseFloat(i.total_amount) || 0), 0);
          const totalPending = invoices.filter(i => i.status === 'pending').reduce((sum, i) => sum + (parseFloat(i.total_amount) || 0), 0);
          setStats({
            totalIncome: Math.round(totalIncome),
            totalPending: Math.round(totalPending),
            paidCount: invoices.filter(i => i.status === 'paid').length,
            pendingCount: invoices.filter(i => i.status === 'pending').length,
          });
          break;
        case 'teachers':
          response = await usersAPI.getTeachers({ page_size: 100 });
          setReportData(response.data.results || []);
          setStats({ total: response.data.count || response.data.results?.length || 0 });
          break;
        case 'students':
          response = await usersAPI.getStudents({ page_size: 100 });
          setReportData(response.data.results || []);
          setStats({ total: response.data.count || response.data.results?.length || 0 });
          break;
        case 'branches':
          response = await branchesAPI.list({ page_size: 100 });
          setReportData(response.data.results || []);
          setStats({ total: response.data.count || response.data.results?.length || 0 });
          break;
        default:
          setReportData([]);
      }
    } catch (error) {
      console.error('Error fetching report:', error);
    } finally {
      setLoadingReport(false);
    }
  };

  const renderReportContent = () => {
    if (!selectedReport) return null;

    switch (selectedReport.id) {
      case 'enrollments':
        return (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{toPersianDigits(stats.total || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>کل</div></CardContent></Card>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(stats.active || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>فعال</div></CardContent></Card>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--warning)' }}>{toPersianDigits(stats.pending || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>در انتظار</div></CardContent></Card>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--info)' }}>{toPersianDigits(stats.completed || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>تکمیل شده</div></CardContent></Card>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>دانش‌آموز</TableHead>
                  <TableHead>کلاس</TableHead>
                  <TableHead>تاریخ</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportData.slice(0, 20).map(item => (
                  <TableRow key={item.id}>
                    <TableCell>{item.student_name || '-'}</TableCell>
                    <TableCell>{item.class_name || '-'}</TableCell>
                    <TableCell>{formatApiDate(item.enrollment_date)}</TableCell>
                    <TableCell><Badge variant={item.status === 'active' ? 'success' : 'warning'}>{item.status_display || item.status}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        );
      case 'financial':
        return (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(stats.totalIncome?.toLocaleString() || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>درآمد (تومان)</div></CardContent></Card>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--warning)' }}>{toPersianDigits(stats.totalPending?.toLocaleString() || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>در انتظار (تومان)</div></CardContent></Card>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{toPersianDigits(stats.paidCount || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>پرداخت شده</div></CardContent></Card>
              <Card><CardContent style={{ textAlign: 'center', padding: '1rem' }}><div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{toPersianDigits(stats.pendingCount || 0)}</div><div style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>منتظر پرداخت</div></CardContent></Card>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>شماره</TableHead>
                  <TableHead>دانش‌آموز</TableHead>
                  <TableHead>مبلغ</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportData.slice(0, 20).map(item => (
                  <TableRow key={item.id}>
                    <TableCell><code>{item.invoice_number}</code></TableCell>
                    <TableCell>{item.student_name || '-'}</TableCell>
                    <TableCell>{toPersianDigits(parseFloat(item.total_amount)?.toLocaleString() || 0)} تومان</TableCell>
                    <TableCell><Badge variant={item.status === 'paid' ? 'success' : 'warning'}>{item.status === 'paid' ? 'پرداخت شده' : 'در انتظار'}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        );
      case 'teachers':
        return (
          <>
            <div style={{ marginBottom: '1rem', padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>
              <strong>تعداد کل معلمان: </strong>{toPersianDigits(stats.total || 0)}
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>نام</TableHead>
                  <TableHead>تخصص</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportData.map(item => (
                  <TableRow key={item.id}>
                    <TableCell>{item.user?.first_name} {item.user?.last_name}</TableCell>
                    <TableCell>{item.expertise || '-'}</TableCell>
                    <TableCell><Badge variant={item.status === 'active' ? 'success' : 'default'}>{item.status === 'active' ? 'فعال' : 'غیرفعال'}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        );
      case 'students':
        return (
          <>
            <div style={{ marginBottom: '1rem', padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>
              <strong>تعداد کل دانش‌آموزان: </strong>{toPersianDigits(stats.total || 0)}
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>نام</TableHead>
                  <TableHead>کد ملی</TableHead>
                  <TableHead>موبایل</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportData.map(item => (
                  <TableRow key={item.id}>
                    <TableCell>{item.user?.first_name} {item.user?.last_name}</TableCell>
                    <TableCell>{item.user?.national_code || '-'}</TableCell>
                    <TableCell>{item.user?.mobile || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        );
      case 'branches':
        return (
          <>
            <div style={{ marginBottom: '1rem', padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>
              <strong>تعداد کل شعب: </strong>{toPersianDigits(stats.total || 0)}
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>نام</TableHead>
                  <TableHead>شهر</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportData.map(item => (
                  <TableRow key={item.id}>
                    <TableCell>{item.name}</TableCell>
                    <TableCell>{item.city}</TableCell>
                    <TableCell><Badge variant={item.is_active ? 'success' : 'default'}>{item.is_active ? 'فعال' : 'غیرفعال'}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        );
      default:
        return <p style={{ textAlign: 'center', color: 'var(--gray-500)' }}>گزارش موجود نیست</p>;
    }
  };

  return (
    <div className="reports-page">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {reports.map((report) => (
          <Card key={report.id} hover>
            <CardContent>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                <span style={{ fontSize: '2.5rem' }}>{report.icon}</span>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: '0 0 0.5rem', color: 'var(--gray-800)' }}>{report.title}</h3>
                  <p style={{ margin: '0 0 1rem', color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                    {report.description}
                  </p>
                  <Button size="small" onClick={() => handleViewReport(report)}>مشاهده گزارش</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Report Modal */}
      <Modal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        title={selectedReport?.title || 'گزارش'}
        size="large"
      >
        {loadingReport ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Spinner size="large" />
          </div>
        ) : (
          renderReportContent()
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowReportModal(false)}>بستن</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminReports;


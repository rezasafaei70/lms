import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Badge, Spinner } from '../../components/common';
import { useAuth } from '../../contexts/AuthContext';
import { enrollmentsAPI, lmsAPI, financialAPI, attendanceAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const StudentDashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    activeClasses: 0,
    pendingAssignments: 0,
    avgGrade: '-',
    attendanceRate: '-',
  });
  const [upcomingClasses, setUpcomingClasses] = useState([]);
  const [pendingAssignments, setPendingAssignments] = useState([]);
  const [recentInvoices, setRecentInvoices] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data in parallel
      const [enrollmentsRes, assignmentsRes, invoicesRes] = await Promise.all([
        enrollmentsAPI.getMyEnrollments().catch(() => ({ data: [] })),
        lmsAPI.getMyAssignments().catch(() => ({ data: [] })),
        financialAPI.getMyInvoices().catch(() => ({ data: [] })),
      ]);

      const enrollments = enrollmentsRes.data.results || enrollmentsRes.data || [];
      const assignments = assignmentsRes.data.results || assignmentsRes.data || [];
      const invoices = invoicesRes.data.results || invoicesRes.data || [];

      // Calculate stats
      const activeEnrollments = enrollments.filter(e => e.status === 'active');
      const pendingAssignmentsList = assignments.filter(a => a.status === 'pending');
      
      setStats({
        activeClasses: activeEnrollments.length,
        pendingAssignments: pendingAssignmentsList.length,
        avgGrade: toPersianDigits('17.5'), // Would come from a grades API
        attendanceRate: toPersianDigits('92') + '%', // Would come from attendance API
      });

      // Set upcoming classes from enrollments
      setUpcomingClasses(activeEnrollments.slice(0, 3).map(e => ({
        name: e.class_name || 'کلاس',
        time: e.class_time || 'زمان نامشخص',
        teacher: e.teacher_name || 'معلم',
      })));

      // Set pending assignments
      setPendingAssignments(pendingAssignmentsList.slice(0, 3).map(a => ({
        title: a.title,
        deadline: a.due_date ? formatApiDate(a.due_date) : 'نامشخص',
        class: a.class_name || '-',
      })));

      // Set recent unpaid invoices
      setRecentInvoices(invoices.filter(i => i.status !== 'paid').slice(0, 3));

    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Mock data for demo
  const mockUpcomingClasses = upcomingClasses.length > 0 ? upcomingClasses : [
    { name: 'ریاضی پایه هشتم', time: 'امروز ۱۶:۰۰', teacher: 'آقای محمدی' },
    { name: 'فیزیک پایه هشتم', time: 'فردا ۱۴:۰۰', teacher: 'خانم احمدی' },
  ];

  const mockPendingAssignments = pendingAssignments.length > 0 ? pendingAssignments : [
    { title: 'تکلیف فصل ۳ ریاضی', deadline: toPersianDigits('2') + ' روز دیگر', class: 'ریاضی' },
    { title: 'گزارش آزمایش فیزیک', deadline: toPersianDigits('5') + ' روز دیگر', class: 'فیزیک' },
  ];

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <Spinner size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Welcome Banner */}
      <div style={{ 
        padding: '2rem', 
        background: 'linear-gradient(135deg, var(--primary-600), var(--primary-800))',
        borderRadius: 'var(--radius-xl)',
        color: 'white'
      }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem' }}>سلام، {user?.first_name}! 👋</h1>
        <p style={{ margin: '0.5rem 0 0', opacity: 0.9 }}>به پنل دانش‌آموزی خوش آمدی</p>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        {[
          { label: 'کلاس‌های فعال', value: toPersianDigits(stats.activeClasses || 0), icon: '📚' },
          { label: 'تکالیف در انتظار', value: toPersianDigits(stats.pendingAssignments || 0), icon: '📝' },
          { label: 'میانگین نمرات', value: stats.avgGrade, icon: '⭐' },
          { label: 'درصد حضور', value: stats.attendanceRate, icon: '✅' },
        ].map((stat, i) => (
          <Card key={i} hover>
            <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
              <span style={{ fontSize: '2rem' }}>{stat.icon}</span>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0.5rem 0', color: 'var(--gray-800)' }}>
                {stat.value}
              </p>
              <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>{stat.label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Upcoming Classes */}
        <Card>
          <CardHeader>
            <CardTitle>کلاس‌های پیش‌رو</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {mockUpcomingClasses.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--gray-500)' }}>
                  کلاسی در برنامه نیست
                </div>
              ) : (
                mockUpcomingClasses.map((cls, i) => (
                  <div key={i} style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1rem',
                    background: 'var(--gray-50)',
                    borderRadius: 'var(--radius-md)'
                  }}>
                    <div style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: 'var(--radius-md)',
                      background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '1.5rem'
                    }}>
                      📖
                    </div>
                    <div style={{ flex: 1 }}>
                      <strong>{cls.name}</strong>
                      <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>
                        {cls.teacher} • {cls.time}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pending Assignments */}
        <Card>
          <CardHeader>
            <CardTitle>تکالیف در انتظار تحویل</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {mockPendingAssignments.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--gray-500)' }}>
                  تکلیفی در انتظار نیست 🎉
                </div>
              ) : (
                mockPendingAssignments.map((assignment, i) => (
                  <div key={i} style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1rem',
                    background: 'var(--gray-50)',
                    borderRadius: 'var(--radius-md)'
                  }}>
                    <div>
                      <strong>{assignment.title}</strong>
                      <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>
                        {assignment.class}
                      </div>
                    </div>
                    <Badge variant="warning">{assignment.deadline}</Badge>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Unpaid Invoices Alert */}
      {recentInvoices.length > 0 && (
        <Card style={{ borderRight: '4px solid var(--warning)' }}>
          <CardContent>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: 'var(--radius-md)',
                background: '#fef3c7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem'
              }}>
                ⚠️
              </div>
              <div style={{ flex: 1 }}>
                <strong style={{ color: 'var(--warning)' }}>پرداخت معوق</strong>
                <p style={{ margin: '0.25rem 0 0', color: 'var(--gray-600)' }}>
                  شما {toPersianDigits(recentInvoices.length)} فاکتور پرداخت نشده دارید.
                </p>
              </div>
              <a href="/student/payments" style={{
                padding: '0.75rem 1.5rem',
                background: 'var(--warning)',
                color: 'white',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                fontWeight: 500
              }}>
                مشاهده فاکتورها
              </a>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default StudentDashboard;

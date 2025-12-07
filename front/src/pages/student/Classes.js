import React, { useState, useEffect } from 'react';
import { Card, CardContent, Badge, Spinner } from '../../components/common';
import { enrollmentsAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const StudentClasses = () => {
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEnrollments();
  }, []);

  const fetchEnrollments = async () => {
    try {
      setLoading(true);
      const response = await enrollmentsAPI.getMyEnrollments();
      setEnrollments(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  // Extract class info from enrollment
  const getClassInfo = (enrollment) => {
    const classDetails = enrollment.class_details || enrollment.class_obj_details || {};
    return {
      name: classDetails.name || enrollment.class_name || 'کلاس بدون نام',
      courseName: classDetails.course_name || '',
      teacherName: classDetails.teacher_name || enrollment.teacher_name || '-',
      branchName: classDetails.branch_name || '',
      startTime: classDetails.start_time || '',
      endTime: classDetails.end_time || '',
      startDate: classDetails.start_date,
      endDate: classDetails.end_date,
      status: classDetails.status || enrollment.status,
      price: classDetails.price || enrollment.total_amount,
    };
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'active': { label: 'فعال', variant: 'success' },
      'approved': { label: 'تأیید شده', variant: 'success' },
      'pending': { label: 'در انتظار', variant: 'warning' },
      'completed': { label: 'تکمیل شده', variant: 'info' },
      'cancelled': { label: 'لغو شده', variant: 'error' },
      'suspended': { label: 'تعلیق', variant: 'error' },
    };
    const statusInfo = statusMap[status] || { label: status || 'نامشخص', variant: 'default' };
    return <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <Spinner size="large" />
      </div>
    );
  }

  if (enrollments.length === 0) {
    return (
      <Card>
        <CardContent style={{ textAlign: 'center', padding: '3rem' }}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 1rem', opacity: 0.4 }}>
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <h3 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>کلاسی یافت نشد</h3>
          <p style={{ margin: 0, color: 'var(--gray-500)' }}>
            شما هنوز در هیچ کلاسی ثبت‌نام نکرده‌اید
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
      {enrollments.map((enrollment) => {
        const classInfo = getClassInfo(enrollment);
        const progress = parseFloat(enrollment.progress_percentage) || 0;
        
        return (
          <Card key={enrollment.id} hover>
            <CardContent>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: 0, color: 'var(--gray-800)' }}>{classInfo.name}</h3>
                    {classInfo.courseName && (
                      <p style={{ margin: '0.25rem 0 0', color: 'var(--primary-600)', fontSize: '0.8125rem', fontWeight: 500 }}>
                        {classInfo.courseName}
                      </p>
                    )}
                  </div>
                  {getStatusBadge(enrollment.status)}
                </div>
                <p style={{ margin: '0.5rem 0 0', color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ verticalAlign: 'middle', marginLeft: '0.25rem' }}>
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  {classInfo.teacherName}
                </p>
              </div>
              
              <div style={{ 
                padding: '1rem', 
                background: 'var(--gray-50)', 
                borderRadius: 'var(--radius-md)',
                marginBottom: '1rem'
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.875rem' }}>
                  <div>
                    <span style={{ color: 'var(--gray-500)' }}>تاریخ شروع</span>
                    <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>
                      {classInfo.startDate ? formatApiDate(classInfo.startDate) : '-'}
                    </p>
                  </div>
                  <div>
                    <span style={{ color: 'var(--gray-500)' }}>ساعت کلاس</span>
                    <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>
                      {classInfo.startTime && classInfo.endTime 
                        ? `${classInfo.startTime.slice(0, 5)} - ${classInfo.endTime.slice(0, 5)}`
                        : '-'
                      }
                    </p>
                  </div>
                  {classInfo.branchName && (
                    <div style={{ gridColumn: '1 / -1' }}>
                      <span style={{ color: 'var(--gray-500)' }}>شعبه</span>
                      <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>{classInfo.branchName}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Progress */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.875rem', color: 'var(--gray-600)' }}>پیشرفت دوره</span>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>{toPersianDigits(Math.round(progress))}%</span>
                </div>
                <div style={{ 
                  height: '8px', 
                  background: 'var(--gray-200)',
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{ 
                    height: '100%', 
                    width: `${progress}%`,
                    background: 'linear-gradient(90deg, var(--primary-500), var(--primary-600))',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              {/* Attendance info */}
              {enrollment.total_sessions_attended !== undefined && (
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  marginTop: '1rem',
                  padding: '0.75rem',
                  background: 'var(--primary-50)',
                  borderRadius: 'var(--radius)',
                  fontSize: '0.8125rem'
                }}>
                  <span style={{ color: 'var(--primary-700)' }}>جلسات حضور</span>
                  <span style={{ fontWeight: 600, color: 'var(--primary-700)' }}>
                    {toPersianDigits(enrollment.total_sessions_attended || 0)} جلسه
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};

export default StudentClasses;


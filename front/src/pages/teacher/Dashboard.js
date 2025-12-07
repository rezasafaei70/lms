import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, Badge } from '../../components/common';
import { useAuth } from '../../contexts/AuthContext';

const TeacherDashboard = () => {
  const { user } = useAuth();

  const todayClasses = [
    { name: 'ریاضی پایه هشتم', time: '۱۴:۰۰ - ۱۶:۰۰', students: 18, room: 'کلاس ۱۰۱' },
    { name: 'هندسه پایه نهم', time: '۱۶:۳۰ - ۱۸:۳۰', students: 15, room: 'کلاس ۱۰۳' },
  ];

  const pendingAssignments = [
    { title: 'تکلیف فصل ۳ ریاضی', class: 'ریاضی هشتم', submitted: 12, total: 18 },
    { title: 'تمرینات هندسه', class: 'هندسه نهم', submitted: 8, total: 15 },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ 
        padding: '1.5rem', 
        background: 'linear-gradient(135deg, #14b8a6, #0d9488)',
        borderRadius: 'var(--radius-lg)',
        color: 'white'
      }}>
        <h2 style={{ margin: 0 }}>سلام، استاد {user?.last_name}!</h2>
        <p style={{ margin: '0.5rem 0 0', opacity: 0.9 }}>امروز ۲ کلاس دارید</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        {[
          { label: 'کلاس‌های فعال', value: 4 },
          { label: 'دانش‌آموزان', value: 67 },
          { label: 'تکالیف در انتظار', value: 23 },
          { label: 'جلسات این هفته', value: 8 },
        ].map((stat, i) => (
          <Card key={i}>
            <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
              <span style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--primary-600)' }}>{stat.value}</span>
              <p style={{ margin: '0.25rem 0 0', color: 'var(--gray-500)', fontSize: '0.875rem' }}>{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <Card>
          <CardHeader>
            <CardTitle>کلاس‌های امروز</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {todayClasses.map((cls, i) => (
                <div key={i} style={{ 
                  padding: '1rem',
                  background: 'var(--gray-50)',
                  borderRadius: 'var(--radius-md)',
                  borderRight: '4px solid var(--primary-500)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{cls.name}</strong>
                    <Badge variant="info">{cls.room}</Badge>
                  </div>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
                    {cls.time} • {cls.students} دانش‌آموز
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>تکالیف در انتظار تصحیح</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {pendingAssignments.map((assignment, i) => (
                <div key={i} style={{ 
                  padding: '1rem',
                  background: 'var(--gray-50)',
                  borderRadius: 'var(--radius-md)'
                }}>
                  <strong>{assignment.title}</strong>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
                    {assignment.class}
                  </div>
                  <div style={{ 
                    marginTop: '0.75rem', 
                    height: '8px', 
                    background: 'var(--gray-200)',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{ 
                      height: '100%', 
                      width: `${(assignment.submitted / assignment.total) * 100}%`,
                      background: 'var(--primary-500)'
                    }} />
                  </div>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--gray-500)' }}>
                    {assignment.submitted} از {assignment.total} تحویل داده‌اند
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default TeacherDashboard;


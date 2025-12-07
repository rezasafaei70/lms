import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Spinner, Badge } from '../../components/common';
import { useAuth } from '../../contexts/AuthContext';

const BranchDashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  
  // Get selected branch from localStorage
  const selectedBranch = JSON.parse(localStorage.getItem('selected_branch') || '{}');

  const stats = [
    { title: 'دانش‌آموزان فعال', value: 156, color: 'purple' },
    { title: 'کلاس‌های در حال برگزاری', value: 12, color: 'blue' },
    { title: 'معلمان', value: 8, color: 'teal' },
    { title: 'درآمد ماه جاری', value: '۴۵,۰۰۰,۰۰۰', color: 'green', suffix: ' تومان' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ 
        padding: '1.5rem', 
        background: 'linear-gradient(135deg, var(--primary-600), var(--primary-700))',
        borderRadius: 'var(--radius-lg)',
        color: 'white'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ margin: 0 }}>خوش آمدید، {user?.first_name}!</h2>
            <p style={{ margin: '0.5rem 0 0', opacity: 0.9 }}>
              پنل مدیریت شعبه {selectedBranch?.name || ''}
            </p>
          </div>
          {selectedBranch?.image_url && (
            <img 
              src={selectedBranch.image_url} 
              alt={selectedBranch.name}
              style={{ 
                width: '60px', 
                height: '60px', 
                borderRadius: 'var(--radius-md)',
                objectFit: 'cover',
                border: '2px solid rgba(255,255,255,0.3)'
              }}
            />
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
        {stats.map((stat, index) => (
          <Card key={index} hover>
            <CardContent>
              <div style={{ textAlign: 'center' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>{stat.title}</span>
                <p style={{ fontSize: '1.75rem', fontWeight: 700, margin: '0.5rem 0', color: 'var(--gray-800)' }}>
                  {stat.value}{stat.suffix}
                </p>
              </div>
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
              {[
                { name: 'ریاضی پایه هشتم', time: '۱۴:۰۰ - ۱۶:۰۰', teacher: 'آقای محمدی', status: 'ongoing' },
                { name: 'فیزیک پایه نهم', time: '۱۶:۳۰ - ۱۸:۳۰', teacher: 'خانم احمدی', status: 'upcoming' },
                { name: 'شیمی پایه دهم', time: '۱۹:۰۰ - ۲۱:۰۰', teacher: 'آقای رضایی', status: 'upcoming' },
              ].map((cls, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  padding: '1rem',
                  background: 'var(--gray-50)',
                  borderRadius: 'var(--radius-md)'
                }}>
                  <div>
                    <strong>{cls.name}</strong>
                    <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>
                      {cls.time} | {cls.teacher}
                    </div>
                  </div>
                  <Badge variant={cls.status === 'ongoing' ? 'success' : 'default'}>
                    {cls.status === 'ongoing' ? 'در حال برگزاری' : 'آینده'}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>اعلان‌ها</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[
                { text: '۳ ثبت‌نام جدید در انتظار تایید', type: 'info' },
                { text: '۲ فاکتور معوق', type: 'warning' },
                { text: 'جلسه معلمان فردا ساعت ۱۰', type: 'default' },
              ].map((notif, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '1rem',
                  background: 'var(--gray-50)',
                  borderRadius: 'var(--radius-md)'
                }}>
                  <Badge variant={notif.type} size="small">!</Badge>
                  <span>{notif.text}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default BranchDashboard;


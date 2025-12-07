import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Badge, Spinner } from '../../components/common';
import { coursesAPI } from '../../services/api';

const TeacherClasses = () => {
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClasses();
  }, []);

  const fetchClasses = async () => {
    try {
      setLoading(true);
      const response = await coursesAPI.getClasses();
      setClasses(response.data.results || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <Spinner size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
      {classes.map((cls) => (
        <Card key={cls.id} hover>
          <CardContent>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ margin: 0, color: 'var(--gray-800)' }}>{cls.name}</h3>
                <p style={{ margin: '0.25rem 0 0', color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                  {cls.course_name}
                </p>
              </div>
              <Badge variant={cls.status === 'ongoing' ? 'success' : 'info'}>
                {cls.status === 'ongoing' ? 'فعال' : 'آینده'}
              </Badge>
            </div>
            
            <div style={{ 
              marginTop: '1.5rem', 
              padding: '1rem', 
              background: 'var(--gray-50)', 
              borderRadius: 'var(--radius-md)' 
            }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.875rem' }}>
                <div>
                  <span style={{ color: 'var(--gray-500)' }}>دانش‌آموزان</span>
                  <p style={{ margin: '0.25rem 0 0', fontWeight: 600 }}>{cls.current_enrollments} نفر</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)' }}>ظرفیت</span>
                  <p style={{ margin: '0.25rem 0 0', fontWeight: 600 }}>{cls.capacity} نفر</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)' }}>روزها</span>
                  <p style={{ margin: '0.25rem 0 0', fontWeight: 600 }}>{cls.schedule_days?.join('، ') || '-'}</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)' }}>ساعت</span>
                  <p style={{ margin: '0.25rem 0 0', fontWeight: 600 }}>{cls.start_time || '-'}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
      
      {classes.length === 0 && (
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '3rem' }}>
            <p style={{ color: 'var(--gray-500)' }}>کلاسی یافت نشد</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TeacherClasses;


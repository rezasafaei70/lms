import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { coursesAPI } from '../../services/api';

const BranchClasses = () => {
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
      console.error('Error fetching classes:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader action={<Button>کلاس جدید</Button>}>
        <CardTitle>کلاس‌های شعبه</CardTitle>
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
                <TableHead>نام کلاس</TableHead>
                <TableHead>معلم</TableHead>
                <TableHead>روزها</TableHead>
                <TableHead>ساعت</TableHead>
                <TableHead>ظرفیت</TableHead>
                <TableHead>وضعیت</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {classes.length === 0 ? (
                <TableEmpty message="کلاسی یافت نشد" />
              ) : (
                classes.map((cls) => (
                  <TableRow key={cls.id}>
                    <TableCell><strong>{cls.name}</strong></TableCell>
                    <TableCell>{cls.teacher_name}</TableCell>
                    <TableCell>{cls.schedule_days?.join('، ')}</TableCell>
                    <TableCell>{cls.start_time} - {cls.end_time}</TableCell>
                    <TableCell>{cls.current_enrollments}/{cls.capacity}</TableCell>
                    <TableCell>
                      <Badge variant={cls.status === 'ongoing' ? 'success' : 'info'}>
                        {cls.status === 'ongoing' ? 'در حال برگزاری' : 'برنامه‌ریزی شده'}
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
  );
};

export default BranchClasses;


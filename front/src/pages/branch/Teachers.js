import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { usersAPI } from '../../services/api';

const BranchTeachers = () => {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeachers();
  }, []);

  const fetchTeachers = async () => {
    try {
      setLoading(true);
      const response = await usersAPI.getTeachers();
      setTeachers(response.data.results || []);
    } catch (error) {
      console.error('Error fetching teachers:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>معلمان</CardTitle>
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
                <TableHead>کد پرسنلی</TableHead>
                <TableHead>نام</TableHead>
                <TableHead>موبایل</TableHead>
                <TableHead>تخصص</TableHead>
                <TableHead>امتیاز</TableHead>
                <TableHead>وضعیت</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teachers.length === 0 ? (
                <TableEmpty message="معلمی یافت نشد" />
              ) : (
                teachers.map((teacher) => (
                  <TableRow key={teacher.id}>
                    <TableCell>{teacher.employee_code}</TableCell>
                    <TableCell>
                      <strong>{teacher.user?.first_name} {teacher.user?.last_name}</strong>
                    </TableCell>
                    <TableCell>{teacher.user?.mobile}</TableCell>
                    <TableCell>{teacher.specialization || '-'}</TableCell>
                    <TableCell>
                      <span style={{ color: 'var(--warning)' }}>★</span> {teacher.rating || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={teacher.is_active ? 'success' : 'default'}>
                        {teacher.is_active ? 'فعال' : 'غیرفعال'}
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

export default BranchTeachers;


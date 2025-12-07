import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Badge, Spinner } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { usersAPI } from '../../services/api';

const BranchStudents = () => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      const response = await usersAPI.getStudents();
      setStudents(response.data.results || []);
    } catch (error) {
      console.error('Error fetching students:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredStudents = students.filter(s => 
    search === '' || 
    s.user?.first_name?.includes(search) ||
    s.user?.last_name?.includes(search)
  );

  return (
    <Card>
      <CardHeader action={<Button>دانش‌آموز جدید</Button>}>
        <CardTitle>دانش‌آموزان</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ marginBottom: '1rem', maxWidth: '300px' }}>
          <Input
            placeholder="جستجوی دانش‌آموز..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Spinner size="large" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>شماره دانش‌آموزی</TableHead>
                <TableHead>نام</TableHead>
                <TableHead>موبایل</TableHead>
                <TableHead>پایه تحصیلی</TableHead>
                <TableHead>وضعیت</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredStudents.length === 0 ? (
                <TableEmpty message="دانش‌آموزی یافت نشد" />
              ) : (
                filteredStudents.map((student) => (
                  <TableRow key={student.id}>
                    <TableCell>{student.student_number}</TableCell>
                    <TableCell>
                      <strong>{student.user?.first_name} {student.user?.last_name}</strong>
                    </TableCell>
                    <TableCell>{student.user?.mobile}</TableCell>
                    <TableCell>{student.grade_level_details?.name || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={student.is_active ? 'success' : 'default'}>
                        {student.is_active ? 'فعال' : 'غیرفعال'}
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

export default BranchStudents;


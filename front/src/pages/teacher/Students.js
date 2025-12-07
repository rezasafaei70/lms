import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Input, Badge, Spinner } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';

const TeacherStudents = () => {
  const [students] = useState([
    { id: 1, name: 'علی محمدی', class: 'ریاضی هشتم', attendance: 95, avgScore: 18.5 },
    { id: 2, name: 'مریم احمدی', class: 'ریاضی هشتم', attendance: 100, avgScore: 19.2 },
    { id: 3, name: 'حسین رضایی', class: 'هندسه نهم', attendance: 85, avgScore: 16.8 },
    { id: 4, name: 'زهرا کریمی', class: 'هندسه نهم', attendance: 92, avgScore: 17.5 },
    { id: 5, name: 'امیر حسینی', class: 'حسابان یازدهم', attendance: 88, avgScore: 15.2 },
  ]);
  const [search, setSearch] = useState('');

  const filteredStudents = students.filter(s => 
    search === '' || s.name.includes(search)
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>دانش‌آموزان من</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ marginBottom: '1rem', maxWidth: '300px' }}>
          <Input
            placeholder="جستجوی دانش‌آموز..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>نام</TableHead>
              <TableHead>کلاس</TableHead>
              <TableHead>درصد حضور</TableHead>
              <TableHead>میانگین نمره</TableHead>
              <TableHead>وضعیت</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredStudents.map((student) => (
              <TableRow key={student.id}>
                <TableCell><strong>{student.name}</strong></TableCell>
                <TableCell>{student.class}</TableCell>
                <TableCell>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ 
                      width: '60px', 
                      height: '6px', 
                      background: 'var(--gray-200)',
                      borderRadius: '3px',
                      overflow: 'hidden'
                    }}>
                      <div style={{ 
                        height: '100%', 
                        width: `${student.attendance}%`,
                        background: student.attendance >= 90 ? 'var(--success)' : 'var(--warning)'
                      }} />
                    </div>
                    <span>{student.attendance}%</span>
                  </div>
                </TableCell>
                <TableCell>{student.avgScore}</TableCell>
                <TableCell>
                  <Badge variant={student.avgScore >= 17 ? 'success' : student.avgScore >= 14 ? 'warning' : 'error'}>
                    {student.avgScore >= 17 ? 'عالی' : student.avgScore >= 14 ? 'خوب' : 'نیاز به تلاش'}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default TeacherStudents;


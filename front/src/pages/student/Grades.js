import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, Badge } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/common';
import { toPersianDigits } from '../../utils/jalaliDate';

const StudentGrades = () => {
  const grades = [
    { subject: 'ریاضی', assignments: [18, 17, 19], exams: [17.5, 18], attendance: 95 },
    { subject: 'فیزیک', assignments: [16, 18, 17], exams: [16, 17.5], attendance: 92 },
    { subject: 'شیمی', assignments: [19, 18.5, 17], exams: [18, 19], attendance: 100 },
    { subject: 'زیست‌شناسی', assignments: [17, 16, 18], exams: [17], attendance: 88 },
  ];

  const calculateAvg = (arr) => arr.length ? (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1) : '-';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits('17.8')}</span>
            <p style={{ margin: '0.5rem 0 0', color: 'var(--gray-500)' }}>معدل کل</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--primary-600)' }}>{toPersianDigits('94')}%</span>
            <p style={{ margin: '0.5rem 0 0', color: 'var(--gray-500)' }}>درصد حضور</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '1.5rem' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--info)' }}>{toPersianDigits('3')}</span>
            <p style={{ margin: '0.5rem 0 0', color: 'var(--gray-500)' }}>رتبه در کلاس</p>
          </CardContent>
        </Card>
      </div>

      {/* Grades Table */}
      <Card>
        <CardHeader>
          <CardTitle>جزئیات نمرات</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>درس</TableHead>
                <TableHead>میانگین تکالیف</TableHead>
                <TableHead>میانگین امتحانات</TableHead>
                <TableHead>حضور</TableHead>
                <TableHead>وضعیت</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {grades.map((grade, i) => {
                const assignmentAvg = calculateAvg(grade.assignments);
                const examAvg = calculateAvg(grade.exams);
                const totalAvg = ((parseFloat(assignmentAvg) + parseFloat(examAvg)) / 2).toFixed(1);
                
                return (
                  <TableRow key={i}>
                    <TableCell><strong>{grade.subject}</strong></TableCell>
                    <TableCell>{toPersianDigits(assignmentAvg)}</TableCell>
                    <TableCell>{toPersianDigits(examAvg)}</TableCell>
                    <TableCell>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ 
                          width: '40px', 
                          height: '6px', 
                          background: 'var(--gray-200)',
                          borderRadius: '3px',
                          overflow: 'hidden'
                        }}>
                          <div style={{ 
                            height: '100%', 
                            width: `${grade.attendance}%`,
                            background: grade.attendance >= 90 ? 'var(--success)' : 'var(--warning)'
                          }} />
                        </div>
                        <span>{toPersianDigits(grade.attendance)}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={parseFloat(totalAvg) >= 17 ? 'success' : parseFloat(totalAvg) >= 14 ? 'warning' : 'error'}>
                        {parseFloat(totalAvg) >= 17 ? 'عالی' : parseFloat(totalAvg) >= 14 ? 'خوب' : 'نیاز به تلاش'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default StudentGrades;

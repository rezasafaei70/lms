import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner, JalaliDatePicker } from '../../components/common';
import { coursesAPI, attendanceAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const TeacherAttendance = () => {
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState(null);
  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    fetchClasses();
  }, []);

  const fetchClasses = async () => {
    try {
      setLoading(true);
      const response = await coursesAPI.getClasses({ status: 'ongoing' });
      setClasses(response.data.results || []);
    } catch (error) {
      console.error('Error fetching classes:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStudents = async (classId) => {
    try {
      setLoadingStudents(true);
      const response = await coursesAPI.getClassStudents(classId);
      const studentsList = response.data.results || response.data || [];
      setStudents(studentsList);
      
      // Initialize attendance state using enrollment_id as key
      const initialAttendance = {};
      studentsList.forEach(student => {
        // Use enrollment_id if available, otherwise use id
        const enrollmentKey = student.enrollment_id || student.id;
        initialAttendance[enrollmentKey] = student.attendance_status || 'present';
      });
      setAttendance(initialAttendance);
    } catch (error) {
      console.error('Error fetching students:', error);
      setStudents([]);
      setAttendance({});
    } finally {
      setLoadingStudents(false);
    }
  };

  const handleClassSelect = (cls) => {
    setSelectedClass(cls);
    fetchStudents(cls.id);
  };

  // enrollmentId is used as key for attendance
  const handleAttendanceChange = (enrollmentId, status) => {
    setAttendance(prev => ({
      ...prev,
      [enrollmentId]: status
    }));
  };

  const handleSaveAttendance = async () => {
    if (!selectedClass) return;
    
    try {
      setSaving(true);
      
      // Format attendance data according to backend API
      const attendanceData = Object.entries(attendance).map(([studentId, status]) => ({
        enrollment: studentId, // enrollment_id from the student data
        status: status,
      }));
      
      // Backend expects: { session: session_id, attendances: [...] }
      await attendanceAPI.bulkRecord({ 
        session: selectedClass.id, // This should be a session ID
        attendances: attendanceData 
      });
      alert('حضور و غیاب با موفقیت ثبت شد');
    } catch (error) {
      console.error('Error saving attendance:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || 'خطا در ثبت حضور و غیاب';
      alert(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const attendanceSummary = {
    present: Object.values(attendance).filter(s => s === 'present').length,
    absent: Object.values(attendance).filter(s => s === 'absent').length,
    late: Object.values(attendance).filter(s => s === 'late').length,
    excused: Object.values(attendance).filter(s => s === 'excused').length,
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <Spinner size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1.5rem' }}>
      {/* Classes List */}
      <Card>
        <CardHeader>
          <CardTitle>کلاس‌های من</CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {classes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--gray-500)' }}>
                کلاسی یافت نشد
              </div>
            ) : (
              classes.map((cls) => (
                <button
                  key={cls.id}
                  onClick={() => handleClassSelect(cls)}
                  style={{
                    padding: '1rem',
                    background: selectedClass?.id === cls.id ? 'var(--primary-50)' : 'var(--gray-50)',
                    border: selectedClass?.id === cls.id ? '2px solid var(--primary-500)' : '2px solid transparent',
                    borderRadius: 'var(--radius-md)',
                    textAlign: 'right',
                    cursor: 'pointer',
                    transition: 'all var(--transition)'
                  }}
                >
                  <strong style={{ display: 'block', color: 'var(--gray-800)' }}>{cls.name}</strong>
                  <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                    {toPersianDigits(cls.current_enrollments || 0)} دانش‌آموز
                  </div>
                  {cls.schedule_days && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '0.25rem' }}>
                      {cls.schedule_days.join('، ')}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Attendance Form */}
      <Card>
        <CardHeader action={
          selectedClass && (
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <JalaliDatePicker
                value={selectedDate}
                onChange={(date) => setSelectedDate(date)}
                placeholder="انتخاب تاریخ"
              />
              <Button onClick={handleSaveAttendance} loading={saving}>
                ثبت حضور و غیاب
              </Button>
            </div>
          )
        }>
          <CardTitle>
            {selectedClass ? `حضور و غیاب - ${selectedClass.name}` : 'یک کلاس انتخاب کنید'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!selectedClass ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-500)' }}>
              لطفاً یک کلاس از لیست سمت راست انتخاب کنید
            </div>
          ) : loadingStudents ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <>
              {/* Summary */}
              <div style={{ 
                display: 'flex', 
                gap: '1rem', 
                marginBottom: '1.5rem',
                padding: '1rem',
                background: 'var(--gray-50)',
                borderRadius: 'var(--radius-lg)'
              }}>
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(attendanceSummary.present)}</span>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--gray-500)' }}>حاضر</p>
                </div>
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--error)' }}>{toPersianDigits(attendanceSummary.absent)}</span>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--gray-500)' }}>غایب</p>
                </div>
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--warning)' }}>{toPersianDigits(attendanceSummary.late)}</span>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--gray-500)' }}>تأخیر</p>
                </div>
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--info)' }}>{toPersianDigits(attendanceSummary.excused)}</span>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--gray-500)' }}>موجه</p>
                </div>
              </div>

              {/* Students List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {students.map((student) => {
                  // Support both direct name fields and nested student_name
                  const studentName = student.student_name || 
                                      `${student.first_name || ''} ${student.last_name || ''}`.trim() ||
                                      student.name || 'بدون نام';
                  const studentNumber = student.student_number || student.mobile || student.national_code || '-';
                  const firstLetter = studentName?.[0] || (student.first_name?.[0]) || '?';
                  // Use enrollment_id for attendance tracking
                  const enrollmentKey = student.enrollment_id || student.id;
                  
                  return (
                    <div
                      key={enrollmentKey}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '1rem',
                        background: 'var(--gray-50)',
                        borderRadius: 'var(--radius-md)',
                        borderRight: `4px solid ${
                          attendance[enrollmentKey] === 'present' ? 'var(--success)' :
                          attendance[enrollmentKey] === 'absent' ? 'var(--error)' :
                          attendance[enrollmentKey] === 'late' ? 'var(--warning)' : 'var(--info)'
                        }`
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{
                          width: '40px',
                          height: '40px',
                          borderRadius: 'var(--radius)',
                          background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 600,
                          fontSize: '0.875rem'
                        }}>
                          {firstLetter}
                        </div>
                        <div>
                          <span style={{ fontWeight: 500 }}>{studentName}</span>
                          <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
                            {studentNumber}
                          </div>
                        </div>
                      </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {[
                        { key: 'present', label: 'حاضر', color: 'success', bg: '#d1fae5' },
                        { key: 'absent', label: 'غایب', color: 'error', bg: '#fee2e2' },
                        { key: 'late', label: 'تأخیر', color: 'warning', bg: '#fef3c7' },
                        { key: 'excused', label: 'موجه', color: 'info', bg: '#dbeafe' },
                      ].map(status => (
                        <button
                          key={status.key}
                          onClick={() => handleAttendanceChange(enrollmentKey, status.key)}
                          style={{
                            padding: '0.5rem 1rem',
                            borderRadius: 'var(--radius)',
                            background: attendance[enrollmentKey] === status.key ? status.bg : 'white',
                            border: attendance[enrollmentKey] === status.key 
                              ? `2px solid var(--${status.color})` 
                              : '2px solid var(--gray-200)',
                            color: attendance[enrollmentKey] === status.key 
                              ? `var(--${status.color})` 
                              : 'var(--gray-500)',
                            cursor: 'pointer',
                            fontWeight: attendance[enrollmentKey] === status.key ? 600 : 400,
                            fontSize: '0.8125rem',
                            transition: 'all var(--transition)'
                          }}
                        >
                          {status.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  );
                })}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TeacherAttendance;

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner, JalaliDatePicker } from '../../components/common';
import { coursesAPI, attendanceAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const TeacherAttendance = () => {
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchClasses();
  }, []);

  const fetchClasses = async () => {
    try {
      setLoading(true);
      const response = await coursesAPI.getClasses({ status: 'ongoing' });
      setClasses(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error fetching classes:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = async (classId) => {
    try {
      setLoadingSessions(true);
      const response = await coursesAPI.getClassSessions(classId);
      const sessionsList = response.data.results || response.data || [];
      setSessions(sessionsList);
      setSelectedSession(null);
    } catch (error) {
      console.error('Error fetching sessions:', error);
      setSessions([]);
    } finally {
      setLoadingSessions(false);
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
    setSelectedSession(null);
    fetchSessions(cls.id);
    fetchStudents(cls.id);
  };

  const handleSessionSelect = async (session) => {
    setSelectedSession(session);
    
    // بارگذاری حضور غیاب ثبت شده قبلی برای این جلسه
    try {
      const response = await attendanceAPI.getBySession(session.id);
      // Backend returns: { session: {...}, attendances: [...] }
      const existingAttendance = response.data.attendances || response.data.results || response.data || [];
      
      if (existingAttendance.length > 0) {
        // بروزرسانی state با اطلاعات قبلی
        const attendanceMap = {};
        existingAttendance.forEach(record => {
          // enrollment می‌تواند آبجکت یا فقط ID باشد
          const enrollmentId = record.enrollment?.id || record.enrollment_id || record.enrollment;
          if (enrollmentId) {
            attendanceMap[enrollmentId] = record.status;
          }
        });
        setAttendance(prev => ({ ...prev, ...attendanceMap }));
      }
    } catch (error) {
      console.error('Error fetching existing attendance:', error);
      // اگر خطا داد، از پیش‌فرض حاضر استفاده کن
    }
  };

  const handleAttendanceChange = (enrollmentId, status) => {
    setAttendance(prev => ({
      ...prev,
      [enrollmentId]: status
    }));
  };

  const handleSaveAttendance = async () => {
    if (!selectedClass || !selectedSession) {
      alert('لطفاً یک جلسه انتخاب کنید');
      return;
    }
    
    try {
      setSaving(true);
      
      const attendanceData = Object.entries(attendance).map(([enrollmentId, status]) => ({
        enrollment: enrollmentId,
        status: status,
      }));
      
      await attendanceAPI.bulkRecord({ 
        session: selectedSession.id,
        attendances: attendanceData 
      });
      alert('حضور و غیاب با موفقیت ثبت شد');
    } catch (error) {
      console.error('Error saving attendance:', error);
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message || 
                       JSON.stringify(error.response?.data) ||
                       'خطا در ثبت حضور و غیاب';
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
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem' }}>
      {/* Sidebar - Classes & Sessions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Classes List */}
        <Card>
          <CardHeader>
            <CardTitle>کلاس‌های من</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '250px', overflowY: 'auto' }}>
              {classes.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--gray-500)' }}>
                  کلاسی یافت نشد
                </div>
              ) : (
                classes.map((cls) => (
                  <button
                    key={cls.id}
                    onClick={() => handleClassSelect(cls)}
                    style={{
                      padding: '0.75rem',
                      background: selectedClass?.id === cls.id ? 'var(--primary-50)' : 'var(--gray-50)',
                      border: selectedClass?.id === cls.id ? '2px solid var(--primary-500)' : '2px solid transparent',
                      borderRadius: 'var(--radius-md)',
                      textAlign: 'right',
                      cursor: 'pointer',
                      transition: 'all var(--transition)'
                    }}
                  >
                    <strong style={{ display: 'block', color: 'var(--gray-800)', fontSize: '0.875rem' }}>{cls.name}</strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                      {toPersianDigits(cls.current_enrollments || 0)} دانش‌آموز
                    </div>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Sessions List */}
        {selectedClass && (
          <Card>
            <CardHeader>
              <CardTitle>جلسات</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingSessions ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '1rem' }}>
                  <Spinner />
                </div>
              ) : sessions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                  جلسه‌ای برای این کلاس ثبت نشده
                  <div style={{ marginTop: '0.5rem' }}>
                    <Button size="small" onClick={() => coursesAPI.generateClassSessions(selectedClass.id).then(() => fetchSessions(selectedClass.id))}>
                      ایجاد جلسات
                    </Button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      onClick={() => handleSessionSelect(session)}
                      style={{
                        padding: '0.75rem',
                        background: selectedSession?.id === session.id ? 'var(--primary-50)' : 'white',
                        border: selectedSession?.id === session.id ? '2px solid var(--primary-500)' : '1px solid var(--gray-200)',
                        borderRadius: 'var(--radius)',
                        textAlign: 'right',
                        cursor: 'pointer',
                        transition: 'all var(--transition)'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                          جلسه {toPersianDigits(session.session_number || session.number || '-')}
                        </span>
                        {session.attendance_taken && (
                          <Badge variant="success" style={{ fontSize: '0.625rem' }}>✓</Badge>
                        )}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                        {formatApiDate(session.date)}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Attendance Form */}
      <Card>
        <CardHeader action={
          selectedClass && selectedSession && (
            <Button onClick={handleSaveAttendance} loading={saving}>
              ثبت حضور و غیاب
            </Button>
          )
        }>
          <CardTitle>
            {!selectedClass ? 'یک کلاس انتخاب کنید' : 
             !selectedSession ? 'یک جلسه انتخاب کنید' :
             `حضور و غیاب - ${selectedClass.name} - جلسه ${toPersianDigits(selectedSession.session_number || selectedSession.number || '')}`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!selectedClass ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-500)' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
              لطفاً یک کلاس از لیست سمت راست انتخاب کنید
            </div>
          ) : !selectedSession ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-500)' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📅</div>
              لطفاً یک جلسه انتخاب کنید
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
              {students.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--gray-500)' }}>
                  دانش‌آموزی در این کلاس ثبت‌نام نکرده است
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {students.map((student) => {
                    const studentName = student.student_name || 
                                        `${student.first_name || ''} ${student.last_name || ''}`.trim() ||
                                        student.name || 'بدون نام';
                    const studentNumber = student.student_number || student.mobile || student.national_code || '-';
                    const firstLetter = studentName?.[0] || (student.first_name?.[0]) || '?';
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
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TeacherAttendance;

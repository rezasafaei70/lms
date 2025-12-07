import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, JalaliDatePicker } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { coursesAPI, branchesAPI, usersAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const AdminClasses = () => {
  const [classes, setClasses] = useState([]);
  const [courses, setCourses] = useState([]);
  const [branches, setBranches] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [classrooms, setClassrooms] = useState([]);
  const [terms, setTerms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showStudentsModal, setShowStudentsModal] = useState(false);
  const [editingClass, setEditingClass] = useState(null);
  const [deletingClass, setDeletingClass] = useState(null);
  const [selectedClass, setSelectedClass] = useState(null);
  const [classStudents, setClassStudents] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [showSessionsModal, setShowSessionsModal] = useState(false);
  const [classSessions, setClassSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [generatingSessions, setGeneratingSessions] = useState(false);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    course: '',
    branch: '',
    teacher: '',
    classroom: '',
    term: '',
    capacity: 20,
    schedule_days: [],
    start_time: '14:00',
    end_time: '16:00',
    start_date: '',
    end_date: '',
    status: 'scheduled',
    description: '',
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const weekDays = [
    { key: 'saturday', label: 'شنبه' },
    { key: 'sunday', label: 'یکشنبه' },
    { key: 'monday', label: 'دوشنبه' },
    { key: 'tuesday', label: 'سه‌شنبه' },
    { key: 'wednesday', label: 'چهارشنبه' },
    { key: 'thursday', label: 'پنجشنبه' },
    { key: 'friday', label: 'جمعه' },
  ];

  const dayNames = {
    saturday: 'شنبه',
    sunday: 'یکشنبه',
    monday: 'دوشنبه',
    tuesday: 'سه‌شنبه',
    wednesday: 'چهارشنبه',
    thursday: 'پنجشنبه',
    friday: 'جمعه',
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [classesRes, coursesRes, branchesRes, teachersRes, termsRes] = await Promise.all([
        coursesAPI.getClasses(),
        coursesAPI.list(),
        branchesAPI.list(),
        usersAPI.getTeachers(),
        coursesAPI.getTerms(),
      ]);
      
      setClasses(classesRes.data.results || []);
      setCourses(coursesRes.data.results || []);
      setBranches(branchesRes.data.results || []);
      setTeachers(teachersRes.data.results || []);
      setTerms(termsRes.data.results || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchClassrooms = async (branchId) => {
    if (!branchId) {
      setClassrooms([]);
      return;
    }
    try {
      const response = await branchesAPI.getClassrooms({ branch: branchId });
      setClassrooms(response.data.results || []);
    } catch (error) {
      console.error('Error fetching classrooms:', error);
    }
  };

  const handleOpenModal = (cls = null) => {
    if (cls) {
      setEditingClass(cls);
      // Get teacher User ID from teacher_details if available, otherwise use teacher
      const teacherId = cls.teacher_details?.id || cls.teacher;
      setFormData({
        name: cls.name || '',
        course: cls.course || '',
        branch: cls.branch || '',
        teacher: teacherId || '',
        classroom: cls.classroom || '',
        term: cls.term || '',
        capacity: cls.capacity || 20,
        schedule_days: cls.schedule_days || [],
        start_time: cls.start_time || '14:00',
        end_time: cls.end_time || '16:00',
        start_date: cls.start_date || '',
        end_date: cls.end_date || '',
        status: cls.status || 'scheduled',
        description: cls.description || '',
      });
      if (cls.branch) {
        fetchClassrooms(cls.branch);
      }
    } else {
      setEditingClass(null);
      setFormData({
        name: '',
        course: '',
        branch: '',
        teacher: '',
        classroom: '',
        term: '',
        capacity: 20,
        schedule_days: [],
        start_time: '14:00',
        end_time: '16:00',
        start_date: '',
        end_date: '',
        status: 'scheduled',
        description: '',
      });
      setClassrooms([]);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingClass(null);
  };

  const handleBranchChange = (branchId) => {
    setFormData({ ...formData, branch: branchId, classroom: '' });
    fetchClassrooms(branchId);
  };

  const handleDayToggle = (day) => {
    const days = formData.schedule_days.includes(day)
      ? formData.schedule_days.filter(d => d !== day)
      : [...formData.schedule_days, day];
    setFormData({ ...formData, schedule_days: days });
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const data = { ...formData };
      
      // Convert numbers
      if (data.capacity) data.capacity = parseInt(data.capacity);
      
      // Remove empty values
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null || (Array.isArray(data[key]) && data[key].length === 0)) {
          delete data[key];
        }
      });

      if (editingClass) {
        await coursesAPI.updateClass(editingClass.id, data);
      } else {
        await coursesAPI.createClass(data);
      }
      handleCloseModal();
      fetchData();
    } catch (error) {
      console.error('Error saving class:', error);
      alert(error.response?.data?.detail || 'خطا در ذخیره کلاس');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (cls) => {
    setDeletingClass(cls);
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!deletingClass) return;
    
    try {
      setDeleting(true);
      await coursesAPI.deleteClass(deletingClass.id);
      setShowDeleteModal(false);
      setDeletingClass(null);
      fetchData();
    } catch (error) {
      console.error('Error deleting class:', error);
      alert(error.response?.data?.detail || 'خطا در حذف کلاس');
    } finally {
      setDeleting(false);
    }
  };

  const handleViewStudents = async (cls) => {
    setSelectedClass(cls);
    setShowStudentsModal(true);
    setLoadingStudents(true);
    try {
      const response = await coursesAPI.getClassStudents(cls.id);
      setClassStudents(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error fetching students:', error);
    } finally {
      setLoadingStudents(false);
    }
  };

  const handleViewSessions = async (cls) => {
    setSelectedClass(cls);
    setShowSessionsModal(true);
    setLoadingSessions(true);
    try {
      const response = await coursesAPI.getClassSessions(cls.id);
      setClassSessions(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    } finally {
      setLoadingSessions(false);
    }
  };

  const handleGenerateSessions = async () => {
    if (!selectedClass) return;
    
    try {
      setGeneratingSessions(true);
      const response = await coursesAPI.generateClassSessions(selectedClass.id);
      setClassSessions(response.data.sessions || []);
      alert(response.data.message || 'جلسات با موفقیت ایجاد شدند');
    } catch (error) {
      console.error('Error generating sessions:', error);
      alert(error.response?.data?.detail || 'خطا در ایجاد جلسات');
    } finally {
      setGeneratingSessions(false);
    }
  };

  const handleJoinOnlineClass = async (cls) => {
    try {
      const response = await coursesAPI.getBBBJoinUrl(cls.id);
      if (response.data.join_url) {
        window.open(response.data.join_url, '_blank');
      } else {
        alert('لینک کلاس آنلاین در دسترس نیست');
      }
    } catch (error) {
      console.error('Error getting BBB URL:', error);
      alert(error.response?.data?.error || 'خطا در دریافت لینک کلاس');
    }
  };

  const getStatusVariant = (status) => {
    const variants = {
      scheduled: 'info',
      ongoing: 'success',
      completed: 'default',
      cancelled: 'error',
    };
    return variants[status] || 'default';
  };

  const getStatusName = (status) => {
    const names = {
      scheduled: 'برنامه‌ریزی شده',
      ongoing: 'در حال برگزاری',
      completed: 'تمام شده',
      cancelled: 'لغو شده',
    };
    return names[status] || status;
  };

  const formatScheduleDays = (days) => {
    if (!days || days.length === 0) return '-';
    return days.map(d => dayNames[d] || d).join('، ');
  };

  const filteredClasses = classes.filter(cls => {
    const matchesFilter = filter === 'all' || cls.status === filter;
    const matchesSearch = search === '' || 
      cls.name?.toLowerCase().includes(search.toLowerCase()) ||
      cls.code?.toLowerCase().includes(search.toLowerCase()) ||
      cls.course_name?.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="classes-page">
      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            کلاس جدید
          </Button>
        }>
          <CardTitle>مدیریت کلاس‌ها</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ 
              display: 'flex', 
              gap: '0.25rem',
              padding: '0.25rem',
              background: 'var(--gray-100)',
              borderRadius: 'var(--radius-lg)',
            }}>
              {[
                { key: 'all', label: 'همه' },
                { key: 'scheduled', label: 'برنامه‌ریزی شده' },
                { key: 'ongoing', label: 'در حال برگزاری' },
                { key: 'completed', label: 'تمام شده' },
                { key: 'cancelled', label: 'لغو شده' },
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    background: filter === tab.key ? 'white' : 'transparent',
                    boxShadow: filter === tab.key ? 'var(--shadow-sm)' : 'none',
                    color: filter === tab.key ? 'var(--primary-600)' : 'var(--gray-600)',
                    fontWeight: filter === tab.key ? 500 : 400,
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    transition: 'all var(--transition)'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div style={{ flex: 1, maxWidth: '300px' }}>
              <Input
                placeholder="جستجوی کلاس..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>کد</TableHead>
                  <TableHead>نام کلاس</TableHead>
                  <TableHead>دوره</TableHead>
                  <TableHead>شعبه</TableHead>
                  <TableHead>معلم</TableHead>
                  <TableHead>برنامه</TableHead>
                  <TableHead>ظرفیت</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredClasses.length === 0 ? (
                  <TableEmpty message="کلاسی یافت نشد" />
                ) : (
                  filteredClasses.map((cls) => (
                    <TableRow key={cls.id}>
                      <TableCell><code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>{cls.code}</code></TableCell>
                      <TableCell><strong>{cls.name}</strong></TableCell>
                      <TableCell>{cls.course_name || '-'}</TableCell>
                      <TableCell>{cls.branch_name || '-'}</TableCell>
                      <TableCell>{cls.teacher_name || '-'}</TableCell>
                      <TableCell>
                        <div style={{ fontSize: '0.8125rem' }}>
                          {formatScheduleDays(cls.schedule_days)}
                          {cls.start_time && (
                            <div style={{ color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                              {cls.start_time} - {cls.end_time}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{ 
                            width: '50px', 
                            height: '6px', 
                            background: 'var(--gray-200)',
                            borderRadius: '3px',
                            overflow: 'hidden'
                          }}>
                            <div style={{ 
                              height: '100%', 
                              width: `${((cls.current_enrollments || 0) / (cls.capacity || 1)) * 100}%`,
                              background: (cls.current_enrollments || 0) >= (cls.capacity || 1) ? 'var(--error)' : 'var(--success)'
                            }} />
                          </div>
                          <span style={{ fontSize: '0.8125rem' }}>
                            {toPersianDigits(cls.current_enrollments || 0)}/{toPersianDigits(cls.capacity)}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(cls.status)}>
                          {getStatusName(cls.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button 
                            onClick={() => handleViewStudents(cls)}
                            style={{
                              padding: '0.5rem',
                              background: '#d1fae5',
                              border: 'none',
                              borderRadius: 'var(--radius)',
                              color: 'var(--success)',
                              cursor: 'pointer'
                            }}
                            title="دانش‌آموزان"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                              <circle cx="9" cy="7" r="4" />
                              <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
                            </svg>
                          </button>
                          <button 
                            onClick={() => handleViewSessions(cls)}
                            style={{
                              padding: '0.5rem',
                              background: '#dbeafe',
                              border: 'none',
                              borderRadius: 'var(--radius)',
                              color: '#2563eb',
                              cursor: 'pointer'
                            }}
                            title="جلسات"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                              <line x1="16" y1="2" x2="16" y2="6" />
                              <line x1="8" y1="2" x2="8" y2="6" />
                              <line x1="3" y1="10" x2="21" y2="10" />
                            </svg>
                          </button>
                          {(cls.class_type === 'online' || cls.class_type === 'hybrid') && (
                            <button 
                              onClick={() => handleJoinOnlineClass(cls)}
                              style={{
                                padding: '0.5rem',
                                background: '#fef3c7',
                                border: 'none',
                                borderRadius: 'var(--radius)',
                                color: '#d97706',
                                cursor: 'pointer'
                              }}
                              title="ورود به کلاس آنلاین"
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polygon points="23 7 16 12 23 17 23 7" />
                                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                              </svg>
                            </button>
                          )}
                          <button 
                            onClick={() => handleOpenModal(cls)}
                            style={{
                              padding: '0.5rem',
                              background: 'var(--primary-50)',
                              border: 'none',
                              borderRadius: 'var(--radius)',
                              color: 'var(--primary-600)',
                              cursor: 'pointer'
                            }}
                            title="ویرایش"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </button>
                          <button 
                            onClick={() => handleDeleteClick(cls)}
                            style={{
                              padding: '0.5rem',
                              background: '#fee2e2',
                              border: 'none',
                              borderRadius: 'var(--radius)',
                              color: 'var(--error)',
                              cursor: 'pointer'
                            }}
                            title="حذف"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                            </svg>
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Modal */}
      <Modal
        isOpen={showModal}
        onClose={handleCloseModal}
        title={editingClass ? 'ویرایش کلاس' : 'کلاس جدید'}
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Basic Info */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>اطلاعات اصلی</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <Input
                label="نام کلاس *"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="مثال: ریاضی هشتم - گروه الف"
              />
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>دوره *</label>
                <select
                  value={formData.course}
                  onChange={(e) => setFormData({ ...formData, course: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid var(--gray-300)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    background: 'white'
                  }}
                >
                  <option value="">انتخاب دوره...</option>
                  {courses.map(course => (
                    <option key={course.id} value={course.id}>{course.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Location */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>مکان</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>شعبه *</label>
                <select
                  value={formData.branch}
                  onChange={(e) => handleBranchChange(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid var(--gray-300)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    background: 'white'
                  }}
                >
                  <option value="">انتخاب شعبه...</option>
                  {branches.map(branch => (
                    <option key={branch.id} value={branch.id}>{branch.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>کلاس درس</label>
                <select
                  value={formData.classroom}
                  onChange={(e) => setFormData({ ...formData, classroom: e.target.value })}
                  disabled={!formData.branch}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid var(--gray-300)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    background: 'white'
                  }}
                >
                  <option value="">انتخاب کلاس درس...</option>
                  {classrooms.map(room => (
                    <option key={room.id} value={room.id}>{room.name} (ظرفیت: {toPersianDigits(room.capacity)})</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Teacher & Term */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>معلم *</label>
              <select
                value={formData.teacher}
                onChange={(e) => setFormData({ ...formData, teacher: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="">انتخاب معلم...</option>
                {teachers.map(teacher => (
                  <option key={teacher.id} value={teacher.user?.id || teacher.id}>
                    {teacher.user?.first_name || teacher.first_name} {teacher.user?.last_name || teacher.last_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>ترم</label>
              <select
                value={formData.term}
                onChange={(e) => setFormData({ ...formData, term: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="">انتخاب ترم...</option>
                {terms.map(term => (
                  <option key={term.id} value={term.id}>{term.name}</option>
                ))}
              </select>
            </div>
            <Input
              label="ظرفیت"
              type="number"
              value={formData.capacity}
              onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
            />
          </div>

          {/* Schedule Days */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500, fontSize: '0.875rem' }}>روزهای برگزاری</label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {weekDays.map(day => (
                <button
                  key={day.key}
                  type="button"
                  onClick={() => handleDayToggle(day.key)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    border: formData.schedule_days.includes(day.key) 
                      ? '2px solid var(--primary-500)' 
                      : '2px solid var(--gray-200)',
                    background: formData.schedule_days.includes(day.key) 
                      ? 'var(--primary-50)' 
                      : 'white',
                    color: formData.schedule_days.includes(day.key) 
                      ? 'var(--primary-600)' 
                      : 'var(--gray-600)',
                    cursor: 'pointer',
                    fontWeight: 500,
                    fontSize: '0.875rem',
                    transition: 'all var(--transition)'
                  }}
                >
                  {day.label}
                </button>
              ))}
            </div>
          </div>

          {/* Time & Date */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1rem' }}>
            <Input
              label="ساعت شروع"
              type="time"
              value={formData.start_time}
              onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
            />
            <Input
              label="ساعت پایان"
              type="time"
              value={formData.end_time}
              onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
            />
            <JalaliDatePicker
              label="تاریخ شروع"
              value={formData.start_date}
              onChange={(date) => setFormData({ ...formData, start_date: date })}
              placeholder="انتخاب تاریخ"
            />
            <JalaliDatePicker
              label="تاریخ پایان"
              value={formData.end_date}
              onChange={(date) => setFormData({ ...formData, end_date: date })}
              placeholder="انتخاب تاریخ"
            />
          </div>

          {/* Status */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>وضعیت</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              style={{
                width: '100%',
                maxWidth: '200px',
                padding: '0.75rem',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                background: 'white'
              }}
            >
              <option value="scheduled">برنامه‌ریزی شده</option>
              <option value="ongoing">در حال برگزاری</option>
              <option value="completed">تمام شده</option>
              <option value="cancelled">لغو شده</option>
            </select>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={handleCloseModal}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingClass ? 'ذخیره تغییرات' : 'ایجاد کلاس'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="حذف کلاس"
        size="small"
      >
        <div style={{ textAlign: 'center', padding: '1rem 0' }}>
          <div style={{ 
            width: '64px', 
            height: '64px', 
            borderRadius: '50%', 
            background: '#fee2e2', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            margin: '0 auto 1rem'
          }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <h3 style={{ margin: '0 0 0.5rem' }}>آیا مطمئن هستید؟</h3>
          <p style={{ color: 'var(--gray-500)', margin: 0 }}>
            کلاس <strong>{deletingClass?.name}</strong> حذف خواهد شد.
            <br />
            این عملیات قابل بازگشت نیست.
          </p>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>انصراف</Button>
          <Button variant="danger" onClick={handleDelete} loading={deleting}>
            بله، حذف شود
          </Button>
        </ModalFooter>
      </Modal>

      {/* Students Modal */}
      <Modal
        isOpen={showStudentsModal}
        onClose={() => setShowStudentsModal(false)}
        title={`دانش‌آموزان کلاس ${selectedClass?.name || ''}`}
        size="medium"
      >
        {loadingStudents ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Spinner size="large" />
          </div>
        ) : classStudents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-500)' }}>
            دانش‌آموزی در این کلاس ثبت‌نام نکرده است
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>نام</TableHead>
                <TableHead>موبایل</TableHead>
                <TableHead>تاریخ ثبت‌نام</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {classStudents.map((student, index) => (
                <TableRow key={student.id}>
                  <TableCell>{toPersianDigits(index + 1)}</TableCell>
                  <TableCell><strong>{student.student_name || `${student.first_name} ${student.last_name}`}</strong></TableCell>
                  <TableCell>{student.mobile || '-'}</TableCell>
                  <TableCell>{formatApiDate(student.enrollment_date)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowStudentsModal(false)}>بستن</Button>
        </ModalFooter>
      </Modal>

      {/* Sessions Modal */}
      <Modal
        isOpen={showSessionsModal}
        onClose={() => setShowSessionsModal(false)}
        title={`جلسات کلاس ${selectedClass?.name || ''}`}
        size="large"
      >
        <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ color: 'var(--gray-600)', fontSize: '0.875rem' }}>
            {classSessions.length > 0 
              ? `${toPersianDigits(classSessions.length)} جلسه تعریف شده`
              : 'هنوز جلسه‌ای تعریف نشده'
            }
          </div>
          <Button 
            variant="secondary" 
            onClick={handleGenerateSessions}
            loading={generatingSessions}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 2v6h-6M3 12a9 9 0 0115-6.7L21 8M3 22v-6h6M21 12a9 9 0 01-15 6.7L3 16" />
            </svg>
            {classSessions.length > 0 ? 'بازسازی جلسات' : 'ایجاد جلسات'}
          </Button>
        </div>
        
        {loadingSessions ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Spinner size="large" />
          </div>
        ) : classSessions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-500)' }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 1rem', opacity: 0.5 }}>
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <p>جلسه‌ای تعریف نشده است</p>
            <p style={{ fontSize: '0.875rem' }}>با کلیک روی دکمه "ایجاد جلسات" می‌توانید جلسات را براساس برنامه کلاس ایجاد کنید</p>
          </div>
        ) : (
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>جلسه</TableHead>
                  <TableHead>تاریخ</TableHead>
                  <TableHead>ساعت</TableHead>
                  <TableHead>موضوع</TableHead>
                  <TableHead>وضعیت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {classSessions.map((session, index) => (
                  <TableRow key={session.id}>
                    <TableCell>
                      <Badge variant="info">جلسه {toPersianDigits(session.session_number || index + 1)}</Badge>
                    </TableCell>
                    <TableCell>{formatApiDate(session.date)}</TableCell>
                    <TableCell>
                      {session.start_time?.slice(0, 5)} - {session.end_time?.slice(0, 5)}
                    </TableCell>
                    <TableCell>{session.title || session.topic || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={
                        session.status === 'completed' ? 'success' :
                        session.status === 'cancelled' ? 'error' :
                        session.status === 'ongoing' ? 'warning' : 'default'
                      }>
                        {session.status === 'completed' ? 'برگزار شده' :
                         session.status === 'cancelled' ? 'لغو شده' :
                         session.status === 'ongoing' ? 'در حال برگزاری' : 'برنامه‌ریزی'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowSessionsModal(false)}>بستن</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminClasses;

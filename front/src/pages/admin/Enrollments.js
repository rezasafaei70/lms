import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, JalaliDatePicker, AutocompleteSelect } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { enrollmentsAPI, coursesAPI, usersAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const AdminEnrollments = () => {
  const [enrollments, setEnrollments] = useState([]);
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingEnrollment, setEditingEnrollment] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState({
    student: '',
    class_obj: '',
    enrollment_date: '',
    total_amount: '',
    discount_amount: '0',
    status: 'pending',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [selectedClass, setSelectedClass] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [enrollmentsRes, classesRes] = await Promise.all([
        enrollmentsAPI.list(),
        coursesAPI.getClasses(),
      ]);
      
      setEnrollments(enrollmentsRes.data.results || []);
      setClasses(classesRes.data.results || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Search students by name or national code
  const searchStudents = useCallback(async (query) => {
    console.log('Enrollments: searchStudents called with query:', query);
    try {
      const response = await usersAPI.searchStudents(query);
      console.log('Enrollments: API response:', response.data);
      
      // Handle both paginated and non-paginated responses
      const studentsData = response.data.results || response.data || [];
      console.log('Enrollments: Found', studentsData.length, 'students');
      
      const mappedResults = studentsData.map(student => {
        // Get user data - might be nested or flat
        const user = student.user || student;
        const firstName = user.first_name || '';
        const lastName = user.last_name || '';
        const nationalCode = user.national_code || '';
        const mobile = user.mobile || '';
        
        // Generate display name
        const fullName = `${firstName} ${lastName}`.trim() || 'بدون نام';
        const identifier = nationalCode || mobile || '';
        const displayName = identifier ? `${fullName} (${identifier})` : fullName;
        
        return {
          ...student,
          userId: user.id || student.id,
          displayName
        };
      });
      
      console.log('Enrollments: Mapped results:', mappedResults);
      return mappedResults;
    } catch (error) {
      console.error('Enrollments: Error searching students:', error);
      return [];
    }
  }, []);

  // Search classes
  const searchClasses = useCallback(async (query) => {
    try {
      const response = await coursesAPI.getClasses({ search: query });
      return (response.data.results || []).map(cls => ({
        ...cls,
        displayName: `${cls.name} - ${cls.course_name || ''} (${cls.current_enrollments || 0}/${cls.capacity || '∞'} نفر)`
      }));
    } catch (error) {
      console.error('Error searching classes:', error);
      return [];
    }
  }, []);

  const handleOpenModal = (enrollment = null) => {
    if (enrollment) {
      setEditingEnrollment(enrollment);
      setFormData({
        student: enrollment.student || '',
        class_obj: enrollment.class_obj || '',
        enrollment_date: enrollment.enrollment_date ? enrollment.enrollment_date.split('T')[0] : '',
        total_amount: enrollment.total_amount || enrollment.final_amount || '',
        discount_amount: enrollment.discount_amount || '0',
        status: enrollment.status || 'pending',
        notes: enrollment.notes || '',
      });
      // Set display names for editing
      setSelectedStudent({ displayName: enrollment.student_name || 'دانش‌آموز' });
      setSelectedClass({ displayName: enrollment.class_name || 'کلاس' });
    } else {
      setEditingEnrollment(null);
      setFormData({
        student: '',
        class_obj: '',
        enrollment_date: new Date().toISOString().split('T')[0],
        total_amount: '',
        discount_amount: '0',
        status: 'pending',
        notes: '',
      });
      setSelectedStudent(null);
      setSelectedClass(null);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingEnrollment(null);
    setSelectedStudent(null);
    setSelectedClass(null);
  };

  const handleStudentSelect = (studentId) => {
    setFormData(prev => ({ ...prev, student: studentId }));
  };

  const handleClassSelect = (classId) => {
    setFormData(prev => ({ ...prev, class_obj: classId }));
    // Auto-fill price from class
    const selectedCls = classes.find(c => c.id === classId);
    if (selectedCls && selectedCls.price && !formData.total_amount) {
      setFormData(prev => ({ ...prev, total_amount: selectedCls.price.toString() }));
    }
  };

  const handleSave = async () => {
    if (!editingEnrollment && (!formData.student || !formData.class_obj)) {
      alert('لطفاً دانش‌آموز و کلاس را انتخاب کنید');
      return;
    }

    try {
      setSaving(true);
      const data = {
        status: formData.status,
        notes: formData.notes,
      };
      
      // For new enrollments, include student and class
      if (!editingEnrollment) {
        data.student = formData.student;
        data.class_obj = formData.class_obj;
        data.total_amount = parseInt(formData.total_amount) || 0;
        data.discount_amount = parseInt(formData.discount_amount) || 0;
      } else {
        // For updates, only update editable fields
        if (formData.total_amount) data.total_amount = parseInt(formData.total_amount);
        if (formData.discount_amount !== undefined) data.discount_amount = parseInt(formData.discount_amount) || 0;
      }

      if (editingEnrollment) {
        await enrollmentsAPI.update(editingEnrollment.id, data);
      } else {
        await enrollmentsAPI.create(data);
      }
      handleCloseModal();
      fetchData();
    } catch (error) {
      console.error('Error saving enrollment:', error);
      const errorMsg = error.response?.data?.detail || 
                       JSON.stringify(error.response?.data?.details) || 
                       JSON.stringify(error.response?.data) ||
                       'خطا در ذخیره ثبت‌نام';
      alert(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (enrollmentId, newStatus) => {
    try {
      await enrollmentsAPI.update(enrollmentId, { status: newStatus });
      fetchData();
    } catch (error) {
      console.error('Error updating status:', error);
      alert('خطا در تغییر وضعیت');
    }
  };

  const getStatusVariant = (status) => {
    const variants = {
      pending: 'warning',
      approved: 'info',
      active: 'success',
      completed: 'info',
      cancelled: 'error',
      suspended: 'default',
    };
    return variants[status] || 'default';
  };

  const getStatusName = (status) => {
    const names = {
      pending: 'در انتظار تأیید',
      approved: 'تایید شده',
      active: 'فعال',
      completed: 'تکمیل شده',
      cancelled: 'لغو شده',
      suspended: 'تعلیق',
    };
    return names[status] || status;
  };

  const filteredEnrollments = enrollments.filter(enrollment => {
    const matchesFilter = filter === 'all' || enrollment.status === filter;
    const matchesSearch = search === '' || 
      enrollment.student_name?.toLowerCase().includes(search.toLowerCase()) ||
      enrollment.class_name?.toLowerCase().includes(search.toLowerCase()) ||
      enrollment.enrollment_number?.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Stats - calculate unique values
  const uniqueStudents = new Set(enrollments.filter(e => e.status === 'active').map(e => e.student));
  const stats = {
    total: enrollments.length,
    pending: enrollments.filter(e => e.status === 'pending').length,
    active: enrollments.filter(e => e.status === 'active').length,
    totalRevenue: enrollments.filter(e => e.status === 'active' || e.status === 'completed')
      .reduce((sum, e) => sum + (parseFloat(e.final_amount) || 0), 0),
  };

  return (
    <div className="enrollments-page">
      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <Card hover>
          <CardContent style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                borderRadius: 'var(--radius-lg)', 
                background: 'var(--primary-100)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: 'var(--primary-600)'
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.total)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کل ثبت‌نام‌ها</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                borderRadius: 'var(--radius-lg)', 
                background: '#fef3c7', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: '#d97706'
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.pending)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>در انتظار تأیید</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                borderRadius: 'var(--radius-lg)', 
                background: '#d1fae5', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: '#059669'
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.active)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>ثبت‌نام فعال</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                borderRadius: 'var(--radius-lg)', 
                background: '#dbeafe', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: '#2563eb'
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(Math.round(stats.totalRevenue).toLocaleString())}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>درآمد (تومان)</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            ثبت‌نام جدید
          </Button>
        }>
          <CardTitle>مدیریت ثبت‌نام‌ها</CardTitle>
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
                { key: 'pending', label: 'در انتظار' },
                { key: 'active', label: 'فعال' },
                { key: 'completed', label: 'تکمیل شده' },
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
                placeholder="جستجوی دانش‌آموز، کلاس یا شماره ثبت‌نام..."
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
                  <TableHead>شماره</TableHead>
                  <TableHead>دانش‌آموز</TableHead>
                  <TableHead>کلاس</TableHead>
                  <TableHead>تاریخ ثبت‌نام</TableHead>
                  <TableHead>مبلغ</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEnrollments.length === 0 ? (
                  <TableEmpty message="ثبت‌نامی یافت نشد" />
                ) : (
                  filteredEnrollments.map((enrollment) => (
                    <TableRow key={enrollment.id}>
                      <TableCell>
                        <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                          {enrollment.enrollment_number}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <div style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontWeight: 600,
                            fontSize: '0.875rem'
                          }}>
                            {enrollment.student_name?.charAt(0) || '?'}
                          </div>
                          <strong>{enrollment.student_name}</strong>
                        </div>
                      </TableCell>
                      <TableCell>{enrollment.class_name}</TableCell>
                      <TableCell>{formatApiDate(enrollment.enrollment_date)}</TableCell>
                      <TableCell>
                        {enrollment.final_amount ? `${toPersianDigits(Math.round(parseFloat(enrollment.final_amount)).toLocaleString())} تومان` : '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(enrollment.status)}>
                          {getStatusName(enrollment.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          {enrollment.status === 'pending' && (
                            <button 
                              onClick={() => handleStatusChange(enrollment.id, 'active')}
                              style={{
                                padding: '0.5rem',
                                background: '#d1fae5',
                                border: 'none',
                                borderRadius: 'var(--radius)',
                                color: 'var(--success)',
                                cursor: 'pointer'
                              }}
                              title="تأیید"
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                            </button>
                          )}
                          <button 
                            onClick={() => handleOpenModal(enrollment)}
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
                          {enrollment.status !== 'cancelled' && (
                            <button 
                              onClick={() => handleStatusChange(enrollment.id, 'cancelled')}
                              style={{
                                padding: '0.5rem',
                                background: '#fee2e2',
                                border: 'none',
                                borderRadius: 'var(--radius)',
                                color: 'var(--error)',
                                cursor: 'pointer'
                              }}
                              title="لغو"
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <line x1="15" y1="9" x2="9" y2="15" />
                                <line x1="9" y1="9" x2="15" y2="15" />
                              </svg>
                            </button>
                          )}
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
        title={editingEnrollment ? 'ویرایش ثبت‌نام' : 'ثبت‌نام جدید'}
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {editingEnrollment ? (
              <>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>دانش‌آموز</label>
                  <div style={{ 
                    padding: '0.75rem', 
                    background: 'var(--gray-100)', 
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    color: 'var(--gray-700)'
                  }}>
                    {selectedStudent?.displayName || editingEnrollment?.student_name || '-'}
                  </div>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>کلاس</label>
                  <div style={{ 
                    padding: '0.75rem', 
                    background: 'var(--gray-100)', 
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    color: 'var(--gray-700)'
                  }}>
                    {selectedClass?.displayName || editingEnrollment?.class_name || '-'}
                  </div>
                </div>
              </>
            ) : (
              <>
                <AutocompleteSelect
                  label="دانش‌آموز *"
                  value={formData.student}
                  onChange={handleStudentSelect}
                  onSearch={searchStudents}
                  displayField="displayName"
                  valueField="userId"
                  placeholder="نام، کد ملی یا موبایل..."
                  minSearchLength={1}
                  required
                  hint="حداقل ۱ کاراکتر برای جستجو"
                />
                <AutocompleteSelect
                  label="کلاس *"
                  value={formData.class_obj}
                  onChange={handleClassSelect}
                  onSearch={searchClasses}
                  options={classes.map(c => ({ ...c, displayName: `${c.name} - ${c.course_name || ''} (${c.current_enrollments || 0}/${c.capacity || '∞'} نفر)` }))}
                  displayField="displayName"
                  valueField="id"
                  placeholder="جستجوی کلاس..."
                  minSearchLength={1}
                  required
                />
              </>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="مبلغ کل (تومان) *"
              type="number"
              value={formData.total_amount}
              onChange={(e) => setFormData({ ...formData, total_amount: e.target.value })}
              placeholder="قیمت کلاس"
            />
            <Input
              label="مبلغ تخفیف (تومان)"
              type="number"
              value={formData.discount_amount}
              onChange={(e) => setFormData({ ...formData, discount_amount: e.target.value })}
              placeholder="0"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <JalaliDatePicker
              label="تاریخ ثبت‌نام"
              value={formData.enrollment_date}
              onChange={(date) => setFormData({ ...formData, enrollment_date: date })}
              placeholder="انتخاب تاریخ"
              disabled={!!editingEnrollment}
            />
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>وضعیت</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="pending">در انتظار تأیید</option>
                <option value="approved">تایید شده</option>
                <option value="active">فعال</option>
                <option value="completed">تکمیل شده</option>
                <option value="cancelled">لغو شده</option>
                <option value="suspended">تعلیق</option>
              </select>
            </div>
          </div>

          {/* Show calculated final amount */}
          {formData.total_amount && (
            <div style={{ 
              padding: '1rem', 
              background: 'var(--primary-50)', 
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span style={{ fontWeight: 500, color: 'var(--gray-700)' }}>مبلغ نهایی:</span>
              <span style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--primary-600)' }}>
                {toPersianDigits(Math.max(0, 
                  (parseInt(formData.total_amount) || 0) - 
                  (parseInt(formData.discount_amount) || 0)
                ).toLocaleString())} تومان
              </span>
            </div>
          )}

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>یادداشت</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="یادداشت..."
              rows={2}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                resize: 'vertical'
              }}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={handleCloseModal}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingEnrollment ? 'ذخیره تغییرات' : 'ثبت‌نام'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminEnrollments;

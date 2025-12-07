import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, AutocompleteSelect } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { enrollmentsAPI, usersAPI, branchesAPI, coursesAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const AdminAnnualRegistrations = () => {
  const [registrations, setRegistrations] = useState([]);
  const [branches, setBranches] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [viewingRegistration, setViewingRegistration] = useState(null);
  const [filter, setFilter] = useState('all');
  const [formData, setFormData] = useState({
    student: '',
    branch: '',
    academic_year: '1403-1404',
    selected_subjects: [],
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [registrationsRes, branchesRes, subjectsRes] = await Promise.all([
        enrollmentsAPI.getAnnualRegistrations(),
        branchesAPI.list(),
        coursesAPI.getSubjects(),
      ]);
      setRegistrations(registrationsRes.data.results || []);
      setBranches(branchesRes.data.results || []);
      setSubjects(subjectsRes.data.results || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  // Search students
  const searchStudents = useCallback(async (query) => {
    try {
      const response = await usersAPI.searchStudents(query);
      // Handle both paginated and non-paginated responses
      const studentsData = response.data.results || response.data || [];
      
      return studentsData.map(student => {
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
    } catch (error) {
      console.error('Error searching students:', error);
      return [];
    }
  }, []);

  const handleOpenModal = () => {
    setFormData({
      student: '',
      branch: '',
      academic_year: '1403-1404',
      selected_subjects: [],
    });
    setShowModal(true);
  };

  const handleSubjectToggle = (subjectId) => {
    setFormData(prev => {
      const subjects = prev.selected_subjects.includes(subjectId)
        ? prev.selected_subjects.filter(id => id !== subjectId)
        : [...prev.selected_subjects, subjectId];
      return { ...prev, selected_subjects: subjects };
    });
  };

  const handleSave = async () => {
    if (!formData.student || !formData.branch || formData.selected_subjects.length === 0) {
      alert('لطفاً دانش‌آموز، شعبه و حداقل یک درس را انتخاب کنید');
      return;
    }

    try {
      setSaving(true);
      await enrollmentsAPI.createAnnualRegistration({
        student: formData.student,
        branch: formData.branch,
        academic_year: formData.academic_year,
        selected_subject_ids: formData.selected_subjects,
      });
      setShowModal(false);
      fetchData();
      alert('ثبت‌نام سالانه با موفقیت انجام شد');
    } catch (error) {
      console.error('Error:', error);
      alert(error.response?.data?.detail || error.response?.data?.message || 'خطا در ثبت‌نام');
    } finally {
      setSaving(false);
    }
  };

  const handleViewDetails = (registration) => {
    setViewingRegistration(registration);
    setShowViewModal(true);
  };

  const getStatusBadge = (status) => {
    const variants = {
      pending: { variant: 'warning', text: 'در انتظار پرداخت' },
      active: { variant: 'success', text: 'فعال' },
      expired: { variant: 'error', text: 'منقضی شده' },
      cancelled: { variant: 'default', text: 'لغو شده' },
    };
    const { variant, text } = variants[status] || { variant: 'default', text: status };
    return <Badge variant={variant}>{text}</Badge>;
  };

  // Calculate total price for selected subjects
  const calculateTotal = () => {
    return formData.selected_subjects.reduce((sum, subjectId) => {
      const subject = subjects.find(s => s.id === subjectId);
      return sum + (subject?.base_price || 0);
    }, 0);
  };

  const filteredRegistrations = registrations.filter(r => 
    filter === 'all' || r.status === filter
  );

  // Stats
  const stats = {
    total: registrations.length,
    active: registrations.filter(r => r.status === 'active').length,
    pending: registrations.filter(r => r.status === 'pending').length,
    totalRevenue: registrations.filter(r => r.status === 'active').reduce((sum, r) => sum + (parseFloat(r.total_amount) || 0), 0),
  };

  return (
    <div className="annual-registrations-page">
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <Card hover>
          <CardContent style={{ padding: '1.25rem', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--primary-600)' }}>{toPersianDigits(stats.total)}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کل ثبت‌نام‌ها</div>
          </CardContent>
        </Card>
        <Card hover>
          <CardContent style={{ padding: '1.25rem', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(stats.active)}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>فعال</div>
          </CardContent>
        </Card>
        <Card hover>
          <CardContent style={{ padding: '1.25rem', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--warning)' }}>{toPersianDigits(stats.pending)}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>در انتظار</div>
          </CardContent>
        </Card>
        <Card hover>
          <CardContent style={{ padding: '1.25rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--info)' }}>{toPersianDigits(Math.round(stats.totalRevenue).toLocaleString())}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>درآمد (تومان)</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader action={
          <Button onClick={handleOpenModal}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            ثبت‌نام جدید
          </Button>
        }>
          <CardTitle>ثبت‌نام سالانه</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div style={{ 
            display: 'flex', 
            gap: '0.25rem',
            padding: '0.25rem',
            background: 'var(--gray-100)',
            borderRadius: 'var(--radius-lg)',
            width: 'fit-content',
            marginBottom: '1.5rem'
          }}>
            {[
              { key: 'all', label: 'همه' },
              { key: 'active', label: 'فعال' },
              { key: 'pending', label: 'در انتظار' },
              { key: 'expired', label: 'منقضی' },
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
                }}
              >
                {tab.label}
              </button>
            ))}
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
                  <TableHead>شعبه</TableHead>
                  <TableHead>سال تحصیلی</TableHead>
                  <TableHead>تعداد دروس</TableHead>
                  <TableHead>مبلغ</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRegistrations.length === 0 ? (
                  <TableEmpty message="ثبت‌نامی یافت نشد" />
                ) : (
                  filteredRegistrations.map((reg) => (
                    <TableRow key={reg.id}>
                      <TableCell>
                        <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                          {reg.registration_number}
                        </code>
                      </TableCell>
                      <TableCell>
                        <strong>{reg.student_details?.first_name} {reg.student_details?.last_name}</strong>
                      </TableCell>
                      <TableCell>{reg.branch_name}</TableCell>
                      <TableCell>{reg.academic_year}</TableCell>
                      <TableCell>{toPersianDigits(reg.selected_subjects_details?.length || 0)} درس</TableCell>
                      <TableCell>{toPersianDigits(Math.round(parseFloat(reg.total_amount) || 0).toLocaleString())} تومان</TableCell>
                      <TableCell>{getStatusBadge(reg.status)}</TableCell>
                      <TableCell>
                        <button 
                          onClick={() => handleViewDetails(reg)}
                          style={{
                            padding: '0.5rem',
                            background: 'var(--primary-50)',
                            border: 'none',
                            borderRadius: 'var(--radius)',
                            color: 'var(--primary-600)',
                            cursor: 'pointer'
                          }}
                          title="جزئیات"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        </button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="ثبت‌نام سالانه جدید"
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <AutocompleteSelect
              label="دانش‌آموز *"
              value={formData.student}
              onChange={(value) => setFormData({ ...formData, student: value })}
              onSearch={searchStudents}
              displayField="displayName"
              valueField="userId"
              placeholder="نام، کد ملی یا موبایل..."
              minSearchLength={1}
              required
              hint="حداقل ۱ کاراکتر برای جستجو"
            />
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>شعبه *</label>
              <select
                value={formData.branch}
                onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
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
          </div>

          <Input
            label="سال تحصیلی"
            value={formData.academic_year}
            onChange={(e) => setFormData({ ...formData, academic_year: e.target.value })}
            placeholder="مثال: 1403-1404"
          />

          <div>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500, fontSize: '0.875rem' }}>انتخاب دروس *</label>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', 
              gap: '0.75rem',
              maxHeight: '250px',
              overflowY: 'auto',
              padding: '0.5rem',
              background: 'var(--gray-50)',
              borderRadius: 'var(--radius-md)'
            }}>
              {subjects.map(subject => (
                <label
                  key={subject.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.75rem',
                    background: formData.selected_subjects.includes(subject.id) ? 'var(--primary-50)' : 'white',
                    border: formData.selected_subjects.includes(subject.id) ? '2px solid var(--primary-500)' : '2px solid var(--gray-200)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={formData.selected_subjects.includes(subject.id)}
                    onChange={() => handleSubjectToggle(subject.id)}
                    style={{ width: '18px', height: '18px' }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>{subject.title}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
                      {toPersianDigits((subject.base_price || 0).toLocaleString())} تومان
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Total */}
          <div style={{ 
            padding: '1rem', 
            background: 'var(--primary-50)', 
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ fontWeight: 500 }}>مجموع شهریه ({toPersianDigits(formData.selected_subjects.length)} درس):</span>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary-600)' }}>
              {toPersianDigits(calculateTotal().toLocaleString())} تومان
            </span>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowModal(false)}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>ثبت‌نام</Button>
        </ModalFooter>
      </Modal>

      {/* View Details Modal */}
      <Modal
        isOpen={showViewModal}
        onClose={() => setShowViewModal(false)}
        title="جزئیات ثبت‌نام"
        size="medium"
      >
        {viewingRegistration && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>دانش‌آموز</label>
                <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>
                  {viewingRegistration.student_details?.first_name} {viewingRegistration.student_details?.last_name}
                </p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>شعبه</label>
                <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>{viewingRegistration.branch_name}</p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>سال تحصیلی</label>
                <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>{viewingRegistration.academic_year}</p>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>تاریخ ثبت‌نام</label>
                <p style={{ margin: '0.25rem 0 0', fontWeight: 500 }}>{formatApiDate(viewingRegistration.registration_date)}</p>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginBottom: '0.5rem', display: 'block' }}>دروس انتخابی</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {viewingRegistration.selected_subjects_details?.map(subject => (
                  <Badge key={subject.id} variant="info">{subject.subject_details?.title || subject.title}</Badge>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>مبلغ کل</div>
                <div style={{ fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(Math.round(parseFloat(viewingRegistration.total_amount) || 0).toLocaleString())}</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>پرداخت شده</div>
                <div style={{ fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(Math.round(parseFloat(viewingRegistration.paid_amount) || 0).toLocaleString())}</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>مانده</div>
                <div style={{ fontWeight: 700, color: 'var(--error)' }}>{toPersianDigits(Math.round(parseFloat(viewingRegistration.remaining_amount) || 0).toLocaleString())}</div>
              </div>
            </div>
          </div>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowViewModal(false)}>بستن</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminAnnualRegistrations;


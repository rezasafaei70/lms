import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { coursesAPI } from '../../services/api';
import { toPersianDigits } from '../../utils/jalaliDate';

const AdminSubjects = () => {
  const [subjects, setSubjects] = useState([]);
  const [gradeLevels, setGradeLevels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editingSubject, setEditingSubject] = useState(null);
  const [deletingSubject, setDeletingSubject] = useState(null);
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    code: '',
    description: '',
    grade_level: '',
    base_price: '',
    standard_sessions: 24,
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subjectsRes] = await Promise.all([
        coursesAPI.getSubjects(),
      ]);
      setSubjects(subjectsRes.data.results || subjectsRes.data || []);
      
      // Grade levels would come from accounts API - mock for now
      setGradeLevels([
        { id: 1, name: 'هفتم' },
        { id: 2, name: 'هشتم' },
        { id: 3, name: 'نهم' },
        { id: 4, name: 'دهم' },
        { id: 5, name: 'یازدهم' },
        { id: 6, name: 'دوازدهم' },
      ]);
    } catch (error) {
      console.error('Error fetching subjects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (subject = null) => {
    if (subject) {
      setEditingSubject(subject);
      setFormData({
        title: subject.title || '',
        code: subject.code || '',
        description: subject.description || '',
        grade_level: subject.grade_level || '',
        base_price: subject.base_price || '',
        standard_sessions: subject.standard_sessions || 24,
        is_active: subject.is_active !== false,
      });
    } else {
      setEditingSubject(null);
      setFormData({
        title: '',
        code: '',
        description: '',
        grade_level: '',
        base_price: '',
        standard_sessions: 24,
        is_active: true,
      });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingSubject(null);
  };

  const handleSave = async () => {
    if (!formData.title) {
      alert('لطفاً عنوان درس را وارد کنید');
      return;
    }

    try {
      setSaving(true);
      const data = { ...formData };
      
      // Convert numbers
      if (data.base_price) data.base_price = parseInt(data.base_price);
      if (data.standard_sessions) data.standard_sessions = parseInt(data.standard_sessions);
      
      // Remove empty values
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
          delete data[key];
        }
      });

      if (editingSubject) {
        await coursesAPI.updateSubject(editingSubject.id, data);
      } else {
        await coursesAPI.createSubject(data);
      }
      handleCloseModal();
      fetchData();
    } catch (error) {
      console.error('Error saving subject:', error);
      alert(error.response?.data?.detail || error.response?.data?.message || 'خطا در ذخیره درس');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (subject) => {
    setDeletingSubject(subject);
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!deletingSubject) return;
    
    try {
      setDeleting(true);
      await coursesAPI.deleteSubject(deletingSubject.id);
      setShowDeleteModal(false);
      setDeletingSubject(null);
      fetchData();
    } catch (error) {
      console.error('Error deleting subject:', error);
      alert(error.response?.data?.detail || 'خطا در حذف درس');
    } finally {
      setDeleting(false);
    }
  };

  const filteredSubjects = subjects.filter(subject => {
    const matchesSearch = search === '' || 
      subject.title?.toLowerCase().includes(search.toLowerCase()) ||
      subject.code?.toLowerCase().includes(search.toLowerCase());
    return matchesSearch;
  });

  return (
    <div className="subjects-page">
      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            درس جدید
          </Button>
        }>
          <CardTitle>مدیریت درس‌ها</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Search */}
          <div style={{ marginBottom: '1.5rem', maxWidth: '300px' }}>
            <Input
              placeholder="جستجوی درس..."
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
                  <TableHead>کد</TableHead>
                  <TableHead>عنوان درس</TableHead>
                  <TableHead>پایه تحصیلی</TableHead>
                  <TableHead>قیمت پایه</TableHead>
                  <TableHead>تعداد جلسات</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSubjects.length === 0 ? (
                  <TableEmpty message="درسی یافت نشد" />
                ) : (
                  filteredSubjects.map((subject) => (
                    <TableRow key={subject.id}>
                      <TableCell>
                        <code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>
                          {subject.code || '-'}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div>
                          <strong>{subject.title}</strong>
                          {subject.description && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                              {subject.description.substring(0, 50)}...
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{subject.grade_level_name || '-'}</TableCell>
                      <TableCell>
                        {subject.base_price 
                          ? `${toPersianDigits(parseInt(subject.base_price).toLocaleString())} تومان` 
                          : '-'}
                      </TableCell>
                      <TableCell>{toPersianDigits(subject.standard_sessions || 0)} جلسه</TableCell>
                      <TableCell>
                        <Badge variant={subject.is_active ? 'success' : 'error'}>
                          {subject.is_active ? 'فعال' : 'غیرفعال'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button 
                            onClick={() => handleOpenModal(subject)}
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
                            onClick={() => handleDeleteClick(subject)}
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
        title={editingSubject ? 'ویرایش درس' : 'درس جدید'}
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="عنوان درس *"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="مثال: ریاضی ۱"
          />
          <Input
            label="کد درس"
            value={formData.code}
            onChange={(e) => setFormData({ ...formData, code: e.target.value })}
            placeholder="مثال: MATH101"
            hint="خالی بگذارید تا خودکار تولید شود"
          />
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>
              پایه تحصیلی
            </label>
            <select
              value={formData.grade_level}
              onChange={(e) => setFormData({ ...formData, grade_level: e.target.value })}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                background: 'white'
              }}
            >
              <option value="">انتخاب پایه...</option>
              {gradeLevels.map((level) => (
                <option key={level.id} value={level.id}>{level.name}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="قیمت پایه (تومان)"
              type="number"
              value={formData.base_price}
              onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
              placeholder="مثال: 500000"
            />
            <Input
              label="تعداد جلسات استاندارد"
              type="number"
              value={formData.standard_sessions}
              onChange={(e) => setFormData({ ...formData, standard_sessions: e.target.value })}
              placeholder="مثال: 24"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>
              توضیحات
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="توضیحات درباره درس..."
              rows={3}
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
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
            />
            <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>فعال</span>
          </label>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={handleCloseModal}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingSubject ? 'ذخیره تغییرات' : 'ایجاد درس'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="حذف درس"
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
            درس <strong>{deletingSubject?.title}</strong> حذف خواهد شد.
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
    </div>
  );
};

export default AdminSubjects;


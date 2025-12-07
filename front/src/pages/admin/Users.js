import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, FileUpload, JalaliDatePicker } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { usersAPI, branchesAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';
import './Users.css';

const getRoleName = (role) => {
  const roles = {
    super_admin: 'مدیر کل',
    branch_manager: 'مدیر شعبه',
    teacher: 'معلم',
    student: 'دانش‌آموز',
    accountant: 'حسابدار',
    receptionist: 'پذیرش',
    support: 'پشتیبان',
  };
  return roles[role] || role;
};

const getRoleVariant = (role) => {
  const variants = {
    super_admin: 'primary',
    branch_manager: 'info',
    teacher: 'success',
    student: 'default',
    accountant: 'warning',
  };
  return variants[role] || 'default';
};

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [deletingUser, setDeletingUser] = useState(null);
  const [profileImageKey, setProfileImageKey] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    mobile: '',
    national_code: '',
    email: '',
    role: 'student',
    gender: 'male',
    birth_date: '',
    address: '',
    branch: '',
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchData();
  }, [filter]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filter !== 'all') {
        params.role = filter;
      }
      const [usersRes, branchesRes] = await Promise.all([
        usersAPI.list(params),
        branchesAPI.list(),
      ]);
      setUsers(usersRes.data.results || []);
      setBranches(branchesRes.data.results || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (user = null) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        mobile: user.mobile || '',
        national_code: user.national_code || '',
        email: user.email || '',
        role: user.role || 'student',
        gender: user.gender || 'male',
        birth_date: user.birth_date || '',
        address: user.address || '',
        branch: user.branch || '',
        is_active: user.is_active !== false,
      });
      setProfileImageKey(null);
    } else {
      setEditingUser(null);
      setFormData({
        first_name: '',
        last_name: '',
        mobile: '',
        national_code: '',
        email: '',
        role: 'student',
        gender: 'male',
        birth_date: '',
        address: '',
        branch: '',
        is_active: true,
      });
      setProfileImageKey(null);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingUser(null);
    setProfileImageKey(null);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const data = { ...formData };
      
      if (profileImageKey) {
        data.profile_image_s3_key = profileImageKey;
      }
      
      // Remove empty values
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
          delete data[key];
        }
      });

      if (editingUser) {
        await usersAPI.update(editingUser.id, data);
      } else {
        await usersAPI.create(data);
      }
      handleCloseModal();
      fetchData();
    } catch (error) {
      console.error('Error saving user:', error);
      alert(error.response?.data?.detail || 'خطا در ذخیره کاربر');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (user) => {
    setDeletingUser(user);
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!deletingUser) return;
    
    try {
      setDeleting(true);
      await usersAPI.delete(deletingUser.id);
      setShowDeleteModal(false);
      setDeletingUser(null);
      fetchData();
    } catch (error) {
      console.error('Error deleting user:', error);
      alert(error.response?.data?.detail || 'خطا در حذف کاربر');
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleStatus = async (user) => {
    try {
      await usersAPI.update(user.id, { is_active: !user.is_active });
      fetchData();
    } catch (error) {
      console.error('Error toggling user status:', error);
    }
  };

  const filteredUsers = users.filter(user => 
    search === '' || 
    user.first_name?.includes(search) ||
    user.last_name?.includes(search) ||
    user.mobile?.includes(search) ||
    user.national_code?.includes(search)
  );

  // Stats
  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active).length,
    students: users.filter(u => u.role === 'student').length,
    teachers: users.filter(u => u.role === 'teacher').length,
  };

  return (
    <div className="users-page">
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
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کل کاربران</div>
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
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کاربر فعال</div>
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
                  <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.students)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>دانش‌آموز</div>
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
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.teachers)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>معلم</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
              <circle cx="8.5" cy="7" r="4" />
              <line x1="20" y1="8" x2="20" y2="14" />
              <line x1="23" y1="11" x2="17" y2="11" />
            </svg>
            کاربر جدید
          </Button>
        }>
          <CardTitle>مدیریت کاربران</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="users-filters">
            <div className="filter-tabs">
              {[
                { key: 'all', label: 'همه' },
                { key: 'student', label: 'دانش‌آموزان' },
                { key: 'teacher', label: 'معلمان' },
                { key: 'branch_manager', label: 'مدیران شعبه' },
                { key: 'accountant', label: 'حسابداران' },
              ].map(tab => (
                <button 
                  key={tab.key}
                  className={`filter-tab ${filter === tab.key ? 'active' : ''}`}
                  onClick={() => setFilter(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <Input
              placeholder="جستجوی کاربر..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>

          {loading ? (
            <div className="loading-container">
              <Spinner size="large" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>کاربر</TableHead>
                  <TableHead>موبایل</TableHead>
                  <TableHead>کد ملی</TableHead>
                  <TableHead>نقش</TableHead>
                  <TableHead>تاریخ عضویت</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableEmpty message="کاربری یافت نشد" />
                ) : (
                  filteredUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div className="user-cell">
                          <div className="user-avatar" style={{
                            backgroundImage: user.profile_image_url ? `url(${user.profile_image_url})` : 'none',
                            backgroundSize: 'cover',
                            backgroundPosition: 'center'
                          }}>
                            {!user.profile_image_url && (
                              <>{user.first_name?.[0]}{user.last_name?.[0]}</>
                            )}
                          </div>
                          <div>
                            <strong>{user.first_name} {user.last_name}</strong>
                            {user.email && <span className="user-email">{user.email}</span>}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell dir="ltr" style={{ textAlign: 'right' }}>{user.mobile}</TableCell>
                      <TableCell>{user.national_code || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={getRoleVariant(user.role)}>
                          {getRoleName(user.role)}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatApiDate(user.date_joined)}</TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? 'success' : 'error'}>
                          {user.is_active ? 'فعال' : 'غیرفعال'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="table-actions">
                          <button 
                            className="action-btn action-btn-edit"
                            onClick={() => handleOpenModal(user)}
                            title="ویرایش"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </button>
                          <button 
                            className={`action-btn ${user.is_active ? 'action-btn-warning' : 'action-btn-success'}`}
                            onClick={() => handleToggleStatus(user)}
                            title={user.is_active ? 'غیرفعال کردن' : 'فعال کردن'}
                          >
                            {user.is_active ? (
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                                <line x1="1" y1="1" x2="23" y2="23" />
                              </svg>
                            ) : (
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                <circle cx="12" cy="12" r="3" />
                              </svg>
                            )}
                          </button>
                          <button 
                            className="action-btn action-btn-delete"
                            onClick={() => handleDeleteClick(user)}
                            title="حذف"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
        title={editingUser ? 'ویرایش کاربر' : 'کاربر جدید'}
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Profile Image */}
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <FileUpload
              accept="image/*"
              maxSize={2 * 1024 * 1024}
              folder="profiles"
              targetModel="User"
              targetField="profile_image"
              preview={true}
              previewUrl={editingUser?.profile_image_url}
              label="آپلود تصویر پروفایل"
              hint="حداکثر ۲ مگابایت"
              onUploadComplete={(result) => setProfileImageKey(result.key)}
              onUploadError={(err) => alert(err)}
              className="profile-upload"
            />
          </div>

          {/* Basic Info */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>اطلاعات شخصی</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <Input
                label="نام *"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
              />
              <Input
                label="نام خانوادگی *"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>جنسیت</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="male">مرد</option>
                <option value="female">زن</option>
              </select>
            </div>
            <JalaliDatePicker
              label="تاریخ تولد"
              value={formData.birth_date}
              onChange={(date) => setFormData({ ...formData, birth_date: date })}
              placeholder="انتخاب تاریخ"
            />
            <Input
              label="کد ملی"
              value={formData.national_code}
              onChange={(e) => setFormData({ ...formData, national_code: e.target.value })}
              placeholder="۰۰۱۲۳۴۵۶۷۸"
            />
          </div>

          {/* Contact Info */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>اطلاعات تماس</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <Input
                label="موبایل *"
                value={formData.mobile}
                onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                placeholder="09123456789"
              />
              <Input
                label="ایمیل"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="email@example.com"
              />
            </div>
            <div style={{ marginTop: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>آدرس</label>
              <textarea
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="آدرس محل سکونت..."
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

          {/* Role & Branch */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>نقش *</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="student">دانش‌آموز</option>
                <option value="teacher">معلم</option>
                <option value="branch_manager">مدیر شعبه</option>
                <option value="accountant">حسابدار</option>
                <option value="receptionist">پذیرش</option>
                <option value="support">پشتیبان</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>شعبه</label>
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
                <option value="">بدون شعبه</option>
                {branches.map(branch => (
                  <option key={branch.id} value={branch.id}>{branch.name}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: '0.5rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
                <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>کاربر فعال باشد</span>
              </label>
            </div>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={handleCloseModal}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingUser ? 'ذخیره تغییرات' : 'ایجاد کاربر'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="حذف کاربر"
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
            کاربر <strong>{deletingUser?.first_name} {deletingUser?.last_name}</strong> حذف خواهد شد.
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

export default AdminUsers;

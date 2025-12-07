import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, FileUpload, JalaliDatePicker } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { branchesAPI, usersAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';
import './Branches.css';

const AdminBranches = () => {
  const [branches, setBranches] = useState([]);
  const [managers, setManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [editingBranch, setEditingBranch] = useState(null);
  const [deletingBranch, setDeletingBranch] = useState(null);
  const [viewingBranch, setViewingBranch] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploadedImageKey, setUploadedImageKey] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    phone: '',
    email: '',
    address: '',
    city: '',
    province: '',
    postal_code: '',
    manager: '',
    total_capacity: 100,
    working_hours_start: '08:00',
    working_hours_end: '20:00',
    working_days: 'شنبه تا پنجشنبه',
    status: 'active',
    description: '',
    facilities: '',
    established_date: '',
    image: null,
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchBranches();
    fetchManagers();
  }, []);

  const fetchBranches = async () => {
    try {
      setLoading(true);
      const response = await branchesAPI.list();
      setBranches(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error fetching branches:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchManagers = async () => {
    try {
      const response = await usersAPI.list({ role: 'branch_manager' });
      setManagers(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error fetching managers:', error);
    }
  };

  const handleViewDetails = async (branch) => {
    setViewingBranch(branch);
    setShowDetailModal(true);
    
    // Fetch full details if needed
    try {
      setLoadingDetails(true);
      const response = await branchesAPI.get(branch.id);
      setViewingBranch(response.data);
    } catch (error) {
      console.error('Error fetching branch details:', error);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleOpenModal = (branch = null) => {
    if (branch) {
      setEditingBranch(branch);
      setFormData({
        name: branch.name || '',
        code: branch.code || '',
        phone: branch.phone || '',
        email: branch.email || '',
        address: branch.address || '',
        city: branch.city || '',
        province: branch.province || '',
        postal_code: branch.postal_code || '',
        manager: branch.manager || '',
        total_capacity: branch.total_capacity || 100,
        working_hours_start: branch.working_hours_start || '08:00',
        working_hours_end: branch.working_hours_end || '20:00',
        working_days: branch.working_days || 'شنبه تا پنجشنبه',
        status: branch.status || 'active',
        description: branch.description || '',
        facilities: branch.facilities || '',
        established_date: branch.established_date || '',
      });
      setImagePreview(branch.image_url);
      setUploadedImageKey(null);
    } else {
      setEditingBranch(null);
      setFormData({
        name: '',
        code: '',
        phone: '',
        email: '',
        address: '',
        city: '',
        province: '',
        postal_code: '',
        manager: '',
        total_capacity: 100,
        working_hours_start: '08:00',
        working_hours_end: '20:00',
        working_days: 'شنبه تا پنجشنبه',
        status: 'active',
        description: '',
        facilities: '',
        established_date: '',
      });
      setImagePreview(null);
      setUploadedImageKey(null);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingBranch(null);
    setImagePreview(null);
    setUploadedImageKey(null);
  };

  const handleImageUploadComplete = (result) => {
    setUploadedImageKey(result.key);
    setImagePreview(result.url);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      // Prepare data
      const data = { ...formData };
      
      // Add uploaded image key if available
      if (uploadedImageKey) {
        data.image_s3_key = uploadedImageKey;
      }
      
      // Remove empty values
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
          delete data[key];
        }
      });

      if (editingBranch) {
        await branchesAPI.update(editingBranch.id, data);
      } else {
        await branchesAPI.create(data);
      }
      
      handleCloseModal();
      fetchBranches();
    } catch (error) {
      console.error('Error saving branch:', error);
      alert(error.response?.data?.message || error.response?.data?.detail || 'خطا در ذخیره اطلاعات');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (branch) => {
    setDeletingBranch(branch);
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!deletingBranch) return;
    
    try {
      setDeleting(true);
      await branchesAPI.delete(deletingBranch.id);
      setShowDeleteModal(false);
      setDeletingBranch(null);
      fetchBranches();
    } catch (error) {
      console.error('Error deleting branch:', error);
      alert(error.response?.data?.message || 'خطا در حذف شعبه');
    } finally {
      setDeleting(false);
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      active: 'success',
      inactive: 'error',
      under_construction: 'warning',
    };
    const names = {
      active: 'فعال',
      inactive: 'غیرفعال',
      under_construction: 'در حال ساخت',
    };
    return <Badge variant={variants[status] || 'default'}>{names[status] || status}</Badge>;
  };

  return (
    <div className="branches-page">
      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            شعبه جدید
          </Button>
        }>
          <CardTitle>مدیریت شعب</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="loading-container">
              <Spinner size="large" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>تصویر</TableHead>
                  <TableHead>کد</TableHead>
                  <TableHead>نام شعبه</TableHead>
                  <TableHead>مدیر</TableHead>
                  <TableHead>شهر</TableHead>
                  <TableHead>تلفن</TableHead>
                  <TableHead>تاریخ تأسیس</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {branches.length === 0 ? (
                  <TableEmpty message="شعبه‌ای یافت نشد" />
                ) : (
                  branches.map((branch) => (
                    <TableRow key={branch.id}>
                      <TableCell>
                        <div className="branch-image">
                          {branch.image_url ? (
                            <img src={branch.image_url} alt={branch.name} />
                          ) : (
                            <div className="branch-image-placeholder">
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                                <polyline points="9,22 9,12 15,12 15,22" />
                              </svg>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell><code>{branch.code}</code></TableCell>
                      <TableCell><strong>{branch.name}</strong></TableCell>
                      <TableCell>{branch.manager_name || branch.manager_details?.first_name + ' ' + branch.manager_details?.last_name || '-'}</TableCell>
                      <TableCell>{branch.city}</TableCell>
                      <TableCell style={{ direction: 'ltr', textAlign: 'right' }}>{branch.phone}</TableCell>
                      <TableCell>{formatApiDate(branch.established_date)}</TableCell>
                      <TableCell>{getStatusBadge(branch.status)}</TableCell>
                      <TableCell>
                        <div className="table-actions">
                          <button 
                            className="action-btn action-btn-view"
                            onClick={() => handleViewDetails(branch)}
                            title="مشاهده جزئیات"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          </button>
                          <button 
                            className="action-btn action-btn-edit"
                            onClick={() => handleOpenModal(branch)}
                            title="ویرایش"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </button>
                          <button 
                            className="action-btn action-btn-delete"
                            onClick={() => handleDeleteClick(branch)}
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

      {/* Branch Details Modal */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        title={`جزئیات شعبه - ${viewingBranch?.name || ''}`}
        size="large"
      >
        {loadingDetails ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Spinner size="large" />
          </div>
        ) : viewingBranch && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Header with Image */}
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              {viewingBranch.image_url && (
                <img 
                  src={viewingBranch.image_url} 
                  alt={viewingBranch.name}
                  style={{ width: '200px', height: '130px', objectFit: 'cover', borderRadius: 'var(--radius-lg)' }}
                />
              )}
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                  <h2 style={{ margin: 0 }}>{viewingBranch.name}</h2>
                  {getStatusBadge(viewingBranch.status)}
                </div>
                <p style={{ margin: '0', color: 'var(--gray-500)' }}>کد: {viewingBranch.code}</p>
                {viewingBranch.description && (
                  <p style={{ margin: '0.5rem 0 0', color: 'var(--gray-600)' }}>{viewingBranch.description}</p>
                )}
              </div>
            </div>

            {/* Stats Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'var(--primary-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-600)' }}>{toPersianDigits(viewingBranch.total_capacity || 0)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-600)' }}>ظرفیت کل</div>
              </div>
              <div style={{ padding: '1rem', background: '#d1fae5', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(viewingBranch.active_classes_count || 0)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-600)' }}>کلاس فعال</div>
              </div>
              <div style={{ padding: '1rem', background: '#dbeafe', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#2563eb' }}>{toPersianDigits(viewingBranch.active_students_count || 0)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-600)' }}>دانش‌آموز فعال</div>
              </div>
            </div>

            {/* Contact Info */}
            <div>
              <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)' }}>اطلاعات تماس</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>تلفن:</span>
                  <p style={{ margin: '0.25rem 0 0', direction: 'ltr', textAlign: 'right' }}>{viewingBranch.phone || '-'}</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>ایمیل:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.email || '-'}</p>
                </div>
              </div>
            </div>

            {/* Address */}
            <div>
              <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)' }}>آدرس</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '0.5rem' }}>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>استان:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.province || '-'}</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>شهر:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.city || '-'}</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>کد پستی:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.postal_code || '-'}</p>
                </div>
              </div>
              <div>
                <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>آدرس کامل:</span>
                <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.address || '-'}</p>
              </div>
            </div>

            {/* Working Hours */}
            <div>
              <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)' }}>ساعات کاری</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>ساعت شروع:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.working_hours_start || '-'}</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>ساعت پایان:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.working_hours_end || '-'}</p>
                </div>
                <div>
                  <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>روزهای کاری:</span>
                  <p style={{ margin: '0.25rem 0 0' }}>{viewingBranch.working_days || '-'}</p>
                </div>
              </div>
            </div>

            {/* Manager */}
            <div>
              <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)' }}>مدیر شعبه</h4>
              {viewingBranch.manager_details ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 600
                  }}>
                    {viewingBranch.manager_details.first_name?.[0]}{viewingBranch.manager_details.last_name?.[0]}
                  </div>
                  <div>
                    <strong>{viewingBranch.manager_details.first_name} {viewingBranch.manager_details.last_name}</strong>
                    <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>{viewingBranch.manager_details.mobile}</div>
                  </div>
                </div>
              ) : (
                <p style={{ color: 'var(--gray-500)' }}>مدیری تعیین نشده است</p>
              )}
            </div>

            {/* Facilities */}
            {viewingBranch.facilities && (
              <div>
                <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)' }}>امکانات</h4>
                <p style={{ margin: 0, padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>{viewingBranch.facilities}</p>
              </div>
            )}

            {/* Dates */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
              <div>
                <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>تاریخ تأسیس:</span>
                <p style={{ margin: '0.25rem 0 0' }}>{formatApiDate(viewingBranch.established_date)}</p>
              </div>
              <div>
                <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>تاریخ ایجاد:</span>
                <p style={{ margin: '0.25rem 0 0' }}>{formatApiDate(viewingBranch.created_at)}</p>
              </div>
              <div>
                <span style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>آخرین بروزرسانی:</span>
                <p style={{ margin: '0.25rem 0 0' }}>{formatApiDate(viewingBranch.updated_at)}</p>
              </div>
            </div>
          </div>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowDetailModal(false)}>بستن</Button>
          <Button onClick={() => { setShowDetailModal(false); handleOpenModal(viewingBranch); }}>ویرایش</Button>
        </ModalFooter>
      </Modal>

      {/* Add/Edit Modal */}
      <Modal
        isOpen={showModal}
        onClose={handleCloseModal}
        title={editingBranch ? 'ویرایش شعبه' : 'شعبه جدید'}
        size="large"
      >
        <div className="branch-form">
          {/* Image Upload */}
          <div className="form-section">
            <h4 className="form-section-title">تصویر شعبه</h4>
            <FileUpload
              accept="image/*"
              maxSize={10 * 1024 * 1024}
              folder="branches"
              targetModel="Branch"
              targetField="image"
              preview={true}
              previewUrl={imagePreview}
              label="آپلود تصویر شعبه"
              hint="حداکثر ۱۰ مگابایت - فرمت‌های JPG, PNG"
              onUploadComplete={handleImageUploadComplete}
              onUploadError={(err) => alert(err)}
            />
          </div>

          {/* Basic Info */}
          <div className="form-section">
            <h4 className="form-section-title">اطلاعات اصلی</h4>
            <div className="form-grid">
              <Input
                label="نام شعبه *"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="مثال: شعبه مرکزی تهران"
              />
              <Input
                label="کد شعبه"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                placeholder="خودکار تولید می‌شود"
                hint="در صورت خالی بودن، کد خودکار تولید می‌شود"
              />
              <div className="form-field">
                <label className="input-label">مدیر شعبه</label>
                <select
                  className="form-select"
                  value={formData.manager}
                  onChange={(e) => setFormData({ ...formData, manager: e.target.value })}
                >
                  <option value="">انتخاب مدیر...</option>
                  {managers.map((manager) => (
                    <option key={manager.id} value={manager.id}>
                      {manager.first_name} {manager.last_name} ({manager.mobile})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label className="input-label">وضعیت</label>
                <select
                  className="form-select"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                >
                  <option value="active">فعال</option>
                  <option value="inactive">غیرفعال</option>
                  <option value="under_construction">در حال ساخت</option>
                </select>
              </div>
            </div>
          </div>

          {/* Contact Info */}
          <div className="form-section">
            <h4 className="form-section-title">اطلاعات تماس</h4>
            <div className="form-grid">
              <Input
                label="تلفن *"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="02112345678"
              />
              <Input
                label="ایمیل"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="branch@example.com"
              />
            </div>
          </div>

          {/* Address */}
          <div className="form-section">
            <h4 className="form-section-title">آدرس</h4>
            <div className="form-grid">
              <Input
                label="استان *"
                value={formData.province}
                onChange={(e) => setFormData({ ...formData, province: e.target.value })}
                placeholder="مثال: تهران"
              />
              <Input
                label="شهر *"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                placeholder="مثال: تهران"
              />
              <Input
                label="کد پستی"
                value={formData.postal_code}
                onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                placeholder="مثال: 1234567890"
              />
            </div>
            <div style={{ marginTop: '1rem' }}>
              <Input
                label="آدرس کامل *"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="آدرس کامل شعبه را وارد کنید"
              />
            </div>
          </div>

          {/* Working Hours */}
          <div className="form-section">
            <h4 className="form-section-title">ساعات کاری</h4>
            <div className="form-grid">
              <Input
                label="ساعت شروع"
                type="time"
                value={formData.working_hours_start}
                onChange={(e) => setFormData({ ...formData, working_hours_start: e.target.value })}
              />
              <Input
                label="ساعت پایان"
                type="time"
                value={formData.working_hours_end}
                onChange={(e) => setFormData({ ...formData, working_hours_end: e.target.value })}
              />
              <Input
                label="روزهای کاری"
                value={formData.working_days}
                onChange={(e) => setFormData({ ...formData, working_days: e.target.value })}
                placeholder="مثال: شنبه تا پنجشنبه"
              />
              <Input
                label="ظرفیت کل"
                type="number"
                value={formData.total_capacity}
                onChange={(e) => setFormData({ ...formData, total_capacity: e.target.value })}
              />
            </div>
          </div>

          {/* Additional Info */}
          <div className="form-section">
            <h4 className="form-section-title">اطلاعات تکمیلی</h4>
            <div className="form-grid">
              <JalaliDatePicker
                label="تاریخ تأسیس"
                value={formData.established_date}
                onChange={(date) => setFormData({ ...formData, established_date: date })}
                placeholder="انتخاب تاریخ"
              />
            </div>
            <div style={{ marginTop: '1rem' }}>
              <div className="form-field">
                <label className="input-label">توضیحات</label>
                <textarea
                  className="form-textarea"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="توضیحات درباره شعبه..."
                  rows={3}
                />
              </div>
            </div>
            <div style={{ marginTop: '1rem' }}>
              <div className="form-field">
                <label className="input-label">امکانات</label>
                <textarea
                  className="form-textarea"
                  value={formData.facilities}
                  onChange={(e) => setFormData({ ...formData, facilities: e.target.value })}
                  placeholder="پارکینگ، آسانسور، بوفه، ..."
                  rows={2}
                />
              </div>
            </div>
          </div>
        </div>
        
        <ModalFooter>
          <Button variant="secondary" onClick={handleCloseModal}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingBranch ? 'ذخیره تغییرات' : 'ایجاد شعبه'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="حذف شعبه"
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
            شعبه <strong>{deletingBranch?.name}</strong> حذف خواهد شد.
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

export default AdminBranches;

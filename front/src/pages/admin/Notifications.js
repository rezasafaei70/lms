import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, JalaliDatePicker, FileUpload } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { notificationsAPI } from '../../services/api';
import { formatApiDate, formatApiDateTime, toPersianDigits } from '../../utils/jalaliDate';

const AdminNotifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('announcements');
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [editingAnnouncement, setEditingAnnouncement] = useState(null);
  const [announcementFormData, setAnnouncementFormData] = useState({
    title: '',
    message: '',
    target_roles: [],
    priority: 'normal',
    is_published: true,
    published_at: '',
    expires_at: '',
  });
  const [attachmentKey, setAttachmentKey] = useState(null);
  const [savingAnnouncement, setSavingAnnouncement] = useState(false);

  const roles = [
    { key: 'super_admin', label: 'مدیر کل' },
    { key: 'branch_manager', label: 'مدیر شعبه' },
    { key: 'teacher', label: 'معلم' },
    { key: 'student', label: 'دانش‌آموز' },
    { key: 'accountant', label: 'حسابدار' },
    { key: 'receptionist', label: 'پذیرش' },
    { key: 'support', label: 'پشتیبان' },
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [notifRes, announRes] = await Promise.all([
        notificationsAPI.list(),
        notificationsAPI.getAnnouncements(),
      ]);
      setNotifications(notifRes.data.results || []);
      setAnnouncements(announRes.data.results || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (id) => {
    try {
      await notificationsAPI.markAsRead(id);
      fetchData();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      fetchData();
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  };

  const handleOpenAnnouncementModal = (announcement = null) => {
    if (announcement) {
      setEditingAnnouncement(announcement);
      setAnnouncementFormData({
        title: announcement.title || '',
        message: announcement.message || '',
        target_roles: announcement.target_roles || [],
        priority: announcement.priority || 'normal',
        is_published: announcement.is_published !== false,
        published_at: announcement.published_at || '',
        expires_at: announcement.expires_at || '',
      });
    } else {
      setEditingAnnouncement(null);
      setAnnouncementFormData({
        title: '',
        message: '',
        target_roles: [],
        priority: 'normal',
        is_published: true,
        published_at: '',
        expires_at: '',
      });
    }
    setAttachmentKey(null);
    setShowAnnouncementModal(true);
  };

  const handleCreateAnnouncement = async () => {
    try {
      setSavingAnnouncement(true);
      const data = { ...announcementFormData };
      
      if (attachmentKey) {
        data.attachment_s3_key = attachmentKey;
      }

      // Remove empty arrays
      if (data.target_roles.length === 0) {
        delete data.target_roles;
      }

      if (editingAnnouncement) {
        await notificationsAPI.updateAnnouncement(editingAnnouncement.id, data);
      } else {
        await notificationsAPI.createAnnouncement(data);
      }
      
      setShowAnnouncementModal(false);
      setEditingAnnouncement(null);
      fetchData();
    } catch (error) {
      console.error('Error saving announcement:', error);
      alert(error.response?.data?.detail || 'خطا در ذخیره اطلاعیه');
    } finally {
      setSavingAnnouncement(false);
    }
  };

  const handleDeleteAnnouncement = async (id) => {
    if (!window.confirm('آیا از حذف این اطلاعیه اطمینان دارید؟')) return;
    
    try {
      await notificationsAPI.deleteAnnouncement(id);
      fetchData();
    } catch (error) {
      console.error('Error deleting announcement:', error);
      alert('خطا در حذف اطلاعیه');
    }
  };

  const handleRoleToggle = (role) => {
    const currentRoles = announcementFormData.target_roles;
    const newRoles = currentRoles.includes(role)
      ? currentRoles.filter(r => r !== role)
      : [...currentRoles, role];
    setAnnouncementFormData({ ...announcementFormData, target_roles: newRoles });
  };

  const getRoleName = (role) => {
    const found = roles.find(r => r.key === role);
    return found ? found.label : role;
  };

  const getPriorityBadge = (priority) => {
    const variants = {
      low: 'default',
      normal: 'info',
      high: 'warning',
      urgent: 'error',
    };
    const names = {
      low: 'کم',
      normal: 'معمولی',
      high: 'بالا',
      urgent: 'فوری',
    };
    return <Badge variant={variants[priority] || 'default'}>{names[priority] || priority}</Badge>;
  };

  // Stats
  const unreadCount = notifications.filter(n => !n.is_read).length;
  const activeAnnouncements = announcements.filter(a => a.is_published).length;

  return (
    <div className="notifications-page">
      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
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
                  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
                  <path d="M13.73 21a2 2 0 01-3.46 0" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(notifications.length)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کل اعلان‌ها</div>
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
                background: '#fee2e2', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: '#ef4444'
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(unreadCount)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>خوانده نشده</div>
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
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(activeAnnouncements)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>اطلاعیه فعال</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader action={
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {activeTab === 'notifications' && unreadCount > 0 && (
              <Button variant="secondary" onClick={handleMarkAllAsRead}>
                همه را خوانده شده علامت بزن
              </Button>
            )}
            {activeTab === 'announcements' && (
              <Button onClick={() => handleOpenAnnouncementModal()}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                اطلاعیه جدید
              </Button>
            )}
          </div>
        }>
          <CardTitle>مدیریت اعلانات و اطلاعیه‌ها</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Tabs */}
          <div style={{ 
            display: 'flex', 
            gap: '0.25rem',
            padding: '0.25rem',
            background: 'var(--gray-100)',
            borderRadius: 'var(--radius-lg)',
            marginBottom: '1.5rem',
            width: 'fit-content'
          }}>
            {[
              { key: 'announcements', label: 'اطلاعیه‌ها' },
              { key: 'notifications', label: 'اعلان‌های سیستم' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: activeTab === tab.key ? 'white' : 'transparent',
                  boxShadow: activeTab === tab.key ? 'var(--shadow-sm)' : 'none',
                  color: activeTab === tab.key ? 'var(--primary-600)' : 'var(--gray-600)',
                  fontWeight: activeTab === tab.key ? 500 : 400,
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

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <>
              {/* Announcements Tab */}
              {activeTab === 'announcements' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>عنوان</TableHead>
                      <TableHead>مخاطبان</TableHead>
                      <TableHead>اولویت</TableHead>
                      <TableHead>تاریخ انتشار</TableHead>
                      <TableHead>انقضا</TableHead>
                      <TableHead>وضعیت</TableHead>
                      <TableHead>عملیات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {announcements.length === 0 ? (
                      <TableEmpty message="اطلاعیه‌ای یافت نشد" />
                    ) : (
                      announcements.map((announ) => (
                        <TableRow key={announ.id}>
                          <TableCell>
                            <div>
                              <strong>{announ.title}</strong>
                              {announ.message && (
                                <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                                  {announ.message.substring(0, 60)}...
                                </div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            {announ.target_roles && announ.target_roles.length > 0
                              ? announ.target_roles.map(getRoleName).join(', ')
                              : <span style={{ color: 'var(--gray-400)' }}>همه</span>}
                          </TableCell>
                          <TableCell>{getPriorityBadge(announ.priority)}</TableCell>
                          <TableCell>{formatApiDate(announ.published_at)}</TableCell>
                          <TableCell>{announ.expires_at ? formatApiDate(announ.expires_at) : '-'}</TableCell>
                          <TableCell>
                            <Badge variant={announ.is_published ? 'success' : 'default'}>
                              {announ.is_published ? 'منتشر شده' : 'پیش‌نویس'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button 
                                onClick={() => handleOpenAnnouncementModal(announ)}
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
                                onClick={() => handleDeleteAnnouncement(announ.id)}
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

              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>عنوان</TableHead>
                      <TableHead>پیام</TableHead>
                      <TableHead>نوع</TableHead>
                      <TableHead>تاریخ</TableHead>
                      <TableHead>وضعیت</TableHead>
                      <TableHead>عملیات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {notifications.length === 0 ? (
                      <TableEmpty message="اعلانی یافت نشد" />
                    ) : (
                      notifications.map((notif) => (
                        <TableRow key={notif.id}>
                          <TableCell><strong>{notif.title}</strong></TableCell>
                          <TableCell>{notif.message}</TableCell>
                          <TableCell>
                            <Badge variant="info">{notif.notification_type || 'سیستم'}</Badge>
                          </TableCell>
                          <TableCell>{formatApiDateTime(notif.created_at)}</TableCell>
                          <TableCell>
                            <Badge variant={notif.is_read ? 'default' : 'error'}>
                              {notif.is_read ? 'خوانده شده' : 'جدید'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {!notif.is_read && (
                              <Button size="small" onClick={() => handleMarkAsRead(notif.id)}>
                                علامت خوانده شده
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Announcement Modal */}
      <Modal
        isOpen={showAnnouncementModal}
        onClose={() => setShowAnnouncementModal(false)}
        title={editingAnnouncement ? 'ویرایش اطلاعیه' : 'اطلاعیه جدید'}
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <Input
            label="عنوان *"
            value={announcementFormData.title}
            onChange={(e) => setAnnouncementFormData({ ...announcementFormData, title: e.target.value })}
            placeholder="عنوان اطلاعیه..."
          />

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>متن اطلاعیه *</label>
            <textarea
              value={announcementFormData.message}
              onChange={(e) => setAnnouncementFormData({ ...announcementFormData, message: e.target.value })}
              placeholder="متن کامل اطلاعیه..."
              rows={4}
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

          {/* Target Roles */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500, fontSize: '0.875rem' }}>
              مخاطبان (خالی = همه)
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {roles.map(role => (
                <button
                  key={role.key}
                  type="button"
                  onClick={() => handleRoleToggle(role.key)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    border: announcementFormData.target_roles.includes(role.key) 
                      ? '2px solid var(--primary-500)' 
                      : '2px solid var(--gray-200)',
                    background: announcementFormData.target_roles.includes(role.key) 
                      ? 'var(--primary-50)' 
                      : 'white',
                    color: announcementFormData.target_roles.includes(role.key) 
                      ? 'var(--primary-600)' 
                      : 'var(--gray-600)',
                    cursor: 'pointer',
                    fontWeight: 500,
                    fontSize: '0.8125rem',
                    transition: 'all var(--transition)'
                  }}
                >
                  {role.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>اولویت</label>
              <select
                value={announcementFormData.priority}
                onChange={(e) => setAnnouncementFormData({ ...announcementFormData, priority: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="low">کم</option>
                <option value="normal">معمولی</option>
                <option value="high">بالا</option>
                <option value="urgent">فوری</option>
              </select>
            </div>
            <JalaliDatePicker
              label="تاریخ انتشار"
              value={announcementFormData.published_at}
              onChange={(date) => setAnnouncementFormData({ ...announcementFormData, published_at: date })}
              placeholder="خالی = الان"
            />
            <JalaliDatePicker
              label="تاریخ انقضا"
              value={announcementFormData.expires_at}
              onChange={(date) => setAnnouncementFormData({ ...announcementFormData, expires_at: date })}
              placeholder="اختیاری"
            />
          </div>

          {/* Attachment */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>فایل پیوست (اختیاری)</label>
            <FileUpload
              accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx"
              maxSize={10 * 1024 * 1024}
              folder="announcements"
              targetModel="Announcement"
              targetField="attachment"
              preview={true}
              label="آپلود فایل"
              hint="تصویر، PDF، Word یا Excel - حداکثر ۱۰ مگابایت"
              previewUrl={editingAnnouncement?.attachment_url}
              onUploadComplete={(result) => setAttachmentKey(result.key)}
              onUploadError={(err) => alert(err)}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={announcementFormData.is_published}
                onChange={(e) => setAnnouncementFormData({ ...announcementFormData, is_published: e.target.checked })}
              />
              <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>منتشر شود</span>
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowAnnouncementModal(false)}>انصراف</Button>
          <Button onClick={handleCreateAnnouncement} loading={savingAnnouncement}>
            {editingAnnouncement ? 'ذخیره تغییرات' : 'ایجاد اطلاعیه'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminNotifications;

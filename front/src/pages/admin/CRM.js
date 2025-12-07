import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, JalaliDatePicker, FileUpload } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { crmAPI } from '../../services/api';
import { formatApiDate, formatApiDateTime, toPersianDigits } from '../../utils/jalaliDate';

const AdminCRM = () => {
  const [leads, setLeads] = useState([]);
  const [activities, setActivities] = useState([]);
  const [feedbacks, setFeedbacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('leads');
  
  // Lead Modal
  const [showLeadModal, setShowLeadModal] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [leadFormData, setLeadFormData] = useState({
    name: '',
    phone: '',
    email: '',
    status: 'new',
    source: '',
    notes: '',
    assigned_to: '',
    expected_value: '',
    follow_up_date: '',
  });
  const [savingLead, setSavingLead] = useState(false);

  // Activity Modal
  const [showActivityModal, setShowActivityModal] = useState(false);
  const [activityFormData, setActivityFormData] = useState({
    lead: '',
    activity_type: 'call',
    activity_date: '',
    notes: '',
    outcome: '',
    next_follow_up: '',
  });
  const [activityAttachment, setActivityAttachment] = useState(null);
  const [savingActivity, setSavingActivity] = useState(false);

  const leadStatuses = [
    { key: 'new', label: 'جدید', variant: 'info' },
    { key: 'contacted', label: 'تماس گرفته شده', variant: 'primary' },
    { key: 'qualified', label: 'واجد شرایط', variant: 'success' },
    { key: 'unqualified', label: 'غیر واجد شرایط', variant: 'error' },
    { key: 'converted', label: 'تبدیل شده', variant: 'default' },
    { key: 'lost', label: 'از دست رفته', variant: 'error' },
  ];

  const activityTypes = [
    { key: 'call', label: 'تماس تلفنی' },
    { key: 'email', label: 'ایمیل' },
    { key: 'meeting', label: 'جلسه' },
    { key: 'sms', label: 'پیامک' },
    { key: 'visit', label: 'بازدید' },
    { key: 'other', label: 'سایر' },
  ];

  const leadSources = [
    'وب‌سایت',
    'اینستاگرام',
    'تلگرام',
    'معرفی',
    'تبلیغات',
    'نمایشگاه',
    'سایر',
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [leadsRes, activitiesRes, feedbacksRes] = await Promise.all([
        crmAPI.getLeads(),
        crmAPI.getActivities(),
        crmAPI.getFeedbacks(),
      ]);
      setLeads(leadsRes.data.results || []);
      setActivities(activitiesRes.data.results || []);
      setFeedbacks(feedbacksRes.data.results || []);
    } catch (error) {
      console.error('Error fetching CRM data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenLeadModal = (lead = null) => {
    if (lead) {
      setEditingLead(lead);
      setLeadFormData({
        name: lead.name || '',
        phone: lead.phone || '',
        email: lead.email || '',
        status: lead.status || 'new',
        source: lead.source || '',
        notes: lead.notes || '',
        assigned_to: lead.assigned_to || '',
        expected_value: lead.expected_value || '',
        follow_up_date: lead.follow_up_date || '',
      });
    } else {
      setEditingLead(null);
      setLeadFormData({
        name: '',
        phone: '',
        email: '',
        status: 'new',
        source: '',
        notes: '',
        assigned_to: '',
        expected_value: '',
        follow_up_date: '',
      });
    }
    setShowLeadModal(true);
  };

  const handleSaveLead = async () => {
    try {
      setSavingLead(true);
      const data = { ...leadFormData };
      
      if (data.expected_value) data.expected_value = parseInt(data.expected_value);
      
      // Remove empty values
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
          delete data[key];
        }
      });

      if (editingLead) {
        await crmAPI.updateLead(editingLead.id, data);
      } else {
        await crmAPI.createLead(data);
      }
      setShowLeadModal(false);
      setEditingLead(null);
      fetchData();
    } catch (error) {
      console.error('Error saving lead:', error);
      alert(error.response?.data?.detail || 'خطا در ذخیره سرنخ');
    } finally {
      setSavingLead(false);
    }
  };

  const handleDeleteLead = async (id) => {
    if (!window.confirm('آیا از حذف این سرنخ اطمینان دارید؟')) return;
    
    try {
      await crmAPI.deleteLead(id);
      fetchData();
    } catch (error) {
      console.error('Error deleting lead:', error);
      alert('خطا در حذف سرنخ');
    }
  };

  const handleOpenActivityModal = (lead = null) => {
    setActivityFormData({
      lead: lead?.id || '',
      activity_type: 'call',
      activity_date: new Date().toISOString().split('T')[0],
      notes: '',
      outcome: '',
      next_follow_up: '',
    });
    setActivityAttachment(null);
    setShowActivityModal(true);
  };

  const handleSaveActivity = async () => {
    try {
      setSavingActivity(true);
      const data = { ...activityFormData };
      
      if (activityAttachment) {
        data.attachment_s3_key = activityAttachment;
      }

      await crmAPI.createActivity(data);
      setShowActivityModal(false);
      fetchData();
    } catch (error) {
      console.error('Error saving activity:', error);
      alert(error.response?.data?.detail || 'خطا در ذخیره فعالیت');
    } finally {
      setSavingActivity(false);
    }
  };

  const getLeadStatusBadge = (status) => {
    const found = leadStatuses.find(s => s.key === status);
    return <Badge variant={found?.variant || 'default'}>{found?.label || status}</Badge>;
  };

  const getActivityTypeName = (type) => {
    const found = activityTypes.find(t => t.key === type);
    return found?.label || type;
  };

  // Stats
  const stats = {
    total: leads.length,
    new: leads.filter(l => l.status === 'new').length,
    qualified: leads.filter(l => l.status === 'qualified').length,
    converted: leads.filter(l => l.status === 'converted').length,
  };

  return (
    <div className="crm-page">
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
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>کل سرنخ‌ها</div>
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
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.new)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>سرنخ جدید</div>
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
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.qualified)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>واجد شرایط</div>
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
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-900)' }}>{toPersianDigits(stats.converted)}</div>
                <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>تبدیل شده</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader action={
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button onClick={() => handleOpenLeadModal()}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              سرنخ جدید
            </Button>
            <Button variant="secondary" onClick={() => handleOpenActivityModal()}>
              ثبت فعالیت
            </Button>
          </div>
        }>
          <CardTitle>مدیریت CRM</CardTitle>
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
              { key: 'leads', label: 'سرنخ‌ها' },
              { key: 'activities', label: 'فعالیت‌ها' },
              { key: 'feedbacks', label: 'بازخوردها' },
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
              {/* Leads Tab */}
              {activeTab === 'leads' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>نام</TableHead>
                      <TableHead>تلفن</TableHead>
                      <TableHead>ایمیل</TableHead>
                      <TableHead>منبع</TableHead>
                      <TableHead>ارزش پیش‌بینی</TableHead>
                      <TableHead>پیگیری بعدی</TableHead>
                      <TableHead>وضعیت</TableHead>
                      <TableHead>عملیات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leads.length === 0 ? (
                      <TableEmpty message="سرنخی یافت نشد" />
                    ) : (
                      leads.map((lead) => (
                        <TableRow key={lead.id}>
                          <TableCell>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                              <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: '50%',
                                background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontWeight: 600,
                                fontSize: '0.875rem'
                              }}>
                                {lead.name?.charAt(0) || '?'}
                              </div>
                              <strong>{lead.name}</strong>
                            </div>
                          </TableCell>
                          <TableCell dir="ltr" style={{ textAlign: 'right' }}>{lead.phone || '-'}</TableCell>
                          <TableCell>{lead.email || '-'}</TableCell>
                          <TableCell>{lead.source || '-'}</TableCell>
                          <TableCell>
                            {lead.expected_value 
                              ? `${toPersianDigits(lead.expected_value.toLocaleString())} تومان`
                              : '-'}
                          </TableCell>
                          <TableCell>{lead.follow_up_date ? formatApiDate(lead.follow_up_date) : '-'}</TableCell>
                          <TableCell>{getLeadStatusBadge(lead.status)}</TableCell>
                          <TableCell>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button 
                                onClick={() => handleOpenActivityModal(lead)}
                                style={{
                                  padding: '0.5rem',
                                  background: '#d1fae5',
                                  border: 'none',
                                  borderRadius: 'var(--radius)',
                                  color: 'var(--success)',
                                  cursor: 'pointer'
                                }}
                                title="ثبت فعالیت"
                              >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z" />
                                </svg>
                              </button>
                              <button 
                                onClick={() => handleOpenLeadModal(lead)}
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
                                onClick={() => handleDeleteLead(lead.id)}
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

              {/* Activities Tab */}
              {activeTab === 'activities' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>سرنخ</TableHead>
                      <TableHead>نوع فعالیت</TableHead>
                      <TableHead>تاریخ</TableHead>
                      <TableHead>نتیجه</TableHead>
                      <TableHead>پیگیری بعدی</TableHead>
                      <TableHead>یادداشت</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {activities.length === 0 ? (
                      <TableEmpty message="فعالیتی یافت نشد" />
                    ) : (
                      activities.map((activity) => (
                        <TableRow key={activity.id}>
                          <TableCell><strong>{activity.lead_name}</strong></TableCell>
                          <TableCell>
                            <Badge variant="info">{getActivityTypeName(activity.activity_type)}</Badge>
                          </TableCell>
                          <TableCell>{formatApiDateTime(activity.activity_date)}</TableCell>
                          <TableCell>{activity.outcome || '-'}</TableCell>
                          <TableCell>
                            {activity.next_follow_up 
                              ? formatApiDate(activity.next_follow_up) 
                              : '-'}
                          </TableCell>
                          <TableCell>
                            {activity.notes 
                              ? (activity.notes.length > 50 ? activity.notes.substring(0, 50) + '...' : activity.notes)
                              : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}

              {/* Feedbacks Tab */}
              {activeTab === 'feedbacks' && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>مشتری</TableHead>
                      <TableHead>نوع</TableHead>
                      <TableHead>امتیاز</TableHead>
                      <TableHead>تاریخ</TableHead>
                      <TableHead>توضیحات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {feedbacks.length === 0 ? (
                      <TableEmpty message="بازخوردی یافت نشد" />
                    ) : (
                      feedbacks.map((feedback) => (
                        <TableRow key={feedback.id}>
                          <TableCell><strong>{feedback.customer_name}</strong></TableCell>
                          <TableCell>{feedback.feedback_type}</TableCell>
                          <TableCell>
                            {feedback.rating ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                {[1, 2, 3, 4, 5].map(star => (
                                  <span 
                                    key={star} 
                                    style={{ 
                                      color: star <= feedback.rating ? '#fbbf24' : '#e5e7eb',
                                      fontSize: '1rem'
                                    }}
                                  >
                                    ★
                                  </span>
                                ))}
                              </div>
                            ) : '-'}
                          </TableCell>
                          <TableCell>{formatApiDate(feedback.feedback_date)}</TableCell>
                          <TableCell>{feedback.comments || '-'}</TableCell>
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

      {/* Lead Modal */}
      <Modal
        isOpen={showLeadModal}
        onClose={() => setShowLeadModal(false)}
        title={editingLead ? 'ویرایش سرنخ' : 'سرنخ جدید'}
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="نام *"
              value={leadFormData.name}
              onChange={(e) => setLeadFormData({ ...leadFormData, name: e.target.value })}
              placeholder="نام و نام خانوادگی"
            />
            <Input
              label="تلفن *"
              value={leadFormData.phone}
              onChange={(e) => setLeadFormData({ ...leadFormData, phone: e.target.value })}
              placeholder="۰۹۱۲۳۴۵۶۷۸۹"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="ایمیل"
              type="email"
              value={leadFormData.email}
              onChange={(e) => setLeadFormData({ ...leadFormData, email: e.target.value })}
              placeholder="email@example.com"
            />
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>منبع</label>
              <select
                value={leadFormData.source}
                onChange={(e) => setLeadFormData({ ...leadFormData, source: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="">انتخاب کنید...</option>
                {leadSources.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>وضعیت</label>
              <select
                value={leadFormData.status}
                onChange={(e) => setLeadFormData({ ...leadFormData, status: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                {leadStatuses.map(status => (
                  <option key={status.key} value={status.key}>{status.label}</option>
                ))}
              </select>
            </div>
            <Input
              label="ارزش پیش‌بینی (تومان)"
              type="number"
              value={leadFormData.expected_value}
              onChange={(e) => setLeadFormData({ ...leadFormData, expected_value: e.target.value })}
              placeholder="مثال: 5000000"
            />
            <JalaliDatePicker
              label="تاریخ پیگیری"
              value={leadFormData.follow_up_date}
              onChange={(date) => setLeadFormData({ ...leadFormData, follow_up_date: date })}
              placeholder="انتخاب تاریخ"
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>یادداشت‌ها</label>
            <textarea
              value={leadFormData.notes}
              onChange={(e) => setLeadFormData({ ...leadFormData, notes: e.target.value })}
              placeholder="توضیحات و یادداشت‌ها..."
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
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowLeadModal(false)}>انصراف</Button>
          <Button onClick={handleSaveLead} loading={savingLead}>
            {editingLead ? 'ذخیره تغییرات' : 'ایجاد سرنخ'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Activity Modal */}
      <Modal
        isOpen={showActivityModal}
        onClose={() => setShowActivityModal(false)}
        title="ثبت فعالیت"
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>سرنخ *</label>
              <select
                value={activityFormData.lead}
                onChange={(e) => setActivityFormData({ ...activityFormData, lead: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="">انتخاب سرنخ...</option>
                {leads.map(lead => (
                  <option key={lead.id} value={lead.id}>{lead.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>نوع فعالیت</label>
              <select
                value={activityFormData.activity_type}
                onChange={(e) => setActivityFormData({ ...activityFormData, activity_type: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                {activityTypes.map(type => (
                  <option key={type.key} value={type.key}>{type.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <JalaliDatePicker
              label="تاریخ فعالیت"
              value={activityFormData.activity_date}
              onChange={(date) => setActivityFormData({ ...activityFormData, activity_date: date })}
            />
            <JalaliDatePicker
              label="پیگیری بعدی"
              value={activityFormData.next_follow_up}
              onChange={(date) => setActivityFormData({ ...activityFormData, next_follow_up: date })}
              placeholder="اختیاری"
            />
          </div>

          <Input
            label="نتیجه"
            value={activityFormData.outcome}
            onChange={(e) => setActivityFormData({ ...activityFormData, outcome: e.target.value })}
            placeholder="نتیجه فعالیت..."
          />

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>یادداشت</label>
            <textarea
              value={activityFormData.notes}
              onChange={(e) => setActivityFormData({ ...activityFormData, notes: e.target.value })}
              placeholder="جزئیات فعالیت..."
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

          {/* Attachment */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>فایل پیوست (اختیاری)</label>
            <FileUpload
              accept="image/*,application/pdf,.doc,.docx"
              maxSize={5 * 1024 * 1024}
              folder="crm-activities"
              targetModel="LeadActivity"
              targetField="attachment"
              preview={true}
              label="آپلود فایل"
              hint="تصویر، PDF یا Word - حداکثر ۵ مگابایت"
              onUploadComplete={(result) => setActivityAttachment(result.key)}
              onUploadError={(err) => alert(err)}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowActivityModal(false)}>انصراف</Button>
          <Button onClick={handleSaveActivity} loading={savingActivity}>ثبت فعالیت</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default AdminCRM;

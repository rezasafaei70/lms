import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner, Modal, ModalFooter, FileUpload } from '../../components/common';
import { lmsAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const StudentAssignments = () => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [submissionFile, setSubmissionFile] = useState(null);
  const [submissionText, setSubmissionText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    try {
      setLoading(true);
      const response = await lmsAPI.getMyAssignments();
      setAssignments(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenSubmitModal = (assignment) => {
    setSelectedAssignment(assignment);
    setSubmissionFile(null);
    setSubmissionText('');
    setShowSubmitModal(true);
  };

  const handleSubmit = async () => {
    if (!selectedAssignment) return;

    try {
      setSubmitting(true);
      const data = {
        text_content: submissionText,
      };
      if (submissionFile) {
        data.s3_key = submissionFile;
      }
      await lmsAPI.submitAssignment(selectedAssignment.id, data);
      setShowSubmitModal(false);
      fetchAssignments();
      alert('تکلیف با موفقیت ارسال شد');
    } catch (error) {
      console.error('Error submitting:', error);
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message ||
                       JSON.stringify(error.response?.data) ||
                       'خطا در ارسال تکلیف';
      alert(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  // Normalize assignment data from backend
  const normalizeAssignment = (a) => ({
    ...a,
    title: a.title || 'بدون عنوان',
    class_name: a.class_name || a.class_details?.name || a.class_obj_name || '-',
    due_date: a.due_date || a.deadline,
    status: a.status || (a.has_submitted ? 'submitted' : 'pending'),
    max_score: a.max_score || 100,
    score: a.score || null,
  });

  const displayData = assignments.map(normalizeAssignment);
  
  const filteredAssignments = displayData.filter(a => {
    if (filter === 'all') return true;
    return a.status === filter;
  });

  const getStatusBadge = (status, score, maxScore) => {
    switch (status) {
      case 'pending':
        return <Badge variant="warning">در انتظار تحویل</Badge>;
      case 'submitted':
        return <Badge variant="info">تحویل داده شده</Badge>;
      case 'graded':
        return <Badge variant="success">نمره: {toPersianDigits(score)}/{toPersianDigits(maxScore)}</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <Spinner size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Filter Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: '0.5rem',
        padding: '0.25rem',
        background: 'var(--gray-100)',
        borderRadius: 'var(--radius-lg)',
        width: 'fit-content'
      }}>
        {[
          { key: 'all', label: 'همه' },
          { key: 'pending', label: 'در انتظار' },
          { key: 'submitted', label: 'تحویل داده' },
          { key: 'graded', label: 'نمره‌دهی شده' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: filter === tab.key ? 'white' : 'transparent',
              boxShadow: filter === tab.key ? 'var(--shadow-sm)' : 'none',
              color: filter === tab.key ? 'var(--primary-600)' : 'var(--gray-600)',
              fontWeight: filter === tab.key ? 500 : 400,
              border: 'none',
              cursor: 'pointer',
              transition: 'all var(--transition)'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Assignments Grid */}
      {filteredAssignments.length === 0 ? (
        <Card>
          <CardContent style={{ textAlign: 'center', padding: '3rem' }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 1rem', opacity: 0.4 }}>
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            <p style={{ color: 'var(--gray-500)', margin: 0 }}>
              {assignments.length === 0 
                ? 'هنوز تکلیفی برای شما تعریف نشده است' 
                : 'تکلیفی با این فیلتر یافت نشد'
              }
            </p>
            {assignments.length === 0 && (
              <p style={{ color: 'var(--gray-400)', fontSize: '0.875rem', margin: '0.5rem 0 0' }}>
                تکالیف پس از تعریف توسط معلم در این بخش نمایش داده می‌شوند
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem' }}>
          {filteredAssignments.map((assignment) => (
            <Card key={assignment.id} hover>
              <CardContent>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1rem' }}>{assignment.title}</h3>
                    <p style={{ margin: '0.25rem 0 0', color: 'var(--gray-500)', fontSize: '0.875rem' }}>
                      {assignment.class_name}
                    </p>
                  </div>
                  {getStatusBadge(assignment.status, assignment.score, assignment.max_score)}
                </div>
                
                {assignment.description && (
                  <p style={{ 
                    margin: '0 0 1rem', 
                    fontSize: '0.875rem', 
                    color: 'var(--gray-600)',
                    lineHeight: 1.6
                  }}>
                    {assignment.description.length > 100 
                      ? assignment.description.substring(0, 100) + '...' 
                      : assignment.description}
                  </p>
                )}
                
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '0.75rem',
                  background: 'var(--gray-50)',
                  borderRadius: 'var(--radius-md)'
                }}>
                  <div style={{ fontSize: '0.875rem' }}>
                    <span style={{ color: 'var(--gray-500)' }}>مهلت:</span>{' '}
                    <span style={{ fontWeight: 500 }}>{formatApiDate(assignment.due_date)}</span>
                  </div>
                  {assignment.status === 'pending' && !assignment.has_submitted && (
                    <Button size="small" onClick={() => handleOpenSubmitModal(assignment)}>
                      تحویل تکلیف
                    </Button>
                  )}
                  {assignment.status === 'graded' && assignment.score !== null && (
                    <div style={{ 
                      padding: '0.25rem 0.75rem', 
                      background: 'var(--success)', 
                      color: 'white', 
                      borderRadius: 'var(--radius)',
                      fontWeight: 600,
                      fontSize: '0.875rem'
                    }}>
                      نمره: {toPersianDigits(assignment.score)}/{toPersianDigits(assignment.max_score)}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Submit Modal */}
      <Modal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        title={`تحویل تکلیف - ${selectedAssignment?.title || ''}`}
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>توضیحات (اختیاری)</label>
            <textarea
              value={submissionText}
              onChange={(e) => setSubmissionText(e.target.value)}
              placeholder="توضیحات تکلیف..."
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

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>فایل تکلیف</label>
            <FileUpload
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.zip"
              maxSize={10 * 1024 * 1024}
              folder="assignments"
              targetModel="AssignmentSubmission"
              targetField="file"
              preview={false}
              label="آپلود فایل تکلیف"
              hint="PDF، Word، تصویر یا ZIP - حداکثر ۱۰ مگابایت"
              onUploadComplete={(result) => setSubmissionFile(result.key)}
              onUploadError={(err) => alert(err)}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowSubmitModal(false)}>انصراف</Button>
          <Button onClick={handleSubmit} loading={submitting}>ارسال تکلیف</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default StudentAssignments;

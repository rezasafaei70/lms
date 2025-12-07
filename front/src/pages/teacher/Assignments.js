import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Spinner, Modal, ModalFooter, Input, FileUpload, JalaliDatePicker } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { lmsAPI, coursesAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';

const TeacherAssignments = () => {
  const [assignments, setAssignments] = useState([]);
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAssignment, setEditingAssignment] = useState(null);
  const [attachmentKey, setAttachmentKey] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    class_obj: '',
    due_date: '',
    max_score: 100,
    instructions: '',
  });
  const [saving, setSaving] = useState(false);

  // Submissions & Grading state
  const [showSubmissionsModal, setShowSubmissionsModal] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const [showGradeModal, setShowGradeModal] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [gradeData, setGradeData] = useState({ score: '', feedback: '' });
  const [grading, setGrading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [assignmentsRes, classesRes] = await Promise.all([
        lmsAPI.getAssignments(),
        coursesAPI.getClasses({ status: 'ongoing' }),
      ]);
      setAssignments(assignmentsRes.data.results || []);
      setClasses(classesRes.data.results || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (assignment = null) => {
    if (assignment) {
      setEditingAssignment(assignment);
      setFormData({
        title: assignment.title || '',
        description: assignment.description || '',
        class_obj: assignment.class_obj || '',
        due_date: assignment.due_date ? assignment.due_date.split('T')[0] : '',
        max_score: assignment.max_score || 100,
        instructions: assignment.instructions || '',
      });
    } else {
      setEditingAssignment(null);
      setFormData({
        title: '',
        description: '',
        class_obj: '',
        due_date: '',
        max_score: 100,
        instructions: '',
      });
    }
    setAttachmentKey(null);
    setShowModal(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const data = { ...formData };
      
      if (data.max_score) data.max_score = parseInt(data.max_score);
      if (attachmentKey) data.attachment_s3_key = attachmentKey;
      
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
          delete data[key];
        }
      });

      if (editingAssignment) {
        await lmsAPI.updateAssignment(editingAssignment.id, data);
      } else {
        await lmsAPI.createAssignment(data);
      }
      setShowModal(false);
      fetchData();
    } catch (error) {
      console.error('Error saving assignment:', error);
      alert(error.response?.data?.detail || 'خطا در ذخیره تکلیف');
    } finally {
      setSaving(false);
    }
  };

  // Fetch submissions for an assignment
  const handleViewSubmissions = async (assignment) => {
    setSelectedAssignment(assignment);
    setShowSubmissionsModal(true);
    setLoadingSubmissions(true);
    
    try {
      const response = await lmsAPI.getSubmissions({ assignment: assignment.id });
      setSubmissions(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error fetching submissions:', error);
      setSubmissions([]);
    } finally {
      setLoadingSubmissions(false);
    }
  };

  // Open grade modal
  const handleOpenGradeModal = (submission) => {
    setSelectedSubmission(submission);
    setGradeData({
      score: submission.score || '',
      feedback: submission.feedback || ''
    });
    setShowGradeModal(true);
  };

  // Submit grade
  const handleGrade = async () => {
    if (!selectedSubmission || gradeData.score === '') {
      alert('لطفاً نمره را وارد کنید');
      return;
    }

    try {
      setGrading(true);
      await lmsAPI.gradeSubmission(selectedSubmission.id, {
        score: parseFloat(gradeData.score),
        feedback: gradeData.feedback
      });
      
      setShowGradeModal(false);
      // Refresh submissions
      handleViewSubmissions(selectedAssignment);
      alert('نمره با موفقیت ثبت شد');
    } catch (error) {
      console.error('Error grading:', error);
      alert(error.response?.data?.detail || 'خطا در ثبت نمره');
    } finally {
      setGrading(false);
    }
  };

  const getSubmissionStatusBadge = (submission) => {
    if (submission.status === 'graded') {
      return <Badge variant="success">نمره‌دهی شده</Badge>;
    } else if (submission.is_late) {
      return <Badge variant="error">تأخیر</Badge>;
    }
    return <Badge variant="warning">در انتظار نمره</Badge>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            تکلیف جدید
          </Button>
        }>
          <CardTitle>تکالیف</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Spinner size="large" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>عنوان</TableHead>
                  <TableHead>کلاس</TableHead>
                  <TableHead>مهلت</TableHead>
                  <TableHead>نمره کل</TableHead>
                  <TableHead>تحویل‌ها</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assignments.length === 0 ? (
                  <TableEmpty message="تکلیفی یافت نشد" />
                ) : (
                  assignments.map((assignment) => (
                    <TableRow key={assignment.id}>
                      <TableCell><strong>{assignment.title}</strong></TableCell>
                      <TableCell>{assignment.class_name || assignment.class_details?.name}</TableCell>
                      <TableCell>{formatApiDate(assignment.due_date)}</TableCell>
                      <TableCell>{toPersianDigits(assignment.max_score || 100)}</TableCell>
                      <TableCell>
                        <Button 
                          variant="secondary" 
                          size="small"
                          onClick={() => handleViewSubmissions(assignment)}
                        >
                          {toPersianDigits(assignment.submission_count || 0)} تحویل
                        </Button>
                      </TableCell>
                      <TableCell>
                        <Badge variant={assignment.is_published ? 'success' : 'default'}>
                          {assignment.is_published ? 'منتشر شده' : 'پیش‌نویس'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button 
                            onClick={() => handleViewSubmissions(assignment)}
                            style={{
                              padding: '0.5rem',
                              background: '#d1fae5',
                              border: 'none',
                              borderRadius: 'var(--radius)',
                              color: 'var(--success)',
                              cursor: 'pointer'
                            }}
                            title="مشاهده تحویل‌ها"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                              <polyline points="14 2 14 8 20 8" />
                              <line x1="16" y1="13" x2="8" y2="13" />
                              <line x1="16" y1="17" x2="8" y2="17" />
                            </svg>
                          </button>
                          <button 
                            onClick={() => handleOpenModal(assignment)}
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

      {/* Create/Edit Assignment Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingAssignment ? 'ویرایش تکلیف' : 'تکلیف جدید'}
        size="medium"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="عنوان تکلیف *"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="مثال: تمرینات فصل ۳"
          />
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>کلاس *</label>
            <select
              value={formData.class_obj}
              onChange={(e) => setFormData({ ...formData, class_obj: e.target.value })}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                background: 'white'
              }}
            >
              <option value="">انتخاب کلاس...</option>
              {classes.map(cls => (
                <option key={cls.id} value={cls.id}>{cls.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>توضیحات</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="توضیحات تکلیف..."
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

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <JalaliDatePicker
              label="مهلت تحویل *"
              value={formData.due_date}
              onChange={(date) => setFormData({ ...formData, due_date: date })}
              placeholder="انتخاب تاریخ"
            />
            <Input
              label="نمره کل"
              type="number"
              value={formData.max_score}
              onChange={(e) => setFormData({ ...formData, max_score: e.target.value })}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>فایل پیوست (اختیاری)</label>
            <FileUpload
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.zip"
              maxSize={10 * 1024 * 1024}
              folder="teacher-assignments"
              targetModel="Assignment"
              targetField="attachment"
              preview={false}
              label="آپلود فایل"
              hint="PDF، Word، تصویر یا ZIP - حداکثر ۱۰ مگابایت"
              previewUrl={editingAssignment?.attachment_url}
              onUploadComplete={(result) => setAttachmentKey(result.key)}
              onUploadError={(err) => alert(err)}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowModal(false)}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingAssignment ? 'ذخیره تغییرات' : 'ایجاد تکلیف'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Submissions Modal */}
      <Modal
        isOpen={showSubmissionsModal}
        onClose={() => setShowSubmissionsModal(false)}
        title={`تحویل‌های تکلیف: ${selectedAssignment?.title || ''}`}
        size="large"
      >
        {loadingSubmissions ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Spinner size="large" />
          </div>
        ) : submissions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-500)' }}>
            هنوز تحویلی ثبت نشده است
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>دانش‌آموز</TableHead>
                <TableHead>تاریخ تحویل</TableHead>
                <TableHead>فایل</TableHead>
                <TableHead>نمره</TableHead>
                <TableHead>وضعیت</TableHead>
                <TableHead>عملیات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {submissions.map((submission) => (
                <TableRow key={submission.id}>
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
                        {submission.student_details?.first_name?.[0] || '?'}
                      </div>
                      <strong>
                        {submission.student_details?.first_name} {submission.student_details?.last_name}
                      </strong>
                    </div>
                  </TableCell>
                  <TableCell>{formatApiDate(submission.submitted_at)}</TableCell>
                  <TableCell>
                    {submission.attachment_url ? (
                      <a 
                        href={submission.attachment_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ color: 'var(--primary-600)' }}
                      >
                        دانلود فایل
                      </a>
                    ) : submission.text_content ? (
                      <span style={{ color: 'var(--gray-500)' }}>متنی</span>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    {submission.score !== null && submission.score !== undefined ? (
                      <strong style={{ color: 'var(--success)' }}>
                        {toPersianDigits(submission.score)}/{toPersianDigits(selectedAssignment?.max_score || 100)}
                      </strong>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>{getSubmissionStatusBadge(submission)}</TableCell>
                  <TableCell>
                    <Button 
                      size="small" 
                      variant={submission.status === 'graded' ? 'secondary' : 'primary'}
                      onClick={() => handleOpenGradeModal(submission)}
                    >
                      {submission.status === 'graded' ? 'ویرایش نمره' : 'نمره‌دهی'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowSubmissionsModal(false)}>بستن</Button>
        </ModalFooter>
      </Modal>

      {/* Grade Modal */}
      <Modal
        isOpen={showGradeModal}
        onClose={() => setShowGradeModal(false)}
        title="نمره‌دهی تکلیف"
        size="small"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {selectedSubmission && (
            <div style={{ 
              padding: '1rem', 
              background: 'var(--gray-50)', 
              borderRadius: 'var(--radius-md)',
              marginBottom: '0.5rem'
            }}>
              <strong>دانش‌آموز: </strong>
              {selectedSubmission.student_details?.first_name} {selectedSubmission.student_details?.last_name}
            </div>
          )}

          {selectedSubmission?.text_content && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>پاسخ دانش‌آموز:</label>
              <div style={{ 
                padding: '0.75rem', 
                background: 'var(--gray-50)', 
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                maxHeight: '150px',
                overflowY: 'auto'
              }}>
                {selectedSubmission.text_content}
              </div>
            </div>
          )}

          <Input
            label={`نمره (از ${selectedAssignment?.max_score || 100}) *`}
            type="number"
            min="0"
            max={selectedAssignment?.max_score || 100}
            value={gradeData.score}
            onChange={(e) => setGradeData({ ...gradeData, score: e.target.value })}
            placeholder="مثال: 85"
          />

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>بازخورد (اختیاری)</label>
            <textarea
              value={gradeData.feedback}
              onChange={(e) => setGradeData({ ...gradeData, feedback: e.target.value })}
              placeholder="نظر شما درباره تکلیف..."
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
          <Button variant="secondary" onClick={() => setShowGradeModal(false)}>انصراف</Button>
          <Button onClick={handleGrade} loading={grading}>ثبت نمره</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};

export default TeacherAssignments;

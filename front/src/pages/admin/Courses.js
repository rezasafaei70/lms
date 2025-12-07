import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Modal, ModalFooter, Badge, Spinner, FileUpload } from '../../components/common';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '../../components/common';
import { coursesAPI } from '../../services/api';
import { formatApiDate, toPersianDigits } from '../../utils/jalaliDate';


const AdminCourses = () => {
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);
  const [deletingCourse, setDeletingCourse] = useState(null);
  const [viewingCourse, setViewingCourse] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [thumbnailKey, setThumbnailKey] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    slug: '',
    description: '',
    short_description: '',
    level: 'beginner',
    duration_hours: '',
    sessions_count: '',
    base_price: '',
    status: 'draft',
    syllabus: '',
    learning_outcomes: '',
    required_materials: '',
    subjects: [],
    prerequisites: [],
    min_students: 5,
    max_students: 20,
    is_featured: false,
    provides_certificate: true,
    meta_description: '',
    meta_keywords: '',
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [coursesRes, subjectsRes] = await Promise.all([
        coursesAPI.list(),
        coursesAPI.getSubjects(),
      ]);
      setCourses(coursesRes.data.results || []);
      setSubjects(subjectsRes.data.results || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Generate slug from name
  const generateSlug = (name) => {
    return name
      .trim()
      .replace(/\s+/g, '-')
      .replace(/[^\u0600-\u06FF\w-]/g, '')
      .toLowerCase();
  };

  const handleOpenModal = (course = null) => {
    if (course) {
      setEditingCourse(course);
      setFormData({
        name: course.name || '',
        code: course.code || '',
        slug: course.slug || '',
        description: course.description || '',
        short_description: course.short_description || '',
        level: course.level || 'beginner',
        duration_hours: course.duration_hours || '',
        sessions_count: course.sessions_count || '',
        base_price: course.base_price || '',
        status: course.status || 'draft',
        syllabus: course.syllabus || '',
        learning_outcomes: course.learning_outcomes || '',
        required_materials: course.required_materials || '',
        subjects: course.subjects?.map(s => s.id || s) || [],
        prerequisites: course.prerequisites?.map(p => p.id || p) || [],
        min_students: course.min_students || 5,
        max_students: course.max_students || 20,
        is_featured: course.is_featured || false,
        provides_certificate: course.provides_certificate !== false,
        meta_description: course.meta_description || '',
        meta_keywords: course.meta_keywords || '',
      });
      setThumbnailKey(null);
    } else {
      setEditingCourse(null);
      setFormData({
        name: '',
        code: '',
        slug: '',
        description: '',
        short_description: '',
        level: 'beginner',
        duration_hours: '',
        sessions_count: '',
        base_price: '',
        status: 'draft',
        syllabus: '',
        learning_outcomes: '',
        required_materials: '',
        subjects: [],
        prerequisites: [],
        min_students: 5,
        max_students: 20,
        is_featured: false,
        provides_certificate: true,
        meta_description: '',
        meta_keywords: '',
      });
      setThumbnailKey(null);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingCourse(null);
    setThumbnailKey(null);
  };

  const handleViewDetails = (course) => {
    setViewingCourse(course);
    setShowDetailModal(true);
  };

  const handleNameChange = (e) => {
    const name = e.target.value;
    setFormData(prev => ({
      ...prev,
      name,
      slug: prev.slug || generateSlug(name)
    }));
  };

  const handleSubjectToggle = (subjectId) => {
    const currentSubjects = formData.subjects;
    const newSubjects = currentSubjects.includes(subjectId)
      ? currentSubjects.filter(s => s !== subjectId)
      : [...currentSubjects, subjectId];
    setFormData({ ...formData, subjects: newSubjects });
  };

  const handlePrerequisiteToggle = (courseId) => {
    const current = formData.prerequisites;
    const newPrerequisites = current.includes(courseId)
      ? current.filter(c => c !== courseId)
      : [...current, courseId];
    setFormData({ ...formData, prerequisites: newPrerequisites });
  };

  const handleSave = async () => {
    // Validate required fields
    if (!formData.name || !formData.description || !formData.short_description || 
        !formData.syllabus || !formData.learning_outcomes || formData.subjects.length === 0 ||
        !formData.duration_hours || !formData.sessions_count || !formData.base_price) {
      alert('لطفاً تمام فیلدهای ضروری را پر کنید');
      return;
    }

    try {
      setSaving(true);
      const data = { ...formData };
      
      // Generate slug if empty
      if (!data.slug) {
        data.slug = generateSlug(data.name);
      }
      
      // Add thumbnail key if uploaded
      if (thumbnailKey) {
        data.thumbnail_id = thumbnailKey;
      }
      
      // Convert numbers
      if (data.duration_hours) data.duration_hours = parseInt(data.duration_hours);
      if (data.sessions_count) data.sessions_count = parseInt(data.sessions_count);
      if (data.base_price) data.base_price = parseInt(data.base_price);
      if (data.min_students) data.min_students = parseInt(data.min_students);
      if (data.max_students) data.max_students = parseInt(data.max_students);
      
      // Ensure arrays
      if (!Array.isArray(data.subjects)) data.subjects = [];
      if (!Array.isArray(data.prerequisites)) data.prerequisites = [];
      
      // Remove empty values (but keep empty arrays and false booleans)
      Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
          delete data[key];
        }
      });

      if (editingCourse) {
        // Use slug for update since backend uses lookup_field='slug'
        await coursesAPI.update(editingCourse.slug, data);
      } else {
        await coursesAPI.create(data);
      }
      handleCloseModal();
      fetchData();
    } catch (error) {
      console.error('Error saving course:', error);
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message ||
                          JSON.stringify(error.response?.data?.details) ||
                          'خطا در ذخیره دوره';
      alert(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (course) => {
    setDeletingCourse(course);
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!deletingCourse) return;
    
    try {
      setDeleting(true);
      // Use slug for delete since backend uses lookup_field='slug'
      await coursesAPI.delete(deletingCourse.slug);
      setShowDeleteModal(false);
      setDeletingCourse(null);
      fetchData();
    } catch (error) {
      console.error('Error deleting course:', error);
      alert(error.response?.data?.detail || 'خطا در حذف دوره');
    } finally {
      setDeleting(false);
    }
  };

  const getLevelName = (level) => {
    const levels = {
      beginner: 'مبتدی',
      elementary: 'ابتدایی',
      pre_intermediate: 'پیش متوسط',
      intermediate: 'متوسط',
      upper_intermediate: 'فوق متوسط',
      advanced: 'پیشرفته',
      proficiency: 'تخصصی',
    };
    return levels[level] || level;
  };

  const getLevelVariant = (level) => {
    const variants = {
      beginner: 'success',
      elementary: 'success',
      pre_intermediate: 'info',
      intermediate: 'warning',
      upper_intermediate: 'warning',
      advanced: 'error',
      proficiency: 'primary',
    };
    return variants[level] || 'default';
  };

  const getStatusName = (status) => {
    const names = {
      active: 'فعال',
      inactive: 'غیرفعال',
      draft: 'پیش‌نویس',
      archived: 'بایگانی شده',
    };
    return names[status] || status;
  };

  const getStatusVariant = (status) => {
    const variants = {
      active: 'success',
      inactive: 'error',
      draft: 'warning',
      archived: 'default',
    };
    return variants[status] || 'default';
  };

  const filteredCourses = courses.filter(course => {
    const matchesFilter = filter === 'all' || course.level === filter || course.status === filter;
    const matchesSearch = search === '' || 
      course.name?.toLowerCase().includes(search.toLowerCase()) ||
      course.code?.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="courses-page">
      <Card>
        <CardHeader action={
          <Button onClick={() => handleOpenModal()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            دوره جدید
          </Button>
        }>
          <CardTitle>مدیریت دوره‌ها</CardTitle>
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
                { key: 'active', label: 'فعال' },
                { key: 'draft', label: 'پیش‌نویس' },
                { key: 'beginner', label: 'مبتدی' },
                { key: 'intermediate', label: 'متوسط' },
                { key: 'advanced', label: 'پیشرفته' },
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
                placeholder="جستجوی دوره..."
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
                  <TableHead>تصویر</TableHead>
                  <TableHead>کد</TableHead>
                  <TableHead>نام دوره</TableHead>
                  <TableHead>سطح</TableHead>
                  <TableHead>مدت (ساعت)</TableHead>
                  <TableHead>قیمت پایه</TableHead>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCourses.length === 0 ? (
                  <TableEmpty message="دوره‌ای یافت نشد" />
                ) : (
                  filteredCourses.map((course) => (
                    <TableRow key={course.id}>
                      <TableCell>
                        <div style={{ width: '48px', height: '48px', borderRadius: 'var(--radius)', overflow: 'hidden', background: 'var(--gray-100)' }}>
                          {course.thumbnail_url || course.thumbnail ? (
                            <img src={course.thumbnail_url || course.thumbnail} alt={course.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          ) : (
                            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--gray-400)' }}>
                              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
                              </svg>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell><code style={{ background: 'var(--gray-100)', padding: '0.25rem 0.5rem', borderRadius: 'var(--radius)' }}>{course.code}</code></TableCell>
                      <TableCell>
                        <div>
                          <strong>{course.name}</strong>
                          {course.short_description && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
                              {course.short_description.substring(0, 50)}...
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getLevelVariant(course.level)}>{getLevelName(course.level)}</Badge>
                      </TableCell>
                      <TableCell>{course.duration_hours ? toPersianDigits(course.duration_hours) : '-'}</TableCell>
                      <TableCell>
                        {course.base_price ? `${toPersianDigits(parseInt(course.base_price).toLocaleString())} تومان` : '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(course.status)}>
                          {getStatusName(course.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button 
                            onClick={() => handleViewDetails(course)}
                            style={{
                              padding: '0.5rem',
                              background: '#d1fae5',
                              border: 'none',
                              borderRadius: 'var(--radius)',
                              color: 'var(--success)',
                              cursor: 'pointer'
                            }}
                            title="مشاهده جزئیات"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          </button>
                          <button 
                            onClick={() => handleOpenModal(course)}
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
                            onClick={() => handleDeleteClick(course)}
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
        title={editingCourse ? 'ویرایش دوره' : 'دوره جدید'}
        size="large"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxHeight: '70vh', overflowY: 'auto', padding: '0.5rem' }}>
          {/* Thumbnail Upload */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>تصویر شاخص</h4>
            <FileUpload
              accept="image/*"
              maxSize={5 * 1024 * 1024}
              folder="courses"
              targetModel="Course"
              targetField="thumbnail"
              preview={true}
              previewUrl={editingCourse?.thumbnail_url || editingCourse?.thumbnail}
              label="آپلود تصویر"
              hint="حداکثر ۵ مگابایت - JPG, PNG"
              onUploadComplete={(result) => setThumbnailKey(result.id)}
              onUploadError={(err) => alert(err)}
            />
          </div>

          {/* Basic Info */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>اطلاعات اصلی *</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <Input
                label="نام دوره *"
                value={formData.name}
                onChange={handleNameChange}
                placeholder="مثال: ریاضیات پایه هشتم"
              />
              <Input
                label="کد دوره"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                placeholder="خالی بگذارید تا خودکار تولید شود"
              />
            </div>
            <div style={{ marginTop: '1rem' }}>
              <Input
                label="اسلاگ (URL)"
                value={formData.slug}
                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                placeholder="ریاضیات-پایه-هشتم"
                hint="اسلاگ برای URL استفاده می‌شود"
              />
            </div>
          </div>

          {/* Subjects Selection */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>درس‌های دوره * (حداقل یک درس انتخاب کنید)</h4>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {subjects.length === 0 ? (
                <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>درسی تعریف نشده است</p>
              ) : (
                subjects.map(subject => (
                  <button
                    key={subject.id}
                    type="button"
                    onClick={() => handleSubjectToggle(subject.id)}
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      border: formData.subjects.includes(subject.id) 
                        ? '2px solid var(--primary-500)' 
                        : '2px solid var(--gray-200)',
                      background: formData.subjects.includes(subject.id) 
                        ? 'var(--primary-50)' 
                        : 'white',
                      color: formData.subjects.includes(subject.id) 
                        ? 'var(--primary-600)' 
                        : 'var(--gray-600)',
                      cursor: 'pointer',
                      fontWeight: 500,
                      fontSize: '0.875rem',
                      transition: 'all var(--transition)'
                    }}
                  >
                    {subject.title}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Level & Status */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>سطح دوره *</label>
              <select
                value={formData.level}
                onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--gray-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  background: 'white'
                }}
              >
                <option value="beginner">مبتدی</option>
                <option value="elementary">ابتدایی</option>
                <option value="pre_intermediate">پیش متوسط</option>
                <option value="intermediate">متوسط</option>
                <option value="upper_intermediate">فوق متوسط</option>
                <option value="advanced">پیشرفته</option>
                <option value="proficiency">تخصصی</option>
              </select>
            </div>
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
                <option value="draft">پیش‌نویس</option>
                <option value="active">فعال</option>
                <option value="inactive">غیرفعال</option>
                <option value="archived">بایگانی شده</option>
              </select>
            </div>
          </div>

          {/* Descriptions */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>توضیحات *</h4>
            <Input
              label="توضیح کوتاه (حداکثر ۵۰۰ کاراکتر) *"
              value={formData.short_description}
              onChange={(e) => setFormData({ ...formData, short_description: e.target.value })}
              placeholder="یک خلاصه کوتاه از دوره..."
            />
            <div style={{ marginTop: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>توضیحات کامل *</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="توضیحات کامل درباره دوره..."
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

          {/* Duration & Price */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <Input
              label="مدت دوره (ساعت) *"
              type="number"
              value={formData.duration_hours}
              onChange={(e) => setFormData({ ...formData, duration_hours: e.target.value })}
              placeholder="مثال: 40"
            />
            <Input
              label="تعداد جلسات *"
              type="number"
              value={formData.sessions_count}
              onChange={(e) => setFormData({ ...formData, sessions_count: e.target.value })}
              placeholder="مثال: 20"
            />
            <Input
              label="قیمت پایه (تومان) *"
              type="number"
              value={formData.base_price}
              onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
              placeholder="مثال: 2000000"
            />
          </div>

          {/* Capacity */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="حداقل دانش‌آموز"
              type="number"
              value={formData.min_students}
              onChange={(e) => setFormData({ ...formData, min_students: e.target.value })}
            />
            <Input
              label="حداکثر دانش‌آموز"
              type="number"
              value={formData.max_students}
              onChange={(e) => setFormData({ ...formData, max_students: e.target.value })}
            />
          </div>

          {/* Syllabus & Learning Outcomes */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>سرفصل‌ها و اهداف *</h4>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>سرفصل‌ها *</label>
              <textarea
                value={formData.syllabus}
                onChange={(e) => setFormData({ ...formData, syllabus: e.target.value })}
                placeholder="سرفصل‌های دوره را بنویسید...&#10;- فصل اول: مقدمه&#10;- فصل دوم: ..."
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
            <div style={{ marginTop: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>اهداف یادگیری *</label>
              <textarea
                value={formData.learning_outcomes}
                onChange={(e) => setFormData({ ...formData, learning_outcomes: e.target.value })}
                placeholder="چه چیزهایی در این دوره یاد می‌گیرید...&#10;- یادگیری مبانی...&#10;- توانایی حل..."
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
          </div>

          {/* Materials */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem' }}>مواد و کتب مورد نیاز</label>
            <textarea
              value={formData.required_materials}
              onChange={(e) => setFormData({ ...formData, required_materials: e.target.value })}
              placeholder="کتاب‌ها و مواد مورد نیاز..."
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

          {/* Prerequisites */}
          {courses.length > 0 && editingCourse && (
            <div>
              <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>پیش‌نیازها (اختیاری)</h4>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {courses.filter(c => c.id !== editingCourse?.id).map(course => (
                  <button
                    key={course.id}
                    type="button"
                    onClick={() => handlePrerequisiteToggle(course.id)}
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      border: formData.prerequisites.includes(course.id) 
                        ? '2px solid var(--info)' 
                        : '2px solid var(--gray-200)',
                      background: formData.prerequisites.includes(course.id) 
                        ? '#dbeafe' 
                        : 'white',
                      color: formData.prerequisites.includes(course.id) 
                        ? '#2563eb' 
                        : 'var(--gray-600)',
                      cursor: 'pointer',
                      fontWeight: 500,
                      fontSize: '0.8125rem',
                      transition: 'all var(--transition)'
                    }}
                  >
                    {course.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Options */}
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.is_featured}
                onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })}
              />
              <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>دوره ویژه</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.provides_certificate}
                onChange={(e) => setFormData({ ...formData, provides_certificate: e.target.checked })}
              />
              <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>دارای گواهینامه</span>
            </label>
          </div>

          {/* SEO */}
          <div>
            <h4 style={{ margin: '0 0 1rem', color: 'var(--gray-700)', fontSize: '0.875rem' }}>سئو (اختیاری)</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <Input
                label="توضیحات متا"
                value={formData.meta_description}
                onChange={(e) => setFormData({ ...formData, meta_description: e.target.value })}
                placeholder="توضیحات متا برای موتورهای جستجو"
              />
              <Input
                label="کلمات کلیدی"
                value={formData.meta_keywords}
                onChange={(e) => setFormData({ ...formData, meta_keywords: e.target.value })}
                placeholder="کلمات کلیدی جدا شده با کاما"
              />
            </div>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={handleCloseModal}>انصراف</Button>
          <Button onClick={handleSave} loading={saving}>
            {editingCourse ? 'ذخیره تغییرات' : 'ایجاد دوره'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Course Details Modal */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        title={`جزئیات دوره - ${viewingCourse?.name || ''}`}
        size="large"
      >
        {viewingCourse && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxHeight: '70vh', overflowY: 'auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              {(viewingCourse.thumbnail_url || viewingCourse.thumbnail) && (
                <img 
                  src={viewingCourse.thumbnail_url || viewingCourse.thumbnail} 
                  alt={viewingCourse.name}
                  style={{ width: '150px', height: '100px', objectFit: 'cover', borderRadius: 'var(--radius-md)' }}
                />
              )}
              <div style={{ flex: 1 }}>
                <h2 style={{ margin: '0 0 0.5rem' }}>{viewingCourse.name}</h2>
                <p style={{ margin: '0', color: 'var(--gray-600)' }}>{viewingCourse.short_description}</p>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                  <Badge variant={getLevelVariant(viewingCourse.level)}>{getLevelName(viewingCourse.level)}</Badge>
                  <Badge variant={getStatusVariant(viewingCourse.status)}>{getStatusName(viewingCourse.status)}</Badge>
                  {viewingCourse.is_featured && <Badge variant="primary">ویژه</Badge>}
                </div>
              </div>
            </div>

            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-600)' }}>{toPersianDigits(viewingCourse.duration_hours || 0)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-500)' }}>ساعت</div>
              </div>
              <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-600)' }}>{toPersianDigits(viewingCourse.sessions_count || 0)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-500)' }}>جلسه</div>
              </div>
              <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{toPersianDigits(viewingCourse.total_enrollments || 0)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-500)' }}>ثبت‌نام</div>
              </div>
              <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--warning)' }}>{toPersianDigits(parseInt(viewingCourse.base_price || 0).toLocaleString())}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--gray-500)' }}>تومان</div>
              </div>
            </div>

            {/* Description */}
            <div>
              <h4 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>توضیحات</h4>
              <p style={{ margin: 0, color: 'var(--gray-600)', whiteSpace: 'pre-line' }}>{viewingCourse.description}</p>
            </div>

            {/* Syllabus */}
            {viewingCourse.syllabus && (
              <div>
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>سرفصل‌ها</h4>
                <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', whiteSpace: 'pre-line' }}>
                  {viewingCourse.syllabus}
                </div>
              </div>
            )}

            {/* Learning Outcomes */}
            {viewingCourse.learning_outcomes && (
              <div>
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>اهداف یادگیری</h4>
                <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', whiteSpace: 'pre-line' }}>
                  {viewingCourse.learning_outcomes}
                </div>
              </div>
            )}

            {/* Subjects */}
            {viewingCourse.subjects_details && viewingCourse.subjects_details.length > 0 && (
              <div>
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>درس‌ها</h4>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {viewingCourse.subjects_details.map(subject => (
                    <Badge key={subject.id} variant="info">{subject.title}</Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Dates */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>تاریخ ایجاد</h4>
                <p style={{ margin: 0 }}>{formatApiDate(viewingCourse.created_at)}</p>
              </div>
              <div>
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--gray-700)' }}>آخرین بروزرسانی</h4>
                <p style={{ margin: 0 }}>{formatApiDate(viewingCourse.updated_at)}</p>
              </div>
            </div>
          </div>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowDetailModal(false)}>بستن</Button>
          <Button onClick={() => { setShowDetailModal(false); handleOpenModal(viewingCourse); }}>ویرایش</Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="حذف دوره"
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
            دوره <strong>{deletingCourse?.name}</strong> حذف خواهد شد.
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

export default AdminCourses;

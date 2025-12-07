import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://185.208.175.44:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Skip token refresh for auth endpoints
    const isAuthEndpoint = originalRequest.url?.includes('/auth/');
    
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/accounts/auth/refresh-token/`, {
            refresh: refreshToken,
          });
          
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Only redirect to login if refresh token is also invalid
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('selected_branch');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// ==================== AUTH API ====================
export const authAPI = {
  sendOTP: (nationalCode) => 
    api.post('/accounts/auth/send-otp/', { national_code: nationalCode, purpose: 'login' }),
  
  login: (nationalCode, code) => 
    api.post('/accounts/auth/login/', { national_code: nationalCode, code }),
  
  logout: () => 
    api.post('/accounts/auth/logout/'),
  
  refreshToken: (refresh) => 
    api.post('/accounts/auth/refresh-token/', { refresh }),
  
  me: () => 
    api.get('/accounts/auth/me/'),
  
  changePassword: (oldPassword, newPassword, newPasswordConfirm) =>
    api.post('/accounts/auth/change-password/', { 
      old_password: oldPassword, 
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm 
    }),
};

// ==================== USERS API ====================
export const usersAPI = {
  list: (params) => api.get('/accounts/users/', { params }),
  get: (id) => api.get(`/accounts/users/${id}/`),
  create: (data) => api.post('/accounts/users/', data),
  update: (id, data) => api.patch(`/accounts/users/${id}/`, data),
  delete: (id) => api.delete(`/accounts/users/${id}/`),
  getStudents: (params) => api.get('/accounts/students/', { params }),
  searchStudents: (query) => api.get('/accounts/students/', { params: { search: query || '', page_size: 20, ordering: '-created_at' } }),
  searchUsers: (query, role = null) => api.get('/accounts/users/', { params: { search: query, role, page_size: 20 } }),
  getTeachers: (params) => api.get('/accounts/teachers/', { params }),
  searchTeachers: (query) => api.get('/accounts/teachers/', { params: { search: query, page_size: 20 } }),
  getStudent: (id) => api.get(`/accounts/students/${id}/`),
  getTeacher: (id) => api.get(`/accounts/teachers/${id}/`),
  updateStudent: (id, data) => api.patch(`/accounts/students/${id}/`, data),
  updateTeacher: (id, data) => api.patch(`/accounts/teachers/${id}/`, data),
};

// ==================== BRANCHES API ====================
export const branchesAPI = {
  list: (params) => api.get('/branches/branches/', { params }),
  get: (id) => api.get(`/branches/branches/${id}/`),
  create: (data) => {
    // Check if data is FormData (for file upload)
    if (data instanceof FormData) {
      return api.post('/branches/branches/', data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    return api.post('/branches/branches/', data);
  },
  update: (id, data) => {
    // Check if data is FormData (for file upload)
    if (data instanceof FormData) {
      return api.patch(`/branches/branches/${id}/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    return api.patch(`/branches/branches/${id}/`, data);
  },
  delete: (id) => api.delete(`/branches/branches/${id}/`),
  getStats: (id) => api.get(`/branches/branches/${id}/statistics/`),
  getActive: () => api.get('/branches/branches/active/'),
  
  // Classrooms
  getClassrooms: (params) => api.get('/branches/classrooms/', { params }),
  getClassroom: (id) => api.get(`/branches/classrooms/${id}/`),
  createClassroom: (data) => api.post('/branches/classrooms/', data),
  updateClassroom: (id, data) => api.patch(`/branches/classrooms/${id}/`, data),
  deleteClassroom: (id) => api.delete(`/branches/classrooms/${id}/`),
  
  // Staff
  getStaff: (params) => api.get('/branches/staff/', { params }),
  addStaff: (data) => api.post('/branches/staff/', data),
  updateStaff: (id, data) => api.patch(`/branches/staff/${id}/`, data),
  removeStaff: (id) => api.delete(`/branches/staff/${id}/`),
};

// ==================== COURSES API ====================
export const coursesAPI = {
  list: (params) => api.get('/courses/courses/', { params }),
  get: (id) => api.get(`/courses/courses/${id}/`),
  create: (data) => api.post('/courses/courses/', data),
  update: (id, data) => api.patch(`/courses/courses/${id}/`, data),
  delete: (id) => api.delete(`/courses/courses/${id}/`),
  
  // Subjects (درس‌ها)
  getSubjects: (params) => api.get('/courses/subjects/', { params }),
  getSubject: (id) => api.get(`/courses/subjects/${id}/`),
  createSubject: (data) => api.post('/courses/subjects/', data),
  updateSubject: (id, data) => api.patch(`/courses/subjects/${id}/`, data),
  deleteSubject: (id) => api.delete(`/courses/subjects/${id}/`),
  
  // Classes
  getClasses: (params) => api.get('/courses/classes/', { params }),
  getClass: (id) => api.get(`/courses/classes/${id}/`),
  createClass: (data) => api.post('/courses/classes/', data),
  updateClass: (id, data) => api.patch(`/courses/classes/${id}/`, data),
  deleteClass: (id) => api.delete(`/courses/classes/${id}/`),
  getClassStudents: (id) => api.get(`/courses/classes/${id}/students/`),
  
  // Sessions
  getSessions: (params) => api.get('/courses/sessions/', { params }),
  getClassSessions: (classId) => api.get(`/courses/classes/${classId}/sessions/`),
  generateClassSessions: (classId) => api.post(`/courses/classes/${classId}/generate-sessions/`),
  getSession: (id) => api.get(`/courses/sessions/${id}/`),
  createSession: (data) => api.post('/courses/sessions/', data),
  updateSession: (id, data) => api.patch(`/courses/sessions/${id}/`, data),
  deleteSession: (id) => api.delete(`/courses/sessions/${id}/`),
  
  // Online Classes
  getBBBJoinUrl: (classId) => api.get(`/courses/classes/${classId}/bbb-join-url/`),
  
  // Terms
  getTerms: (params) => api.get('/courses/terms/', { params }),
  getTerm: (id) => api.get(`/courses/terms/${id}/`),
  createTerm: (data) => api.post('/courses/terms/', data),
  updateTerm: (id, data) => api.patch(`/courses/terms/${id}/`, data),
  
  // Reviews
  getReviews: (params) => api.get('/courses/reviews/', { params }),
};

// ==================== ENROLLMENTS API ====================
export const enrollmentsAPI = {
  list: (params) => api.get('/enrollments/enrollments/', { params }),
  get: (id) => api.get(`/enrollments/enrollments/${id}/`),
  create: (data) => api.post('/enrollments/enrollments/', data),
  update: (id, data) => api.patch(`/enrollments/enrollments/${id}/`, data),
  cancel: (id) => api.post(`/enrollments/enrollments/${id}/cancel/`),
  getMyEnrollments: () => api.get('/enrollments/enrollments/my-enrollments/'),
  
  // Waiting List
  getWaitingList: (params) => api.get('/enrollments/waiting-lists/', { params }),
  addToWaitingList: (data) => api.post('/enrollments/waiting-lists/', data),
  
  // Placement Tests
  getPlacementTests: (params) => api.get('/enrollments/placement-tests/', { params }),
  
  // Annual Registration
  getAnnualRegistrations: (params) => api.get('/enrollments/annual-registrations/', { params }),
  createAnnualRegistration: (data) => api.post('/enrollments/annual-registrations/', data),
};

// ==================== ATTENDANCE API ====================
export const attendanceAPI = {
  list: (params) => api.get('/attendance/attendances/', { params }),
  get: (id) => api.get(`/attendance/attendances/${id}/`),
  create: (data) => api.post('/attendance/attendances/', data),
  update: (id, data) => api.patch(`/attendance/attendances/${id}/`, data),
  bulkRecord: (data) => api.post('/attendance/attendances/bulk-record/', data),
  getBySession: (sessionId) => api.get(`/attendance/attendances/session/${sessionId}/`),
  getMyAttendance: () => api.get('/attendance/attendances/my-attendance/'),
  getMySummary: (enrollmentId) => api.get('/attendance/attendances/my-summary/', { params: { enrollment: enrollmentId } }),
  markExcused: (id, data) => api.post(`/attendance/attendances/${id}/mark-excused/`, data),
  
  // Reports
  getReports: (params) => api.get('/attendance/reports/', { params }),
  getClassSummary: (classId) => api.get(`/attendance/reports/class-summary/${classId}/`),
};

// ==================== FINANCIAL API ====================
export const financialAPI = {
  // Invoices
  getInvoices: (params) => api.get('/financial/invoices/', { params }),
  getInvoice: (id) => api.get(`/financial/invoices/${id}/`),
  createInvoice: (data) => api.post('/financial/invoices/create-invoice/', data),
  getMyInvoices: () => api.get('/financial/invoices/my-invoices/'),
  
  // Payments
  getPayments: (params) => api.get('/financial/payments/', { params }),
  getPayment: (id) => api.get(`/financial/payments/${id}/`),
  createPayment: (data) => api.post('/financial/payments/', data),
  verifyPayment: (id, data) => api.post(`/financial/payments/${id}/verify/`, data),
  
  // Coupons
  getCoupons: (params) => api.get('/financial/coupons/', { params }),
  validateCoupon: (code, userId, amount) => 
    api.post('/financial/coupons/validate/', { code, user_id: userId, amount }),
  
  // Transactions
  getTransactions: (params) => api.get('/financial/transactions/', { params }),
  createTransaction: (data) => api.post('/financial/transactions/', data),
  
  // Reports
  getReport: (params) => api.get('/financial/reports/summary/', { params }),
  getBranchReport: (branchId, params) => 
    api.get(`/financial/reports/branch/${branchId}/`, { params }),
  
  // Credit
  getCredit: (userId) => api.get(`/financial/credit/${userId}/`),
  addCredit: (userId, data) => api.post(`/financial/credit/${userId}/add/`, data),
  getMyCredit: () => api.get('/financial/credit/my-credit/'),
  getMyBalance: () => api.get('/financial/credit/my-balance/'),
  
  // Sadad Payment Gateway
  initiatePayment: (invoiceId) => api.post('/financial/payment/initiate/', { invoice_id: invoiceId }),
  verifyPaymentStatus: (invoiceId) => api.get(`/financial/payment/verify/${invoiceId}/`),
};

// ==================== LMS API ====================
export const lmsAPI = {
  // Materials
  getMaterials: (params) => api.get('/lms/materials/', { params }),
  getMaterial: (id) => api.get(`/lms/materials/${id}/`),
  createMaterial: (data) => api.post('/lms/materials/', data),
  updateMaterial: (id, data) => api.patch(`/lms/materials/${id}/`, data),
  deleteMaterial: (id) => api.delete(`/lms/materials/${id}/`),
  downloadMaterial: (id) => api.get(`/lms/materials/${id}/download/`),
  
  // Assignments
  getAssignments: (params) => api.get('/lms/assignments/', { params }),
  getAssignment: (id) => api.get(`/lms/assignments/${id}/`),
  createAssignment: (data) => api.post('/lms/assignments/', data),
  updateAssignment: (id, data) => api.patch(`/lms/assignments/${id}/`, data),
  deleteAssignment: (id) => api.delete(`/lms/assignments/${id}/`),
  getMyAssignments: () => api.get('/lms/assignments/my-assignments/'),
  getUpcomingAssignments: () => api.get('/lms/assignments/upcoming/'),
  
  // Submissions
  getSubmissions: (params) => api.get('/lms/submissions/', { params }),
  getSubmission: (id) => api.get(`/lms/submissions/${id}/`),
  createSubmission: (data) => api.post('/lms/submissions/', data),
  submitAssignment: (assignmentId, data) => api.post('/lms/submissions/', { assignment: assignmentId, ...data }),
  gradeSubmission: (id, data) => api.post(`/lms/submissions/${id}/grade/`, data),
  getMySubmissions: () => api.get('/lms/submissions/my-submissions/'),
  getPendingGrading: () => api.get('/lms/submissions/pending-grading/'),
  
  // Online Sessions
  getOnlineSessions: (params) => api.get('/lms/online-sessions/', { params }),
  createOnlineSession: (data) => api.post('/lms/online-sessions/create-session/', data),
  joinSession: (id) => api.post(`/lms/online-sessions/${id}/join/`),
  endSession: (id) => api.post(`/lms/online-sessions/${id}/end/`),
};

// ==================== NOTIFICATIONS API ====================
export const notificationsAPI = {
  list: (params) => api.get('/notifications/notifications/', { params }),
  get: (id) => api.get(`/notifications/notifications/${id}/`),
  markAsRead: (id) => api.post(`/notifications/notifications/${id}/mark-read/`),
  markAllAsRead: () => api.post('/notifications/notifications/mark-all-read/'),
  getUnreadCount: () => api.get('/notifications/notifications/unread-count/'),
  
  // Announcements
  getAnnouncements: (params) => api.get('/notifications/announcements/', { params }),
  createAnnouncement: (data) => api.post('/notifications/announcements/', data),
};

// ==================== REPORTS API ====================
export const reportsAPI = {
  list: (params) => api.get('/reports/reports/', { params }),
  get: (id) => api.get(`/reports/reports/${id}/`),
  generate: (data) => api.post('/reports/reports/generate/', data),
  download: (id) => api.get(`/reports/reports/${id}/download/`, { responseType: 'blob' }),
  
  // Templates
  getTemplates: (params) => api.get('/reports/templates/', { params }),
};

// ==================== CRM API ====================
export const crmAPI = {
  // Leads
  getLeads: (params) => api.get('/crm/leads/', { params }),
  getLead: (id) => api.get(`/crm/leads/${id}/`),
  createLead: (data) => api.post('/crm/leads/', data),
  updateLead: (id, data) => api.patch(`/crm/leads/${id}/`, data),
  convertLead: (id, data) => api.post(`/crm/leads/${id}/convert/`, data),
  
  // Activities
  getActivities: (params) => api.get('/crm/lead-activities/', { params }),
  createActivity: (data) => api.post('/crm/lead-activities/', data),
  
  // Campaigns
  getCampaigns: (params) => api.get('/crm/campaigns/', { params }),
  
  // Feedbacks
  getFeedbacks: (params) => api.get('/crm/feedbacks/', { params }),
  createFeedback: (data) => api.post('/crm/feedbacks/', data),
};

// ==================== FILES API ====================
export const filesAPI = {
  initiateUpload: (data) => api.post('/files/initiate/', data),
  reportPart: (data) => api.post('/files/report-part/', data),
  completeUpload: (data) => api.post('/files/complete/', data),
  abortUpload: (data) => api.post('/files/abort/', data),
  simpleUpload: (formData) => api.post('/files/simple/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getUploadStatus: (id) => api.get(`/files/status/${id}/`),
  deleteFile: (id) => api.delete(`/files/${id}/`),
  getPresignedUrl: (key) => api.post('/files/get-url/', { key }),
};

export default api;

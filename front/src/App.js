import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoadingScreen } from './components/common';
import { DashboardLayout } from './components/layout';

// Pages
import Login from './pages/Login';
import SelectBranch from './pages/SelectBranch';

// Admin Pages
import AdminDashboard from './pages/admin/Dashboard';
import AdminBranches from './pages/admin/Branches';
import AdminUsers from './pages/admin/Users';
import AdminCourses from './pages/admin/Courses';
import AdminClasses from './pages/admin/Classes';
import AdminEnrollments from './pages/admin/Enrollments';
import AdminAnnualRegistrations from './pages/admin/AnnualRegistrations';
import AdminFinancial from './pages/admin/Financial';
import AdminReports from './pages/admin/Reports';
import AdminNotifications from './pages/admin/Notifications';
import AdminCRM from './pages/admin/CRM';
import AdminSubjects from './pages/admin/Subjects';

// Branch Manager Pages
import BranchDashboard from './pages/branch/Dashboard';
import BranchClasses from './pages/branch/Classes';
import BranchStudents from './pages/branch/Students';
import BranchTeachers from './pages/branch/Teachers';
import BranchEnrollments from './pages/branch/Enrollments';
import BranchFinancial from './pages/branch/Financial';

// Teacher Pages
import TeacherDashboard from './pages/teacher/Dashboard';
import TeacherClasses from './pages/teacher/Classes';
import TeacherAssignments from './pages/teacher/Assignments';
import TeacherAttendance from './pages/teacher/Attendance';
import TeacherStudents from './pages/teacher/Students';

// Student Pages
import StudentDashboard from './pages/student/Dashboard';
import StudentClasses from './pages/student/Classes';
import StudentAssignments from './pages/student/Assignments';
import StudentGrades from './pages/student/Grades';
import StudentPayments from './pages/student/Payments';

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check if branch manager has selected a branch (except for select-branch page)
  const selectedBranch = localStorage.getItem('selected_branch');
  const isSelectBranchPage = window.location.pathname === '/select-branch';
  
  if (user?.role === 'branch_manager' && !selectedBranch && !isSelectBranchPage) {
    return <Navigate to="/select-branch" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    switch (user?.role) {
      case 'super_admin':
        return <Navigate to="/admin" replace />;
      case 'branch_manager':
        if (!selectedBranch) {
          return <Navigate to="/select-branch" replace />;
        }
        return <Navigate to="/branch" replace />;
      case 'teacher':
        return <Navigate to="/teacher" replace />;
      case 'student':
        return <Navigate to="/student" replace />;
      default:
        return <Navigate to="/login" replace />;
    }
  }

  return children;
};

// Public Route
const PublicRoute = ({ children }) => {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (isAuthenticated) {
    // Check if branch manager has selected a branch
    const selectedBranch = localStorage.getItem('selected_branch');
    
    switch (user?.role) {
      case 'super_admin':
        return <Navigate to="/admin" replace />;
      case 'branch_manager':
        // If no branch selected, go to selection page
        if (!selectedBranch) {
          return <Navigate to="/select-branch" replace />;
        }
        return <Navigate to="/branch" replace />;
      case 'teacher':
        return <Navigate to="/teacher" replace />;
      case 'student':
        return <Navigate to="/student" replace />;
      default:
        return <Navigate to="/" replace />;
    }
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />

      {/* Branch Selection (for branch managers) */}
      <Route path="/select-branch" element={
        <ProtectedRoute allowedRoles={['branch_manager']}>
          <SelectBranch />
        </ProtectedRoute>
      } />

      {/* Admin Routes */}
      <Route path="/admin" element={
        <ProtectedRoute allowedRoles={['super_admin']}>
          <DashboardLayout />
        </ProtectedRoute>
      }>
        <Route index element={<AdminDashboard />} />
        <Route path="branches" element={<AdminBranches />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="subjects" element={<AdminSubjects />} />
        <Route path="courses" element={<AdminCourses />} />
        <Route path="classes" element={<AdminClasses />} />
        <Route path="enrollments" element={<AdminEnrollments />} />
        <Route path="annual-registrations" element={<AdminAnnualRegistrations />} />
        <Route path="financial" element={<AdminFinancial />} />
        <Route path="reports" element={<AdminReports />} />
        <Route path="notifications" element={<AdminNotifications />} />
        <Route path="crm" element={<AdminCRM />} />
      </Route>

      {/* Branch Manager Routes */}
      <Route path="/branch" element={
        <ProtectedRoute allowedRoles={['branch_manager']}>
          <DashboardLayout />
        </ProtectedRoute>
      }>
        <Route index element={<BranchDashboard />} />
        <Route path="classes" element={<BranchClasses />} />
        <Route path="students" element={<BranchStudents />} />
        <Route path="teachers" element={<BranchTeachers />} />
        <Route path="enrollments" element={<BranchEnrollments />} />
        <Route path="financial" element={<BranchFinancial />} />
      </Route>

      {/* Teacher Routes */}
      <Route path="/teacher" element={
        <ProtectedRoute allowedRoles={['teacher']}>
          <DashboardLayout />
        </ProtectedRoute>
      }>
        <Route index element={<TeacherDashboard />} />
        <Route path="classes" element={<TeacherClasses />} />
        <Route path="assignments" element={<TeacherAssignments />} />
        <Route path="attendance" element={<TeacherAttendance />} />
        <Route path="students" element={<TeacherStudents />} />
      </Route>

      {/* Student Routes */}
      <Route path="/student" element={
        <ProtectedRoute allowedRoles={['student']}>
          <DashboardLayout />
        </ProtectedRoute>
      }>
        <Route index element={<StudentDashboard />} />
        <Route path="classes" element={<StudentClasses />} />
        <Route path="assignments" element={<StudentAssignments />} />
        <Route path="grades" element={<StudentGrades />} />
        <Route path="payments" element={<StudentPayments />} />
      </Route>

      {/* Redirect root to login */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      
      {/* 404 */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

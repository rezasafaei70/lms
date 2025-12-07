import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    // Initialize user from localStorage immediately
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Verify token on mount
  useEffect(() => {
    const verifyAuth = async () => {
      const token = localStorage.getItem('access_token');
      const savedUser = localStorage.getItem('user');
      
      if (!token || !savedUser) {
        setUser(null);
        setLoading(false);
        return;
      }

      // User is already set from initialization
      // Optionally verify token in background (don't logout on error)
      try {
        const response = await authAPI.me();
        if (response.data) {
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
        }
      } catch (err) {
        // Only logout if it's a 401 Unauthorized error
        if (err.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          setUser(null);
        }
        // For other errors (network, server), keep the user logged in
        console.log('Auth verification failed:', err.message);
      }
      
      setLoading(false);
    };

    verifyAuth();
  }, []);

  const sendOTP = useCallback(async (nationalCode) => {
    setError(null);
    try {
      const response = await authAPI.sendOTP(nationalCode);
      return response.data;
    } catch (err) {
      const message = err.response?.data?.message || err.response?.data?.national_code?.[0] || 'خطا در ارسال کد';
      setError(message);
      throw new Error(message);
    }
  }, []);

  const login = useCallback(async (nationalCode, code) => {
    setError(null);
    try {
      const response = await authAPI.login(nationalCode, code);
      const { tokens, user: userData } = response.data;
      
      // API returns tokens.access and tokens.refresh
      const accessToken = tokens?.access || response.data.access;
      const refreshToken = tokens?.refresh || response.data.refresh;
      
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
      localStorage.setItem('user', JSON.stringify(userData));
      
      setUser(userData);
      return userData;
    } catch (err) {
      const message = err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'خطا در ورود';
      setError(message);
      throw new Error(message);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authAPI.logout();
    } catch (err) {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      localStorage.removeItem('selected_branch');
      setUser(null);
    }
  }, []);

  const updateUser = useCallback((userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  }, []);

  // Role checking helpers
  const isSuperAdmin = user?.role === 'super_admin';
  const isBranchManager = user?.role === 'branch_manager';
  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student';
  const isStaff = ['super_admin', 'branch_manager', 'accountant', 'receptionist', 'support'].includes(user?.role);

  const value = {
    user,
    loading,
    error,
    sendOTP,
    login,
    logout,
    updateUser,
    isAuthenticated: !!user,
    isSuperAdmin,
    isBranchManager,
    isTeacher,
    isStudent,
    isStaff,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;


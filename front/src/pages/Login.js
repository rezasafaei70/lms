import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button, Input } from '../components/common';
import './Login.css';

const Login = () => {
  const [step, setStep] = useState('national_code'); // 'national_code' or 'otp'
  const [nationalCode, setNationalCode] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { sendOTP, login } = useAuth();
  const navigate = useNavigate();

  const handleSendOTP = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await sendOTP(nationalCode);
      setStep('otp');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(nationalCode, otp);
      
      // Navigate based on role
      switch (user.role) {
        case 'super_admin':
          navigate('/admin');
          break;
        case 'branch_manager':
          // Branch managers need to select their branch first
          navigate('/select-branch');
          break;
        case 'teacher':
          navigate('/teacher');
          break;
        case 'student':
          navigate('/student');
          break;
        default:
          navigate('/');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setStep('national_code');
    setOtp('');
    setError('');
  };

  return (
    <div className="login-page">
      {/* Background Pattern */}
      <div className="login-bg">
        <div className="login-bg-gradient" />
        <div className="login-bg-pattern" />
      </div>

      {/* Login Card */}
      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <svg viewBox="0 0 60 60" fill="none">
            <rect width="60" height="60" rx="16" fill="url(#login-gradient)" />
            <path d="M18 42V24l12-9 12 9v18" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M18 42h24" stroke="white" strokeWidth="3" strokeLinecap="round" />
            <circle cx="30" cy="30" r="5" stroke="white" strokeWidth="2.5" />
            <defs>
              <linearGradient id="login-gradient" x1="0" y1="0" x2="60" y2="60">
                <stop stopColor="#8B5CF6" />
                <stop offset="1" stopColor="#6D28D9" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h1 className="login-title">آموزشگاه کانون</h1>
        <p className="login-subtitle">
          {step === 'national_code' 
            ? 'برای ورود، کد ملی خود را وارد کنید'
            : 'کد تایید ارسال شده به موبایل خود را وارد کنید'
          }
        </p>

        {error && (
          <div className="login-error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </div>
        )}

        {step === 'national_code' ? (
          <form onSubmit={handleSendOTP} className="login-form">
            <Input
              label="کد ملی"
              placeholder="کد ملی ۱۰ رقمی"
              value={nationalCode}
              onChange={(e) => setNationalCode(e.target.value)}
              maxLength={10}
              autoFocus
            />
            <Button 
              type="submit" 
              fullWidth 
              loading={loading}
              disabled={nationalCode.length !== 10}
            >
              دریافت کد تایید
            </Button>
          </form>
        ) : (
          <form onSubmit={handleLogin} className="login-form">
            <Input
              label="کد تایید"
              placeholder="کد ۶ رقمی"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              maxLength={6}
              autoFocus
            />
            <Button 
              type="submit" 
              fullWidth 
              loading={loading}
              disabled={otp.length !== 6}
            >
              ورود
            </Button>
            <Button 
              type="button"
              variant="ghost"
              fullWidth
              onClick={handleBack}
            >
              بازگشت
            </Button>
          </form>
        )}

        <p className="login-footer">
          با ورود به سیستم، <a href="/terms">قوانین و مقررات</a> را می‌پذیرید.
        </p>
      </div>
    </div>
  );
};

export default Login;


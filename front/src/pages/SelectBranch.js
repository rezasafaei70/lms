import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button, Spinner } from '../components/common';
import { branchesAPI } from '../services/api';
import './SelectBranch.css';

const SelectBranch = () => {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBranch, setSelectedBranch] = useState(null);

  useEffect(() => {
    fetchBranches();
  }, []);

  const fetchBranches = async () => {
    try {
      setLoading(true);
      // Get branches where user is manager
      const response = await branchesAPI.list();
      setBranches(response.data.results || response.data || []);
      
      // If only one branch, select it automatically
      const data = response.data.results || response.data || [];
      if (data.length === 1) {
        handleSelectBranch(data[0]);
      }
    } catch (error) {
      console.error('Error fetching branches:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectBranch = (branch) => {
    // Store selected branch in localStorage
    localStorage.setItem('selected_branch', JSON.stringify(branch));
    
    // Update user context with selected branch
    const updatedUser = { ...user, selected_branch: branch };
    updateUser(updatedUser);
    
    // Navigate to branch dashboard
    navigate('/branch');
  };

  if (loading) {
    return (
      <div className="select-branch-page">
        <div className="select-branch-loading">
          <Spinner size="large" />
          <p>در حال بارگذاری شعب...</p>
        </div>
      </div>
    );
  }

  if (branches.length === 0) {
    return (
      <div className="select-branch-page">
        <div className="select-branch-card">
          <div className="select-branch-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              <polyline points="9,22 9,12 15,12 15,22" />
            </svg>
            <h2>شعبه‌ای یافت نشد</h2>
            <p>شما به هیچ شعبه‌ای دسترسی ندارید. لطفاً با مدیر سیستم تماس بگیرید.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="select-branch-page">
      <div className="select-branch-card">
        <div className="select-branch-header">
          <div className="select-branch-logo">
            <svg viewBox="0 0 60 60" fill="none">
              <rect width="60" height="60" rx="16" fill="url(#branch-gradient)" />
              <path d="M18 42V24l12-9 12 9v18" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M18 42h24" stroke="white" strokeWidth="3" strokeLinecap="round" />
              <circle cx="30" cy="30" r="5" stroke="white" strokeWidth="2.5" />
              <defs>
                <linearGradient id="branch-gradient" x1="0" y1="0" x2="60" y2="60">
                  <stop stopColor="#8B5CF6" />
                  <stop offset="1" stopColor="#6D28D9" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1>انتخاب شعبه</h1>
          <p>سلام {user?.first_name}، لطفاً شعبه مورد نظر را انتخاب کنید</p>
        </div>

        <div className="branch-list">
          {branches.map((branch) => (
            <button
              key={branch.id}
              className={`branch-item ${selectedBranch?.id === branch.id ? 'selected' : ''}`}
              onClick={() => setSelectedBranch(branch)}
            >
              <div className="branch-item-image">
                {branch.image_url ? (
                  <img src={branch.image_url} alt={branch.name} />
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                    <polyline points="9,22 9,12 15,12 15,22" />
                  </svg>
                )}
              </div>
              <div className="branch-item-info">
                <h3>{branch.name}</h3>
                <span>{branch.city} - {branch.address?.substring(0, 50)}...</span>
              </div>
              <div className="branch-item-check">
                {selectedBranch?.id === branch.id && (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </div>
            </button>
          ))}
        </div>

        <div className="select-branch-footer">
          <Button
            fullWidth
            disabled={!selectedBranch}
            onClick={() => handleSelectBranch(selectedBranch)}
          >
            ورود به شعبه
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SelectBranch;


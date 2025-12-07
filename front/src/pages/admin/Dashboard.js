import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Spinner, Badge } from '../../components/common';
import { branchesAPI, usersAPI, coursesAPI, enrollmentsAPI, financialAPI, notificationsAPI } from '../../services/api';
import './Dashboard.css';

const StatCard = ({ title, value, icon: Icon, color, change, loading, suffix = '' }) => (
  <Card className={`stat-card stat-card-${color}`} hover>
    <div className="stat-card-content">
      <div className="stat-card-info">
        <span className="stat-card-title">{title}</span>
        {loading ? (
          <Spinner size="small" />
        ) : (
          <span className="stat-card-value">
            {typeof value === 'number' ? value.toLocaleString('fa-IR') : value}{suffix}
          </span>
        )}
        {change !== undefined && (
          <span className={`stat-card-change ${change >= 0 ? 'positive' : 'negative'}`}>
            {change >= 0 ? '+' : ''}{change}%
          </span>
        )}
      </div>
      <div className="stat-card-icon">
        <Icon />
      </div>
    </div>
  </Card>
);

const MiniChart = ({ data, color }) => {
  const max = Math.max(...data, 1);
  return (
    <div className="mini-chart">
      {data.map((value, index) => (
        <div
          key={index}
          className="mini-chart-bar"
          style={{
            height: `${(value / max) * 100}%`,
            background: `var(--${color})`,
          }}
        />
      ))}
    </div>
  );
};

const Icons = {
  Branch: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9,22 9,12 15,12 15,22" />
    </svg>
  ),
  Users: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
    </svg>
  ),
  Course: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c3 3 9 3 12 0v-5" />
    </svg>
  ),
  Money: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
    </svg>
  ),
  Enrollment: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
      <path d="M9 14l2 2 4-4" />
    </svg>
  ),
  Class: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
};

const AdminDashboard = () => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [recentEnrollments, setRecentEnrollments] = useState([]);
  const [recentInvoices, setRecentInvoices] = useState([]);
  const [chartData, setChartData] = useState({
    enrollments: [0, 0, 0, 0, 0, 0, 0],
    revenue: [0, 0, 0, 0, 0, 0, 0],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [branchesRes, usersRes, coursesRes, classesRes, enrollmentsRes, invoicesRes] = await Promise.all([
          branchesAPI.list({ page_size: 1 }),
          usersAPI.list({ page_size: 1 }),
          coursesAPI.list({ page_size: 1 }),
          coursesAPI.getClasses({ page_size: 1 }),
          enrollmentsAPI.list({ page_size: 5 }),
          financialAPI.getInvoices({ page_size: 5 }),
        ]);

        // Calculate stats
        const enrollmentsData = enrollmentsRes.data.results || [];
        const invoicesData = invoicesRes.data.results || [];
        
        // Properly parse and calculate total revenue
        const totalRevenue = invoicesData
          .filter(i => i.status === 'paid')
          .reduce((sum, i) => {
            const amount = parseFloat(i.total_amount) || parseFloat(i.final_amount) || 0;
            return sum + amount;
          }, 0);

        setStats({
          branches: branchesRes.data.count || 0,
          users: usersRes.data.count || 0,
          courses: coursesRes.data.count || 0,
          classes: classesRes.data.count || 0,
          enrollments: enrollmentsRes.data.count || 0,
          revenue: Math.round(totalRevenue),
        });

        setRecentEnrollments(enrollmentsData.slice(0, 5));
        setRecentInvoices(invoicesData.slice(0, 5));

        // Mock chart data (in real app, this would come from an API)
        setChartData({
          enrollments: [12, 19, 8, 15, 22, 18, 25],
          revenue: [3200000, 4500000, 2800000, 5100000, 3900000, 4200000, 5500000],
        });

      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const getStatusBadge = (status) => {
    const variants = {
      active: 'success',
      pending: 'warning',
      cancelled: 'error',
      paid: 'success',
      overdue: 'error',
    };
    const names = {
      active: 'فعال',
      pending: 'در انتظار',
      cancelled: 'لغو شده',
      paid: 'پرداخت شده',
      overdue: 'معوق',
    };
    return <Badge variant={variants[status] || 'default'}>{names[status] || status}</Badge>;
  };

  return (
    <div className="admin-dashboard">
      {/* Stats Grid */}
      <div className="stats-grid">
        <StatCard
          title="شعب فعال"
          value={stats.branches}
          icon={Icons.Branch}
          color="purple"
          loading={loading}
        />
        <StatCard
          title="کل کاربران"
          value={stats.users}
          icon={Icons.Users}
          color="blue"
          loading={loading}
        />
        <StatCard
          title="دوره‌های فعال"
          value={stats.courses}
          icon={Icons.Course}
          color="teal"
          loading={loading}
        />
        <StatCard
          title="کلاس‌های فعال"
          value={stats.classes}
          icon={Icons.Class}
          color="orange"
          loading={loading}
        />
        <StatCard
          title="ثبت‌نام‌ها"
          value={stats.enrollments}
          icon={Icons.Enrollment}
          color="pink"
          loading={loading}
        />
        <StatCard
          title="درآمد"
          value={stats.revenue}
          icon={Icons.Money}
          color="green"
          loading={loading}
          suffix=" تومان"
        />
      </div>

      {/* Charts Row */}
      <div className="dashboard-row">
        <Card className="chart-card">
          <CardHeader>
            <CardTitle>آمار ثبت‌نام هفتگی</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container">
              <div className="bar-chart">
                {chartData.enrollments.map((value, index) => {
                  const max = Math.max(...chartData.enrollments, 1);
                  const days = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
                  return (
                    <div key={index} className="bar-item">
                      <div 
                        className="bar" 
                        style={{ height: `${(value / max) * 100}%` }}
                        data-value={value}
                      />
                      <span className="bar-label">{days[index]}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="chart-card">
          <CardHeader>
            <CardTitle>درآمد هفتگی</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container">
              <div className="bar-chart revenue-chart">
                {chartData.revenue.map((value, index) => {
                  const max = Math.max(...chartData.revenue, 1);
                  const days = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
                  return (
                    <div key={index} className="bar-item">
                      <div 
                        className="bar" 
                        style={{ height: `${(value / max) * 100}%` }}
                        data-value={(value / 1000000).toFixed(1) + 'M'}
                      />
                      <span className="bar-label">{days[index]}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activities & Quick Actions */}
      <div className="dashboard-row">
        <Card>
          <CardHeader>
            <CardTitle>ثبت‌نام‌های اخیر</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="recent-list">
              {recentEnrollments.length === 0 ? (
                <div className="empty-state">
                  <p>ثبت‌نامی یافت نشد</p>
                </div>
              ) : (
                recentEnrollments.map((enrollment, index) => (
                  <div key={enrollment.id || index} className="recent-item">
                    <div className="recent-item-avatar">
                      {enrollment.student_name?.[0] || '?'}
                    </div>
                    <div className="recent-item-content">
                      <strong>{enrollment.student_name || 'نامشخص'}</strong>
                      <span>{enrollment.class_name || '-'}</span>
                    </div>
                    {getStatusBadge(enrollment.status)}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>آخرین فاکتورها</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="recent-list">
              {recentInvoices.length === 0 ? (
                <div className="empty-state">
                  <p>فاکتوری یافت نشد</p>
                </div>
              ) : (
                recentInvoices.map((invoice, index) => (
                  <div key={invoice.id || index} className="recent-item">
                    <div className="recent-item-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                        <polyline points="14,2 14,8 20,8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                      </svg>
                    </div>
                    <div className="recent-item-content">
                      <strong>{invoice.invoice_number || `#${invoice.id}`}</strong>
                      <span>{(invoice.total_amount || 0).toLocaleString('fa-IR')} تومان</span>
                    </div>
                    {getStatusBadge(invoice.status)}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>دسترسی سریع</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="quick-actions">
            <a href="/admin/users" className="quick-action-btn">
              <div className="quick-action-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                  <circle cx="8.5" cy="7" r="4" />
                  <line x1="20" y1="8" x2="20" y2="14" />
                  <line x1="23" y1="11" x2="17" y2="11" />
                </svg>
              </div>
              <span>افزودن کاربر</span>
            </a>
            <a href="/admin/courses" className="quick-action-btn">
              <div className="quick-action-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                  <path d="M6 12v5c3 3 9 3 12 0v-5" />
                </svg>
              </div>
              <span>دوره جدید</span>
            </a>
            <a href="/admin/classes" className="quick-action-btn">
              <div className="quick-action-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              </div>
              <span>کلاس جدید</span>
            </a>
            <a href="/admin/enrollments" className="quick-action-btn">
              <div className="quick-action-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" />
                  <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
                </svg>
              </div>
              <span>ثبت‌نام جدید</span>
            </a>
            <a href="/admin/financial" className="quick-action-btn">
              <div className="quick-action-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                  <line x1="1" y1="10" x2="23" y2="10" />
                </svg>
              </div>
              <span>صدور فاکتور</span>
            </a>
            <a href="/admin/reports" className="quick-action-btn">
              <div className="quick-action-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                </svg>
              </div>
              <span>گزارش‌گیری</span>
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminDashboard;

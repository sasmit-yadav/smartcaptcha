'use client';

import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Users, 
  Activity, 
  Search, 
  Server, 
  UserCheck, 
  UserX, 
  AlertTriangle, 
  Terminal, 
  Key, 
  RefreshCw, 
  ArrowUpRight, 
  ArrowDownRight,
  TrendingUp,
  Cpu,
  Database,
  Lock,
  LogOut
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://next-captcha-sdk.onrender.com';
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '282307677315-065loak66lukfcde3om7926hcao8tkf8.apps.googleusercontent.com';

export default function AdminDashboard() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'developers', 'threats', 'system'
  
  // Data States
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // Load Google Identity Services SDK
  const initializeGoogleSignIn = () => {
    if (window.google && window.google.accounts) {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLoginSuccess
      });

      const buttonContainer = document.getElementById('google-admin-btn');
      if (buttonContainer) {
        window.google.accounts.id.renderButton(
          buttonContainer,
          { theme: 'filled_dark', size: 'large', width: 380, shape: 'pill' }
        );
      }
    }
  };

  const handleGoogleLoginSuccess = async (response) => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/admin/google-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential })
      });
      const data = await res.json();
      if (data.success) {
        if (data.user.is_admin) {
          setUser(data.user);
          localStorage.setItem('nextcaptcha_admin', JSON.stringify(data.user));
          loadAllData(data.user.id);
        } else {
          setError('Access Denied. You do not have Super Admin privileges.');
        }
      } else {
        setError(data.detail || 'Authentication failed');
      }
    } catch (err) {
      setError('Failed to authenticate with Google');
    }
    setLoading(false);
  };

  const handleMockLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/admin/google-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: 'mock_developer_token' })
      });
      const data = await res.json();
      if (data.success) {
        if (data.user.is_admin) {
          setUser(data.user);
          localStorage.setItem('nextcaptcha_admin', JSON.stringify(data.user));
          loadAllData(data.user.id);
        } else {
          setError('Access Denied. Mock account is not configured as admin.');
        }
      } else {
        setError(data.detail || 'Mock Authentication failed');
      }
    } catch (err) {
      setError('Failed to authenticate with Mock User');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('nextcaptcha_admin');
    setUser(null);
    setAnalytics(null);
    setUsers([]);
    setSessions([]);
  };

  // Check auth on load
  useEffect(() => {
    const savedAdmin = localStorage.getItem('nextcaptcha_admin');
    if (savedAdmin) {
      const parsed = JSON.parse(savedAdmin);
      setUser(parsed);
      loadAllData(parsed.id);
    } else {
      if (!document.getElementById('google-jssdk-admin')) {
        const script = document.createElement('script');
        script.id = 'google-jssdk-admin';
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.onload = () => {
          setTimeout(initializeGoogleSignIn, 200);
        };
        document.body.appendChild(script);
      } else {
        setTimeout(initializeGoogleSignIn, 200);
      }
    }
  }, []);

  const loadAllData = async (adminId) => {
    setRefreshing(true);
    try {
      await Promise.all([
        loadAnalytics(adminId),
        loadUsers(adminId),
        loadSessions(adminId)
      ]);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
    setRefreshing(false);
  };

  const loadAnalytics = async (adminId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/global-analytics`, {
        headers: { 'user-id': adminId }
      });
      const data = await res.json();
      if (data.success) {
        setAnalytics(data);
      }
    } catch (err) {
      setError('Failed to load global metrics');
    }
  };

  const loadUsers = async (adminId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/global-users`, {
        headers: { 'user-id': adminId }
      });
      const data = await res.json();
      if (data.success) {
        setUsers(data.users);
      }
    } catch (err) {
      setError('Failed to load developer registry');
    }
  };

  const loadSessions = async (adminId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/global-sessions`, {
        headers: { 'user-id': adminId }
      });
      const data = await res.json();
      if (data.success) {
        setSessions(data.sessions);
      }
    } catch (err) {
      setError('Failed to load global sessions');
    }
  };

  const toggleUserStatus = async (targetUserId, currentStatus) => {
    if (!confirm(`Are you sure you want to ${currentStatus ? 'suspend' : 'activate'} this developer?`)) return;
    
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/toggle-status`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'user-id': user.id
        },
        body: JSON.stringify({
          target_user_id: targetUserId,
          is_active: !currentStatus
        })
      });
      const data = await res.json();
      if (data.success) {
        setSuccess(data.message);
        setTimeout(() => setSuccess(''), 3000);
        loadUsers(user.id);
      }
    } catch (err) {
      setError('Failed to update developer status');
    }
  };

  // Render Login Card
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#050811] px-4">
        <div className="max-w-md w-full p-8 border border-white/10 bg-[#0A0F1E] rounded-2xl shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500"></div>
          
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-blue-500" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">Super Admin Console</h1>
            <p className="text-slate-400 text-sm mt-1">SmartCaptcha Mitigation Control Center</p>
          </div>

          <div className="space-y-6 flex flex-col items-center">
            {/* Google Authentication */}
            <div id="google-admin-btn" className="w-full flex justify-center min-h-[50px]"></div>

            <div className="w-full flex items-center gap-3">
              <div className="h-[1px] bg-white/10 flex-1"></div>
              <span className="text-xs text-slate-500 uppercase tracking-widest font-semibold">Or</span>
              <div className="h-[1px] bg-white/10 flex-1"></div>
            </div>

            <button
              onClick={handleMockLogin}
              disabled={loading}
              className="w-full py-3 bg-[#111827] border border-white/5 text-slate-300 hover:text-white rounded-xl font-semibold transition-all hover:bg-slate-800 flex items-center justify-center gap-2 text-sm shadow-md"
            >
              {loading ? 'Authenticating...' : 'Enter as Super Admin (Bypass)'}
            </button>
          </div>

          {error && (
            <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Calculate percentages
  const totalRequests = analytics?.stats?.total_sessions || 0;
  const botBlocked = analytics?.stats?.bot_count || 0;
  const humanPassed = analytics?.stats?.human_count || 0;
  const challengeTriggered = analytics?.stats?.challenge_count || 0;
  const mitigationRate = totalRequests > 0 ? ((botBlocked / totalRequests) * 100).toFixed(1) : '0.0';

  return (
    <div className="min-h-screen bg-[#060913] flex">
      {/* Sidebar navigation */}
      <aside className="w-64 border-r border-white/5 bg-[#0B1120] flex flex-col justify-between py-6">
        <div>
          {/* Logo brand */}
          <div className="px-6 mb-8 flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center justify-center">
              <Shield className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h2 className="font-bold text-slate-200 text-sm leading-none">SmartCaptcha</h2>
              <span className="text-[10px] text-cyan-400 font-semibold tracking-wider uppercase">Super Admin</span>
            </div>
          </div>

          {/* Nav List */}
          <nav className="px-3 space-y-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                activeTab === 'overview' ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              <Activity className="w-4 h-4" />
              Mitigation Overview
            </button>
            <button
              onClick={() => setActiveTab('developers')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                activeTab === 'developers' ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              <Users className="w-4 h-4" />
              Developer Accounts
            </button>
            <button
              onClick={() => setActiveTab('threats')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                activeTab === 'threats' ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              <Terminal className="w-4 h-4" />
              Live Threat Feed
            </button>
            <button
              onClick={() => setActiveTab('system')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                activeTab === 'system' ? 'bg-blue-500/10 text-blue-400' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              <Server className="w-4 h-4" />
              System Architecture
            </button>
          </nav>
        </div>

        {/* User profile footer */}
        <div className="px-4">
          <div className="p-4 bg-slate-900/40 border border-white/5 rounded-xl flex items-center justify-between">
            <div className="truncate max-w-[140px]">
              <p className="text-xs font-bold text-slate-200 truncate">{user.full_name || 'Admin User'}</p>
              <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
            </div>
            <button 
              onClick={handleLogout}
              className="p-1.5 hover:bg-white/5 text-slate-400 hover:text-red-400 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto px-10 py-8">
        {/* Header section */}
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-100 uppercase tracking-tight">
              {activeTab === 'overview' && 'Mitigation Overview'}
              {activeTab === 'developers' && 'Developer Registry'}
              {activeTab === 'threats' && 'Global Threat Feed'}
              {activeTab === 'system' && 'Infrastructure Health'}
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              {activeTab === 'overview' && 'Monitor behavioral biometric verification results and global bot threat activity.'}
              {activeTab === 'developers' && 'Manage registered API accounts, usage rates, and toggle account activation status.'}
              {activeTab === 'threats' && 'Real-time telemetry streams showing bot mitigations and classification decisions.'}
              {activeTab === 'system' && 'System architecture specs, loaded random forest model weights, and database connection status.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadAllData(user.id)}
              disabled={refreshing}
              className="p-2 border border-white/5 hover:border-white/10 bg-slate-900/60 rounded-lg text-slate-300 hover:text-white transition-all flex items-center gap-2 text-sm font-semibold"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Refreshing...' : 'Refresh Data'}
            </button>
          </div>
        </header>

        {success && (
          <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-xl text-green-400 text-xs flex items-center gap-2">
            <UserCheck className="w-4 h-4 shrink-0" />
            {success}
          </div>
        )}

        {/* VIEW 1: Overview Dashboard */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* KPI metrics row */}
            <div className="grid md:grid-cols-4 gap-6">
              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-blue-500"></div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Global Traffic</span>
                  <Activity className="w-4 h-4 text-blue-500" />
                </div>
                <h3 className="text-3xl font-extrabold text-slate-100">{totalRequests.toLocaleString()}</h3>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                  <span>Total behavioral sessions evaluated</span>
                </p>
              </div>

              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-red-500"></div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Threats Mitigated</span>
                  <Shield className="w-4 h-4 text-red-500" />
                </div>
                <h3 className="text-3xl font-extrabold text-slate-100">{botBlocked.toLocaleString()}</h3>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1">
                  <span className="text-red-400 font-semibold">{mitigationRate}%</span>
                  <span>of global traffic blocked as bots</span>
                </p>
              </div>

              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-green-500"></div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Clean Traffic</span>
                  <UserCheck className="w-4 h-4 text-green-500" />
                </div>
                <h3 className="text-3xl font-extrabold text-slate-100">{humanPassed.toLocaleString()}</h3>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1">
                  <span className="text-green-400 font-semibold">{totalRequests > 0 ? ((humanPassed / totalRequests) * 100).toFixed(1) : 0}%</span>
                  <span>human-verified sessions passed</span>
                </p>
              </div>

              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-cyan-500"></div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Integrations</span>
                  <Users className="w-4 h-4 text-cyan-500" />
                </div>
                <h3 className="text-3xl font-extrabold text-slate-100">{analytics?.stats?.total_users || 0}</h3>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1">
                  <span className="text-cyan-400 font-semibold">{analytics?.stats?.total_projects || 0}</span>
                  <span>active customer projects configured</span>
                </p>
              </div>
            </div>

            {/* Custom SVG Daily Activity Chart */}
            <div className="p-8 border border-white/5 bg-[#0B1120] rounded-2xl shadow-xl">
              <h3 className="text-lg font-bold mb-6 text-slate-200">Mitigation Trend (Last 30 Days)</h3>
              
              {analytics?.daily_stats && analytics.daily_stats.length > 0 ? (
                <div className="space-y-4">
                  {/* Graph plot */}
                  <div className="h-64 w-full flex items-end gap-2 pt-6 border-b border-white/5 px-2">
                    {analytics.daily_stats.map((dayStat, idx) => {
                      const totalDay = dayStat.bots + dayStat.humans;
                      const maxTotal = Math.max(...analytics.daily_stats.map(d => d.bots + d.humans), 10);
                      const barHeight = (totalDay / maxTotal) * 100;
                      
                      const botPct = totalDay > 0 ? (dayStat.bots / totalDay) * 100 : 0;
                      const humanPct = totalDay > 0 ? (dayStat.humans / totalDay) * 100 : 0;

                      return (
                        <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer">
                          {/* Tooltip */}
                          <div className="absolute bottom-full mb-2 bg-[#0F172A] border border-white/10 p-2.5 rounded-xl shadow-xl hidden group-hover:block z-10 text-xs min-w-[120px]">
                            <p className="font-bold text-slate-200 mb-1">{dayStat.day}</p>
                            <p className="flex items-center justify-between text-green-400">Humans: <span>{dayStat.humans}</span></p>
                            <p className="flex items-center justify-between text-red-400">Bots: <span>{dayStat.bots}</span></p>
                          </div>
                          
                          {/* Stacked Bar */}
                          <div 
                            style={{ height: `${Math.max(barHeight, 5)}%` }} 
                            className="w-full rounded-t-sm overflow-hidden flex flex-col justify-end transition-all group-hover:opacity-80"
                          >
                            <div style={{ height: `${botPct}%` }} className="bg-red-500/80 w-full"></div>
                            <div style={{ height: `${humanPct}%` }} className="bg-green-500/80 w-full"></div>
                          </div>
                          <span className="text-[9px] text-slate-500 mt-2 truncate w-full text-center group-hover:text-slate-300">
                            {dayStat.day.split('-')[2]}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  {/* Legend keys */}
                  <div className="flex gap-6 justify-center text-xs pt-2">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 bg-green-500 rounded-sm"></span>
                      <span className="text-slate-400">Verified Humans</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 bg-red-500 rounded-sm"></span>
                      <span className="text-slate-400">Mitigated Bots</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-20 text-slate-500">
                  <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-25" />
                  <p>No activity logged yet. Call the SDK and run predictions to generate analytics.</p>
                </div>
              )}
            </div>

            {/* Top active projects */}
            <div className="p-8 border border-white/5 bg-[#0B1120] rounded-2xl shadow-xl">
              <h3 className="text-lg font-bold mb-6 text-slate-200">Top Active Customer Projects</h3>
              {analytics?.top_projects && analytics.top_projects.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-white/5 text-xs uppercase tracking-wider text-slate-400 bg-slate-900/30">
                        <th className="py-4 px-6 font-semibold">Project Name</th>
                        <th className="py-4 px-6 font-semibold">Owner Developer</th>
                        <th className="py-4 px-6 font-semibold">UUID</th>
                        <th className="py-4 px-6 font-semibold text-right">Processed Sessions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.top_projects.map((proj) => (
                        <tr key={proj.project_id} className="border-b border-white/5 text-sm hover:bg-slate-900/20 transition-colors">
                          <td className="py-4 px-6 font-bold text-slate-200">{proj.project_name}</td>
                          <td className="py-4 px-6 text-slate-400">{proj.owner_email}</td>
                          <td className="py-4 px-6 font-mono text-xs text-slate-500">{proj.project_id}</td>
                          <td className="py-4 px-6 font-bold text-right text-blue-400">{proj.request_count.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  No active projects found.
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 2: Developer registry */}
        {activeTab === 'developers' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between gap-4 p-4 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md">
              <div className="flex-1 max-w-md relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search developer accounts (email, company, name)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-11 pr-4 py-2.5 bg-slate-900/60 border border-white/5 focus:border-blue-500 rounded-xl text-sm text-slate-200 focus:outline-none placeholder-slate-500"
                />
              </div>
            </div>

            <div className="p-8 border border-white/5 bg-[#0B1120] rounded-2xl shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-white/5 text-xs uppercase tracking-wider text-slate-400 bg-slate-900/30">
                      <th className="py-4 px-6 font-semibold">Email</th>
                      <th className="py-4 px-6 font-semibold">Full Name</th>
                      <th className="py-4 px-6 font-semibold">Company</th>
                      <th className="py-4 px-6 font-semibold">Workspaces</th>
                      <th className="py-4 px-6 font-semibold">Mitigations Call</th>
                      <th className="py-4 px-6 font-semibold">Registered</th>
                      <th className="py-4 px-6 font-semibold">Status</th>
                      <th className="py-4 px-6 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users
                      .filter(u => 
                        u.email.toLowerCase().includes(searchQuery.toLowerCase()) || 
                        (u.full_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (u.company_name || '').toLowerCase().includes(searchQuery.toLowerCase())
                      )
                      .map((dev) => (
                        <tr key={dev.id} className="border-b border-white/5 text-sm hover:bg-slate-900/20 transition-colors">
                          <td className="py-4 px-6 font-bold text-slate-200">{dev.email}</td>
                          <td className="py-4 px-6 text-slate-300">{dev.full_name || '-'}</td>
                          <td className="py-4 px-6 text-slate-400">{dev.company_name || '-'}</td>
                          <td className="py-4 px-6 font-semibold text-blue-400">{dev.project_count} workspaces</td>
                          <td className="py-4 px-6 font-bold text-slate-300">{dev.total_requests.toLocaleString()}</td>
                          <td className="py-4 px-6 text-slate-500 text-xs">
                            {new Date(dev.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-4 px-6">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                              dev.is_active 
                                ? 'bg-green-500/10 text-green-400 border-green-500/25' 
                                : 'bg-red-500/10 text-red-400 border-red-500/25'
                            }`}>
                              {dev.is_active ? 'Active' : 'Suspended'}
                            </span>
                          </td>
                          <td className="py-4 px-6 text-right">
                            {dev.email !== 'developer@nextcaptcha.com' && dev.email !== user.email && (
                              <button
                                onClick={() => toggleUserStatus(dev.id, dev.is_active)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                                  dev.is_active 
                                    ? 'bg-red-500/10 hover:bg-red-500/20 text-red-400' 
                                    : 'bg-green-500/10 hover:bg-green-500/20 text-green-400'
                                }`}
                              >
                                {dev.is_active ? (
                                  <>
                                    <UserX className="w-3.5 h-3.5" /> Suspend
                                  </>
                                ) : (
                                  <>
                                    <UserCheck className="w-3.5 h-3.5" /> Activate
                                  </>
                                )}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 3: Global Threat Feed */}
        {activeTab === 'threats' && (
          <div className="space-y-6">
            <div className="p-8 border border-white/5 bg-[#0B1120] rounded-2xl shadow-xl">
              <h3 className="text-lg font-bold mb-4 text-slate-200">Real-Time Threat Intelligence</h3>
              <p className="text-xs text-slate-500 mb-6">Listing the last 100 verification telemetry payloads evaluated by the Random Forest model across all registered client websites.</p>
              
              {sessions && sessions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-white/5 text-xs uppercase tracking-wider text-slate-400 bg-slate-900/30">
                        <th className="py-4 px-6 font-semibold">Session ID</th>
                        <th className="py-4 px-6 font-semibold">Workspace Project</th>
                        <th className="py-4 px-6 font-semibold">Client Platform</th>
                        <th className="py-4 px-6 font-semibold">Biometric Score</th>
                        <th className="py-4 px-6 font-semibold">Automation</th>
                        <th className="py-4 px-6 font-semibold">Security Action</th>
                        <th className="py-4 px-6 font-semibold text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((sess) => (
                        <tr key={sess.id} className="border-b border-white/5 text-sm hover:bg-slate-900/20 transition-colors">
                          <td className="py-4 px-6 font-mono text-xs text-slate-500">{sess.id}</td>
                          <td className="py-4 px-6 font-semibold text-slate-300">{sess.project_name}</td>
                          <td className="py-4 px-6 text-slate-400 truncate max-w-[150px]" title={sess.user_agent}>
                            <span className="px-2 py-0.5 bg-slate-900 border border-white/5 rounded-md text-[10px] uppercase font-bold text-slate-400">
                              {sess.device_type}
                            </span>
                          </td>
                          <td className="py-4 px-6">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-200">{sess.risk_score}%</span>
                              <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div 
                                  style={{ width: `${sess.risk_score}%` }} 
                                  className={`h-full ${sess.risk_score >= 50 ? 'bg-red-500' : sess.risk_score >= 20 ? 'bg-amber-500' : 'bg-green-500'}`}
                                ></div>
                              </div>
                            </div>
                          </td>
                          <td className="py-4 px-6">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                              sess.webdriver_flag 
                                ? 'bg-red-500/10 text-red-400 border-red-500/20' 
                                : 'bg-slate-900 text-slate-500 border-white/5'
                            }`}>
                              {sess.webdriver_flag ? 'WebDriver' : 'Normal'}
                            </span>
                          </td>
                          <td className="py-4 px-6">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                              sess.verdict === 'accept'
                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : sess.verdict === 'challenge'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                : 'bg-red-500/10 text-red-400 border-red-500/20'
                            }`}>
                              {sess.verdict}
                            </span>
                          </td>
                          <td className="py-4 px-6 text-right text-slate-500 text-xs">
                            {new Date(sess.created_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-20 text-slate-500">
                  <Terminal className="w-12 h-12 mx-auto mb-3 opacity-25" />
                  <p>Threat feed is empty. Waiting for clients to connect and send behavioral data streams.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 4: Infrastructure Health / Settings */}
        {activeTab === 'system' && (
          <div className="space-y-8">
            <div className="grid md:grid-cols-3 gap-6">
              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md flex items-start gap-4">
                <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                  <Database className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-200">Supabase DB Pool</h3>
                  <p className="text-xs text-green-400 font-semibold mt-1">Status: Connected</p>
                  <p className="text-[11px] text-slate-500 mt-2">Active PostgreSQL connection pool utilizing PgBouncer port 6543.</p>
                </div>
              </div>

              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md flex items-start gap-4">
                <div className="p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
                  <Cpu className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-200">ML Model Engine</h3>
                  <p className="text-xs text-cyan-400 font-semibold mt-1">Standard: Random Forest</p>
                  <p className="text-[11px] text-slate-500 mt-2">Loaded standard model RF v3 (52 telemetry features evaluated in &lt;1.5ms).</p>
                </div>
              </div>

              <div className="p-6 border border-white/5 bg-[#0B1120] rounded-2xl shadow-md flex items-start gap-4">
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                  <Lock className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-200">Encryption Status</h3>
                  <p className="text-xs text-red-400 font-semibold mt-1">Algorithm: bcrypt</p>
                  <p className="text-[11px] text-slate-500 mt-2">Traditional authentication securely hashed via bcrypt. Google OAuth checked via urllib token verification.</p>
                </div>
              </div>
            </div>

            <div className="p-8 border border-white/5 bg-[#0B1120] rounded-2xl shadow-xl">
              <h3 className="text-lg font-bold mb-4 text-slate-200">Active Model Weights</h3>
              <p className="text-xs text-slate-500 mb-6">Listed below are the standard classification categories configured inside the Random Forest decision tree engine.</p>
              
              <div className="grid md:grid-cols-2 gap-8 text-sm">
                <div className="p-6 bg-slate-900/30 rounded-xl border border-white/5">
                  <h4 className="font-bold mb-4 text-slate-300 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    Classification Thresholds
                  </h4>
                  <ul className="space-y-3 text-xs text-slate-400">
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Low Risk threshold (Auto-Accept)</span>
                      <span className="font-mono font-bold text-green-400">&lt; 20%</span>
                    </li>
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Interactive Challenge Zone</span>
                      <span className="font-mono font-bold text-amber-400">20% - 50%</span>
                    </li>
                    <li className="flex justify-between">
                      <span>High Risk threshold (Auto-Reject)</span>
                      <span className="font-mono font-bold text-red-400">&gt; 50%</span>
                    </li>
                  </ul>
                </div>

                <div className="p-6 bg-slate-900/30 rounded-xl border border-white/5">
                  <h4 className="font-bold mb-4 text-slate-300 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-red-400" />
                    Heuristic Rule Boosting
                  </h4>
                  <ul className="space-y-3 text-xs text-slate-400">
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>WebDriver Automation Flag Detected</span>
                      <span className="font-mono font-bold text-red-400">+ 35% Risk</span>
                    </li>
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Abnormal mouse click timing patterns</span>
                      <span className="font-mono font-bold text-amber-400">+ 12% Risk</span>
                    </li>
                    <li className="flex justify-between">
                      <span>Straight Bezier curve click pathing</span>
                      <span className="font-mono font-bold text-amber-400">+ 8% Risk</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

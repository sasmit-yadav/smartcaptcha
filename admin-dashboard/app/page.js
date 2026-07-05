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
  LogOut,
  ChevronLeft,
  ChevronRight,
  Globe,
  Settings,
  Bell,
  Sliders,
  Sparkles,
  Layers,
  Clock,
  ExternalLink
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://next-captcha-sdk.onrender.com';

export default function AdminDashboard() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'developers', 'threats', 'system'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Credentials
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Data States
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [timeFilter, setTimeFilter] = useState('24H'); // '1H', '24H', '7D', '30D'

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/admin/verify-credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.status === 200 && data.success) {
        setUser(data.user);
        localStorage.setItem('nextcaptcha_admin', JSON.stringify(data.user));
        loadAllData(data.user.id);
      } else {
        setError(data.detail || 'Invalid admin username or password');
      }
    } catch (err) {
      setError('Connection to admin API failed. Please try again.');
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

  useEffect(() => {
    const savedAdmin = localStorage.getItem('nextcaptcha_admin');
    if (savedAdmin) {
      const parsed = JSON.parse(savedAdmin);
      setUser(parsed);
      loadAllData(parsed.id);
    }
  }, []);

  // Set up 10-second polling for real-time live threat data
  useEffect(() => {
    if (!user) return;
    
    const interval = setInterval(() => {
      loadAnalytics(user.id);
      loadSessions(user.id);
    }, 10000); // 10 seconds
    
    return () => clearInterval(interval);
  }, [user]);

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
      <div className="min-h-screen flex items-center justify-center bg-[#03060E] px-4 font-sans selection:bg-cfOrange/30">
        <div className="max-w-md w-full p-8 border border-white/[0.04] bg-[#090D1A] rounded-xl shadow-2xl relative">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-cfOrange"></div>
          
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-cfOrange/10 border border-cfOrange/20 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Shield className="w-6 h-6 text-cfOrange" />
            </div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Super Admin Console</h1>
            <p className="text-slate-400 text-xs mt-1">SmartCaptcha Mitigation Control Center</p>
          </div>

          <form onSubmit={handleAdminLogin} className="space-y-4 w-full">
            <div>
              <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Username</label>
              <input
                type="text"
                placeholder="Enter admin username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full px-4 py-2.5 bg-[#05070F] border border-white/[0.06] focus:border-cfOrange rounded-lg text-sm text-slate-200 focus:outline-none placeholder-slate-600 transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Password</label>
              <input
                type="password"
                placeholder="Enter admin password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-2.5 bg-[#05070F] border border-white/[0.06] focus:border-cfOrange rounded-lg text-sm text-slate-200 focus:outline-none placeholder-slate-600 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-cfOrange hover:bg-cfOrange/90 disabled:bg-cfOrange/50 text-white rounded-lg font-semibold transition-all flex items-center justify-center gap-2 text-sm shadow-md mt-6"
            >
              {loading ? 'Verifying...' : 'Log In'}
            </button>
          </form>

          {error && (
            <div className="mt-6 p-3 bg-cfRed/10 border border-cfRed/20 rounded-lg text-cfRed text-xs flex items-center gap-2">
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
    <div className="min-h-screen bg-[#05070f] flex text-slate-200 font-sans antialiased selection:bg-cfOrange/30">
      {/* Collapsible Sidebar */}
      <aside className={`${sidebarCollapsed ? 'w-16' : 'w-64'} shrink-0 border-r border-white/[0.04] bg-[#080c16] flex flex-col justify-between py-5 transition-all duration-300 relative`}>
        {/* Toggle Collapse Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-12 w-6 h-6 border border-white/[0.06] bg-[#0b101e] hover:bg-slate-800 rounded-full flex items-center justify-center text-slate-400 hover:text-white transition-colors shadow-md z-20"
        >
          {sidebarCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>

        <div>
          {/* Logo brand */}
          <div className={`px-5 mb-8 flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3'}`}>
            <div className="w-8 h-8 bg-cfOrange/10 border border-cfOrange/20 rounded-lg flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-cfOrange" />
            </div>
            {!sidebarCollapsed && (
              <div>
                <h2 className="font-bold text-slate-100 text-sm leading-none tracking-tight">SmartCaptcha</h2>
                <span className="text-[9px] text-cfOrange font-bold tracking-wider uppercase">Super Admin</span>
              </div>
            )}
          </div>

          {/* Nav List */}
          <div className="px-3">
            {!sidebarCollapsed && (
              <span className="block px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Security Analytics</span>
            )}
            <nav className="space-y-1">
              <button
                onClick={() => setActiveTab('overview')}
                className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center px-0' : 'px-3 py-2.5'} rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'overview' ? 'bg-white/[0.04] text-cfOrange border-l-2 border-cfOrange' : 'text-slate-400 hover:bg-white/[0.02] hover:text-slate-200'
                }`}
                title="Overview"
              >
                <Activity className="w-4 h-4 shrink-0" />
                {!sidebarCollapsed && <span className="ml-3">Threat Intelligence</span>}
              </button>

              <button
                onClick={() => setActiveTab('threats')}
                className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center px-0' : 'px-3 py-2.5'} rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'threats' ? 'bg-white/[0.04] text-cfOrange border-l-2 border-cfOrange' : 'text-slate-400 hover:bg-white/[0.02] hover:text-slate-200'
                }`}
                title="Threat Feed"
              >
                <Terminal className="w-4 h-4 shrink-0" />
                {!sidebarCollapsed && <span className="ml-3">Live Threat Feed</span>}
              </button>
            </nav>

            {!sidebarCollapsed && (
              <span className="block px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-6 mb-3">Management</span>
            )}
            <nav className="space-y-1">
              <button
                onClick={() => setActiveTab('developers')}
                className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center px-0' : 'px-3 py-2.5'} rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'developers' ? 'bg-white/[0.04] text-cfOrange border-l-2 border-cfOrange' : 'text-slate-400 hover:bg-white/[0.02] hover:text-slate-200'
                }`}
                title="Developers"
              >
                <Users className="w-4 h-4 shrink-0" />
                {!sidebarCollapsed && <span className="ml-3">Developer Registry</span>}
              </button>

              <button
                onClick={() => setActiveTab('system')}
                className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center px-0' : 'px-3 py-2.5'} rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'system' ? 'bg-white/[0.04] text-cfOrange border-l-2 border-cfOrange' : 'text-slate-400 hover:bg-white/[0.02] hover:text-slate-200'
                }`}
                title="System Health"
              >
                <Server className="w-4 h-4 shrink-0" />
                {!sidebarCollapsed && <span className="ml-3">Infrastructure Specs</span>}
              </button>
            </nav>
          </div>
        </div>

        {/* Profile Footer */}
        <div className="px-3">
          <div className={`p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center justify-between ${sidebarCollapsed ? 'flex-col gap-2' : ''}`}>
            {!sidebarCollapsed && (
              <div className="truncate max-w-[140px] pr-2">
                <p className="text-[11px] font-bold text-slate-200 truncate">{user.full_name || 'Super Admin'}</p>
                <p className="text-[9px] text-slate-500 truncate">{user.email}</p>
              </div>
            )}
            <button 
              onClick={handleLogout}
              className="p-1.5 hover:bg-white/5 text-slate-400 hover:text-cfRed rounded-lg transition-colors shrink-0"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Panel */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Navigation */}
        <header className="h-14 border-b border-white/[0.04] bg-[#070a13] px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 bg-white/[0.02] border border-white/[0.06] px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-cfGreen animate-pulse"></span>
              Environment: Live Production
            </div>
            <span className="text-xs text-slate-500">
              System Latency: <span className="font-semibold text-slate-300">1.2ms</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-[11px] font-mono text-slate-500">
              Local: {new Date().toLocaleTimeString()}
            </span>
            <button
              onClick={() => loadAllData(user.id)}
              disabled={refreshing}
              className="p-1.5 border border-white/[0.06] bg-white/[0.02] rounded-lg text-slate-400 hover:text-white transition-all flex items-center gap-2 text-xs font-semibold"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <div className="h-4 w-[1px] bg-white/10"></div>
            <div className="w-7 h-7 rounded-full bg-[#1e293b] flex items-center justify-center font-bold text-xs text-cfOrange border border-cfOrange/20">
              SR
            </div>
          </div>
        </header>

        {/* Contents */}
        <div className="flex-1 px-10 py-8 max-w-7xl w-full mx-auto">
          {/* Hero Header */}
          <div className="flex justify-between items-start mb-8">
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Global Threat Intelligence</h1>
              <p className="text-slate-400 text-xs mt-1">Real-time behavioral verification across all protected client applications.</p>
            </div>
          </div>

          {success && (
            <div className="mb-6 p-3 bg-cfGreen/10 border border-cfGreen/20 rounded-lg text-cfGreen text-xs flex items-center gap-2">
              <UserCheck className="w-4 h-4 shrink-0" />
              {success}
            </div>
          )}

          {/* VIEW 1: Overview */}
          {activeTab === 'overview' && (
            <div className="space-y-8">
              {/* Informative Stats Card Grid */}
              <div className="grid md:grid-cols-4 gap-4">
                {/* Metric 1 */}
                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm relative overflow-hidden flex flex-col justify-between h-32">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Total Evaluated Traffic</span>
                    <h3 className="text-2xl font-bold text-slate-100 mt-2">{totalRequests.toLocaleString()}</h3>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-white/[0.03] pt-2">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3 text-cfGreen" />
                      100% telemetry capture
                    </span>
                    <svg viewBox="0 0 100 30" className="w-16 h-6 text-cfBlue stroke-current fill-none stroke-2">
                      <path d="M0,25 Q15,5 30,18 T60,8 T90,20" />
                    </svg>
                  </div>
                </div>

                {/* Metric 2 */}
                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm relative overflow-hidden flex flex-col justify-between h-32">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Mitigated Bots</span>
                    <h3 className="text-2xl font-bold text-slate-100 mt-2">{botBlocked.toLocaleString()}</h3>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-white/[0.03] pt-2">
                    <span className="font-semibold text-cfOrange">
                      {mitigationRate}% block rate
                    </span>
                    <svg viewBox="0 0 100 30" className="w-16 h-6 text-cfOrange stroke-current fill-none stroke-2">
                      <path d="M0,20 Q20,22 40,5 T80,18 T100,2" />
                    </svg>
                  </div>
                </div>

                {/* Metric 3 */}
                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm relative overflow-hidden flex flex-col justify-between h-32">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Verified Humans</span>
                    <h3 className="text-2xl font-bold text-slate-100 mt-2">{humanPassed.toLocaleString()}</h3>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-white/[0.03] pt-2">
                    <span className="font-semibold text-cfGreen">
                      {totalRequests > 0 ? ((humanPassed / totalRequests) * 100).toFixed(1) : 0}% success
                    </span>
                    <svg viewBox="0 0 100 30" className="w-16 h-6 text-cfGreen stroke-current fill-none stroke-2">
                      <path d="M0,15 T30,22 T60,5 T90,15" />
                    </svg>
                  </div>
                </div>

                {/* Metric 4 */}
                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm relative overflow-hidden flex flex-col justify-between h-32">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Active Integrations</span>
                    <h3 className="text-2xl font-bold text-slate-100 mt-2">{analytics?.stats?.total_users || 0}</h3>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-white/[0.03] pt-2">
                    <span className="text-slate-400 font-semibold">
                      {analytics?.stats?.total_projects || 0} workspaces
                    </span>
                    <svg viewBox="0 0 100 30" className="w-16 h-6 text-cfGreen stroke-current fill-none stroke-2">
                      <path d="M0,25 T20,22 T50,25 T90,20" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Stacked Threat Timeline */}
              <div className="p-6 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm">
                <h3 className="text-xs font-bold uppercase tracking-widest mb-6 text-slate-400">Threat Mitigation Trend (Last 30 Days)</h3>
                
                {analytics?.daily_stats && analytics.daily_stats.length > 0 ? (
                  <div className="space-y-4">
                    {/* Graph Plot */}
                    <div className="h-56 w-full flex items-end gap-1.5 pt-6 border-b border-white/[0.04] px-2">
                      {analytics.daily_stats.map((dayStat, idx) => {
                        const totalDay = dayStat.bots + dayStat.humans;
                        const maxTotal = Math.max(...analytics.daily_stats.map(d => d.bots + d.humans), 10);
                        const barHeight = (totalDay / maxTotal) * 100;
                        
                        const botPct = totalDay > 0 ? (dayStat.bots / totalDay) * 100 : 0;
                        const humanPct = totalDay > 0 ? (dayStat.humans / totalDay) * 100 : 0;

                        return (
                          <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer">
                            {/* Hover info panel */}
                            <div className="absolute bottom-full mb-2 bg-[#090d16] border border-white/[0.06] p-2.5 rounded-lg shadow-xl hidden group-hover:block z-30 text-[10px] min-w-[120px]">
                              <p className="font-bold text-slate-200 mb-1">{dayStat.day}</p>
                              <p className="flex items-center justify-between text-cfGreen">Humans: <span>{dayStat.humans}</span></p>
                              <p className="flex items-center justify-between text-cfOrange">Bots: <span>{dayStat.bots}</span></p>
                            </div>
                            
                            {/* Stacked Bar */}
                            <div 
                              style={{ height: `${Math.max(barHeight, 5)}%` }} 
                              className="w-full rounded-t-sm overflow-hidden flex flex-col justify-end transition-all group-hover:opacity-80"
                            >
                              <div style={{ height: `${botPct}%` }} className="bg-cfOrange w-full"></div>
                              <div style={{ height: `${humanPct}%` }} className="bg-slate-700 w-full"></div>
                            </div>
                            <span className="text-[9px] text-slate-500 mt-2 truncate w-full text-center group-hover:text-slate-300">
                              {dayStat.day.split('-')[2]}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    {/* Graph Keys */}
                    <div className="flex gap-6 justify-center text-[10px] font-semibold uppercase tracking-widest pt-2">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 bg-slate-700 rounded-sm"></span>
                        <span className="text-slate-400">Verified Humans</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 bg-cfOrange rounded-sm"></span>
                        <span className="text-slate-400">Mitigated Bots</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-16 text-slate-600">
                    <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-25" />
                    <p className="text-xs">No analytics logged yet. Verification metrics will display here.</p>
                  </div>
                )}
              </div>

              {/* Top active projects */}
              <div className="p-6 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm">
                <h3 className="text-xs font-bold uppercase tracking-widest mb-6 text-slate-400">Active Workspaces Summary</h3>
                {analytics?.top_projects && analytics.top_projects.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-white/[0.04] text-[10px] uppercase tracking-wider text-slate-500 bg-white/[0.01]">
                          <th className="py-3.5 px-6 font-semibold">Workspace Name</th>
                          <th className="py-3.5 px-6 font-semibold">Developer Account</th>
                          <th className="py-3.5 px-6 font-semibold">ID Token</th>
                          <th className="py-3.5 px-6 font-semibold text-right">Telemetry Requests</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analytics.top_projects.map((proj) => (
                          <tr key={proj.project_id} className="border-b border-white/[0.04] text-xs hover:bg-white/[0.01] transition-colors">
                            <td className="py-4 px-6 font-bold text-slate-300">{proj.project_name}</td>
                            <td className="py-4 px-6 text-slate-400">{proj.owner_email}</td>
                            <td className="py-4 px-6 font-mono text-[10px] text-slate-500">{proj.project_id}</td>
                            <td className="py-4 px-6 font-bold text-right text-cfOrange">{proj.request_count.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-6 text-slate-500 text-xs">
                    No active workspaces found.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW 2: Developer accounts */}
          {activeTab === 'developers' && (
            <div className="space-y-6">
              <div className="p-4 border border-white/[0.04] bg-[#0b0f19] rounded-lg flex items-center justify-between shadow-sm">
                <div className="flex-1 max-w-md relative">
                  <Search className="w-4 h-4 text-slate-600 absolute left-4 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search developer accounts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-11 pr-4 py-2 bg-[#05070F] border border-white/[0.06] focus:border-cfOrange rounded-lg text-xs text-slate-200 focus:outline-none placeholder-slate-600 transition-colors"
                  />
                </div>
              </div>

              <div className="p-6 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-white/[0.04] text-[10px] uppercase tracking-wider text-slate-500 bg-white/[0.01]">
                        <th className="py-3.5 px-6 font-semibold">Account Email</th>
                        <th className="py-3.5 px-6 font-semibold">Full Name</th>
                        <th className="py-3.5 px-6 font-semibold">Company Name</th>
                        <th className="py-3.5 px-6 font-semibold">Active Workspaces</th>
                        <th className="py-3.5 px-6 font-semibold">API Requests</th>
                        <th className="py-3.5 px-6 font-semibold">Registered</th>
                        <th className="py-3.5 px-6 font-semibold">Status</th>
                        <th className="py-3.5 px-6 font-semibold text-right">Actions</th>
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
                          <tr key={dev.id} className="border-b border-white/[0.04] text-xs hover:bg-white/[0.01] transition-colors">
                            <td className="py-4 px-6 font-bold text-slate-300">{dev.email}</td>
                            <td className="py-4 px-6 text-slate-400">{dev.full_name || '-'}</td>
                            <td className="py-4 px-6 text-slate-400">{dev.company_name || '-'}</td>
                            <td className="py-4 px-6 font-semibold text-cfBlue">{dev.project_count} projects</td>
                            <td className="py-4 px-6 font-bold text-slate-300">{dev.total_requests.toLocaleString()}</td>
                            <td className="py-4 px-6 text-slate-500">
                              {new Date(dev.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-4 px-6">
                              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase border ${
                                dev.is_active 
                                  ? 'bg-cfGreen/10 text-cfGreen border-cfGreen/20' 
                                  : 'bg-cfRed/10 text-cfRed border-cfRed/20'
                              }`}>
                                {dev.is_active ? 'Active' : 'Suspended'}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-right">
                              {dev.email !== 'developer@nextcaptcha.com' && dev.email !== user.email && (
                                <button
                                  onClick={() => toggleUserStatus(dev.id, dev.is_active)}
                                  className={`px-2.5 py-1.5 rounded-lg text-[10px] font-bold uppercase transition-all inline-flex items-center gap-1.5 ${
                                    dev.is_active 
                                      ? 'bg-cfRed/10 hover:bg-cfRed/20 text-cfRed' 
                                      : 'bg-cfGreen/10 hover:bg-cfGreen/20 text-cfGreen'
                                  }`}
                                >
                                  {dev.is_active ? (
                                    <>
                                      <UserX className="w-3 h-3" /> Suspend
                                    </>
                                  ) : (
                                    <>
                                      <UserCheck className="w-3 h-3" /> Activate
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

          {/* VIEW 3: Threat Feed */}
          {activeTab === 'threats' && (
            <div className="space-y-6">
              <div className="p-6 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm">
                <h3 className="text-xs font-bold uppercase tracking-widest mb-2 text-slate-400">Real-Time Threat Intelligence</h3>
                <p className="text-[10px] text-slate-500 mb-6">Listing the last 100 verification telemetry payloads evaluated by the Random Forest model across all registered client websites.</p>
                
                {sessions && sessions.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-white/[0.04] text-[10px] uppercase tracking-wider text-slate-500 bg-white/[0.01]">
                          <th className="py-3.5 px-6 font-semibold">Session ID</th>
                          <th className="py-3.5 px-6 font-semibold">Workspace Project</th>
                          <th className="py-3.5 px-6 font-semibold">Client Platform</th>
                          <th className="py-3.5 px-6 font-semibold">Biometric Score</th>
                          <th className="py-3.5 px-6 font-semibold">Automation</th>
                          <th className="py-3.5 px-6 font-semibold">Security Action</th>
                          <th className="py-3.5 px-6 font-semibold text-right">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sessions.map((sess) => (
                          <tr key={sess.id} className="border-b border-white/[0.04] text-xs hover:bg-white/[0.01] transition-colors">
                            <td className="py-4 px-6 font-mono text-[10px] text-slate-500">{sess.id}</td>
                            <td className="py-4 px-6 font-semibold text-slate-300">{sess.project_name}</td>
                            <td className="py-4 px-6 text-slate-400 truncate max-w-[150px]" title={sess.user_agent}>
                              <span className="px-2 py-0.5 bg-white/[0.02] border border-white/[0.06] rounded text-[9px] uppercase font-bold text-slate-400">
                                {sess.device_type}
                              </span>
                            </td>
                            <td className="py-4 px-6">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-200">{sess.risk_score}%</span>
                                <div className="w-16 h-1 bg-slate-800 rounded-full overflow-hidden">
                                  <div 
                                    style={{ width: `${sess.risk_score}%` }} 
                                    className={`h-full ${sess.risk_score >= 50 ? 'bg-cfRed' : sess.risk_score >= 20 ? 'bg-cfAmber' : 'bg-cfGreen'}`}
                                  ></div>
                                </div>
                              </div>
                            </td>
                            <td className="py-4 px-6">
                              <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${
                                sess.webdriver_flag 
                                  ? 'bg-cfRed/10 text-cfRed border-cfRed/20' 
                                  : 'bg-white/[0.02] text-slate-500 border-white/[0.06]'
                              }`}>
                                {sess.webdriver_flag ? 'WebDriver' : 'Normal'}
                              </span>
                            </td>
                            <td className="py-4 px-6">
                              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase border ${
                                (sess.verdict === 'accept' || sess.verdict === 'human' || sess.verdict === 'allow')
                                  ? 'bg-cfGreen/10 text-cfGreen border-cfGreen/20'
                                  : sess.verdict === 'challenge'
                                  ? 'bg-cfAmber/10 text-cfAmber border-cfAmber/20'
                                  : 'bg-cfRed/10 text-cfRed border-cfRed/20'
                              }`}>
                                {sess.verdict}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-right text-slate-500">
                              {new Date(sess.created_at).toLocaleTimeString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-16 text-slate-600">
                    <Terminal className="w-12 h-12 mx-auto mb-3 opacity-25" />
                    <p className="text-xs">Threat feed is empty. Verification telemetry will stream here.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW 4: Infrastructure Specs */}
          {activeTab === 'system' && (
            <div className="space-y-8">
              <div className="grid md:grid-cols-3 gap-4">
                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg flex items-start gap-4 shadow-sm">
                  <div className="p-2.5 bg-cfBlue/10 border border-cfBlue/20 rounded-lg">
                    <Database className="w-5 h-5 text-cfBlue" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider">Supabase Connection Pool</h3>
                    <p className="text-[10px] text-cfGreen font-bold mt-1">Status: Connected</p>
                    <p className="text-[11px] text-slate-500 mt-2">Active PostgreSQL connection pool utilizing PgBouncer port 6543.</p>
                  </div>
                </div>

                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg flex items-start gap-4 shadow-sm">
                  <div className="p-2.5 bg-cfOrange/10 border border-cfOrange/20 rounded-lg">
                    <Cpu className="w-5 h-5 text-cfOrange" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider">Biometric Model Engine</h3>
                    <p className="text-[10px] text-cfOrange font-bold mt-1">Algorithm: Random Forest</p>
                    <p className="text-[11px] text-slate-500 mt-2">Loaded standard model RF v3 (52 telemetry features evaluated in &lt;1.5ms).</p>
                  </div>
                </div>

                <div className="p-5 border border-white/[0.04] bg-[#0b0f19] rounded-lg flex items-start gap-4 shadow-sm">
                  <div className="p-2.5 bg-cfRed/10 border border-cfRed/20 rounded-lg">
                    <Lock className="w-5 h-5 text-cfRed" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider">Credential Encryption</h3>
                    <p className="text-[10px] text-cfRed font-bold mt-1">Algorithm: bcrypt</p>
                    <p className="text-[11px] text-slate-500 mt-2">Authentication securely hashed via bcrypt. Local validation locked via verify-credentials endpoint.</p>
                  </div>
                </div>
              </div>

              <div className="p-6 border border-white/[0.04] bg-[#0b0f19] rounded-lg shadow-sm">
                <h3 className="text-xs font-bold uppercase tracking-widest mb-4 text-slate-400">Decision Classification Weights</h3>
                <p className="text-[10px] text-slate-500 mb-6">List of heuristic thresholds configured inside the Random Forest logic model.</p>
                
                <div className="grid md:grid-cols-2 gap-8 text-xs">
                  <div className="p-5 bg-white/[0.01] rounded-lg border border-white/[0.04]">
                    <h4 className="font-bold mb-4 text-slate-300 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-cfBlue" />
                      Classification Zones
                    </h4>
                    <ul className="space-y-3 text-xs text-slate-400">
                      <li className="flex justify-between border-b border-white/[0.03] pb-2">
                        <span>Low Risk threshold (Auto-Accept)</span>
                        <span className="font-mono font-bold text-cfGreen">&lt; 20%</span>
                      </li>
                      <li className="flex justify-between border-b border-white/[0.03] pb-2">
                        <span>Interactive Challenge Zone</span>
                        <span className="font-mono font-bold text-cfAmber">20% - 50%</span>
                      </li>
                      <li className="flex justify-between">
                        <span>High Risk threshold (Auto-Reject)</span>
                        <span className="font-mono font-bold text-cfRed">&gt; 50%</span>
                      </li>
                    </ul>
                  </div>

                  <div className="p-5 bg-white/[0.01] rounded-lg border border-white/[0.04]">
                    <h4 className="font-bold mb-4 text-slate-300 flex items-center gap-2">
                      <Shield className="w-4 h-4 text-cfOrange" />
                      Heuristic Rule Boosting
                    </h4>
                    <ul className="space-y-3 text-xs text-slate-400">
                      <li className="flex justify-between border-b border-white/[0.03] pb-2">
                        <span>WebDriver Automation Flag Detected</span>
                        <span className="font-mono font-bold text-cfRed">+ 35% Risk</span>
                      </li>
                      <li className="flex justify-between border-b border-white/[0.03] pb-2">
                        <span>Abnormal mouse click timing patterns</span>
                        <span className="font-mono font-bold text-cfAmber">+ 12% Risk</span>
                      </li>
                      <li className="flex justify-between">
                        <span>Straight Bezier curve click pathing</span>
                        <span className="font-mono font-bold text-cfAmber">+ 8% Risk</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import {
  Key,
  Plus,
  Copy,
  Trash2,
  CheckCircle2,
  XCircle,
  BookOpen
} from 'lucide-react';
import CodeBlock from '../../components/docs/CodeBlock';
import SiteNav from '../../components/chrome/SiteNav';
import { scriptTagSnippet, siteverifyCurlSnippet } from '../../components/docs/docSnippets';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.veilproof.tech';

/** Turn free-text into hostname list (comma or newline separated). */
function parseDomainsInput(raw) {
  return String(raw || '')
    .split(/[,\n]+/)
    .map((part) => {
      let d = part.trim().toLowerCase();
      if (!d) return '';
      if (d === '*') return '*';
      d = d.replace(/^https?:\/\//, '');
      d = d.split('/')[0].split('?')[0];
      if (d.startsWith('*.')) d = d.slice(2);
      if (d.includes(':') && !d.startsWith('[')) d = d.replace(/:\d+$/, '');
      return d;
    })
    .filter(Boolean)
    .filter((d, i, arr) => arr.indexOf(d) === i);
}

function domainsToInput(domains) {
  if (!domains || domains.length === 0) return '';
  return domains.join(', ');
}

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);
  const [apiKeys, setApiKeys] = useState({});
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDomains, setNewProjectDomains] = useState('');
  const [editDomains, setEditDomains] = useState('');
  const [generatedPair, setGeneratedPair] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [authMode, setAuthMode] = useState('login'); // login | signup
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');

  const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '40763777720-bb2cmdjfi2p15h03pclgpfoklachvmpp.apps.googleusercontent.com';

  const persistSession = (data) => {
    setUser(data.user);
    localStorage.setItem('veilproof_user', JSON.stringify(data.user));
    localStorage.setItem('veilproof_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('veilproof_refresh_token', data.refresh_token);
    }
  };

  const clearSession = () => {
    localStorage.removeItem('veilproof_user');
    localStorage.removeItem('veilproof_token');
    localStorage.removeItem('veilproof_refresh_token');
    setUser(null);
  };

  const apiFetch = async (path, options = {}) => {
    const headers = { ...(options.headers || {}) };
    const token = localStorage.getItem('veilproof_token');
    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`;
    }
    let response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
    if (response.status === 401 && localStorage.getItem('veilproof_refresh_token')) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        headers.Authorization = `Bearer ${localStorage.getItem('veilproof_token')}`;
        response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
      }
    }
    return response;
  };

  const refreshAccessToken = async () => {
    const refresh = localStorage.getItem('veilproof_refresh_token');
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_BASE_URL}/admin/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        clearSession();
        return false;
      }
      localStorage.setItem('veilproof_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('veilproof_refresh_token', data.refresh_token);
      }
      if (data.user) {
        const merged = { ...(JSON.parse(localStorage.getItem('veilproof_user') || '{}')), ...data.user };
        localStorage.setItem('veilproof_user', JSON.stringify(merged));
        setUser(merged);
      }
      return true;
    } catch {
      clearSession();
      return false;
    }
  };

  const initializeGoogleSignIn = () => {
    if (window.google && window.google.accounts) {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLoginSuccess
      });

      const buttonContainer = document.getElementById('google-btn-container');
      if (buttonContainer) {
        buttonContainer.innerHTML = '';
        window.google.accounts.id.renderButton(
          buttonContainer,
          { theme: 'filled_black', size: 'large', width: 380, shape: 'rectangular' }
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
        persistSession(data);
        loadProjects(data.access_token);
      } else {
        setError(typeof data.detail === 'string' ? data.detail : 'Google sign-in failed');
      }
    } catch (err) {
      setError('Failed to authenticate with Google');
    }
    setLoading(false);
  };

  const handleEmailAuth = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    if (authMode === 'signup') {
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        setLoading(false);
        return;
      }
      if (password.length < 12) {
        setError('Password must be at least 12 characters');
        setLoading(false);
        return;
      }
    }

    try {
      const path = authMode === 'signup' ? '/admin/register' : '/admin/login';
      const body =
        authMode === 'signup'
          ? { email, password, full_name: fullName || undefined }
          : { email, password };
      const res = await fetch(`${API_BASE_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        const detail = data.detail;
        setError(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg || 'Request failed' : 'Authentication failed');
        setLoading(false);
        return;
      }
      persistSession(data);
      setPassword('');
      setConfirmPassword('');
      loadProjects(data.access_token);
    } catch {
      setError(authMode === 'signup' ? 'Signup failed' : 'Login failed');
    }
    setLoading(false);
  };

  // Check for logged in user and load Google SDK
  useEffect(() => {
    const savedUser = localStorage.getItem('veilproof_user');
    const savedToken = localStorage.getItem('veilproof_token');
    if (savedUser && savedToken) {
      setUser(JSON.parse(savedUser));
      loadProjects(savedToken);
    } else {
      if (!document.getElementById('google-jssdk')) {
        const script = document.createElement('script');
        script.id = 'google-jssdk';
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

  useEffect(() => {
    if (!user) {
      setTimeout(initializeGoogleSignIn, 250);
    }
  }, [user, authMode]);

  const loadProjects = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/projects`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 401) {
        const ok = await refreshAccessToken();
        if (ok) return loadProjects(localStorage.getItem('veilproof_token'));
        clearSession();
        setError('Session expired — please sign in again');
        return;
      }
      const data = await response.json();
      if (data.success && data.projects.length > 0) {
        setProjects(data.projects);
        const defaultProj = data.projects[0];
        setSelectedProject(defaultProj.id);
        setEditDomains(domainsToInput(defaultProj.allowed_domains));
        loadApiKeys(defaultProj.id);
      } else if (data.success) {
        setProjects([]);
      }
    } catch (err) {
      setError('Failed to load projects');
    }
  };

  const loadApiKeys = async (projectId) => {
    try {
      const token = localStorage.getItem('veilproof_token');
      const response = await fetch(`${API_BASE_URL}/admin/api-keys/${projectId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success) {
        setApiKeys(prev => ({ ...prev, [projectId]: data.api_keys }));
      }
    } catch (err) {
      setError('Failed to load API keys');
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('veilproof_token');
      const domains = parseDomainsInput(newProjectDomains);
      const response = await fetch(`${API_BASE_URL}/admin/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newProjectName,
          allowed_domains: domains
        })
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('Project created successfully');
        setNewProjectName('');
        setNewProjectDomains('');
        setShowCreateProject(false);
        loadProjects(token);
      } else {
        setError(data.detail || 'Failed to create project');
      }
    } catch (err) {
      setError('Failed to create project');
    }
    setLoading(false);
  };

  const handleSaveDomains = async () => {
    if (!selectedProject) return;
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const token = localStorage.getItem('veilproof_token');
      const domains = parseDomainsInput(editDomains);
      const response = await fetch(`${API_BASE_URL}/admin/projects/${selectedProject}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ allowed_domains: domains })
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('Allowed domains updated');
        setProjects((prev) =>
          prev.map((p) => (p.id === selectedProject ? { ...p, ...data.project } : p))
        );
        setEditDomains(domainsToInput(data.project.allowed_domains));
      } else {
        setError(data.detail || 'Failed to update domains');
      }
    } catch (err) {
      setError('Failed to update domains');
    }
    setLoading(false);
  };

  const handleCreateKeyPair = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('veilproof_token');
      const response = await fetch(`${API_BASE_URL}/admin/api-keys/pair`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ project_id: selectedProject })
      });
      const data = await response.json();
      if (data.success) {
        setGeneratedPair({ siteKey: data.site_key.api_key, secretKey: data.secret_key.api_key });
        setSuccess('API key pair generated successfully');
        setShowCreateKey(false);
        loadApiKeys(selectedProject);
      } else {
        setError(data.detail || 'Failed to generate API key pair');
      }
    } catch (err) {
      setError('Failed to generate API key pair');
    }
    setLoading(false);
  };

  const handleRevokeKey = async (keyId) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('veilproof_token');
      const response = await fetch(`${API_BASE_URL}/admin/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('API key revoked successfully');
        loadApiKeys(selectedProject);
      } else {
        setError(data.detail || 'Failed to revoke API key');
      }
    } catch (err) {
      setError('Failed to revoke API key');
    }
    setLoading(false);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard');
    setTimeout(() => setSuccess(''), 2000);
  };

  const handleLogout = async () => {
    const refresh = localStorage.getItem('veilproof_refresh_token');
    try {
      if (refresh) {
        await fetch(`${API_BASE_URL}/admin/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh }),
        });
      }
    } catch {
      // ignore network errors on logout
    }
    clearSession();
    window.location.href = '/dashboard';
  };

  const selectProject = (projectId) => {
    setSelectedProject(projectId);
    const project = projects.find((p) => p.id === projectId);
    setEditDomains(domainsToInput(project?.allowed_domains));
    if (!apiKeys[projectId]) loadApiKeys(projectId);
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-canvas text-ink">
        <SiteNav />
        <div className="dashboard-login min-h-[calc(100vh-64px)] flex items-center justify-center px-6">
          <div className="dashboard-login-panel max-w-md w-full card p-8">
          <div className="text-center mb-6">
            <img src="/veilproof-mark.png" alt="VeilProof" className="dashboard-login-logo" />
            <h1 className="text-2xl font-semibold mb-2">
              <span className="font-brand font-bold uppercase tracking-wide">VeilProof</span> Dashboard
            </h1>
            <p className="text-mute text-sm">Sign in to manage projects, domains, and API keys</p>
          </div>

          <div className="flex mb-5 p-1 bg-canvas border border-hairline rounded-lg">
            <button
              type="button"
              onClick={() => { setAuthMode('login'); setError(''); }}
              className={`flex-1 h-9 rounded-md text-sm font-semibold transition-colors ${
                authMode === 'login' ? 'bg-white/10 text-ink' : 'text-mute hover:text-ink'
              }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => { setAuthMode('signup'); setError(''); }}
              className={`flex-1 h-9 rounded-md text-sm font-semibold transition-colors ${
                authMode === 'signup' ? 'bg-white/10 text-ink' : 'text-mute hover:text-ink'
              }`}
            >
              Sign up
            </button>
          </div>

          <form onSubmit={handleEmailAuth} className="space-y-3 mb-5">
            {authMode === 'signup' && (
              <label className="block text-xs font-bold text-mute uppercase tracking-wider">
                Full name <span className="font-normal normal-case">(optional)</span>
                <input
                  type="text"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
                />
              </label>
            )}
            <label className="block text-xs font-bold text-mute uppercase tracking-wider">
              Email
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
              />
            </label>
            <label className="block text-xs font-bold text-mute uppercase tracking-wider">
              Password
              <input
                type="password"
                required
                minLength={authMode === 'signup' ? 12 : 1}
                autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
              />
            </label>
            {authMode === 'signup' && (
              <>
                <label className="block text-xs font-bold text-mute uppercase tracking-wider">
                  Confirm password
                  <input
                    type="password"
                    required
                    minLength={12}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
                  />
                </label>
                <p className="text-mute text-xs leading-relaxed">
                  Use at least 12 characters. Avoid common passwords and your email name.
                </p>
              </>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-primary hover:bg-primaryDark disabled:opacity-50 text-white rounded-md font-bold text-sm transition-colors"
            >
              {loading ? 'Please wait…' : authMode === 'signup' ? 'Create account' : 'Log in'}
            </button>
          </form>

          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-hairline" /></div>
            <div className="relative flex justify-center text-xs uppercase tracking-wider">
              <span className="bg-[var(--card-bg,transparent)] px-3 text-mute">or continue with Google</span>
            </div>
          </div>

          <div className="space-y-6 flex flex-col items-center">
            <div id="google-btn-container" className="w-full flex justify-center py-1 min-h-[50px]"></div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-dangerSoft border border-danger/25 rounded-lg text-danger text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 p-3 bg-primarySoft border border-primary/25 rounded-lg text-primary text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              {success}
            </div>
          )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-shell min-h-screen bg-canvas text-ink">
      <SiteNav user={user} onLogout={handleLogout} />

      <div className="dashboard-content max-w-[1280px] mx-auto px-6 py-10">
        {/* Success/Error Messages */}
        {error && (
          <div className="mb-4 p-3 bg-dangerSoft border border-danger/25 rounded-lg text-danger text-sm flex items-center gap-2">
            <XCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-primarySoft border border-primary/25 rounded-lg text-primary text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            {success}
          </div>
        )}

        <div className="mb-6 card p-4 flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex-1 flex flex-wrap gap-2">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => selectProject(project.id)}
                className={`px-4 h-10 rounded-md text-sm font-semibold border transition-all ${
                  selectedProject === project.id
                    ? 'bg-primarySoft text-primary border-primary/30'
                    : 'bg-canvas text-mute border-hairline hover:text-ink hover:border-hairlineStrong'
                }`}
              >
                {project.name}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowCreateProject(!showCreateProject)}
            className="flex items-center justify-center gap-2 bg-primary hover:bg-primaryDark text-white px-5 h-10 rounded-md font-bold transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            Create Project
          </button>
        </div>

        {showCreateProject && (
          <div className="mb-6 card p-6">
            <h3 className="font-bold text-base mb-2">Create Project</h3>
            <p className="text-mute text-sm mb-4">
              A project holds your site/secret keys and which websites may use them.
            </p>
            <div className="space-y-4">
              <label className="block text-xs font-bold text-mute uppercase tracking-wider">
                Project name
                <input
                  value={newProjectName}
                  onChange={(event) => setNewProjectName(event.target.value)}
                  placeholder="e.g. Production website"
                  className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
                />
              </label>
              <label className="block text-xs font-bold text-mute uppercase tracking-wider">
                Allowed domains
                <textarea
                  value={newProjectDomains}
                  onChange={(event) => setNewProjectDomains(event.target.value)}
                  rows={3}
                  placeholder="example.com, www.example.com, localhost"
                  className="mt-2 w-full px-4 py-3 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60 resize-y"
                />
              </label>
              <div className="text-mute text-xs leading-relaxed space-y-1 bg-canvas border border-hairline rounded-md p-3">
                <p><strong className="text-ink">How to fill this:</strong> list the hostnames where your site key will run, separated by commas.</p>
                <p>✅ Good: <code className="text-primary">myshop.com, www.myshop.com, localhost</code></p>
                <p>❌ Avoid: <code className="text-primary">https://myshop.com/signup</code> (we strip this automatically, but hostnames are clearer)</p>
                <p>Leave empty to allow <strong className="text-ink">any</strong> domain (fine for local testing; lock it down before launch).</p>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <button
                onClick={handleCreateProject}
                disabled={loading || !newProjectName.trim()}
                className="bg-primary hover:bg-primaryDark disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 h-10 rounded-md font-bold transition-colors text-sm"
              >
                {loading ? 'Creating...' : 'Create Project'}
              </button>
              <button
                onClick={() => setShowCreateProject(false)}
                className="bg-canvas hover:bg-surfaceSoft text-ink px-5 h-10 rounded-md font-bold transition-colors border border-hairline text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {selectedProject && (
          <div className="mb-6 card p-6">
            <h3 className="font-bold text-base mb-1">Allowed domains</h3>
            <p className="text-mute text-sm mb-4">
              Only these websites can use this project&apos;s <strong className="text-ink">site key</strong> in the browser.
              Subdomains of a listed domain are included automatically (e.g. <code className="text-primary">shop.example.com</code> if you add <code className="text-primary">example.com</code>).
            </p>
            <textarea
              value={editDomains}
              onChange={(event) => setEditDomains(event.target.value)}
              rows={3}
              placeholder="example.com, www.example.com, localhost"
              className="w-full px-4 py-3 bg-canvas border border-hairline rounded-md text-ink text-sm outline-none focus:border-primary/60 resize-y"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                onClick={handleSaveDomains}
                disabled={loading}
                className="bg-primary hover:bg-primaryDark disabled:opacity-50 text-white px-5 h-10 rounded-md font-bold transition-colors text-sm"
              >
                {loading ? 'Saving...' : 'Save domains'}
              </button>
              <span className="text-mute text-xs">
                Empty = all domains allowed. Use commas or new lines between hosts.
              </span>
            </div>
          </div>
        )}

        {/* Generated Key Pair Panel */}
        {generatedPair && (
          <div className="mb-6 p-6 bg-primarySoft border border-primary/25 rounded-lg">
            <h3 className="font-bold mb-2 flex items-center gap-2">
              <Key className="w-5 h-5 text-primary" />
              API Key Pair Generated
            </h3>
            <p className="text-mute text-sm mb-4">
              Copy these now — the secret key won't be shown again.
            </p>

            <div className="space-y-3 mb-6">
              <div>
                <label className="block text-xs font-bold text-mute uppercase tracking-wider mb-1">Site key (browser)</label>
                <div className="flex gap-2">
                  <input type="text" value={generatedPair.siteKey} readOnly className="flex-1 px-4 py-2 bg-canvas border border-hairline rounded-lg font-mono text-sm" />
                  <button onClick={() => copyToClipboard(generatedPair.siteKey)} className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold">
                    <Copy className="w-4 h-4" /> Copy
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-mute uppercase tracking-wider mb-1">Secret key (server only — never expose in browser code)</label>
                <div className="flex gap-2">
                  <input type="text" value={generatedPair.secretKey} readOnly className="flex-1 px-4 py-2 bg-canvas border border-hairline rounded-lg font-mono text-sm" />
                  <button onClick={() => copyToClipboard(generatedPair.secretKey)} className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold">
                    <Copy className="w-4 h-4" /> Copy
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs font-bold text-mute uppercase tracking-wider mb-2">Next steps: drop this in your HTML</p>
                <CodeBlock language="html" code={scriptTagSnippet(generatedPair.siteKey)} />
              </div>
              <div>
                <p className="text-xs font-bold text-mute uppercase tracking-wider mb-2">Then verify server-side</p>
                <CodeBlock language="bash" code={siteverifyCurlSnippet(generatedPair.secretKey)} />
              </div>
              <a href="/docs#client" className="inline-flex items-center gap-2 text-primary hover:underline text-sm font-semibold">
                <BookOpen className="w-4 h-4" /> Integration guide →
              </a>
            </div>

            <button
              onClick={() => setGeneratedPair(null)}
              className="mt-6 text-mute hover:text-ink text-sm font-semibold"
            >
              Close
            </button>
          </div>
        )}

        {/* API Keys Console */}
        {selectedProject && (
          <div className="card overflow-hidden">
            {/* Header info */}
            <div className="p-8 border-b border-hairline flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold mb-1">API Keys</h2>
                <p className="text-mute text-sm max-w-xl">
                  Site keys authenticate your client SDK; secret keys verify decisions server-side. Keep secret keys out of public repositories and browser code.
                </p>
                <a href="/docs#client" className="inline-flex items-center gap-1.5 text-primary hover:underline text-sm font-semibold mt-2">
                  <BookOpen className="w-4 h-4" /> Integration guide →
                </a>
              </div>
              <div>
                <button
                  onClick={() => setShowCreateKey(true)}
                  className="flex items-center gap-2 bg-primary hover:bg-primaryDark text-white px-5 h-11 rounded-lg font-bold transition-colors text-sm"
                >
                  <Plus className="w-4 h-4" />
                  Create API Key Pair
                </button>
              </div>
            </div>

            {/* Generate Key Pair Panel */}
            {showCreateKey && (
              <div className="p-8 bg-surfaceSoft border-b border-hairline">
                <div className="max-w-md">
                  <h3 className="font-bold text-base mb-2">Generate API Key Pair</h3>
                  <p className="text-mute text-sm mb-4">
                    Creates a site key (for your browser SDK) and a secret key (for server-side verification), shown once.
                  </p>
                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={handleCreateKeyPair}
                      disabled={loading}
                      className="flex-1 bg-primary hover:bg-primaryDark text-white h-11 rounded-lg font-bold transition-colors text-sm"
                    >
                      {loading ? 'Generating...' : 'Create Key Pair'}
                    </button>
                    <button
                      onClick={() => setShowCreateKey(false)}
                      className="flex-1 bg-canvas hover:bg-surfaceSoft text-ink h-11 rounded-lg font-bold transition-colors border border-hairline text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Keys Table */}
            {apiKeys[selectedProject] && apiKeys[selectedProject].length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-hairline text-xs uppercase tracking-wider text-mute bg-surfaceSoft">
                      <th className="py-4 px-6 font-bold">Name</th>
                      <th className="py-4 px-6 font-bold">Key Token</th>
                      <th className="py-4 px-6 font-bold">Created</th>
                      <th className="py-4 px-6 font-bold">Last Used</th>
                      <th className="py-4 px-6 font-bold">Status</th>
                      <th className="py-4 px-6 font-bold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(apiKeys[selectedProject] || []).map((key) => {
                      const keyType = key.key_type || 'legacy';
                      const badgeClasses = {
                        site: 'bg-primarySoft text-primary border-primary/25',
                        secret: 'bg-dangerSoft text-danger border-danger/25',
                        legacy: 'bg-warningSoft text-warning border-warning/25',
                        live: 'bg-primarySoft text-primary border-primary/25',
                        test: 'bg-warningSoft text-warning border-warning/25',
                      }[keyType] || 'bg-warningSoft text-warning border-warning/25';
                      return (
                        <tr key={key.id} className="border-b border-hairline text-sm hover:bg-surfaceSoft/60 transition-colors">
                          <td className="py-4 px-6 font-medium">
                            <span className={`px-2 py-1 rounded-lg text-xs font-bold uppercase border ${badgeClasses}`}>
                              {keyType}
                            </span>
                          </td>
                          <td className="py-4 px-6 font-mono text-xs text-mute">
                            <div className="flex items-center gap-2">
                              <span title="Only the prefix is stored — the full key was shown once at creation and can't be retrieved again">{key.key_prefix}...</span>
                              <button
                                onClick={() => copyToClipboard(key.key_prefix)}
                                className="text-mute hover:text-ink p-1 rounded-lg hover:bg-surfaceSoft transition-colors"
                                title="Copy prefix only — full key was shown once at creation and isn't retrievable again"
                              >
                                <Copy className="w-3 h-3" />
                              </button>
                            </div>
                          </td>
                          <td className="py-4 px-6 text-mute">
                            {new Date(key.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-4 px-6 text-mute">
                            {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}
                          </td>
                          <td className="py-4 px-6">
                            <span className={`px-2.5 py-0.5 rounded-lg text-xs font-bold ${
                              key.is_active ? 'bg-successSoft text-success border border-success/25' : 'bg-dangerSoft text-danger border border-danger/25'
                            }`}>
                              {key.is_active ? 'Active' : 'Revoked'}
                            </span>
                          </td>
                          <td className="py-4 px-6 text-right">
                            {key.is_active && (
                              <button
                                onClick={() => handleRevokeKey(key.id)}
                                className="p-1.5 hover:bg-dangerSoft text-danger rounded-lg transition-colors inline-flex items-center gap-1.5 text-xs font-bold"
                              >
                                <Trash2 className="w-4 h-4" /> Revoke
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-16 bg-surfaceSoft/50">
                <Key className="w-10 h-10 mx-auto mb-4 text-mute opacity-40" />
                <h3 className="font-bold text-base mb-1">No API keys yet</h3>
                <p className="text-sm text-mute mb-6 max-w-sm mx-auto">
                  Get started by generating your first live or test API credentials.
                </p>
                <button
                  onClick={() => setShowCreateKey(true)}
                  className="bg-primary hover:bg-primaryDark text-white px-5 h-11 rounded-lg text-sm font-bold transition-colors"
                >
                  Create API Key
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Shield,
  Key,
  Plus,
  Copy,
  Trash2,
  CheckCircle2,
  XCircle,
  LogOut,
  Building2,
  Globe,
  BookOpen
} from 'lucide-react';
import CodeBlock from '../../components/docs/CodeBlock';
import { scriptTagSnippet, siteverifyCurlSnippet } from '../../components/docs/docSnippets';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://next-captcha-sdk.onrender.com';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);
  const [apiKeys, setApiKeys] = useState({});
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDomains, setNewProjectDomains] = useState('');
  const [generatedPair, setGeneratedPair] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '282307677315-065loak66lukfcde3om7926hcao8tkf8.apps.googleusercontent.com';

  const initializeGoogleSignIn = () => {
    if (window.google && window.google.accounts) {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLoginSuccess
      });

      const buttonContainer = document.getElementById('google-btn-container');
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
        setUser(data.user);
        localStorage.setItem('veriflow_user', JSON.stringify(data.user));
        localStorage.setItem('veriflow_token', data.access_token);
        loadProjects(data.access_token);
      } else {
        setError(data.detail || 'Google Authentication failed');
      }
    } catch (err) {
      setError('Failed to authenticate with Google');
    }
    setLoading(false);
  };

  // Local-only bypass: compiled out of production builds (NODE_ENV is inlined at build time)
  const MOCK_LOGIN_ENABLED = process.env.NODE_ENV === 'development';

  const handleMockLogin = async () => {
    if (!MOCK_LOGIN_ENABLED) return;
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
        setUser(data.user);
        localStorage.setItem('veriflow_user', JSON.stringify(data.user));
        localStorage.setItem('veriflow_token', data.access_token);
        loadProjects(data.access_token);
      } else {
        setError(data.detail || 'Mock Authentication failed');
      }
    } catch (err) {
      setError('Failed to authenticate with Mock User');
    }
    setLoading(false);
  };

  // Check for logged in user and load Google SDK
  useEffect(() => {
    const savedUser = localStorage.getItem('veriflow_user');
    const savedToken = localStorage.getItem('veriflow_token');
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

  const loadProjects = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/projects`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success && data.projects.length > 0) {
        setProjects(data.projects);
        const defaultProj = data.projects[0];
        setSelectedProject(defaultProj.id);
        loadApiKeys(defaultProj.id);
      }
    } catch (err) {
      setError('Failed to load projects');
    }
  };

  const loadApiKeys = async (projectId) => {
    try {
      const token = localStorage.getItem('veriflow_token');
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
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('veriflow_token');
      const domains = newProjectDomains.split(',').map(d => d.trim()).filter(d => d);
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

  const handleCreateKeyPair = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('veriflow_token');
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
      const token = localStorage.getItem('veriflow_token');
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

  const handleLogout = () => {
    localStorage.removeItem('veriflow_user');
    localStorage.removeItem('veriflow_token');
    setUser(null);
    window.location.href = '/';
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="max-w-md w-full p-8">
          <div className="text-center mb-8">
            <Shield className="w-16 h-16 text-primary mx-auto mb-4" />
            <h1 className="text-3xl font-bold mb-2">VeriFlow Dashboard</h1>
            <p className="text-textSecondary">Manage your API keys and projects</p>
          </div>
          
          <div className="space-y-6 flex flex-col items-center">
            {/* Google Identity Services button container */}
            <div id="google-btn-container" className="w-full flex justify-center py-1 min-h-[50px]"></div>
            
            {MOCK_LOGIN_ENABLED && (
              <>
                <div className="w-full flex items-center gap-3">
                  <div className="h-[1px] bg-border flex-1"></div>
                  <span className="text-xs text-textSecondary font-medium uppercase tracking-wider">Or</span>
                  <div className="h-[1px] bg-border flex-1"></div>
                </div>

                <button
                  onClick={handleMockLogin}
                  disabled={loading}
                  className="w-full bg-surface2 hover:bg-surface text-textSecondary hover:text-text py-3 rounded-lg font-medium transition-colors border border-border flex items-center justify-center gap-2"
                >
                  {loading ? 'Authenticating...' : 'Continue as Mock Developer (Local Bypass)'}
                </button>
              </>
            )}
          </div>
          
          {error && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4" />
              {error}
            </div>
          )}
          
          {success && (
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-500 text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              {success}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <nav className="border-b border-border bg-surface">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold">VeriFlow</span>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="text-textSecondary">{user.email}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-textSecondary hover:text-text transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Success/Error Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            {error}
          </div>
        )}
        
        {success && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-500 text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            {success}
          </div>
        )}

        {/* Generated Key Pair Modal */}
        {generatedPair && (
          <div className="mb-6 p-6 bg-primary/10 border border-primary/20 rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Key className="w-5 h-5 text-primary" />
              API Key Pair Generated
            </h3>
            <p className="text-textSecondary text-sm mb-4">
              Copy these now — the secret key won't be shown again.
            </p>

            <div className="space-y-3 mb-6">
              <div>
                <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Site key (browser)</label>
                <div className="flex gap-2">
                  <input type="text" value={generatedPair.siteKey} readOnly className="flex-1 px-4 py-2 bg-surface2 border border-border rounded-lg font-mono text-sm" />
                  <button onClick={() => copyToClipboard(generatedPair.siteKey)} className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors flex items-center gap-2">
                    <Copy className="w-4 h-4" /> Copy
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Secret key (server only — never expose in browser code)</label>
                <div className="flex gap-2">
                  <input type="text" value={generatedPair.secretKey} readOnly className="flex-1 px-4 py-2 bg-surface2 border border-border rounded-lg font-mono text-sm" />
                  <button onClick={() => copyToClipboard(generatedPair.secretKey)} className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors flex items-center gap-2">
                    <Copy className="w-4 h-4" /> Copy
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold text-textSecondary uppercase tracking-wider mb-2">Next steps: drop this in your HTML</p>
                <CodeBlock language="html" code={scriptTagSnippet(generatedPair.siteKey)} />
              </div>
              <div>
                <p className="text-xs font-semibold text-textSecondary uppercase tracking-wider mb-2">Then verify server-side</p>
                <CodeBlock language="bash" code={siteverifyCurlSnippet(generatedPair.secretKey)} />
              </div>
              <a href="/docs" className="inline-flex items-center gap-2 text-primary hover:underline text-sm font-medium">
                <BookOpen className="w-4 h-4" /> Integration guide →
              </a>
            </div>

            <button
              onClick={() => setGeneratedPair(null)}
              className="mt-6 text-textSecondary hover:text-text text-sm"
            >
              Close
            </button>
          </div>
        )}

        {/* API Keys Console (Stripe-inspired) */}
        {selectedProject && (
          <div className="bg-surface border border-border rounded-2xl shadow-xl overflow-hidden">
            {/* Header info */}
            <div className="p-8 border-b border-border flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold mb-1">API Keys</h2>
                <p className="text-textSecondary text-sm max-w-xl">
                  Site keys authenticate your client SDK; secret keys verify decisions server-side. Keep secret keys out of public repositories and browser code.
                </p>
                <a href="/docs" className="inline-flex items-center gap-1.5 text-primary hover:underline text-sm font-medium mt-2">
                  <BookOpen className="w-4 h-4" /> Integration guide →
                </a>
              </div>
              <div>
                <button
                  onClick={() => setShowCreateKey(true)}
                  className="flex items-center gap-2 bg-primary hover:bg-primaryDark text-white px-5 py-2.5 rounded-lg font-semibold transition-colors text-sm shadow-md"
                >
                  <Plus className="w-4 h-4" />
                  Create API Key Pair
                </button>
              </div>
            </div>

            {/* Generate Key Pair Panel */}
            {showCreateKey && (
              <div className="p-8 bg-surface2 border-b border-border">
                <div className="max-w-md">
                  <h3 className="font-bold text-lg mb-2">Generate API Key Pair</h3>
                  <p className="text-textSecondary text-sm mb-4">
                    Creates a site key (for your browser SDK) and a secret key (for server-side verification), shown once.
                  </p>
                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={handleCreateKeyPair}
                      disabled={loading}
                      className="flex-1 bg-primary hover:bg-primaryDark text-white py-2.5 rounded-lg font-semibold transition-colors text-sm"
                    >
                      {loading ? 'Generating...' : 'Create Key Pair'}
                    </button>
                    <button
                      onClick={() => setShowCreateKey(false)}
                      className="flex-1 bg-surface hover:bg-surface2 text-text py-2.5 rounded-lg font-semibold transition-colors border border-border text-sm"
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
                    <tr className="border-b border-border text-xs uppercase tracking-wider text-textSecondary bg-surface2">
                      <th className="py-4 px-6 font-semibold">Name</th>
                      <th className="py-4 px-6 font-semibold">Key Token</th>
                      <th className="py-4 px-6 font-semibold">Created</th>
                      <th className="py-4 px-6 font-semibold">Last Used</th>
                      <th className="py-4 px-6 font-semibold">Status</th>
                      <th className="py-4 px-6 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(apiKeys[selectedProject] || []).map((key) => {
                      const keyType = key.key_type || 'legacy';
                      const badgeClasses = {
                        site: 'bg-primary/10 text-primary border-primary/20',
                        secret: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
                        legacy: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
                        live: 'bg-primary/10 text-primary border-primary/20',
                        test: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
                      }[keyType] || 'bg-amber-500/10 text-amber-500 border-amber-500/20';
                      return (
                        <tr key={key.id} className="border-b border-border text-sm hover:bg-surface2/40 transition-colors">
                          <td className="py-4 px-6 font-medium">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold uppercase border ${badgeClasses}`}>
                              {keyType}
                            </span>
                          </td>
                          <td className="py-4 px-6 font-mono text-xs text-textSecondary">
                            <div className="flex items-center gap-2">
                              <span>{key.key_prefix}...</span>
                              <button 
                                onClick={() => copyToClipboard(key.key_prefix)}
                                className="text-textSecondary hover:text-text p-1 rounded hover:bg-surface transition-colors"
                                title="Copy Prefix"
                              >
                                <Copy className="w-3 h-3" />
                              </button>
                            </div>
                          </td>
                          <td className="py-4 px-6 text-textSecondary">
                            {new Date(key.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-4 px-6 text-textSecondary">
                            {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}
                          </td>
                          <td className="py-4 px-6">
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              key.is_active ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'
                            }`}>
                              {key.is_active ? 'Active' : 'Revoked'}
                            </span>
                          </td>
                          <td className="py-4 px-6 text-right">
                            {key.is_active && (
                              <button
                                onClick={() => handleRevokeKey(key.id)}
                                className="p-1.5 hover:bg-red-500/10 text-red-500 rounded-lg transition-colors inline-flex items-center gap-1.5 text-xs font-semibold"
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
              <div className="text-center py-16 bg-surface2/30">
                <Key className="w-12 h-12 mx-auto mb-4 text-textSecondary opacity-30" />
                <h3 className="font-bold text-lg mb-1">No API keys yet</h3>
                <p className="text-sm text-textSecondary mb-6 max-w-sm mx-auto">
                  Get started by generating your first live or test API credentials.
                </p>
                <button
                  onClick={() => setShowCreateKey(true)}
                  className="bg-primary hover:bg-primaryDark text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors"
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

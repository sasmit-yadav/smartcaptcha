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
  Globe
} from 'lucide-react';

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
  const [newKeyType, setNewKeyType] = useState('live');
  const [generatedKey, setGeneratedKey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Check for logged in user
  useEffect(() => {
    const savedUser = localStorage.getItem('nextcaptcha_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
      loadProjects(JSON.parse(savedUser).id);
    }
  }, []);

  const loadProjects = async (userId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/projects`, {
        headers: { 'user-id': userId }
      });
      const data = await response.json();
      if (data.success) {
        setProjects(data.projects);
      }
    } catch (err) {
      setError('Failed to load projects');
    }
  };

  const loadApiKeys = async (projectId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/api-keys/${projectId}`);
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
      const domains = newProjectDomains.split(',').map(d => d.trim()).filter(d => d);
      const response = await fetch(`${API_BASE_URL}/admin/projects`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'user-id': user.id
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
        loadProjects(user.id);
      } else {
        setError(data.detail || 'Failed to create project');
      }
    } catch (err) {
      setError('Failed to create project');
    }
    setLoading(false);
  };

  const handleCreateApiKey = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/admin/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProject,
          key_type: newKeyType
        })
      });
      const data = await response.json();
      if (data.success) {
        setGeneratedKey(data.api_key);
        setSuccess('API key generated successfully');
        setShowCreateKey(false);
        loadApiKeys(selectedProject);
      } else {
        setError(data.detail || 'Failed to generate API key');
      }
    } catch (err) {
      setError('Failed to generate API key');
    }
    setLoading(false);
  };

  const handleRevokeKey = async (keyId) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/api-keys/${keyId}`, {
        method: 'DELETE'
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
    localStorage.removeItem('nextcaptcha_user');
    setUser(null);
    window.location.href = '/';
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="max-w-md w-full p-8">
          <div className="text-center mb-8">
            <Shield className="w-16 h-16 text-primary mx-auto mb-4" />
            <h1 className="text-3xl font-bold mb-2">NextCaptcha Dashboard</h1>
            <p className="text-textSecondary">Manage your API keys and projects</p>
          </div>
          
          <div className="space-y-4">
            <input
              type="email"
              placeholder="Email"
              className="w-full px-4 py-3 rounded-lg bg-surface2 border border-border focus:border-primary focus:outline-none"
              id="login-email"
            />
            <input
              type="password"
              placeholder="Password"
              className="w-full px-4 py-3 rounded-lg bg-surface2 border border-border focus:border-primary focus:outline-none"
              id="login-password"
            />
            <button
              onClick={async () => {
                const email = document.getElementById('login-email').value;
                const password = document.getElementById('login-password').value;
                setLoading(true);
                try {
                  const response = await fetch(`${API_BASE_URL}/admin/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                  });
                  const data = await response.json();
                  if (data.success) {
                    setUser(data.user);
                    localStorage.setItem('nextcaptcha_user', JSON.stringify(data.user));
                    loadProjects(data.user.id);
                  } else {
                    setError('Invalid credentials');
                  }
                } catch (err) {
                  setError('Login failed');
                }
                setLoading(false);
              }}
              disabled={loading}
              className="w-full bg-primary hover:bg-primaryDark text-white py-3 rounded-lg font-medium transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            
            <button
              onClick={async () => {
                const email = document.getElementById('login-email').value;
                const password = document.getElementById('login-password').value;
                setLoading(true);
                try {
                  const response = await fetch(`${API_BASE_URL}/admin/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                  });
                  const data = await response.json();
                  if (data.success) {
                    setSuccess('Account created! Please sign in.');
                  } else {
                    setError(data.detail || 'Registration failed');
                  }
                } catch (err) {
                  setError('Registration failed');
                }
                setLoading(false);
              }}
              disabled={loading}
              className="w-full bg-surface2 hover:bg-surface text-text py-3 rounded-lg font-medium transition-colors border border-border"
            >
              Create Account
            </button>
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
            <span className="text-xl font-bold">NextCaptcha</span>
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

        {/* Generated Key Modal */}
        {generatedKey && (
          <div className="mb-6 p-6 bg-primary/10 border border-primary/20 rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Key className="w-5 h-5 text-primary" />
              API Key Generated
            </h3>
            <p className="text-textSecondary text-sm mb-4">
              Copy this key now. You won't be able to see it again.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={generatedKey.api_key}
                readOnly
                className="flex-1 px-4 py-2 bg-surface2 border border-border rounded-lg font-mono text-sm"
              />
              <button
                onClick={() => copyToClipboard(generatedKey.api_key)}
                className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Copy
              </button>
            </div>
            <button
              onClick={() => setGeneratedKey(null)}
              className="mt-4 text-textSecondary hover:text-text text-sm"
            >
              Close
            </button>
          </div>
        )}

        {/* Projects Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">Projects</h2>
            <button
              onClick={() => setShowCreateProject(true)}
              className="flex items-center gap-2 bg-primary hover:bg-primaryDark text-white px-4 py-2 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>

          {showCreateProject && (
            <div className="mb-6 p-6 bg-surface2 border border-border rounded-lg">
              <h3 className="font-semibold mb-4">Create New Project</h3>
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Project Name"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:border-primary focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Allowed Domains (comma-separated)"
                  value={newProjectDomains}
                  onChange={(e) => setNewProjectDomains(e.target.value)}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:border-primary focus:outline-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleCreateProject}
                    disabled={loading || !newProjectName}
                    className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors"
                  >
                    {loading ? 'Creating...' : 'Create Project'}
                  </button>
                  <button
                    onClick={() => setShowCreateProject(false)}
                    className="px-4 py-2 bg-surface hover:bg-surface2 text-text rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 bg-surface2 border border-border rounded-lg hover:border-primary/50 transition-colors cursor-pointer"
                onClick={() => {
                  setSelectedProject(project.id);
                  loadApiKeys(project.id);
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold">{project.name}</h3>
                  </div>
                </div>
                
                {project.allowed_domains && project.allowed_domains.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {project.allowed_domains.slice(0, 3).map((domain, i) => (
                      <span key={i} className="text-xs px-2 py-1 bg-surface rounded-full flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        {domain}
                      </span>
                    ))}
                    {project.allowed_domains.length > 3 && (
                      <span className="text-xs px-2 py-1 bg-surface rounded-full">
                        +{project.allowed_domains.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* API Keys Section */}
        {selectedProject && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">API Keys</h2>
              <button
                onClick={() => setShowCreateKey(true)}
                className="flex items-center gap-2 bg-primary hover:bg-primaryDark text-white px-4 py-2 rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Generate Key
              </button>
            </div>

            {showCreateKey && (
              <div className="mb-6 p-6 bg-surface2 border border-border rounded-lg">
                <h3 className="font-semibold mb-4">Generate API Key</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-textSecondary mb-2">Key Type</label>
                    <select
                      value={newKeyType}
                      onChange={(e) => setNewKeyType(e.target.value)}
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:border-primary focus:outline-none"
                    >
                      <option value="live">Live (Production)</option>
                      <option value="test">Test (Development)</option>
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleCreateApiKey}
                      disabled={loading}
                      className="px-4 py-2 bg-primary hover:bg-primaryDark text-white rounded-lg transition-colors"
                    >
                      {loading ? 'Generating...' : 'Generate Key'}
                    </button>
                    <button
                      onClick={() => setShowCreateKey(false)}
                      className="px-4 py-2 bg-surface hover:bg-surface2 text-text rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {(apiKeys[selectedProject] || []).map((key) => (
                <div key={key.id} className="p-4 bg-surface2 border border-border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Key className="text-primary" />
                    <div>
                      <div className="font-mono text-sm">{key.key_prefix}...</div>
                      <div className="text-xs text-textSecondary">
                        Created: {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used_at && ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs ${key.is_active ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                      {key.is_active ? 'Active' : 'Revoked'}
                    </span>
                    {key.is_active && (
                      <button
                        onClick={() => handleRevokeKey(key.id)}
                        className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
              
              {(!apiKeys[selectedProject] || apiKeys[selectedProject].length === 0) && (
                <div className="text-center py-8 text-textSecondary">
                  <Key className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No API keys yet. Generate your first key to get started.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

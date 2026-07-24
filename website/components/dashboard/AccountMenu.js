'use client';

import { useEffect, useId, useRef, useState } from 'react';
import {
  BookOpen,
  Check,
  ChevronDown,
  Copy,
  KeyRound,
  LogOut,
  Mail,
  Shield,
  X,
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.veilproof.tech';

function initialsFromUser(user) {
  const name = (user?.full_name || '').trim();
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }
  const email = (user?.email || '?').trim();
  return email.slice(0, 2).toUpperCase();
}

function authLabel(user) {
  const methods = Array.isArray(user?.auth_methods) ? user.auth_methods : [];
  const hasPw = methods.includes('password') || user?.has_password === true;
  const google =
    methods.includes('google') || user?.google_linked === true || user?.has_password === false;
  if (google && hasPw) return 'Google · Password';
  if (google) return 'Google';
  return 'Email & password';
}

/**
 * Industry-standard account trigger (Stripe / Twilio / Cloudflare style):
 * circular avatar → panel with identity, sign-in method, copyable email/id,
 * change/set password, docs link, sign out.
 */
export default function AccountMenu({ user, onLogout, onUserUpdate, apiFetch }) {
  const [open, setOpen] = useState(false);
  const [panel, setPanel] = useState('menu'); // menu | password
  const [copied, setCopied] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const rootRef = useRef(null);
  const menuId = useId();

  const needsCurrent = Boolean(user?.has_password);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
        setPanel('menu');
        setError('');
        setSuccess('');
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        setPanel('menu');
      }
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const copyText = async (label, value) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      setTimeout(() => setCopied(''), 1600);
    } catch {
      setCopied('');
    }
  };

  const resetPasswordForm = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setSuccess('');
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    setBusy(true);
    try {
      const fetcher =
        apiFetch ||
        ((path, options) =>
          fetch(`${API_BASE_URL}${path}`, {
            ...options,
            headers: {
              Authorization: `Bearer ${localStorage.getItem('veilproof_token')}`,
              ...(options?.headers || {}),
            },
          }));
      const res = await fetcher('/admin/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: needsCurrent ? currentPassword : null,
          new_password: newPassword,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.success) {
        setError(typeof data.detail === 'string' ? data.detail : 'Could not update password');
        setBusy(false);
        return;
      }
      if (data.access_token) localStorage.setItem('veilproof_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('veilproof_refresh_token', data.refresh_token);
      if (data.user) {
        localStorage.setItem('veilproof_user', JSON.stringify(data.user));
        onUserUpdate?.(data.user);
      }
      setSuccess(data.message || 'Password updated');
      resetPasswordForm();
      setPanel('menu');
      setTimeout(() => setSuccess(''), 2500);
    } catch {
      setError('Could not update password');
    }
    setBusy(false);
  };

  if (!user) return null;

  const displayName = (user.full_name || '').trim() || user.email?.split('@')[0] || 'Account';
  const initials = initialsFromUser(user);

  return (
    <div className="vp-account" ref={rootRef}>
      <button
        type="button"
        className={`vp-account-trigger${open ? ' is-open' : ''}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => {
          setOpen((v) => !v);
          setPanel('menu');
          setError('');
        }}
        title={user.email}
      >
        <span className="vp-account-avatar" aria-hidden="true">
          {initials}
        </span>
        <ChevronDown size={14} className="vp-account-caret" aria-hidden="true" />
      </button>

      {open && (
        <div id={menuId} className="vp-account-panel" role="dialog" aria-label="Account menu">
          {panel === 'menu' ? (
            <>
              <div className="vp-account-head">
                <span className="vp-account-avatar vp-account-avatar-lg" aria-hidden="true">
                  {initials}
                </span>
                <div className="vp-account-head-text">
                  <strong>{displayName}</strong>
                  <span className="vp-account-email">{user.email}</span>
                  <span className="vp-account-badge">
                    <Shield size={11} aria-hidden="true" />
                    {authLabel(user)}
                  </span>
                </div>
              </div>

              {success ? <p className="vp-account-toast ok">{success}</p> : null}

              <div className="vp-account-section">
                <p className="vp-account-section-label">Account</p>
                <button
                  type="button"
                  className="vp-account-row"
                  onClick={() => copyText('email', user.email)}
                >
                  <Mail size={14} />
                  <span>
                    <em>Email</em>
                    <small>{user.email}</small>
                  </span>
                  {copied === 'email' ? <Check size={14} /> : <Copy size={14} />}
                </button>
                <button
                  type="button"
                  className="vp-account-row"
                  onClick={() => copyText('id', user.id)}
                >
                  <KeyRound size={14} />
                  <span>
                    <em>User ID</em>
                    <small className="mono">{user.id}</small>
                  </span>
                  {copied === 'id' ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>

              <div className="vp-account-section">
                <p className="vp-account-section-label">Security</p>
                <button
                  type="button"
                  className="vp-account-row"
                  onClick={() => {
                    resetPasswordForm();
                    setPanel('password');
                  }}
                >
                  <KeyRound size={14} />
                  <span>
                    <em>{needsCurrent ? 'Change password' : 'Set password'}</em>
                    <small>
                      {needsCurrent
                        ? 'Update your email login password'
                        : 'Add a password alongside Google sign-in'}
                    </small>
                  </span>
                </button>
              </div>

              <div className="vp-account-section">
                <p className="vp-account-section-label">Resources</p>
                <a href="/docs#start" className="vp-account-row" onClick={() => setOpen(false)}>
                  <BookOpen size={14} />
                  <span>
                    <em>API docs</em>
                    <small>Keys, siteverify, client SDK</small>
                  </span>
                </a>
              </div>

              <button
                type="button"
                className="vp-account-signout"
                onClick={() => {
                  setOpen(false);
                  onLogout?.();
                }}
              >
                <LogOut size={14} /> Sign out
              </button>
            </>
          ) : (
            <form className="vp-account-password" onSubmit={submitPassword} noValidate>
              <div className="vp-account-password-head">
                <strong>{needsCurrent ? 'Change password' : 'Set password'}</strong>
                <button
                  type="button"
                  className="vp-account-close"
                  aria-label="Close"
                  onClick={() => {
                    setPanel('menu');
                    resetPasswordForm();
                  }}
                >
                  <X size={16} />
                </button>
              </div>
              <p className="vp-account-hint">
                At least 12 characters. Other signed-in devices will be signed out.
              </p>
              {needsCurrent ? (
                <label>
                  Current password
                  <input
                    type="password"
                    autoComplete="current-password"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                  />
                </label>
              ) : null}
              <label>
                New password
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </label>
              <label>
                Confirm new password
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </label>
              {error ? <p className="vp-account-toast err">{error}</p> : null}
              <button type="submit" className="vp-account-save" disabled={busy}>
                {busy ? 'Saving…' : needsCurrent ? 'Update password' : 'Set password'}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.veilproof.tech';
const GOOGLE_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
  '40763777720-bb2cmdjfi2p15h03pclgpfoklachvmpp.apps.googleusercontent.com';

/**
 * Full dashboard auth surface: email/password login + signup, then Google.
 * Parent owns session persistence via onAuthenticated({ user, access_token, refresh_token }).
 */
export default function AuthPanel({ initialMode = 'login', onAuthenticated }) {
  const [authMode, setAuthMode] = useState(initialMode === 'signup' ? 'signup' : 'login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mode = new URLSearchParams(window.location.search).get('mode');
    if (mode === 'signup' || mode === 'login') setAuthMode(mode);
  }, []);

  const renderGoogleButton = () => {
    if (!window.google?.accounts?.id) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleGoogleCredential,
    });
    const el = document.getElementById('vp-google-btn');
    if (!el) return;
    el.innerHTML = '';
    window.google.accounts.id.renderButton(el, {
      theme: 'filled_black',
      size: 'large',
      width: 340,
      shape: 'rectangular',
      text: authMode === 'signup' ? 'signup_with' : 'signin_with',
    });
  };

  useEffect(() => {
    const boot = () => setTimeout(renderGoogleButton, 50);
    if (document.getElementById('google-jssdk')) {
      boot();
      return;
    }
    const script = document.createElement('script');
    script.id = 'google-jssdk';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = boot;
    document.body.appendChild(script);
  }, [authMode]);

  const finishAuth = (data) => {
    setPassword('');
    setConfirmPassword('');
    onAuthenticated?.(data);
  };

  const handleGoogleCredential = async (response) => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/admin/google-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(typeof data.detail === 'string' ? data.detail : 'Google sign-in failed');
        setLoading(false);
        return;
      }
      finishAuth(data);
    } catch {
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
        setError(
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail[0]?.msg || 'Request failed'
              : 'Authentication failed'
        );
        setLoading(false);
        return;
      }
      if (authMode === 'signup') {
        setSuccess('Account created — loading your dashboard…');
      }
      finishAuth(data);
    } catch {
      setError(authMode === 'signup' ? 'Signup failed' : 'Login failed');
    }
    setLoading(false);
  };

  const switchMode = (mode) => {
    setAuthMode(mode);
    setError('');
    setSuccess('');
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('mode', mode);
      window.history.replaceState(null, '', url.pathname + url.search);
    }
  };

  return (
    <div className="dashboard-login-panel max-w-md w-full card p-8">
      <div className="text-center mb-6">
        <img src="/veilproof-mark.png" alt="VeilProof" className="dashboard-login-logo" />
        <h1 className="text-2xl font-semibold mb-2">
          <span className="font-brand font-bold uppercase tracking-wide">VeilProof</span> Dashboard
        </h1>
        <p className="text-mute text-sm">
          {authMode === 'signup'
            ? 'Create an account with email — or continue with Google'
            : 'Log in with email and password — or continue with Google'}
        </p>
      </div>

      <div className="flex mb-5 p-1 bg-canvas border border-hairline rounded-lg" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={authMode === 'login'}
          onClick={() => switchMode('login')}
          className={`flex-1 h-9 rounded-md text-sm font-semibold transition-colors ${
            authMode === 'login' ? 'bg-white/10 text-ink' : 'text-mute hover:text-ink'
          }`}
        >
          Log in
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={authMode === 'signup'}
          onClick={() => switchMode('signup')}
          className={`flex-1 h-9 rounded-md text-sm font-semibold transition-colors ${
            authMode === 'signup' ? 'bg-white/10 text-ink' : 'text-mute hover:text-ink'
          }`}
        >
          Sign up
        </button>
      </div>

      <form onSubmit={handleEmailAuth} className="space-y-3 mb-5" noValidate>
        {authMode === 'signup' && (
          <label className="block text-xs font-bold text-mute uppercase tracking-wider">
            Full name <span className="font-normal normal-case">(optional)</span>
            <input
              type="text"
              name="name"
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
            name="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
          />
        </label>
        <label className="block text-xs font-bold text-mute uppercase tracking-wider">
          Password
          <input
            type="password"
            name="password"
            required
            minLength={authMode === 'signup' ? 12 : 1}
            autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={authMode === 'signup' ? 'At least 12 characters' : 'Your password'}
            className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
          />
        </label>
        {authMode === 'signup' && (
          <>
            <label className="block text-xs font-bold text-mute uppercase tracking-wider">
              Confirm password
              <input
                type="password"
                name="confirmPassword"
                required
                minLength={12}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat password"
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
          {loading ? 'Please wait…' : authMode === 'signup' ? 'Create account' : 'Log in with email'}
        </button>
      </form>

      <div className="relative my-5">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-hairline" />
        </div>
        <div className="relative flex justify-center text-xs uppercase tracking-wider">
          <span className="px-3 text-mute bg-surface">or</span>
        </div>
      </div>

      <div className="flex flex-col items-center gap-2">
        <div id="vp-google-btn" className="w-full flex justify-center min-h-[44px]" />
        <p className="text-mute text-xs text-center">
          Google creates an account without a password. Use email signup if you want password login.
        </p>
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
  );
}

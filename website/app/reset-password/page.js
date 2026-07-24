'use client';

import { useEffect, useMemo, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CheckCircle2, XCircle } from 'lucide-react';
import SiteNav from '../../components/chrome/SiteNav';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.veilproof.tech';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = useMemo(() => (searchParams.get('token') || '').trim(), [searchParams]);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!token) setError('This reset link is missing or invalid.');
  }, [token]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (!token) {
      setError('This reset link is missing or invalid.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.success) {
        setError(typeof data.detail === 'string' ? data.detail : 'Unable to reset password');
        setLoading(false);
        return;
      }
      setSuccess(data.message || 'Password updated. Redirecting to sign in…');
      setTimeout(() => router.replace('/dashboard?mode=login'), 1200);
    } catch {
      setError('Unable to reset password');
    }
    setLoading(false);
  };

  return (
    <div className="dashboard-login-panel max-w-md w-full card p-8">
      <div className="text-center mb-6">
        <img src="/veilproof-mark.png" alt="VeilProof" className="dashboard-login-logo" />
        <h1 className="text-2xl font-semibold mb-2">Reset password</h1>
        <p className="text-mute text-sm">Choose a new password for your VeilProof account.</p>
      </div>
      <form onSubmit={onSubmit} className="space-y-3" noValidate>
        <label className="block text-xs font-bold text-mute uppercase tracking-wider">
          New password
          <input
            type="password"
            required
            minLength={12}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2 w-full h-11 px-4 bg-canvas border border-hairline rounded-md text-ink normal-case tracking-normal font-normal outline-none focus:border-primary/60"
          />
        </label>
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
        <button
          type="submit"
          disabled={loading || !token}
          className="w-full h-11 bg-primary hover:bg-primaryDark disabled:opacity-50 text-white rounded-md font-bold text-sm transition-colors"
        >
          {loading ? 'Please wait…' : 'Update password'}
        </button>
      </form>
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

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <SiteNav />
      <main className="flex justify-center px-4 py-16">
        <Suspense fallback={<div className="text-mute text-sm">Loading…</div>}>
          <ResetPasswordForm />
        </Suspense>
      </main>
    </div>
  );
}

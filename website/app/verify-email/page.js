'use client';

import { useEffect, useMemo, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CheckCircle2, XCircle } from 'lucide-react';
import SiteNav from '../../components/chrome/SiteNav';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.veilproof.tech';

function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = useMemo(() => (searchParams.get('token') || '').trim(), [searchParams]);
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('Verifying your email…');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('This verification link is missing or invalid.');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/admin/verify-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        });
        const data = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (!res.ok || !data.success) {
          setStatus('error');
          setMessage(typeof data.detail === 'string' ? data.detail : 'Unable to verify email');
          return;
        }
        setStatus('ok');
        setMessage(data.message || 'Email verified.');
        setTimeout(() => router.replace('/dashboard'), 1400);
      } catch {
        if (!cancelled) {
          setStatus('error');
          setMessage('Unable to verify email');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  return (
    <div className="dashboard-login-panel max-w-md w-full card p-8 text-center">
      <img src="/veilproof-mark.png" alt="VeilProof" className="dashboard-login-logo mx-auto" />
      <h1 className="text-2xl font-semibold mb-3">Email verification</h1>
      <div
        className={`mt-4 p-3 rounded-lg text-sm flex items-center gap-2 justify-center ${
          status === 'error'
            ? 'bg-dangerSoft border border-danger/25 text-danger'
            : 'bg-primarySoft border border-primary/25 text-primary'
        }`}
      >
        {status === 'error' ? <XCircle className="w-4 h-4 shrink-0" /> : <CheckCircle2 className="w-4 h-4 shrink-0" />}
        {message}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <SiteNav />
      <main className="flex justify-center px-4 py-16">
        <Suspense fallback={<div className="text-mute text-sm">Loading…</div>}>
          <VerifyEmailForm />
        </Suspense>
      </main>
    </div>
  );
}

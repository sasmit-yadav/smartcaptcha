/**
 * Normalize account profile fields for the dashboard.
 *
 * Critical rule: missing `has_password` must NOT mean "no password".
 * Stale localStorage from before auth_methods existed often omits the flag;
 * treating undefined as false incorrectly shows "Set password" for email users.
 *
 * Only `has_password === false` means Google-only (set-password flow).
 */

export function normalizeAccountProfile(raw) {
  if (!raw || typeof raw !== 'object') return null;

  const explicitNoPassword = raw.has_password === false;
  const explicitHasPassword = raw.has_password === true;
  const methodsIn = Array.isArray(raw.auth_methods)
    ? raw.auth_methods.filter((m) => m === 'password' || m === 'google')
    : [];

  let hasPassword;
  if (explicitNoPassword) hasPassword = false;
  else if (explicitHasPassword) hasPassword = true;
  else if (methodsIn.includes('password')) hasPassword = true;
  else if (methodsIn.includes('google') && !methodsIn.includes('password')) hasPassword = false;
  else hasPassword = true; // safe default for email/password and legacy sessions

  let googleLinked =
    raw.google_linked === true ||
    methodsIn.includes('google') ||
    explicitNoPassword === true;

  // Password-only accounts are never Google-linked unless the API said so.
  if (!googleLinked && !explicitNoPassword) {
    googleLinked = false;
  }

  const authMethods = [];
  if (hasPassword) authMethods.push('password');
  if (googleLinked) authMethods.push('google');
  if (authMethods.length === 0) authMethods.push('password');

  return {
    ...raw,
    id: raw.id != null ? String(raw.id) : raw.id,
    email: raw.email || '',
    full_name: raw.full_name ?? null,
    company_name: raw.company_name ?? null,
    is_admin: Boolean(raw.is_admin),
    has_password: hasPassword,
    google_linked: googleLinked,
    auth_methods: authMethods,
  };
}

export function accountAuthLabel(user) {
  const u = normalizeAccountProfile(user) || {};
  const hasPw = u.has_password === true;
  const google = u.google_linked === true;
  if (google && hasPw) return 'Google · Password';
  if (google) return 'Google';
  return 'Email & password';
}

/** True when the account already has a password (change flow, not set flow). */
export function accountHasPassword(user) {
  return normalizeAccountProfile(user)?.has_password === true;
}

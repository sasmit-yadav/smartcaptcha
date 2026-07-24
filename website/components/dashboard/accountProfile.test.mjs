/**
 * Lightweight node checks for account profile normalization.
 * Run: node website/components/dashboard/accountProfile.test.mjs
 */
import assert from 'node:assert/strict';
import {
  accountAuthLabel,
  accountHasPassword,
  normalizeAccountProfile,
} from './accountProfile.js';

// Legacy localStorage user (no has_password) → Change password, Email & password
const legacy = normalizeAccountProfile({ id: '1', email: 'a@b.com' });
assert.equal(legacy.has_password, true);
assert.equal(legacy.google_linked, false);
assert.deepEqual(legacy.auth_methods, ['password']);
assert.equal(accountHasPassword(legacy), true);
assert.equal(accountAuthLabel(legacy), 'Email & password');

// Explicit Google-only
const googleOnly = normalizeAccountProfile({
  id: '2',
  email: 'g@b.com',
  has_password: false,
  google_linked: true,
  auth_methods: ['google'],
});
assert.equal(googleOnly.has_password, false);
assert.equal(accountHasPassword(googleOnly), false);
assert.equal(accountAuthLabel(googleOnly), 'Google');

// Explicit email password
const email = normalizeAccountProfile({
  id: '3',
  email: 'e@b.com',
  has_password: true,
  google_linked: false,
});
assert.equal(accountHasPassword(email), true);
assert.equal(accountAuthLabel(email), 'Email & password');

// Dual
const dual = normalizeAccountProfile({
  id: '4',
  email: 'd@b.com',
  has_password: true,
  google_linked: true,
});
assert.equal(accountAuthLabel(dual), 'Google · Password');

// has_password false without google_linked still Google-only
const inferred = normalizeAccountProfile({ id: '5', email: 'i@b.com', has_password: false });
assert.equal(inferred.google_linked, true);
assert.equal(accountHasPassword(inferred), false);

// auth_methods password alone
const fromMethods = normalizeAccountProfile({
  id: '6',
  email: 'm@b.com',
  auth_methods: ['password'],
});
assert.equal(fromMethods.has_password, true);

console.log('accountProfile tests passed');

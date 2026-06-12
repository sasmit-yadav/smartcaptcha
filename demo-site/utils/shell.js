/**
 * Injects shared navbar and footer into every page.
 * Call initShell(currentPage) at DOMContentLoaded.
 */
import { getSessionShort } from './session.js';

const PAGES = [
  { href: '/',          label: 'Home' },
  { href: '/login.html',    label: 'Login' },
  { href: '/signup.html',   label: 'Sign Up' },
  { href: '/shop.html',     label: 'Shop' },
  { href: '/article.html',  label: 'Article' },
];

const LOGO_SVG = `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="32" height="32" rx="8" fill="#16a34a"/>
  <path d="M16 8c0 0-6 4-6 10a6 6 0 0012 0c0-6-6-10-6-10z" fill="#fff" opacity="0.9"/>
  <path d="M16 14v8M14 18h4" stroke="#16a34a" stroke-width="1.5" stroke-linecap="round"/>
</svg>`;

export function initShell(currentPage) {
  // ── Test banner ──
  const banner = document.createElement('div');
  banner.className = 'test-banner';
  banner.textContent = '🌿 Welcome to EcoHub — explore sustainable living and environmental awareness.';
  document.body.prepend(banner);

  // ── Navbar ──
  const nav = document.createElement('nav');
  nav.className = 'navbar';
  nav.innerHTML = `<div class="container">
    <a href="/" class="navbar-brand">${LOGO_SVG}<span>EcoHub</span></a>
    <ul class="navbar-links">
      ${PAGES.map(p =>
        `<li><a href="${p.href}" class="${p.label === currentPage ? 'active' : ''}">${p.label}</a></li>`
      ).join('')}
    </ul>
  </div>`;
  banner.after(nav);

  // ── Footer ──
  const footer = document.createElement('footer');
  footer.className = 'footer';
  footer.innerHTML = `<div class="container">
    <p>&copy; 2026 EcoHub &middot; Building a greener future together</p>
  </div>`;
  document.body.appendChild(footer);
}

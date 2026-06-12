/**
 * Injects shared navbar and footer into every page.
 * Call initShell(currentPage) at DOMContentLoaded.
 */
import { getSessionShort } from './session.js';

const PAGES = [
  { href: '/',          label: 'Home' },
  { href: '/login.html',    label: 'Login' },
  { href: '/signup.html',   label: 'Sign Up' },
  { href: '/quiz.html',     label: 'Quiz' },
  { href: '/survey.html',   label: 'Survey' },
  { href: '/typing-test.html', label: 'Typing Test' },
  { href: '/memory-game.html', label: 'Memory Game' },
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
  banner.textContent = '🌿 Welcome to EcoHub — Your hub for sustainable living and environmental awareness.';
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
    <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:2rem; margin-bottom:2rem;">
      <div>
        <h4 style="margin-bottom:0.75rem; color:var(--color-primary);">EcoHub</h4>
        <p class="text-sm text-muted">Demonstrating sustainable living through interactive experiences.</p>
      </div>
      <div>
        <h4 style="margin-bottom:0.75rem;">Quick Links</h4>
        <ul style="list-style:none; padding:0; margin:0;">
          <li style="margin-bottom:0.5rem;"><a href="/quiz.html" style="color:var(--color-text-muted); text-decoration:none;">Quiz</a></li>
          <li style="margin-bottom:0.5rem;"><a href="/survey.html" style="color:var(--color-text-muted); text-decoration:none;">Survey</a></li>
          <li style="margin-bottom:0.5rem;"><a href="/typing-test.html" style="color:var(--color-text-muted); text-decoration:none;">Typing Test</a></li>
          <li style="margin-bottom:0.5rem;"><a href="/memory-game.html" style="color:var(--color-text-muted); text-decoration:none;">Memory Game</a></li>
        </ul>
      </div>
      <div>
        <h4 style="margin-bottom:0.75rem;">Resources</h4>
        <ul style="list-style:none; padding:0; margin:0;">
          <li style="margin-bottom:0.5rem;"><a href="/article.html" style="color:var(--color-text-muted); text-decoration:none;">Articles</a></li>
          <li style="margin-bottom:0.5rem;"><a href="/login.html" style="color:var(--color-text-muted); text-decoration:none;">Login</a></li>
          <li style="margin-bottom:0.5rem;"><a href="/signup.html" style="color:var(--color-text-muted); text-decoration:none;">Sign Up</a></li>
        </ul>
      </div>
    </div>
    <div style="padding-top:1.5rem; border-top:1px solid var(--color-border); text-align:center;">
      <p class="text-sm text-muted">&copy; 2026 EcoHub &middot; Building a greener future together</p>
    </div>
  </div>`;
  document.body.appendChild(footer);
}

'use client';

import { useState } from 'react';
import { CircleHelp, ExternalLink, LogOut, Menu, X } from 'lucide-react';
import SiteSearch from './SiteSearch';

export default function SiteNav({ active, user, onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const links = [
    { label: 'Features', href: '/#features' },
    { label: 'Platform', href: '/#platform' },
    { label: 'Developers', href: '/docs#client' },
    { label: 'Docs', href: '/docs#start', external: true },
  ];

  return (
    <header className="vp-nav">
      <div className="vp-nav-inner">
        <a href="/" className="vp-brand" aria-label="VeilProof home">
          <span className="veilproof-brand-crop">
            <img src="/veilproof-logo.png" alt="VeilProof" />
          </span>
        </a>

        <nav className="vp-desktop-links" aria-label="Main navigation">
          {links.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className={active === l.label ? 'active' : undefined}
            >
              {l.label} {l.external && <ExternalLink size={11} />}
            </a>
          ))}
        </nav>

        <div className="vp-shared-search"><SiteSearch placeholder="Search" /></div>

        <div className="vp-nav-actions">
          <a href="/docs#start" aria-label="Help">
            <CircleHelp size={17} />
          </a>
          {user ? (
            <>
              <span className="vp-nav-user">{user.email}</span>
              <button onClick={onLogout} className="vp-nav-cta">
                <LogOut size={13} /> Sign out
              </button>
            </>
          ) : (
            <>
              <a href="/dashboard?mode=login" className="vp-login">Log in</a>
              <a href="/dashboard?mode=signup" className="vp-nav-cta">Get started</a>
            </>
          )}
          <button className="vp-menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav className="vp-mobile-menu">
          {links.map((link) => (
            <a key={link.label} href={link.href} onClick={() => setMenuOpen(false)}>{link.label}</a>
          ))}
          {user ? (
            <button onClick={() => { setMenuOpen(false); onLogout?.(); }} className="vp-mobile-cta">
              Sign out
            </button>
          ) : (
            <>
              <a href="/dashboard?mode=login" onClick={() => setMenuOpen(false)}>Log in</a>
              <a href="/dashboard?mode=signup" onClick={() => setMenuOpen(false)} className="vp-mobile-cta">Get started</a>
            </>
          )}
        </nav>
      )}
    </header>
  );
}

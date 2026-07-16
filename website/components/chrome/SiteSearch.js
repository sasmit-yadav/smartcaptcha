'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Code2,
  History,
  Layers,
  Rocket,
  Search,
  Server,
  ShieldCheck,
} from 'lucide-react';

const ITEMS = [
  { title: 'Getting Started', detail: 'Quick start', href: '/docs#start', icon: Rocket },
  { title: 'Client Integration', detail: 'React SDK', href: '/docs#client', icon: Code2 },
  { title: 'Server Verification', detail: 'Integration guide', href: '/docs#server', icon: Server },
  { title: 'API Reference', detail: 'API reference', href: '/docs#api', icon: Layers },
  { title: 'Security Best Practices', detail: 'Invisible bot protection', href: '/docs#security', icon: ShieldCheck },
  { title: 'SDK Reference', detail: 'SDKs', href: '/docs#sdk', icon: BookOpen },
];

export default function SiteSearch({ variant = 'compact', placeholder = 'Search' }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [recent, setRecent] = useState(null);
  const rootRef = useRef(null);
  const inputRef = useRef(null);

  const matches = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return ITEMS;
    return ITEMS.filter((item) =>
      `${item.title} ${item.detail}`.toLowerCase().includes(normalized)
    );
  }, [query]);

  useEffect(() => {
    const stored = localStorage.getItem('veilproof_recent_search');
    if (stored) setRecent(ITEMS.find((item) => item.href === stored) || null);

    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen(true);
        inputRef.current?.focus();
      }
      if (event.key === 'Escape') {
        setOpen(false);
        inputRef.current?.blur();
      }
    };
    const onPointerDown = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, []);

  useEffect(() => setActive(0), [query]);

  const visit = (item) => {
    if (!item) return;
    localStorage.setItem('veilproof_recent_search', item.href);
    window.location.href = item.href;
  };

  const submit = (event) => {
    event.preventDefault();
    visit(matches[active] || matches[0] || ITEMS[0]);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((value) => Math.min(value + 1, Math.max(matches.length - 1, 0)));
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((value) => Math.max(value - 1, 0));
    }
  };

  const hero = variant === 'hero';

  return (
    <div className={`site-search ${hero ? 'site-search-hero' : 'site-search-compact'}`} ref={rootRef}>
      <form onSubmit={submit} className="site-search-form">
        <Search />
        <input
          ref={inputRef}
          aria-label="Search documentation"
          aria-expanded={open}
          aria-controls={`site-search-results-${variant}`}
          autoComplete="off"
          placeholder={placeholder}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
        />
        {hero ? (
          <button type="submit" aria-label="Search"><ArrowRight /></button>
        ) : (
          <kbd>Ctrl+K</kbd>
        )}
      </form>

      {open && (
        <div className="site-search-panel" id={`site-search-results-${variant}`}>
          {recent && !query && (
            <div className="site-search-group">
              <div className="site-search-label"><History /> Recently Viewed</div>
              <button type="button" className="site-search-result recent" onClick={() => visit(recent)}>
                <recent.icon />
                <span><strong>{recent.title}</strong><small>{recent.detail}</small></span>
                <ArrowRight />
              </button>
            </div>
          )}

          <div className="site-search-group">
            <div className="site-search-label"><ArrowRight /> Shortcuts</div>
            {matches.length ? matches.map((item, index) => (
              <button
                type="button"
                key={item.href}
                className={`site-search-result ${index === active ? 'active' : ''}`}
                onMouseEnter={() => setActive(index)}
                onClick={() => visit(item)}
              >
                <item.icon />
                <span><strong>{item.title}</strong><small>{item.detail}</small></span>
                <ArrowRight />
              </button>
            )) : (
              <button type="button" className="site-search-result active" onClick={() => visit(ITEMS[0])}>
                <Search />
                <span><strong>{query}</strong><small>Getting Started</small></span>
                <ArrowRight />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

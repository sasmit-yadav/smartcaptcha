import SiteNav from './SiteNav';
import SiteFooter from './SiteFooter';

export default function LegalPage({ title, updated, children }) {
  return (
    <div className="interior-shell min-h-screen bg-canvas text-ink">
      <SiteNav />
      <article className="legal-page">
        <header className="legal-hero">
          <p className="legal-kicker">Legal</p>
          <h1>{title}</h1>
          <p className="legal-updated">Last updated: {updated}</p>
        </header>
        <div className="legal-body">{children}</div>
      </article>
      <SiteFooter />
    </div>
  );
}

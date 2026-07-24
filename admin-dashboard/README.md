# VeilProof admin dashboard

Internal super-admin console (Next.js). Not required for customer integrations.

**Product status:** see CAPTCHA repo `docs/INDEX.md` (through P1: strict signing,
stealth Playwright blocked, Cloudflare ASN Worker live on `api.veilproof.tech`).

## Getting Started

```bash
npm install
npm run dev
```

Open http://localhost:3000 (or the port Next prints). Configure API base /
auth against production `https://api.veilproof.tech` per project env conventions.

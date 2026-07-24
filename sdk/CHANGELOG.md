# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.6] - 2026-07-24

### Fixed
- Structured FastAPI signing errors (`detail` object) are stringified for
  callers; `no_session_key` / expired registration triggers one forced
  re-register + retry under strict mode (multi-dyno safe with backend 1.1.6+).

## [1.1.5] - 2026-07-24

### Security
- CDP Runtime.enable leak is now **inconclusive soft evidence** only
  (`automation_score` 30, never decisive alone). Decisive signals remain
  `webdriver_true`, `webdriver_undefined`, non-native getters, and driver
  globals. Aligns with industry practice after Chrome 2025+ / CDP-minimal
  drivers made the classic console.stack probe unreliable as a sole verdict.

## [1.1.4] - 2026-07-24

### Security
- Detect stealth automation that hides `navigator.webdriver` (Playwright /
  Puppeteer init-script spoofs, driver globals, CDP Runtime.enable leak).
  Spoofed webdriver now sets `webdriver_flag` and `automation_score` so
  fingerprint scoring can block even when classic webdriver is patched.

## [1.1.3] - 2026-07-24

### Security
- Added session-bound request integrity and exact-request replay protection.
  The browser creates a non-exportable ECDSA P-256 private key, registers only
  its public key, and signs each `/api/predict` body with a fresh timestamp and
  nonce. The SDK waits for registration, refreshes expired/lost registration,
  and retries once after a backend restart. Client-computed feature values
  remain untrusted by design; duplicate feature-vector detection is a separate
  server-side layer.

## [1.1.2] - 2026-07-20

### Changed
- Default backend endpoint moved from the Render-hosted URL to
  `https://api.veilproof.tech`. Existing integrations pinning a custom
  `endpoint`/`data-endpoint` are unaffected; anyone relying on the default
  now talks to the new host.

## [1.1.1] - 2026-07-20

### Changed
- Reworded internal documentation (README, TypeScript type declarations) that
  described `behavior_score`/`fingerprint_score` in terms of implementation
  details (model type, specific signal names). No functional change —
  `dist/` output and the wire format are identical to `1.1.0`.

## [1.1.0] - 2026-07-18

### Fixed
- The published `1.0.0` package predated the client-side feature computation
  needed by the currently-deployed detection model — real integrations on
  `1.0.0` were silently sending an incomplete feature vector, with the
  missing fields defaulting to zero server-side. `1.1.0` ships the complete
  client-side computation; no integration code changes required, just
  upgrading the package/CDN version.

## [1.0.0] - 2026-07-15

### Changed — package renamed veriflow-sdk → veilproof
"VeriFlow" is a name already in use by another organization; the project is
rebranding to **VeilProof** before the customer base grows. Breaking changes:
- npm package: `veriflow-sdk` → `veilproof`. Install with `npm install veilproof`.
- Global: `window.VeriFlow` → `window.VeilProof`; `VeriFlowConfig` type →
  `VeilProofConfig`.
- Script-tag integration: `data-veriflow` → `data-veilproof`; the
  auto-injected hidden field defaults to `veilproof-token` (was
  `veriflow-token`), still overridable via `data-token-field`.
- Dist filenames: `veriflow.min.js`/`.esm.js`/`.cjs.js` →
  `veilproof.min.js`/`.esm.js`/`.cjs.js`.
- API key prefixes: `vf_site_`/`vf_secret_`/`vf_live_`/`vf_test_`/`vf_admin_`
  → `vp_site_`/`vp_secret_`/`vp_live_`/`vp_test_`/`vp_admin_`. Existing
  `vf_*` keys issued before this release are re-issued as `vp_*` — there was
  no live customer base yet, so no migration/dual-accept window was needed.
- `window.VERIFLOW_CONFIG` legacy global → `window.VEILPROOF_CONFIG`.

The prior `veriflow-sdk@0.1.1` package on npm is deprecated in favor of
`veilproof`; it is not unpublished (npm doesn't allow removing a package
that already has zero external dependents cleanly re-added later, and this
avoids breaking anyone who already installed it).

## [0.3.0] - 2026-07-14

### Added
- Script-tag auto-init: `<script src="..." data-site-key="vf_site_...">` now
  initializes the SDK with zero JS — no `<script data-*>` support existed
  before. Also reads `data-endpoint`, `data-debug`, `data-token-field`.
- `<form data-veriflow>` integration: intercepts submit, fetches a token, and
  injects a hidden `veriflow-token` input (name configurable via
  `data-token-field`) before letting the form submit natively. Fails open on
  token error.
- `getToken()` — callback and Promise overloads, wraps `getDecision()` and
  returns `{ token, decision, error? }` for the new server-side
  `/api/siteverify` flow (see `sdk-backend` — a bot can ignore/fake the raw
  browser decision, so the server must redeem a signed token to trust it).
- `DecisionResult.verification_token` — present when the backend issues one.

### Changed
- `validateConfig` now accepts `vf_site_` keys and **hard-rejects**
  `vf_secret_` keys with a loud error — secret keys must never run in the
  browser (they're valid only at `/api/siteverify`, server-side).
- `selfTest()`'s API-key check now prefers the actual `init()` config over
  the legacy `window.VERIFLOW_CONFIG` global, which script-tag/npm callers
  never set.
- `SDK_VERSION` synced to `0.3.0`; corrected the stale `Version: 0.1.0`
  header comment in `index.ts`.

## [0.2.0] - 2026-07-14

### Fixed
- `getDecision()` no longer passes a non-2xx `/api/predict` error body through
  as if it were a decision result (previously crashed downstream callers with
  `Cannot read properties of undefined (reading 'toLowerCase')`). Now returns
  a clean `{ action: 'block', error: '<reason>' }`.
- Default endpoint changed from `http://localhost:8001` to the production API
  (`https://next-captcha-sdk.onrender.com`) so the SDK works out of the box
  without an explicit `endpoint` config.
- `package.json` `exports` map now lists `types` first in each condition
  block (required for correct TypeScript resolution).
- `repository`/`bugs`/`homepage` metadata corrected to point at the real repo.

### Added
- `LICENSE` file (MIT, matching `package.json`).

### Changed
- Collector start/stop calls are now wrapped so an internal collector bug logs
  a warning instead of throwing into the host page.
- `SDK_VERSION` kept in sync with `package.json`.

## [0.1.0] - 2026-07-04

### Added
- Initial release of SmartCaptcha SDK
- Behavioral telemetry collection (mouse, keyboard, scroll, click, focus, touch events)
- Session management with unique session IDs
- Event buffering and batch transmission
- `init()` method for SDK initialization
- `getDecision()` method for bot detection decisions
- `getSessionId()` and `getSessionMeta()` methods
- Support for custom backend endpoints
- Debug mode for development
- Multiple build formats (UMD, ESM, CJS)
- Package exports map for automatic format selection
- Risk Engine integration with fingerprint detection

### Technical Details
- Bundle size: 11.7KB (minified UMD)
- Dependencies: esbuild for bundling
- Compatible with modern browsers and bundlers

### Known Limitations
- TypeScript types not yet included (planned for 0.2.0)
- CDN distribution not yet available (planned for 0.2.0)
- Framework wrappers (React, Vue) not yet available (planned for 0.3.0)

## [Unreleased]

### Planned
- TypeScript type definitions
- CDN distribution
- Enhanced error handling
- Debug mode improvements
- Framework wrappers

# VeilProof SDK

Behavioral telemetry SDK for invisible bot detection and fraud prevention.

## Installation

### Script tag — zero JS (any HTML site: WordPress, Django templates, Rails views, ...)

```html
<script src="https://cdn.jsdelivr.net/npm/veilproof@1.1.1/dist/veilproof.min.js"
        data-site-key="vp_site_..."
        async defer></script>
```

That's it — the SDK auto-initializes from the `data-site-key` attribute. Add
`data-debug="true"` for console logging, or `data-endpoint="..."` to override
the API host.

For a classic HTML `<form>` that posts to your server, add `data-veilproof`
and the SDK injects a hidden `veilproof-token` field before the real submit:

```html
<form data-veilproof action="/signup" method="post">
  <input name="email" type="email" required>
  <button type="submit">Sign up</button>
</form>
```

Your server then redeems that token with your **secret key** at
`POST /api/siteverify` — see [Server-side verification](#server-side-verification-siteverify) below. **Never put your secret key
(`vp_secret_...`) in browser code** — the SDK will refuse to initialize with one.

### Via npm (React/Vue/Next.js)

```bash
npm install veilproof
```

```javascript
import VeilProof from 'veilproof';

// Read the site key from your bundler's env convention (NEXT_PUBLIC_*,
// VITE_*, REACT_APP_*, webpack DefinePlugin, ...) rather than a string
// literal — not a secret, since it ships in the browser bundle either way,
// but a literal scattered across source files is still sloppy config hygiene.
VeilProof.init({
  apiKey: process.env.NEXT_PUBLIC_VEILPROOF_SITE_KEY // your site key — never your secret key
});
```

## Quick Start

```javascript
// Initialize the SDK with your site key
VeilProof.init({
  apiKey: process.env.NEXT_PUBLIC_VEILPROOF_SITE_KEY,
  debug: true // Enable for development
});

// Get a token and send it to your server for verification
VeilProof.getToken((result) => {
  fetch('/my-api/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ veilproofToken: result.token, /* ...your form data */ })
  });
});
```

## Server-side verification (siteverify)

The browser's decision is not a trust boundary — a bot can ignore or fake
it. Your **server** must redeem the token with your **secret key**
(`vp_secret_...`, never exposed to the browser) at `POST /api/siteverify`
before trusting the request:

```bash
curl -X POST https://next-captcha-sdk.onrender.com/api/siteverify \
  -H "X-API-Key: vp_secret_..." \
  -H "Content-Type: application/json" \
  -d '{"token": "<token from the browser>"}'
```

```json
{ "success": true, "risk_score": 12, "action": "allow", "hostname": "example.com" }
```

Tokens are single-use and expire after 120 seconds. On failure, the response
is still HTTP 200 with `{"success": false, "error-codes": [...]}` — check
`success`, not the status code.

## API Reference

### `VeilProof.init(config)`

Initialize the SDK with your configuration.

**Parameters:**
- `config.apiKey` (string, required) - Your **site key** (`vp_site_...`) from the dashboard. Never pass a secret key (`vp_secret_...`) here — the SDK rejects it.
- `config.endpoint` (string, optional) - Backend API URL (default: `https://next-captcha-sdk.onrender.com`)
- `config.debug` (boolean, optional) - Enable debug logging (default: false)
- `config.disableTelemetry` (boolean, optional) - Disable telemetry sending (default: false)

### `VeilProof.getDecision(callback)`

Get a bot detection decision based on collected behavioral data.

**Parameters:**
- `callback` (function) - Callback function receiving the decision result

**Result:**
```javascript
{
  action: 'allow' | 'block', // binary — no 'challenge' tier is implemented anywhere in the product
  risk_score: 0-100,         // combined risk score; >=50 blocks
  behavior_score: 0-100,     // VeilProof's behavioral risk signal
  fingerprint_score: 0-100,  // VeilProof's device/environment risk signal
  confidence: 0.0-1.0,       // distance of risk_score from the 50-point decision boundary
  error: undefined // present with action: 'block' if the request itself failed
}
```

`getDecision` fails **closed**: if the request to `/api/predict` errors, times
out, or the API key/domain is rejected, the callback receives
`{ action: 'block', risk_score: 100, error: '<reason>' }` rather than an
uncaught exception.

### `VeilProof.getToken(callback?)`

Get a verification token for your server to redeem at `/api/siteverify`.
Wraps `getDecision` — same failure semantics. Supports both a callback and a
Promise:

```javascript
// Callback style
VeilProof.getToken((result) => {
  // result.token, result.decision, result.error
});

// Promise style
const result = await VeilProof.getToken();
```

**Result:**
```javascript
{
  token: 'eyJhbGci...' | null, // null if acquisition failed — fail open in your integration
  decision: { action, risk_score, ... }, // same shape as getDecision's result
  error: undefined // present if the underlying request failed
}
```

### `VeilProof.getSessionId()`

Get the current session ID.

**Returns:** (string) Session identifier

### `VeilProof.getSessionMeta()`

Get session metadata including start time and platform info.

**Returns:** (object) Session metadata

### `VeilProof.getDebugSnapshot()`

Get current SDK state for troubleshooting.

**Returns:** (object) Debug snapshot with version, session info, buffer state, and recent events

### `VeilProof.selfTest(callback)`

Run self-test to verify SDK integration.

**Parameters:**
- `callback` (function) - Callback receiving test results

**Result:**
```javascript
{
  version: '1.1.1',
  tests: [
    { name: 'SDK Initialized', status: 'pass' },
    { name: 'API Key Valid', status: 'pass' },
    { name: 'Events Collected', status: 'pass' },
    { name: 'Network Reachable', status: 'pass' }
  ],
  passed: 4,
  failed: 0,
  overall: 'pass'
}
```

### `VeilProof.destroy()`

Stop all tracking and flush remaining events.

## Failure behavior

- **Never throws into the host page.** Collector start/stop and teardown
  calls are wrapped internally — a bug in one collector is logged to
  `console.warn` and suppressed, not propagated.
- **SSR-safe.** `init()` no-ops with a console warning when `window`/`document`
  are unavailable (Next.js App Router server components, etc).
- **Fails closed on `/api/predict` errors.** See `getDecision` above — this is
  a deliberate default for a security product; revisit if a backend outage
  should not block real users on your integration.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Development

```bash
# Install dependencies
npm install

# Build all formats
npm run build

# Development mode with watch
npm run dev

# Prepare for npm publish
npm run prepublishOnly
```

## License

MIT — see [LICENSE](./LICENSE).

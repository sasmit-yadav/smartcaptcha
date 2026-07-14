# VeriFlow SDK

Behavioral telemetry SDK for invisible bot detection and fraud prevention.

## Installation

### Via CDN (Plain HTML/WordPress)

```html
<script src="https://cdn.jsdelivr.net/npm/veriflow-sdk@0.2.0/dist/veriflow.min.js"></script>
<script>
  VeriFlow.init({
    apiKey: 'your-api-key'
  });
</script>
```

### Via npm (React/Vue/Next.js)

```bash
npm install veriflow-sdk
```

```javascript
import VeriFlow from 'veriflow-sdk';

VeriFlow.init({
  apiKey: 'your-api-key'
});
```

## Quick Start

```javascript
// Initialize the SDK
VeriFlow.init({
  apiKey: 'your-api-key',
  debug: true // Enable for development
});

// Get bot detection decision
VeriFlow.getDecision((result) => {
  if (result.action === 'block') {
    console.log('Bot detected:', result);
  } else {
    console.log('Human verified:', result);
  }
});
```

## API Reference

### `VeriFlow.init(config)`

Initialize the SDK with your configuration.

**Parameters:**
- `config.apiKey` (string, required) - Your API key from the dashboard
- `config.endpoint` (string, optional) - Backend API URL (default: `https://next-captcha-sdk.onrender.com`)
- `config.debug` (boolean, optional) - Enable debug logging (default: false)
- `config.disableTelemetry` (boolean, optional) - Disable telemetry sending (default: false)

### `VeriFlow.getDecision(callback)`

Get a bot detection decision based on collected behavioral data.

**Parameters:**
- `callback` (function) - Callback function receiving the decision result

**Result:**
```javascript
{
  action: 'allow' | 'block' | 'challenge',
  bot_probability: 0.0-1.0,
  risk_score: 0-100,
  confidence: 0.0-1.0,
  risk_engine_enabled: true,
  behavior_score: 0-100,
  fingerprint_score: 0-100,
  overall_risk: 0-100,
  error: undefined // present with action: 'block' if the request itself failed
}
```

`getDecision` fails **closed**: if the request to `/api/predict` errors, times
out, or the API key/domain is rejected, the callback receives
`{ action: 'block', risk_score: 100, error: '<reason>' }` rather than an
uncaught exception.

### `VeriFlow.getSessionId()`

Get the current session ID.

**Returns:** (string) Session identifier

### `VeriFlow.getSessionMeta()`

Get session metadata including start time and platform info.

**Returns:** (object) Session metadata

### `VeriFlow.getDebugSnapshot()`

Get current SDK state for troubleshooting.

**Returns:** (object) Debug snapshot with version, session info, buffer state, and recent events

### `VeriFlow.selfTest(callback)`

Run self-test to verify SDK integration.

**Parameters:**
- `callback` (function) - Callback receiving test results

**Result:**
```javascript
{
  version: '0.2.0',
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

### `VeriFlow.destroy()`

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

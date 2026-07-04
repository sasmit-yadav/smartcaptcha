# NextCaptcha SDK

Behavioral telemetry SDK for bot detection and fraud prevention.

## Installation

### Via CDN (Plain HTML/WordPress)

```html
<script src="https://cdn.nextcaptcha.ai/v0.1.0/sdk.min.js"></script>
<script>
  NextCaptcha.init({
    apiKey: 'your-api-key',
    endpoint: 'https://api.nextcaptcha.ai'
  });
</script>
```

### Via npm (React/Vue/Next.js)

```bash
npm install @nextcaptcha/sdk
```

```javascript
import NextCaptcha from '@nextcaptcha/sdk';

NextCaptcha.init({
  apiKey: 'your-api-key',
  endpoint: 'https://api.nextcaptcha.ai'
});
```

## Quick Start

```javascript
// Initialize the SDK
NextCaptcha.init({
  apiKey: 'your-api-key',
  endpoint: 'https://api.nextcaptcha.ai',
  debug: true // Enable for development
});

// Get bot detection decision
NextCaptcha.getDecision((result) => {
  if (result.action === 'block') {
    console.log('Bot detected:', result);
  } else {
    console.log('Human verified:', result);
  }
});
```

## API Reference

### `NextCaptcha.init(config)`

Initialize the SDK with your configuration.

**Parameters:**
- `config.apiKey` (string, required) - Your API key from the dashboard
- `config.endpoint` (string, optional) - Backend API URL (default: from global config)
- `config.debug` (boolean, optional) - Enable debug logging (default: false)

### `NextCaptcha.getDecision(callback)`

Get a bot detection decision based on collected behavioral data.

**Parameters:**
- `callback` (function) - Callback function receiving the decision result

**Result:**
```javascript
{
  action: 'allow' | 'block',
  bot_probability: 0.0-1.0,
  risk_score: 0-100,
  confidence: 0.0-1.0,
  risk_engine_enabled: true,
  behavior_score: 0-100,
  fingerprint_score: 0-100,
  overall_risk: 0-100
}
```

### `NextCaptcha.getSessionId()`

Get the current session ID.

**Returns:** (string) Session identifier

### `NextCaptcha.getSessionMeta()`

Get session metadata including start time and platform info.

**Returns:** (object) Session metadata

### `NextCaptcha.getDebugSnapshot()`

Get current SDK state for troubleshooting.

**Returns:** (object) Debug snapshot with version, session info, buffer state, and recent events

### `NextCaptcha.selfTest(callback)`

Run self-test to verify SDK integration.

**Parameters:**
- `callback` (function) - Callback receiving test results

**Result:**
```javascript
{
  version: '0.1.0',
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

### `NextCaptcha.destroy()`

Stop all tracking and flush remaining events.

## Bundle Size

- UMD (minified): 13.3KB
- ESM: 25.8KB  
- CJS: 26.7KB

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

MIT

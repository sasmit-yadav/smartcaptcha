# Quick Start Guide

Get SmartCaptcha working on your site in under 5 minutes.

## Step 1: Get Your API Key

1. Go to [https://smartcaptcha.ai/dashboard](https://smartcaptcha.ai/dashboard)
2. Sign up for an account
3. Copy your API key (starts with `sc_live_`)

## Step 2: Add the SDK to Your Site

### Option A: Plain HTML / WordPress

```html
<!DOCTYPE html>
<html>
<head>
  <title>Your Site</title>
  <script src="https://cdn.smartcaptcha.ai/v0.1.0/sdk.min.js"></script>
</head>
<body>
  <script>
    SmartCaptcha.init({
      apiKey: 'YOUR_API_KEY_HERE',
      endpoint: 'https://api.smartcaptcha.ai'
    });
  </script>
</body>
</html>
```

### Option B: React / Next.js

```bash
npm install @smartcaptcha/sdk
```

```javascript
import { useEffect } from 'react';
import SmartCaptcha from '@smartcaptcha/sdk';

function App() {
  useEffect(() => {
    SmartCaptcha.init({
      apiKey: 'YOUR_API_KEY_HERE',
      endpoint: 'https://api.smartcaptcha.ai'
    });
  }, []);

  return <div>Your App</div>;
}
```

### Option C: Vue / Nuxt

```bash
npm install @smartcaptcha/sdk
```

```javascript
import { onMounted } from 'vue';
import SmartCaptcha from '@smartcaptcha/sdk';

export default {
  setup() {
    onMounted(() => {
      SmartCaptcha.init({
        apiKey: 'YOUR_API_KEY_HERE',
        endpoint: 'https://api.smartcaptcha.ai'
      });
    });
  }
}
```

## Step 3: Get Bot Detection Decision

```javascript
SmartCaptcha.getDecision((result) => {
  if (result.action === 'block') {
    // Block the action - likely a bot
    console.log('Bot detected:', result);
    alert('Security check failed. Please try again.');
  } else {
    // Allow the action - likely human
    console.log('Human verified:', result);
    // Proceed with form submission, etc.
  }
});
```

## Step 4: Verify It's Working

1. Open your site in a browser
2. Open browser console (F12)
3. Run: `SmartCaptcha.getDebugSnapshot()`
4. Check your dashboard at [https://smartcaptcha.ai/dashboard](https://smartcaptcha.ai/dashboard)
5. You should see "It's Working!" with session count

## Troubleshooting

### SDK not loading
- Check browser console for errors
- Verify CDN URL is correct
- Check network tab for failed requests

### No events in dashboard
- Make sure you've interacted with the page (mouse, keyboard, etc.)
- Check that API key is correct
- Verify endpoint URL matches your dashboard

### Integration issues
- Run `SmartCaptcha.selfTest((results) => console.log(results))` to diagnose
- Check debug logs by setting `debug: true` in init config
- Ensure you're not initializing the SDK multiple times

## Next Steps

- Read the [full API documentation](README.md)
- Check out the [interactive playground](https://playground.smartcaptcha.ai)
- Review [integration guides](INTEGRATION.md) for your framework

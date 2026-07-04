/**
 * NextCaptcha SDK Configuration
 * 
 * NOTE: This config is for SDK development/testing only.
 * Production SDK does not use this file - customers configure
 * backend URL via NextCaptcha.init({ endpoint: '...' })
 * 
 * Current Architecture:
 * - Port 8000: Telemetry backend (demo site)
 * - Port 8001: SDK backend (predictions for customers)
 */

window.SMARTCAPTCHA_CONFIG = {
  // SDK Backend for predictions (port 8001)
  BACKEND_URL: (function() {
    const DEFAULT_BACKEND = 'https://api.nextcaptcha.com';
    const LOCAL_SDK_BACKEND = 'http://localhost:8001';
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return LOCAL_SDK_BACKEND;
    }
    return DEFAULT_BACKEND;
  })(),

  // API key (for demo purposes)
  API_KEY: 'demo-key',

  // Debug mode
  DEBUG: false,
};

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
    // Always use production backend
    return 'https://api.veilproof.tech';
  })(),

  // API key (for demo purposes)
  API_KEY: 'demo-key',

  // Debug mode
  DEBUG: false,
};

/**
 * VeilProof Demo Site Configuration
 * Centralized backend URL configuration - update this single file to change backend endpoint
 */

window.NEXTCAPTCHA_CONFIG = {
  // Backend API endpoint - automatically use local backend when running on localhost
  BACKEND_URL: (function() {
    // Consolidated VeilProof API (predictions + telemetry storage)
    const DEFAULT_BACKEND = 'https://next-captcha-sdk.onrender.com';
    // sdk-backend runs on port 8001 locally (uvicorn main:app --port 8001)
    const LOCAL_BACKEND = 'http://localhost:8001';
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return LOCAL_BACKEND;
    }
    return DEFAULT_BACKEND;
  })(),

  // API key (for demo purposes)
  API_KEY: 'demo-key',

  // Debug mode
  DEBUG: false,
};

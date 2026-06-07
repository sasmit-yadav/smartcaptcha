(function(){
  // Mobile blocker: if running on a mobile device, show a full-screen overlay
  // and set flags so the SDK can avoid sending telemetry.

  function isMobile() {
    // Common UA check + small viewport fallback
    const ua = navigator.userAgent || navigator.vendor || window.opera;
    const mobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
    if (mobileUA.test(ua)) return true;
    try {
      return window.matchMedia && window.matchMedia('(pointer:coarse)').matches && window.innerWidth <= 900;
    } catch (e) {
      return (window.innerWidth || 0) <= 700;
    }
  }

  // Allow forcing mobile mode for testing via URL param: ?force_mobile=1
  const urlParams = (typeof URLSearchParams !== 'undefined') ? new URLSearchParams(window.location.search) : null;
  const forceMobile = urlParams && (urlParams.get('force_mobile') === '1' || urlParams.get('force_mobile') === 'true');

  if (!isMobile() && !forceMobile) return;
  if (forceMobile) console.warn('[SmartCaptcha] mobile_blocker: forced mobile mode via URL param');

  // Set global flags for SDKs to respect
  window.SMARTCAPTCHA_DISABLED = true;
  window.SMARTCAPTCHA_BLOCKED_FOR_MOBILE = true;

  // Create overlay
  const overlay = document.createElement('div');
  overlay.id = 'smartcaptcha-mobile-blocker';
  Object.assign(overlay.style, {
    position: 'fixed',
    top: '0', left: '0', right: '0', bottom: '0',
    background: 'rgba(0,0,0,0.85)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: '999999',
    padding: '20px',
    textAlign: 'center',
    fontFamily: 'Inter, Arial, sans-serif',
  });

  const box = document.createElement('div');
  Object.assign(box.style, {
    maxWidth: '520px',
    borderRadius: '12px',
    padding: '24px',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))',
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
  });

  const title = document.createElement('h2');
  title.textContent = 'Desktop / Laptop Only';
  Object.assign(title.style, {margin: '0 0 8px 0', fontSize: '22px'});

  const msg = document.createElement('p');
  msg.textContent = 'This demo is intended for desktop and laptop browsers. For accurate telemetry and testing, please open the site from a PC or laptop.';
  Object.assign(msg.style, {margin: '0 0 16px 0', fontSize: '15px', lineHeight: '1.4', opacity: '0.95'});

  const actions = document.createElement('div');
  Object.assign(actions.style, {display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '12px'});

  const closeBtn = document.createElement('button');
  closeBtn.textContent = 'I understand, continue anyway';
  Object.assign(closeBtn.style, {
    padding: '10px 14px',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    background: '#444',
    color: '#fff',
  });

  const infoBtn = document.createElement('button');
  infoBtn.textContent = 'Open on Desktop';
  Object.assign(infoBtn.style, {
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.08)',
    cursor: 'pointer',
    background: 'transparent',
    color: '#fff'
  });

  actions.appendChild(closeBtn);
  actions.appendChild(infoBtn);

  box.appendChild(title);
  box.appendChild(msg);
  box.appendChild(actions);
  overlay.appendChild(box);
  document.documentElement.appendChild(overlay);

  // If user insists, allow continuing but keep telemetry disabled
  closeBtn.addEventListener('click', function(){
    // Keep SMARTCAPTCHA_DISABLED true to avoid telemetry, but remove overlay
    try{ overlay.remove(); } catch(e){}
    window.SMARTCAPTCHA_USER_OVERRIDEMOBILE = true;
  });

  infoBtn.addEventListener('click', function(){
    // Suggest desktop URL copy
    try{ navigator.clipboard && navigator.clipboard.writeText(window.location.href); } catch(e){}
    alert('Open this page on a desktop or laptop for full functionality. URL has been copied to clipboard.');
  });

})();

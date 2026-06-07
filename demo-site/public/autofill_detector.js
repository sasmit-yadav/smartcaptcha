(function(){
  // Autofill detector: marks probable autofill events and suppresses sending next input
  // Usage: include this script after SDK and config; SDK should respect window.SMARTCAPTCHA_SUPPRESS_NEXT_INPUT

  const AF_THRESHOLD_MS = 400; // if no key within this time, value-change likely autofill
  const SUPPRESS_MS = 1500; // suppression duration after detection

  const keyTimes = new WeakMap();
  const lastValues = new WeakMap();

  function recordKey(e){
    try{ keyTimes.set(e.target, Date.now()); }catch(_){ }
  }

  function onFocus(e){
    try{
      // store value at focus to compare later
      lastValues.set(e.target, e.target.value || '');
      keyTimes.set(e.target, 0);
      // try to discourage browser autofill for sensitive fields
      try{
        if (e.target && e.target.autocomplete !== 'off'){
          e.target.setAttribute('autocomplete', 'off');
        }
      }catch(_){ }
    }catch(_){ }
  }

  function onInput(e){
    try{
      const prev = lastValues.get(e.target) || '';
      const val = e.target.value || '';
      const lastKey = keyTimes.get(e.target) || 0;
      const dt = lastKey ? (Date.now() - lastKey) : Infinity;

      // If value changed and there was no recent keypress, consider autofill/paste
      const changed = val !== prev;
      if (changed && (dt > AF_THRESHOLD_MS)){
        // Heuristic: if the change is large (many chars) or exactly replaces empty -> filled, mark autofill
        const likelyAutofill = (prev.length === 0 && val.length > 0) || (Math.abs(val.length - prev.length) > 3);
        if (likelyAutofill) {
          window.SMARTCAPTCHA_AUTOFILL = window.SMARTCAPTCHA_AUTOFILL || {detected: true, firstSeen: Date.now()};
          window.SMARTCAPTCHA_SUPPRESS_NEXT_INPUT = true;
          setTimeout(()=>{ window.SMARTCAPTCHA_SUPPRESS_NEXT_INPUT = false; }, SUPPRESS_MS);
          if (window.smartcaptcha && typeof window.smartcaptcha.setSessionMeta === 'function'){
            try{ window.smartcaptcha.setSessionMeta({ hasAutofill: true }); }catch(_){ }
          }
          console.warn('[SmartCaptcha] Autofill detected, suppressing next input event');
        }
      }

      // update last value
      lastValues.set(e.target, val);
    }catch(err){ /* noop */ }
  }

  function onPaste(e){
    try{
      // Consider pasted values as user-driven; do not mark as autofill, but update state
      lastValues.set(e.target, e.target.value || '');
      keyTimes.set(e.target, Date.now());
    }catch(_){ }
  }

  // Attach listeners to document to cover dynamically added inputs
  document.addEventListener('keydown', recordKey, true);
  document.addEventListener('input', onInput, true);
  document.addEventListener('change', onInput, true);
  document.addEventListener('focus', onFocus, true);
  document.addEventListener('paste', onPaste, true);

  // Initial pass: set autocomplete="off" on common inputs to reduce suggestion popups
  try{
    const selectors = 'input[type="email"],input[type="password"],input[type="text"],input[autocomplete]';
    document.querySelectorAll(selectors).forEach(el => {
      try{ if (!el.getAttribute('data-allow-autofill')) el.setAttribute('autocomplete','off'); }catch(_){ }
    });
  }catch(_){ }

})();

(function(){
  // SDK shim to respect global suppression/disable flags set by detector scripts.
  if (!window.SmartCaptcha) return;
  if (window.__SMARTCAPTCHA_SHIM_INSTALLED) return;
  window.__SMARTCAPTCHA_SHIM_INSTALLED = true;

  const origInit = window.SmartCaptcha.init.bind(window.SmartCaptcha);

  function wrapClient(client){
    if (!client || typeof client !== 'object') return client;
    // store reference
    window.smartcaptcha = client;

    const methodNames = ['sendEvent','track','reportEvent','sendTelemetry','setSessionMeta','identify','record'];
    methodNames.forEach(name => {
      if (typeof client[name] === 'function'){
        const orig = client[name].bind(client);
        client[name] = function(){
          try{
            if (window.SMARTCAPTCHA_DISABLED) return; // globally disabled (e.g., mobile)
            // simple heuristic: if suppress-next-input set and event looks like an input
            const args = Array.from(arguments);
            const first = args[0] || {};
            const type = (first && first.type) || (first && first.event) || '';
            if (window.SMARTCAPTCHA_SUPPRESS_NEXT_INPUT && typeof type === 'string'){
              const t = type.toLowerCase();
              if (t.includes('input') || t.includes('change') || t.includes('autofill')){
                // consume suppression then skip sending
                window.SMARTCAPTCHA_SUPPRESS_NEXT_INPUT = false;
                return;
              }
            }
          }catch(e){ /* swallow */ }
          return orig.apply(null, arguments);
        };
      }
    });

    return client;
  }

  window.SmartCaptcha.init = function(){
    const res = origInit.apply(null, arguments);
    if (res && typeof res.then === 'function'){
      return res.then(c => wrapClient(c));
    }
    return wrapClient(res);
  };
})();

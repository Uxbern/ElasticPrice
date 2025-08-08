// content.js
(() => {
  const STATE = {
    processing: false
  };

  function findComposer() {
    // ChatGPT composer textarea
    const t = document.querySelector('textarea');
    return t || null;
  }

  function findSendButton() {
    // ChatGPT send button (data-testid is stable)
    return document.querySelector('button[data-testid="send-button"]');
  }

  function showBanner(text) {
    let el = document.getElementById('__ner_banner__');
    if (!el) {
      el = document.createElement('div');
      el.id = '__ner_banner__';
      Object.assign(el.style, {
        position: 'fixed',
        right: '12px',
        bottom: '12px',
        zIndex: 999999,
        fontFamily: 'system-ui, sans-serif',
        padding: '10px 12px',
        borderRadius: '8px',
        background: '#111',
        color: '#fff',
        boxShadow: '0 6px 20px rgba(0,0,0,0.25)',
        opacity: '0.9'
      });
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.style.display = 'block';
    clearTimeout(el.__t);
    el.__t = setTimeout(() => (el.style.display = 'none'), 2000);
  }

  function dispatchInput(el) {
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }

  async function sanitizeAndSend() {
    if (STATE.processing) return;
    const textarea = findComposer();
    const sendBtn = findSendButton();
    if (!textarea) return;

    const text = textarea.value || '';
    if (!text.trim()) return;

    STATE.processing = true;
    showBanner('Sanitizing with NER… (first run may take a few seconds)');
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'NER_SANITIZE',
        text
        // model/threshold/maskStyle can be overridden here if desired
      });

      const sanitized = response?.sanitizedText || text;
      textarea.value = sanitized;
      dispatchInput(textarea);

      if (sendBtn) {
        sendBtn.click();
      } else {
        // Fallback: simulate Enter key
        textarea.dispatchEvent(new KeyboardEvent('keydown', {
          bubbles: true,
          cancelable: true,
          key: 'Enter',
          code: 'Enter'
        }));
      }

      const changed = sanitized !== text;
      showBanner(changed ? 'Prompt sanitized (NER applied) ✅' : 'No entities detected (sent as-is).');
    } catch (e) {
      console.warn('NER sanitize failed', e);
      showBanner('Sanitization failed — sent original.');
      // Let the original submit happen (user can press Enter again)
    } finally {
      STATE.processing = false;
    }
  }

  function installKeyInterceptor() {
    const textarea = findComposer();
    if (!textarea) return;

    // Avoid duplicate listeners
    if (textarea.__ner_installed) return;
    textarea.__ner_installed = true;

    textarea.addEventListener('keydown', (ev) => {
      // Intercept Enter (without Shift/Ctrl) to sanitize before sending
      if (ev.key === 'Enter' && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        ev.stopPropagation();
        sanitizeAndSend();
      }
    }, true);
  }

  // Retry until composer is available
  const iv = setInterval(() => {
    installKeyInterceptor();
    if (findComposer()) clearInterval(iv);
  }, 500);
})();

// service_worker.js
let offscreenCreated = false;

async function ensureOffscreen() {
  if (offscreenCreated) return;
  try {
    // chrome.offscreen.hasDocument() may not exist on older builds; catch creation errors instead.
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['BLOBS'],
      justification: 'Run Transformers.js NER locally to sanitize prompts before sending.'
    });
    offscreenCreated = true;
  } catch (e) {
    // If it's already created, ignore.
    if (!String(e).includes('Offscreen document already exists')) {
      console.warn('Offscreen create failed:', e);
    } else {
      offscreenCreated = true;
    }
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  await ensureOffscreen();
  // Defaults
  chrome.storage.local.set({
    ner_model: 'Xenova/bert-base-NER', // Change to another Transformers.js-compatible NER if desired
    ner_threshold: 0.5,                 // confidence threshold
    ner_mask_style: 'tag'               // 'tag' or 'block'
  });
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === 'NER_SANITIZE') {
    (async () => {
      await ensureOffscreen();

      const id = crypto.randomUUID();
      const listener = (response, _sender) => {
        if (response?.type === 'OFFSCREEN_NER_RESULT' && response.id === id) {
          chrome.runtime.onMessage.removeListener(listener);
          sendResponse(response.payload);
        }
      };
      chrome.runtime.onMessage.addListener(listener);

      // Gather config
      const conf = await chrome.storage.local.get(['ner_model', 'ner_threshold', 'ner_mask_style']);

      await chrome.runtime.sendMessage({
        type: 'OFFSCREEN_NER',
        id,
        text: msg.text,
        model: msg.model || conf.ner_model || 'Xenova/bert-base-NER',
        threshold: typeof msg.threshold === 'number' ? msg.threshold : (conf.ner_threshold ?? 0.5),
        maskStyle: msg.maskStyle || conf.ner_mask_style || 'tag'
      });
    })();

    return true; // keep the message channel open for async sendResponse
  }
});

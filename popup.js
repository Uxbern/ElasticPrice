// popup.js  (FULL FILE)
// New vs. “no-popup” setup: this adds a UI to toggle the sanitizer,
// set model/threshold/mask style, and send NER_WARMUP to preload the model.
// If you already used my earlier popup.js, this is the same file.

const els = {
  enabled: document.getElementById('enabled'),
  model: document.getElementById('model'),
  threshold: document.getElementById('threshold'),
  mask: document.getElementById('mask'),
  save: document.getElementById('save'),
  warmup: document.getElementById('warmup'),
  status: document.getElementById('status'),
};

async function load() {
  const {
    ner_enabled = true,
    ner_model = 'Xenova/bert-base-NER',
    ner_threshold = 0.5,
    ner_mask_style = 'tag',
  } = await chrome.storage.local.get([
    'ner_enabled',
    'ner_model',
    'ner_threshold',
    'ner_mask_style',
  ]);

  els.enabled.checked = !!ner_enabled;
  els.model.value = ner_model;
  els.threshold.value = ner_threshold;
  els.mask.value = ner_mask_style;
}

async function save() {
  const payload = {
    ner_enabled: !!els.enabled.checked,
    ner_model: (els.model.value || '').trim() || 'Xenova/bert-base-NER',
    ner_threshold: Math.min(1, Math.max(0, parseFloat(els.threshold.value) || 0.5)),
    ner_mask_style: els.mask.value === 'block' ? 'block' : 'tag',
  };
  await chrome.storage.local.set(payload);
  els.status.textContent = 'Saved';
  setTimeout(() => (els.status.textContent = ''), 1200);
}

async function warmup() {
  els.status.textContent = 'Loading…';
  try {
    const model = (els.model.value || '').trim() || 'Xenova/bert-base-NER';
    const ok = await chrome.runtime.sendMessage({ type: 'NER_WARMUP', model });
    els.status.textContent = ok ? 'Ready' : 'Failed';
  } catch (e) {
    console.warn(e);
    els.status.textContent = 'Failed';
  }
  setTimeout(() => (els.status.textContent = ''), 1500);
}

els.save.addEventListener('click', save);
els.warmup.addEventListener('click', warmup);
document.addEventListener('DOMContentLoaded', load);

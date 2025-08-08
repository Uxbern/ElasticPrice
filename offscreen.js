// offscreen.js  (FULL FILE)
// Runs entirely on-device with Transformers.js in an offscreen document.
// Handles two messages:
//   - OFFSCREEN_NER: run NER, return sanitized text + entities
//   - OFFSCREEN_WARMUP: preload the model to avoid first-run latency

import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers/dist/transformers.min.js';

const pipelines = new Map();

/** Lazy-load and memoize a token-classification (NER) pipeline */
async function getNER(model) {
  if (!pipelines.has(model)) {
    const ner = await pipeline('token-classification', model, {
      aggregation_strategy: 'simple',
    });
    pipelines.set(model, ner);
  }
  return pipelines.get(model);
}

/** Replace entity spans with tags or blocks */
function applyRedaction(text, entities, maskStyle = 'tag') {
  // Replace from the end so indices remain valid
  const sorted = [...entities].sort((a, b) => b.start - a.start);
  let out = text;
  for (const e of sorted) {
    const label = (e.entity_group || e.entity || 'ENT').toUpperCase();
    const replacement =
      maskStyle === 'block'
        ? '█'.repeat(Math.max(1, e.end - e.start))
        : `<${label}>`;
    out = out.slice(0, e.start) + replacement + out.slice(e.end);
  }
  return out;
}

chrome.runtime.onMessage.addListener(async (msg) => {
  // Preload model
  if (msg?.type === 'OFFSCREEN_WARMUP') {
    try {
      await getNER(msg.model);
      chrome.runtime.sendMessage({
        type: 'OFFSCREEN_WARMUP_RESULT',
        id: msg.id,
        ok: true,
      });
    } catch (error) {
      chrome.runtime.sendMessage({
        type: 'OFFSCREEN_WARMUP_RESULT',
        id: msg.id,
        ok: false,
        error: String(error),
      });
    }
    return; // no sendResponse needed
  }

  // Run NER + sanitization
  if (msg?.type === 'OFFSCREEN_NER') {
    try {
      const ner = await getNER(msg.model);
      const result = await ner(msg.text, { ignore_labels: [] }); // return all labels

      const threshold =
        typeof msg.threshold === 'number' ? msg.threshold : 0.5;

      // Normalize & filter
      const entities = (Array.isArray(result) ? result : [])
        .map((e) => ({
          start: e.start,
          end: e.end,
          score: e.score,
          entity_group: (e.entity_group || e.entity || '').toUpperCase(),
          word: e.word,
        }))
        .filter(
          (e) =>
            e.start != null &&
            e.end != null &&
            (e.score ?? 1) >= threshold
        );

      const sanitizedText = applyRedaction(
        msg.text,
        entities,
        msg.maskStyle
      );

      chrome.runtime.sendMessage({
        type: 'OFFSCREEN_NER_RESULT',
        id: msg.id,
        payload: { sanitizedText, entities },
      });
    } catch (error) {
      chrome.runtime.sendMessage({
        type: 'OFFSCREEN_NER_RESULT',
        id: msg.id,
        payload: {
          sanitizedText: msg.text, // fallback
          entities: [],
          error: String(error),
        },
      });
    }
  }
});

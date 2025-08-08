// offscreen.js
// NOTE: For local dev this imports from CDN. For store submission, bundle this file instead.
import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers/dist/transformers.min.js';

// Optional tuning for WASM backends if needed:
// env.backends.onnx.wasm.wasmPaths = 'https://cdn.jsdelivr.net/npm/@xenova/transformers/dist/';

const pipelines = new Map();

/**
 * Load (or reuse) a token-classification pipeline.
 * @param {string} model
 */
async function getNER(model) {
  if (!pipelines.has(model)) {
    // Lazy-load model on first use
    const ner = await pipeline('token-classification', model, {
      // Use simple aggregation to get entity-level spans
      aggregation_strategy: 'simple'
    });
    pipelines.set(model, ner);
  }
  return pipelines.get(model);
}

/**
 * Sanitize text by masking detected entities.
 * @param {string} text
 * @param {Array} entities - [{start, end, entity_group, score}]
 * @param {string} maskStyle - 'tag' | 'block'
 */
function applyRedaction(text, entities, maskStyle = 'tag') {
  // Sort by start descending so indexes remain valid while replacing
  const sorted = [...entities].sort((a, b) => b.start - a.start);

  let out = text;
  for (const e of sorted) {
    const label = (e.entity_group || e.entity || 'ENT').toUpperCase();
    const replacement = maskStyle === 'block'
      ? '█'.repeat(Math.max(1, e.end - e.start))
      : `<${label}>`;
    out = out.slice(0, e.start) + replacement + out.slice(e.end);
  }
  return out;
}

chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {
  if (msg?.type === 'OFFSCREEN_NER') {
    try {
      const ner = await getNER(msg.model);
      const result = await ner(msg.text, { ignore_labels: [] });

      const threshold = typeof msg.threshold === 'number' ? msg.threshold : 0.5;

      // Filter, normalize fields
      const ents = (Array.isArray(result) ? result : []).map(e => ({
        start: e.start,
        end: e.end,
        score: e.score,
        entity_group: (e.entity_group || e.entity || '').toUpperCase(),
        word: e.word
      })).filter(e => e.start != null && e.end != null && (e.score ?? 1) >= threshold);

      const sanitizedText = applyRedaction(msg.text, ents, msg.maskStyle);

      chrome.runtime.sendMessage({
        type: 'OFFSCREEN_NER_RESULT',
        id: msg.id,
        payload: {
          sanitizedText,
          entities: ents
        }
      });
    } catch (err) {
      chrome.runtime.sendMessage({
        type: 'OFFSCREEN_NER_RESULT',
        id: msg.id,
        payload: {
          sanitizedText: msg.text, // graceful fallback: no changes
          entities: [],
          error: String(err)
        }
      });
    }
  }
});

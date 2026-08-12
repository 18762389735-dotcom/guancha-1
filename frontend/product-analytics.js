(function (global) {
  'use strict';

  const CLIENT_EVENTS = new Set([
    'app_open', 'start_selection', 'onboarding_started', 'onboarding_completed',
    'onboarding_skipped', 'need_started', 'candidate_result_viewed',
    'merchant_question_viewed', 'merchant_question_copied', 'merchant_reply_started',
    'candidate_selected', 'tea_stock_added', 'flow_abandoned',
  ]);
  const METADATA_FIELDS = new Set([
    'candidate_count', 'image_count', 'has_budget', 'has_sensory_need',
    'question_field', 'question_count', 'action_bucket', 'processing_mode',
    'failure_category', 'onboarding_status', 'source', 'screen',
  ]);
  const SESSION_KEY = 'guancha.analytics-session.v1';
  const MAX_STRING = 64;

  function uuid() {
    if (global.crypto && typeof global.crypto.randomUUID === 'function') return global.crypto.randomUUID();
    const bytes = new Uint8Array(16);
    global.crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  function sessionId() {
    try {
      const existing = global.sessionStorage.getItem(SESSION_KEY);
      if (existing) return existing;
      const created = uuid(); global.sessionStorage.setItem(SESSION_KEY, created); return created;
    } catch { return uuid(); }
  }
  function safeMetadata(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) return {};
    const result = {};
    for (const [key, value] of Object.entries(input)) {
      if (!METADATA_FIELDS.has(key)) continue;
      if (typeof value === 'boolean') result[key] = value;
      else if (typeof value === 'number' && Number.isFinite(value)) result[key] = Math.max(0, Math.min(10000, value));
      else if (typeof value === 'string' && value.length <= MAX_STRING) result[key] = value;
    }
    return result;
  }
  function create(options) {
    const endpoint = (options && options.endpoint) || '/api/v1/events';
    const transport = options && options.transport;
    let flowId = null;
    function startFlow() { flowId = uuid(); return flowId; }
    function endFlow() { flowId = null; }
    function track(eventName, fields) {
      if (!CLIENT_EVENTS.has(eventName)) return false;
      const values = fields || {};
      const event = {
        event_id: uuid(), event_name: eventName, anonymous_session_id: sessionId(),
        occurred_at: new Date().toISOString(), flow_id: values.flow_id || flowId,
        metadata: safeMetadata(values.metadata),
      };
      for (const key of ['candidate_id', 'decision_version_id', 'stage', 'duration_ms', 'error_category']) {
        const value = values[key];
        if (typeof value === 'string' && value.length <= MAX_STRING) event[key] = value;
        else if (key === 'duration_ms' && typeof value === 'number' && Number.isFinite(value)) event[key] = Math.max(0, Math.min(86400000, value));
      }
      try {
        const body = JSON.stringify(event);
        if (transport) Promise.resolve().then(() => transport(event)).catch(() => {});
        else if (global.fetch) global.fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true }).catch(() => {});
        return true;
      } catch { return false; }
    }
    return Object.freeze({ track, startFlow, endFlow, currentFlowId: () => flowId, safeMetadata });
  }

  global.GuanchaProductAnalytics = Object.freeze({ create, getSessionId: sessionId, CLIENT_EVENTS, METADATA_FIELDS });
}(window));

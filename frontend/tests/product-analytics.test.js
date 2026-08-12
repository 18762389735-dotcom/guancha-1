const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const crypto = require('node:crypto').webcrypto;

function analytics(initial = {}) {
  const values = new Map(Object.entries(initial)); const sent = [];
  const window = { crypto, sessionStorage: { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value) }, setTimeout };
  window.window = window;
  vm.runInNewContext(fs.readFileSync(path.resolve(__dirname, '..', 'product-analytics.js'), 'utf8'), window);
  return { api: window.GuanchaProductAnalytics.create({ transport: event => sent.push(event) }), sent, values };
}

test('client analytics uses session identity and strict bounded metadata', async () => {
  const { api, sent } = analytics(); api.startFlow();
  assert.equal(api.track('start_selection', { metadata: { candidate_count: 2, has_budget: true, need_text: 'private', raw_text: 'secret', screen: 'home', nested: { token: 'bad' } } }), true);
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(sent.length, 1); assert.equal(sent[0].metadata.candidate_count, 2);
  assert.equal(sent[0].metadata.need_text, undefined); assert.equal(JSON.stringify(sent[0]).includes('private'), false);
  assert.match(sent[0].anonymous_session_id, /^[0-9a-f-]{36}$/); assert.ok(sent[0].flow_id);
});

test('client cannot report server-authoritative outcomes and telemetry is fail-open', async () => {
  const { api, sent } = analytics();
  assert.equal(api.track('analysis_completed', { metadata: { screen: 'result' } }), false);
  assert.equal(sent.length, 0);
  const failing = (function () { const values = new Map(); const window = { crypto, sessionStorage: { getItem:k=>values.get(k)||null, setItem:(k,v)=>values.set(k,v) } }; window.window=window; vm.runInNewContext(fs.readFileSync(path.resolve(__dirname, '..', 'product-analytics.js'), 'utf8'), window); return window.GuanchaProductAnalytics.create({ transport: () => Promise.reject(new Error('offline')) }); }());
  assert.equal(failing.track('app_open'), true);
  await new Promise(resolve => setTimeout(resolve, 0));
});

test('analytics rotates invalid session ids and rejects non-enum ids and metadata values', async () => {
  const { api, sent, values } = analytics({ 'guancha.analytics-session.v1': 'not-a-uuid' });
  api.startFlow();
  assert.equal(api.track('candidate_result_viewed', { candidate_id: 'candidate-name', stage: 'private Need text', metadata: { screen: 'C:\\private\\path', source: '=formula', question_field: 'merchant secret' } }), true);
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(values.get('guancha.analytics-session.v1'), /^[0-9a-f-]{36}$/);
  assert.equal(sent[0].candidate_id, undefined);
  assert.equal(sent[0].stage, undefined);
  assert.deepEqual(JSON.parse(JSON.stringify(sent[0].metadata)), {});
});

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadStore(initial = {}) {
  const values = new Map(Object.entries(initial));
  const window = {
    localStorage: { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) },
    structuredClone,
  };
  window.window = window;
  vm.runInNewContext(fs.readFileSync(path.resolve(__dirname, '..', 'stores.js'), 'utf8'), window);
  return { window, values };
}

test('legacy merchant reply text is removed from returned and backing selection state on load', () => {
  const key = 'guancha.selection-bridge.v1';
  const question = '11111111-1111-4111-8111-111111111111';
  const legacy = JSON.stringify({ unknown_top: 'secret', merchantReplies: { [question]: { id: '22222222-2222-4222-8222-222222222222', status: 'submitted', raw_text: 'private chat', summary: 'private summary', candidate_id: '33333333-3333-4333-8333-333333333333', nested: { token: 'bad' } }, bad: [{ raw_text: 'array secret' }] }, reply: 'draft' });
  const { window, values } = loadStore({ [key]: legacy });
  const loaded = window.GuanchaStores.selectionBridge.load({ merchantReplies: {}, reply: '' });
  assert.deepEqual(JSON.parse(JSON.stringify(loaded.merchantReplies[question])), { id: '22222222-2222-4222-8222-222222222222', status: 'submitted', candidate_id: '33333333-3333-4333-8333-333333333333' });
  assert.equal(loaded.merchantReplies.bad, undefined);
  assert.equal(loaded.unknown_top, undefined);
  assert.equal(loaded.reply, '');
  const backing = values.get(key);
  assert.doesNotMatch(backing, /private chat|private summary|raw_text|summary|draft/);
});

test('future selection saves use a second merchant reply allowlist and reset clears it', () => {
  const { window, values } = loadStore();
  const store = window.GuanchaStores.selectionBridge;
  store.save({ merchantReplies: { '11111111-1111-4111-8111-111111111111': { id: '22222222-2222-4222-8222-222222222222', parse_status: 'answered', raw_text: 'secret', arbitrary: 'no' } }, reply: 'secret draft' });
  assert.doesNotMatch(values.get(store.key), /secret|raw_text|arbitrary/);
  window.GuanchaStores.clearAll();
  assert.equal(values.has(store.key), false);
});

test('corrupt selection JSON is removed immediately and falls back safely', () => {
  const key = 'guancha.selection-bridge.v1';
  const { window, values } = loadStore({ [key]: '{broken' });
  const fallback = { candidates: [], merchantReplies: {}, reply: '' };
  assert.deepEqual(JSON.parse(JSON.stringify(window.GuanchaStores.selectionBridge.load(fallback))), fallback);
  assert.equal(values.has(key), false);
});

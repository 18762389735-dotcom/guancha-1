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
  const legacy = JSON.stringify({ merchantReplies: { q1: { id: 'r1', status: 'saved', raw_text: 'private chat', summary: 'private summary', candidate_id: 'c1' } }, reply: 'draft' });
  const { window, values } = loadStore({ [key]: legacy });
  const loaded = window.GuanchaStores.selectionBridge.load({ merchantReplies: {}, reply: '' });
  assert.deepEqual(JSON.parse(JSON.stringify(loaded.merchantReplies.q1)), { id: 'r1', status: 'saved', candidate_id: 'c1' });
  assert.equal(loaded.reply, '');
  const backing = values.get(key);
  assert.doesNotMatch(backing, /private chat|private summary|raw_text|summary|draft/);
});

test('future selection saves use a second merchant reply allowlist and reset clears it', () => {
  const { window, values } = loadStore();
  const store = window.GuanchaStores.selectionBridge;
  store.save({ merchantReplies: { q1: { id: 'r1', parse_status: 'answered', raw_text: 'secret', arbitrary: 'no' } }, reply: 'secret draft' });
  assert.doesNotMatch(values.get(store.key), /secret|raw_text|arbitrary/);
  window.GuanchaStores.clearAll();
  assert.equal(values.has(store.key), false);
});

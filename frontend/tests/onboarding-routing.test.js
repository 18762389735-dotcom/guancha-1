const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

function storage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { getItem: (key) => values.get(key) || null, setItem: (key, value) => values.set(key, String(value)), values };
}

function routing() {
  const window = {};
  vm.runInNewContext(fs.readFileSync(path.join(root, 'onboarding-routing.js'), 'utf8'), { window });
  return window.GuanchaOnboarding;
}

test('first-time users have no persisted onboarding status and route from Home to O1', () => {
  const api = routing();
  const local = storage();
  assert.equal(api.resolveStatus(local, null), 'not_started');
  assert.equal(local.getItem(api.STATUS_KEY), null);
});

test('existing saved O1/O2 choices migrate to completed', () => {
  const api = routing();
  const local = storage();
  const status = api.resolveStatus(local, { o1: { tea: ['花香茶'] }, o2: { flavors: ['茉莉花'] } });
  assert.equal(status, 'completed');
  assert.equal(local.getItem(api.STATUS_KEY), 'completed');
});

test('completed and skipped users both go to the current need route after Home', () => {
  const api = routing();
  for (const status of ['completed', 'skipped']) {
    const local = storage({ [api.STATUS_KEY]: status });
    assert.equal(api.resolveStatus(local, null), status);
  }
});

test('cold starts always use Home, while a reload restores only a valid active flow', () => {
  const api = routing();
  const active = { screen: 'result', activeSelectionFlow: true, decisionVersionId: 'decision-1', candidates: [{ serverCandidateId: 'candidate-1' }] };
  assert.equal(api.initialScreen({ reload: false, state: active }), 'home');
  assert.equal(api.initialScreen({ reload: true, state: active }), 'result');
  assert.equal(api.initialScreen({ reload: true, state: { screen: 'result', candidates: [] } }), 'home');
  assert.equal(api.initialScreen({ reload: true, state: { ...active, activeSelectionFlow: false } }), 'home');
});

test('navigation timing recognizes reloads without treating ordinary navigation as reload', () => {
  const api = routing();
  assert.equal(api.isReload({ getEntriesByType: () => [{ type: 'reload' }] }), true);
  assert.equal(api.isReload({ getEntriesByType: () => [{ type: 'navigate' }] }), false);
});

test('app wires Home entry, completion, skip and finished-flow cleanup to the routing helper', () => {
  const source = fs.readFileSync(path.resolve(root, '..', 'app.js'), 'utf8');
  assert.match(source, /if \(action === 'start-task'\) return routeAfterHomeStart\(\);/);
  assert.match(source, /GuanchaOnboarding\.markStatus\(localStorage, 'completed'\)/);
  assert.match(source, /GuanchaOnboarding\.markStatus\(localStorage, 'skipped'\)/);
  assert.match(source, /function completeSelectionFlow\(\)/);
});

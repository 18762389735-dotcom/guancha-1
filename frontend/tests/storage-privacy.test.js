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

test('schema v3 serializes only recovery anchors from hostile nested selection trees', () => {
  const key = 'guancha.selection-bridge.v1';
  const questionId = '11111111-1111-4111-8111-111111111111';
  const candidateId = '33333333-3333-4333-8333-333333333333';
  const { window, values } = loadStore();
  window.GuanchaStores.selectionBridge.save({
    sessionId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    candidates: [{ id: 'local-candidate-123-0', serverCandidateId: candidateId, letter: 'A', extractionStatus: 'completed', name: 'secret', fields: { raw_text: 'merchant' }, extraction: { evidence: [{ text: 'reply' }] }, decision: { reasons: ['private'] }, riskFlags: ['private'], images: [{ id: 'local-image-123-abcd', serverImageId: '44444444-4444-4444-8444-444444444444', status: 'completed', previewUrl: 'data:image/png;base64,SECRET', file: { name: 'private.png', type: 'image/png' } }] }],
    followupQuestions: [{ reply: { text: 'secret' } }], selectionAnswer: { summary: 'secret' }, lastDecisionDelta: { added_facts: ['secret'] }, jobIds: { arbitrary: 'secret' }, need: { taste: 'user free text' },
    merchantReplyIds: { [questionId]: '22222222-2222-4222-8222-222222222222' },
    merchantReplies: { [questionId]: { id: '22222222-2222-4222-8222-222222222222', candidate_id: candidateId, status: 'submitted', raw_text: 'secret' } },
    unexpected: [{ summary: 'secret' }],
  });
  const persisted = JSON.parse(values.get(key));
  assert.equal(persisted.schemaVersion, 3);
  assert.equal(persisted.candidates.length, 1);
  assert.equal(persisted.candidates[0].serverCandidateId, candidateId);
  assert.equal(persisted.merchantReplyIds[questionId], '22222222-2222-4222-8222-222222222222');
  assert.doesNotMatch(values.get(key), /secret|raw_text|previewUrl|data:image|followupQuestions|selectionAnswer|lastDecisionDelta|jobIds|need|unexpected/);
});

test('schema v3 rejects arrays invalid UUIDs open statuses and excessive anchors then rewrites backing', () => {
  const key = 'guancha.selection-bridge.v1';
  const candidate = index => ({ serverCandidateId: `${String(index).padStart(8, '0')}-1111-4111-8111-111111111111`, letter: String.fromCharCode(65 + index), extractionStatus: index ? 'made-up' : 'queued', images: Array.from({ length: 3 }, (_, image) => ({ serverImageId: `${String(image + 20).padStart(8, '0')}-2222-4222-8222-222222222222`, status: 'queued' })) });
  const raw = JSON.stringify({ schemaVersion: 2, sessionId: 'not-a-uuid', candidates: Array.from({ length: 7 }, (_, index) => candidate(index)), merchantReplies: [], decisionVersionId: true, decisionStatus: 'private' });
  const { window, values } = loadStore({ [key]: raw });
  const loaded = window.GuanchaStores.selectionBridge.load({ candidates: [], merchantReplies: {} });
  assert.equal(loaded.schemaVersion, 3);
  assert.equal(loaded.sessionId, null);
  assert.equal(loaded.candidates.length, 5);
  assert.equal(loaded.candidates[0].images.length, 2);
  assert.equal(loaded.candidates[1].extractionStatus, undefined);
  assert.equal(loaded.decisionStatus, undefined);
  assert.equal(JSON.parse(values.get(key)).schemaVersion, 3);
});

test('ui session is a closed anchor store and cannot retain reply text', () => {
  const { window, values } = loadStore();
  window.GuanchaStores.uiSession.save({ screen: 'result', activeCandidateId: '33333333-3333-4333-8333-333333333333', o1: { tea: ['绿茶', 'private reply'] }, o2: { flavors: ['兰花', 'merchant raw text'], sweetness: 75 }, overlay: { raw_text: 'secret' }, brew: { impression: 'secret' } });
  const persisted = values.get(window.GuanchaStores.uiSession.key);
  assert.match(persisted, /33333333-3333-4333-8333-333333333333/);
  assert.match(persisted, /绿茶|兰花/);
  assert.doesNotMatch(persisted, /private|merchant|raw_text|secret|overlay|brew/);
});

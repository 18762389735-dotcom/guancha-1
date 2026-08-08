const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

function browser() {
  const values = new Map();
  const window = {
    crypto: require('node:crypto').webcrypto,
    localStorage: { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) },
    FormData: global.FormData,
    setTimeout,
    clearTimeout,
    document: { hidden: false },
  };
  window.window = window;
  return window;
}

function load(window, filename) {
  vm.runInNewContext(fs.readFileSync(filename, 'utf8'), window, { filename });
}

test('real-flow client uses only backend contracts for session, candidate, image, job and decision', async () => {
  const window = browser();
  load(window, path.join(root, 'api-client.js'));
  const calls = [];
  const client = window.GuanchaApi.createApiClient({
    clientId: 'd3ac0eb0-6436-4d48-a3cc-6f0d9f171a0f',
    transport: async item => {
      calls.push(item);
      return { ok: true, body: { id: 'server-id', image: { id: 'image-id' }, extraction_job: { id: 'job-id', status: 'queued' } } };
    },
  });
  const key = '4d482cc6-3546-4859-9fbf-01063e12d234';
  await client.createSelectionSession({ taste_text: 'floral' }, key);
  await client.createCandidate('session-id', { display_label: 'A', display_name: 'candidate' }, key);
  await client.uploadCandidateImage('candidate-id', new Blob(['image'], { type: 'image/png' }), key);
  await client.getJob('job-id');
  await client.getCurrentExtraction('candidate-id');
  await client.analyzeSelectionSession('session-id', key);
  await client.getCurrentDecision('session-id');
  assert.deepEqual(calls.map(call => call.path), [
    '/api/v1/selection-sessions',
    '/api/v1/selection-sessions/session-id/candidates',
    '/api/v1/candidates/candidate-id/images',
    '/api/v1/jobs/job-id',
    '/api/v1/candidates/candidate-id/current-extraction',
    '/api/v1/selection-sessions/session-id/analyze',
    '/api/v1/selection-sessions/session-id/current-decision',
  ]);
  assert.equal(calls[2].payload instanceof window.FormData, true);
  assert.equal(calls[0].headers['X-Client-Id'], 'd3ac0eb0-6436-4d48-a3cc-6f0d9f171a0f');
  assert.equal(calls[5].headers['Idempotency-Key'], key);
});

test('job poller ignores an obsolete job version instead of reporting a late result', async () => {
  const window = browser();
  window.GuanchaPublicConfig = { get: () => ({ pollInitialWindowMs: 1, pollInitialMs: 1, pollAfterInitialMs: 1, pollBackgroundMs: 1 }) };
  load(window, path.join(root, 'job-poller.js'));
  let updates = 0;
  window.GuanchaJobPoller.start({
    jobId: 'old-job', resourceId: 'candidate-id', versionId: 'old-job',
    fetchStatus: async () => ({ status: 'completed', extraction_version_id: 'old-version' }),
    getCurrentVersion: () => 'new-job',
    onUpdate: () => { updates += 1; },
  });
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(updates, 0);
  assert.equal(window.GuanchaJobPoller.activeCount(), 0);
});

test('API client exposes backend and network failures as recoverable contract errors', async () => {
  const window = browser();
  load(window, path.join(root, 'api-client.js'));
  const forbidden = window.GuanchaApi.createApiClient({
    clientId: 'd3ac0eb0-6436-4d48-a3cc-6f0d9f171a0f',
    transport: async () => ({ ok: false, body: { error: { code: 'resource_not_owned', message: 'not yours' } } }),
  });
  await assert.rejects(() => forbidden.getJob('job-id'), error => error.code === 'resource_not_owned');
  const unconfigured = window.GuanchaApi.createApiClient({ clientId: 'd3ac0eb0-6436-4d48-a3cc-6f0d9f171a0f' });
  await assert.rejects(() => unconfigured.getJob('job-id'), error => error.code === 'api_not_configured');
});

test('real-flow client preserves server order for questions, rejudgement and post-purchase bridge calls', async () => {
  const window = browser();
  load(window, path.join(root, 'api-client.js'));
  const calls = [];
  const client = window.GuanchaApi.createApiClient({
    clientId: 'd3ac0eb0-6436-4d48-a3cc-6f0d9f171a0f',
    transport: async item => { calls.push(item); return { ok: true, body: [] }; },
  });
  const key = '4d482cc6-3546-4859-9fbf-01063e12d234';
  await client.getDecisionQuestions('decision-id');
  await client.generateDecisionQuestions('decision-id', key);
  await client.createMerchantReply('session-id', { decision_version_id: 'decision-id', followup_question_id: 'question-id', raw_text: 'merchant reply' }, key);
  await client.rejudgeMerchantReply('session-id', 'reply-id', key);
  await client.getDecisionDelta('delta-id');
  await client.analyzeBrewFeedback({ brew_session_id: 'local-brew-id' }, key);
  assert.deepEqual(calls.map(call => call.path), [
    '/api/v1/decision-versions/decision-id/questions',
    '/api/v1/decision-versions/decision-id/questions',
    '/api/v1/selection-sessions/session-id/merchant-replies',
    '/api/v1/selection-sessions/session-id/rejudge',
    '/api/v1/decision-deltas/delta-id',
    '/api/v1/brew-feedback/analyze',
  ]);
  assert.equal(calls[1].headers['Idempotency-Key'], key);
  assert.equal(calls[4].method, 'GET');
});

test('production frontend contains no provider key or evaluation fixture leakage', () => {
  const sources = [
    path.resolve(root, '..', 'app.js'),
    path.join(root, 'api-client.js'),
    path.join(root, 'adapters.js'),
    path.join(root, 'job-poller.js'),
  ].map(filename => fs.readFileSync(filename, 'utf8')).join('\n');
  assert.doesNotMatch(sources, /(?:MIMO|OPENAI)_API_KEY|VITE_MIMO_API_KEY/i);
  assert.doesNotMatch(sources, /(?:EVAL-|HOLDOUT-|PERSONA-|META-|golden|corrected_value|expected_bucket|expected_rank|blind-holdout|decision-eval)/i);
});

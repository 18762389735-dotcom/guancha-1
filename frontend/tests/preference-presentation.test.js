const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function adapters() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname, '..', 'adapters.js'), 'utf8'), context);
  return context.window.GuanchaAdapters;
}

test('O1/O2 only form bounded low-confidence presentation references', () => {
  const result = adapters().buildPreferenceReference({
    o1: { coffee: ['浅烘手冲', '冷萃', '深烘咖啡'] },
    o2: { flavors: ['兰花', '柑橘', '焦糖'] },
  });
  assert.equal(result.length, 2);
  assert.match(result[0].text, /浅烘手冲、冷萃/);
  assert.match(result[1].text, /兰花、柑橘/);
});

test('current need is always first and references cannot replace it', () => {
  const presentation = adapters().buildPersonalFitPresentation({
    need: { taste: '清爽低火味', purpose: '送礼' },
    sensoryInterpretations: [{ text: '受控线索' }],
    preferenceReference: [{ text: '你关注焦糖。' }],
  });
  assert.match(presentation.lines[0], /清爽低火味、送礼/);
  assert.match(presentation.lines.at(-1), /不会覆盖你这次的需求/);
});

test('missing sensory evidence stays cautious', () => {
  const presentation = adapters().buildPersonalFitPresentation({ need: { taste: '清爽花香' } });
  assert.match(presentation.lines[1], /还不足以判断/);
});

test('controlled sensory evidence can explain a different fit without ranking', () => {
  const presentation = adapters().buildPersonalFitPresentation({
    need: { taste: '清爽花香' },
    sensoryInterpretations: [{ text: '如果商品页的浓香型描述准确，风格通常更偏熟香、醇厚方向。' }],
  });
  assert.match(presentation.lines[1], /更偏另一种风格/);
  assert.doesNotMatch(presentation.lines[1], /首选|排名|一定/);
});

test('fit presentation uses explicit sensory and legacy need signals together', () => {
  const api = adapters();
  assert.equal(api.sensoryNeedMatch({ score_components: { explicit_sensory_need_match: 2, need_match: -1 } }), 1);
  assert.equal(api.sensoryNeedMatch({ score_components: { explicit_sensory_need_match: -1, need_match: 1 } }), 0);
  assert.equal(api.sensoryNeedMatch({}), 0);
});

test('changing Need invalidates every derived decision artifact but preserves extraction', () => {
  const api = adapters();
  const invalidated = api.invalidateDecisionState({
    decisionVersionId: 'v2', decisionJobId: 'job', selectionAnswer: { headline: 'old' },
    followupQuestions: [{ id: 'q1' }], merchantReplyIds: { q1: 'r1' },
    merchantReplies: { q1: { id: 'r1' } }, rejudgeJobId: 'rejudge', lastDecisionDelta: { id: 'delta' },
    candidates: [{ id: 'a', extraction: { id: 'extract-a' }, decision: { overall_order: 1 }, riskFlags: ['old-risk'] }],
  });
  assert.equal(invalidated.decisionVersionId, null);
  assert.equal(invalidated.selectionAnswer, null);
  assert.equal(invalidated.followupQuestions.length, 0);
  assert.equal(Object.keys(invalidated.merchantReplyIds).length, 0);
  assert.equal(invalidated.lastDecisionDelta, null);
  assert.equal(invalidated.candidates[0].extraction.id, 'extract-a');
  assert.equal(invalidated.candidates[0].decision, null);
});

test('server snapshot recovers active analysis and completed rejudge screens', () => {
  const api = adapters();
  assert.equal(api.activeRecoveryScreen({
    candidates: [{ images: [{ current_job_status: 'processing' }] }], current_decision_id: null,
  }), 'analysis');
  assert.equal(api.activeRecoveryScreen({
    candidates: [], current_decision_id: 'v2', decision_delta: { id: 'delta-1' },
  }), 'rejudge');
  assert.equal(api.activeRecoveryScreen({ candidates: [], current_decision_id: 'v1' }), 'result');
  assert.equal(api.activeRecoveryScreen({ candidates: [] }), 'candidates');
});

test('remote Need transition requires configuration and a successful PATCH', async () => {
  const api = adapters();
  const original = {
    sessionId: 'session-1', need: { taste: 'old' }, decisionVersionId: 'v1',
    candidates: [{ id: 'a', extraction: { id: 'e1' }, decision: { overall_order: 1 } }],
  };
  let calls = 0;
  await assert.rejects(() => api.prepareNeedUpdate({
    state: original, nextNeed: { taste: 'new' }, isApiConfigured: false,
    updateRemote: async () => { calls += 1; },
  }), error => error.code === 'api_not_configured');
  await assert.rejects(() => api.prepareNeedUpdate({
    state: original, nextNeed: { taste: 'new' }, isApiConfigured: true,
    updateRemote: async () => { calls += 1; throw Object.assign(new Error('offline'), { code: 'network_error' }); },
  }), error => error.code === 'network_error');
  assert.equal(calls, 1);
  assert.equal(original.need.taste, 'old');
  assert.equal(original.decisionVersionId, 'v1');
});

test('local first Need can save without an API session', async () => {
  const api = adapters();
  const transition = await api.prepareNeedUpdate({
    state: { sessionId: null, need: { taste: 'old' }, candidates: [] },
    nextNeed: { taste: 'new' }, isApiConfigured: false,
    updateRemote: async () => { throw new Error('must not call'); },
  });
  assert.equal(transition.need.taste, 'new');
  assert.equal(transition.decisionVersionId, null);
});

test('current session Decision Job controls recovery without local job state', () => {
  const api = adapters();
  assert.equal(api.activeRecoveryScreen({ candidates: [], session_decision_job: { status: 'queued' } }), 'analysis');
  assert.equal(api.activeRecoveryScreen({ candidates: [], session_decision_job: { status: 'processing' } }), 'analysis');
  assert.equal(api.activeRecoveryScreen({ candidates: [], current_decision_id: 'v1', session_decision_job: { status: 'completed' } }), 'result');
  assert.equal(api.activeRecoveryScreen({ candidates: [], session_decision_job: { status: 'failed' } }), 'candidates');
  assert.equal(api.activeRecoveryScreen({ candidates: [], session_decision_job: { status: 'stale' } }), 'candidates');
});

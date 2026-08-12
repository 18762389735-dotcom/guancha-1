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

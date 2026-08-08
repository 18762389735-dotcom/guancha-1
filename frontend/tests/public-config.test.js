const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.resolve(__dirname, '..', 'public-config.js'), 'utf8');

function loadConfig() {
  const window = {};
  window.window = window;
  vm.runInNewContext(source, window, { filename: 'public-config.js' });
  return window.GuanchaPublicConfig;
}

test('public product bounds retain five candidates and two screenshots', () => {
  const config = loadConfig();
  assert.equal(config.get().maxCandidates, 5);
  assert.equal(config.get().maxImagesPerCandidate, 2);

  const applied = config.apply({
    candidate_limit: 5,
    candidate_image_limit: 2,
    // Older API responses may still carry the retired 1/1 rollout flags.
    phase2_candidate_limit: 1,
    phase2_candidate_image_limit: 1,
  });
  assert.equal(applied.maxCandidates, 5);
  assert.equal(applied.maxImagesPerCandidate, 2);
});

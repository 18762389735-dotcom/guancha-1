const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const { File: NodeFile } = require('node:buffer');

const root = path.resolve(__dirname, '..');
const FileCtor = global.File || NodeFile;

function loadPreparation(options = {}) {
  const window = {
    File: FileCtor,
    Blob,
    URL: {
      createObjectURL: () => 'blob:test-image',
      revokeObjectURL: () => {},
    },
    Image: options.Image || class {
      set src(value) {
        this.naturalWidth = 1200;
        this.naturalHeight = 900;
        queueMicrotask(() => this.onload && this.onload({ target: this, value }));
      }
    },
    document: {
      createElement: () => ({
        width: 0,
        height: 0,
        getContext: () => ({ drawImage: () => {} }),
        toBlob: callback => callback(new Blob([new Uint8Array(80)], { type: 'image/jpeg' })),
      }),
    },
  };
  window.window = window;
  vm.runInNewContext(fs.readFileSync(path.join(root, 'image-preparation.js'), 'utf8'), window, { filename: 'image-preparation.js' });
  return window.GuanchaImagePreparation;
}

const limits = { allowedImageMimeTypes: ['image/jpeg', 'image/png'], maxImageBytes: 100 };

test('invalid MIME never yields a staged image result', async () => {
  const preparation = loadPreparation();
  const result = await preparation.prepareFiles([new FileCtor(['not an image'], 'photo.gif', { type: 'image/gif' })], { ...limits, remaining: 1 });
  assert.equal(result.ok, false);
  assert.equal(result.code, 'invalid_image_type');
  assert.equal(result.files.length, 0);
});

test('JPEG and PNG, including an iOS blank MIME with a known extension, stage successfully', async () => {
  const preparation = loadPreparation();
  const jpeg = await preparation.prepareFiles([new FileCtor(['jpeg'], 'screenshot.jpg', { type: 'image/jpeg' })], { ...limits, remaining: 1 });
  const png = await preparation.prepareFiles([new FileCtor(['png'], 'screenshot.PNG', { type: '' })], { ...limits, remaining: 1 });
  assert.equal(jpeg.ok, true);
  assert.equal(png.ok, true);
  assert.equal(png.files[0].type, 'image/png');
});

test('a decodable oversized image is compressed locally before staging', async () => {
  const preparation = loadPreparation();
  const file = new FileCtor([new Uint8Array(200)], 'large.jpg', { type: 'image/jpeg' });
  const result = await preparation.prepareFiles([file], { ...limits, remaining: 1 });
  assert.equal(result.ok, true);
  assert.equal(result.converted, true);
  assert.equal(result.files[0].type, 'image/jpeg');
  assert.ok(result.files[0].size <= limits.maxImageBytes);
});

test('an undecodable HEIC returns an explicit failure instead of a false success', async () => {
  class BrokenImage {
    set src(value) { queueMicrotask(() => this.onerror && this.onerror({ target: this, value })); }
  }
  const preparation = loadPreparation({ Image: BrokenImage });
  const result = await preparation.prepareFiles([new FileCtor(['heic'], 'iphone.heic', { type: 'image/heic' })], { ...limits, remaining: 1 });
  assert.equal(result.ok, false);
  assert.equal(result.code, 'heif_not_decodable');
});

test('candidate-input success toast is gated on an explicit addCandidate result', () => {
  const app = fs.readFileSync(path.resolve(root, '..', 'app.js'), 'utf8');
  const page = fs.readFileSync(path.resolve(root, '..', 'index.html'), 'utf8');
  assert.match(app, /return \{ ok: true, candidate, converted: prepared\.converted \}/);
  assert.match(app, /const added = await addCandidate\(files\);\s*if \(!added\.ok\) return showToast\(added\.message\);\s*setScreen\('candidates'\);\s*showToast\('候选图片已暂存，尚未调用识别'\);/);
  assert.match(page, /accept="image\/jpeg,image\/png,image\/heic,image\/heif,.heic,.heif"/);
});

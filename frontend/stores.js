(function (global) {
  'use strict';

  function safeRead(key, fallback) {
    try { return JSON.parse(global.localStorage.getItem(key)) || fallback; } catch { return fallback; }
  }
  function safeWrite(key, value) {
    try { global.localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
  }
  function clone(value) { return global.structuredClone ? global.structuredClone(value) : JSON.parse(JSON.stringify(value)); }
  function createStore(key, version, migrate) {
    return {
      key,
      load(fallback) {
        const raw = safeRead(key, null);
        if (!raw || typeof raw !== 'object') return clone(fallback);
        try { return migrate(raw, fallback); } catch { return clone(fallback); }
      },
      save(value) { return safeWrite(key, { schemaVersion: version, ...value }); },
    };
  }
  function withVersion(version) {
    return (raw, fallback) => {
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return clone(fallback);
      const payload = { ...raw };
      delete payload.schemaVersion;
      return { ...clone(fallback), ...payload, schemaVersion: version };
    };
  }
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const replyStatus = new Set(['submitted', 'parsed', 'failed']);
  const processingStatus = new Set(['queued', 'processing', 'completed', 'failed']);
  const parseStatus = new Set(['answered', 'partially-answered', 'evasive', 'not-answered', 'conflicting']);
  const extractionStatus = new Set(['idle', 'empty', 'uploading', 'queued', 'processing', 'completed', 'failed', 'stale']);
  const decisionStatus = new Set(['not_requested', 'loading', 'ready', 'failed']);
  const questionStatus = new Set(['idle', 'loading', 'completed', 'ready', 'rejudging', 'not-needed', 'failed']);
  const deltaStatus = new Set(['idle', 'loading', 'ready', 'failed']);
  const screens = new Set(['home','candidates','o1','o2','analysis','result','rejudge','ownership','warehouse','warehouse-detail','warehouse-add','journal','journal-day','choose-tea','prepare','timer','infusion-done','feedback','advanced','brew-result','record-detail','settings']);
  const localCandidatePattern = /^local-candidate-\d{1,16}(?:-\d{1,2})?$/;
  const localImagePattern = /^(?:local-image-\d{1,16}-[0-9a-f]{1,20}|server-[0-9a-f-]{36})$/i;
  const extractionErrors = new Set(['network_error','result_unavailable','ai_timeout','ai_provider_error','ai_schema_invalid','worker_interrupted','temporary_image_cleanup_failed','unsafe_or_corrupt_image']);
  const preferenceValues = new Set(['绿茶','花香茶','乌龙茶','红茶','焙火茶','陈香茶','奶茶 / 果茶','美式 / 黑咖啡','拿铁','冷萃','浅烘手冲','深烘咖啡','纯牛奶','酸奶','豆浆','燕麦奶','椰奶','柑橘类果汁','苹果 / 梨汁','桃子 / 荔枝饮品','葡萄 / 莓果汁','热带水果汁','蔬菜汁','椰子水','茉莉花','兰花','桂花','玫瑰','水蜜桃','荔枝','梨','柑橘','桂圆','红枣','青梅','葡萄干','嫩叶','青草','竹叶','青豆','板栗','炒黄豆','烤花生','烤面包','蜂蜜','焦糖','糯米','陈皮']);
  function isIsoTimestamp(value) { return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value)); }
  function sanitizedReply(reply) {
    if (!reply || typeof reply !== 'object' || Array.isArray(reply)) return null;
    const cleaned = {};
    for (const field of ['id', 'selection_session_id', 'decision_version_id', 'followup_question_id', 'candidate_id']) {
      if (typeof reply[field] === 'string' && uuidPattern.test(reply[field])) cleaned[field] = reply[field];
    }
    if (replyStatus.has(reply.status)) cleaned.status = reply.status;
    if (processingStatus.has(reply.processing_status)) cleaned.processing_status = reply.processing_status;
    if (parseStatus.has(reply.parse_status)) cleaned.parse_status = reply.parse_status;
    for (const field of ['created_at', 'updated_at']) if (isIsoTimestamp(reply[field])) cleaned[field] = reply[field];
    return Object.keys(cleaned).length ? cleaned : null;
  }
  function persistedMerchantReplies(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).flatMap(([questionId, reply]) => {
      const cleaned = uuidPattern.test(questionId) ? sanitizedReply(reply) : null;
      return cleaned ? [[questionId, cleaned]] : [];
    }));
  }
  function persistedMerchantReplyIds(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter(([questionId, replyId]) => uuidPattern.test(questionId) && typeof replyId === 'string' && uuidPattern.test(replyId)));
  }
  function safeUuid(value) { return typeof value === 'string' && uuidPattern.test(value) ? value : null; }
  function safeLocalId(value, pattern) { return typeof value === 'string' && pattern.test(value) ? value : null; }
  function imageAnchor(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const id = safeLocalId(value.id, localImagePattern);
    const serverImageId = safeUuid(value.serverImageId);
    if (!id && !serverImageId) return null;
    const result = {};
    if (id) result.id = id;
    if (serverImageId) result.serverImageId = serverImageId;
    if (extractionStatus.has(value.status)) result.status = value.status;
    if (typeof value.localOnly === 'boolean') result.localOnly = value.localOnly;
    return result;
  }
  function candidateAnchor(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const id = safeLocalId(value.id, localCandidatePattern);
    const serverCandidateId = safeUuid(value.serverCandidateId);
    if (!id && !serverCandidateId) return null;
    const result = {};
    if (id) result.id = id;
    if (serverCandidateId) result.serverCandidateId = serverCandidateId;
    if (/^[A-E]$/.test(value.letter)) result.letter = value.letter;
    if (extractionStatus.has(value.extractionStatus)) result.extractionStatus = value.extractionStatus;
    if (extractionErrors.has(value.jobError)) result.jobError = value.jobError;
    for (const field of ['jobId', 'extractionVersionId']) {
      const valid = safeUuid(value[field]);
      if (valid) result[field] = valid;
    }
    result.images = (Array.isArray(value.images) ? value.images : []).slice(0, 2).map(imageAnchor).filter(Boolean);
    return result;
  }
  function selectionBridgeStore() {
    const key = 'guancha.selection-bridge.v1';
    const version = 3;
    function sanitize(value) {
      const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
      const payload = {
        sessionId: safeUuid(input.sessionId),
        candidates: (Array.isArray(input.candidates) ? input.candidates : []).slice(0, 5).map(candidateAnchor).filter(Boolean),
        merchantReplyIds: persistedMerchantReplyIds(input.merchantReplyIds),
        merchantReplies: persistedMerchantReplies(input.merchantReplies),
      };
      for (const field of ['decisionVersionId', 'decisionJobId', 'questionDecisionVersionId', 'rejudgeJobId']) {
        payload[field] = safeUuid(input[field]);
      }
      if (decisionStatus.has(input.decisionStatus)) payload.decisionStatus = input.decisionStatus;
      if (questionStatus.has(input.questionStatus)) payload.questionStatus = input.questionStatus;
      if (deltaStatus.has(input.deltaStatus)) payload.deltaStatus = input.deltaStatus;
      return { schemaVersion: version, ...payload };
    }
    return {
      key,
      load(fallback) {
        let raw;
        try { raw = JSON.parse(global.localStorage.getItem(key)); }
        catch { global.localStorage.removeItem(key); return clone(fallback); }
        if (!raw || typeof raw !== 'object' || Array.isArray(raw)) { global.localStorage.removeItem(key); return clone(fallback); }
        const cleaned = sanitize(raw);
        // Reading legacy state is itself a privacy migration: the backing
        // localStorage value must no longer retain merchant free text.
        safeWrite(key, cleaned);
        return { ...clone(fallback), ...cleaned };
      },
      save(value) { return safeWrite(key, sanitize(value)); },
    };
  }
  function uiSessionStore() {
    const key = 'guancha.ui-session.v1';
    function sanitize(value) {
      const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
      const result = { schemaVersion: 2 };
      if (screens.has(input.screen)) result.screen = input.screen;
      if (typeof input.openDrink === 'string' && ['tea','coffee','milk','juice',''].includes(input.openDrink)) result.openDrink = input.openDrink;
      if (typeof input.activeSelectionFlow === 'boolean') result.activeSelectionFlow = input.activeSelectionFlow;
      if (['onboarding','edit'].includes(input.preferenceFlow)) result.preferenceFlow = input.preferenceFlow;
      if (['bought','owned'].includes(input.ownershipChoice)) result.ownershipChoice = input.ownershipChoice;
      const activeCandidateId = safeUuid(input.activeCandidateId) || safeLocalId(input.activeCandidateId, localCandidatePattern);
      if (activeCandidateId) result.activeCandidateId = activeCandidateId;
      const o1 = input.o1 && typeof input.o1 === 'object' && !Array.isArray(input.o1) ? input.o1 : {};
      result.o1 = Object.fromEntries(['tea','coffee','milk','juice'].map(keyName => [keyName, (Array.isArray(o1[keyName]) ? o1[keyName] : []).filter(item => preferenceValues.has(item)).slice(0, 8)]));
      const o2 = input.o2 && typeof input.o2 === 'object' && !Array.isArray(input.o2) ? input.o2 : {};
      result.o2 = { flavors: (Array.isArray(o2.flavors) ? o2.flavors : []).filter(item => preferenceValues.has(item)).slice(0, 5) };
      if (Number.isInteger(o2.sweetness) && o2.sweetness >= 0 && o2.sweetness <= 100) result.o2.sweetness = o2.sweetness;
      return result;
    }
    return {
      key,
      load(fallback) {
        const raw = safeRead(key, null);
        if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return clone(fallback);
        const cleaned = sanitize(raw); safeWrite(key, cleaned);
        return { ...clone(fallback), ...cleaned };
      },
      save(value) { return safeWrite(key, sanitize(value)); },
    };
  }
  const pendingImageDatabase = 'guancha.pending-images.v1';
  const pendingImageStore = 'images';
  function withPendingImageStore(mode, callback) {
    if (!global.indexedDB) return Promise.resolve(null);
    return new Promise((resolve) => {
      const request = global.indexedDB.open(pendingImageDatabase, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(pendingImageStore)) request.result.createObjectStore(pendingImageStore);
      };
      request.onerror = () => resolve(null);
      request.onsuccess = () => {
        const database = request.result;
        const transaction = database.transaction(pendingImageStore, mode);
        const store = transaction.objectStore(pendingImageStore);
        callback(store, resolve);
        transaction.oncomplete = () => database.close();
        transaction.onerror = () => { database.close(); resolve(null); };
      };
    });
  }
  const pendingImages = {
    save(id, file) { return withPendingImageStore('readwrite', (store, resolve) => { const request = store.put(file, id); request.onsuccess = () => resolve(true); request.onerror = () => resolve(false); }); },
    load(id) { return withPendingImageStore('readonly', (store, resolve) => { const request = store.get(id); request.onsuccess = () => resolve(request.result || null); request.onerror = () => resolve(null); }); },
    remove(id) { return withPendingImageStore('readwrite', (store, resolve) => { const request = store.delete(id); request.onsuccess = () => resolve(true); request.onerror = () => resolve(false); }); },
    clear() { return withPendingImageStore('readwrite', (store, resolve) => { const request = store.clear(); request.onsuccess = () => resolve(true); request.onerror = () => resolve(false); }); },
  };
  const stores = {
    uiSession: uiSessionStore(),
    selectionBridge: selectionBridgeStore(),
    localPostPurchase: createStore('guancha.local-post-purchase.v1', 1, withVersion(1)),
    preferenceEvidence: createStore('guancha.preference-evidence.v1', 1, (raw, fallback) => {
      if (!raw || typeof raw !== 'object' || !Array.isArray(raw.items)) return clone(fallback);
      const cutoff = Date.now() - 90 * 24 * 60 * 60 * 1000;
      const seen = new Set();
      const items = raw.items.filter((item) => {
        if (!item || typeof item !== 'object' || item.confidence !== 'low' || typeof item.source_brew_session_id !== 'string' || seen.has(item.source_brew_session_id)) return false;
        const created = Date.parse(item.created_at || '');
        if (Number.isFinite(created) && created < cutoff) return false;
        seen.add(item.source_brew_session_id);
        return true;
      }).slice(-12);
      return { items, schemaVersion: 1 };
    }),
    pendingImages,
    legacy: { load: () => safeRead('guancha-prototype-v2', null), clear: () => global.localStorage.removeItem('guancha-prototype-v2') },
  };
  stores.clearAll = () => {
    [stores.uiSession.key, stores.selectionBridge.key, stores.localPostPurchase.key, stores.preferenceEvidence.key, 'guancha-prototype-v2'].forEach((key) => global.localStorage.removeItem(key));
    pendingImages.clear();
  };
  global.GuanchaStores = stores;
}(window));

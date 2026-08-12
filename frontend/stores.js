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
  const merchantReplyPersistedFields = Object.freeze([
    'id', 'selection_session_id', 'decision_version_id', 'followup_question_id',
    'candidate_id', 'status', 'processing_status', 'parse_status', 'created_at', 'updated_at',
  ]);
  function persistedMerchantReplies(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).map(([questionId, reply]) => {
      if (!reply || typeof reply !== 'object' || Array.isArray(reply)) return [questionId, {}];
      return [questionId, Object.fromEntries(
        merchantReplyPersistedFields
          .filter((field) => reply[field] !== undefined && reply[field] !== null)
          .map((field) => [field, reply[field]])
      )];
    }));
  }
  function selectionBridgeStore() {
    const key = 'guancha.selection-bridge.v1';
    const version = 2;
    function sanitize(value) {
      const payload = value && typeof value === 'object' && !Array.isArray(value) ? { ...value } : {};
      delete payload.schemaVersion;
      payload.reply = '';
      payload.merchantReplies = persistedMerchantReplies(payload.merchantReplies);
      return { schemaVersion: version, ...payload };
    }
    return {
      key,
      load(fallback) {
        const raw = safeRead(key, null);
        if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return clone(fallback);
        const cleaned = sanitize(raw);
        // Reading legacy state is itself a privacy migration: the backing
        // localStorage value must no longer retain merchant free text.
        safeWrite(key, cleaned);
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
    uiSession: createStore('guancha.ui-session.v1', 1, withVersion(1)),
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

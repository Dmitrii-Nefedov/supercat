// Service worker unit tests for sw.js
// Run: node tests/test_sw.js

const assert = {
  strictEqual(a, b, msg) {
    if (a !== b) throw new Error(`FAIL: ${msg || ''} — expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
  },
  ok(val, msg) {
    if (!val) throw new Error(`FAIL: ${msg || ''} — expected truthy`);
  },
};

const fs = require('fs');
const path = require('path');

// ---------- Mock ServiceWorker environment ----------

class MockRequest {
  constructor(url, opts = {}) {
    this.url = url;
    this.mode = opts.mode || 'navigate';
  }
}

class MockResponse {
  constructor(body, opts = {}) {
    this.body = body;
    this.ok = opts.ok !== undefined ? opts.ok : true;
    this.status = opts.status || 200;
    this.headers = new Map();
    this.cloneCalled = false;
  }
  clone() {
    this.cloneCalled = true;
    return new MockResponse(this.body, { ok: this.ok, status: this.status });
  }
}

let cacheAddAllArgs = null;
let cachePutArgs = null;
let cacheMatchResult = null;
let fetchResponse = null;
let fetchError = null;
let respondWithArgs = null;
let waitUntilArgs = null;
let skipWaitingCalled = false;
let clientsClaimCalled = false;
let deletedCacheKeys = [];

const mockCacheInstance = {
  addAll(urls) {
    cacheAddAllArgs = urls;
    return Promise.resolve();
  },
  put(request, response) {
    cachePutArgs = { request: request.url, response };
    return Promise.resolve();
  },
  match(url) {
    return Promise.resolve(cacheMatchResult);
  },
};

const mockCacheStorage = {
  open(name) {
    return Promise.resolve(mockCacheInstance);
  },
  keys() {
    return Promise.resolve(['supercat-weather-v2', 'old-cache-v1']);
  },
  delete(key) {
    deletedCacheKeys.push(key);
    return Promise.resolve(true);
  },
};

function resetMocks() {
  cacheAddAllArgs = null;
  cachePutArgs = null;
  cacheMatchResult = null;
  fetchResponse = new MockResponse('ok', { ok: true, status: 200 });
  fetchError = null;
  respondWithArgs = null;
  waitUntilArgs = null;
  skipWaitingCalled = false;
  clientsClaimCalled = false;
  deletedCacheKeys = [];
}

const mockSelf = {
  addEventListener(type, handler) {
    mockSelf._listeners = mockSelf._listeners || {};
    mockSelf._listeners[type] = mockSelf._listeners[type] || [];
    mockSelf._listeners[type].push(handler);
  },
  skipWaiting() {
    skipWaitingCalled = true;
  },
  clients: {
    claim() {
      clientsClaimCalled = true;
    },
  },
  location: {
    origin: 'https://example.com',
  },
  _listeners: {},
};

const mockFetch = (url) => {
  if (fetchError) return Promise.reject(fetchError);
  return Promise.resolve(fetchResponse);
};

// ---------- Load and evaluate sw.js ----------

function loadSW() {
  resetMocks();
  mockSelf._listeners = {};
  const code = fs.readFileSync(path.join(__dirname, '..', 'sw.js'), 'utf8');

  const vm = require('vm');
  const context = {
    self: mockSelf,
    caches: mockCacheStorage,
    fetch: mockFetch,
    Request: MockRequest,
    Response: MockResponse,
    Promise: Promise,
    console: console,
  };
  vm.createContext(context);
  vm.runInContext(code, context, { filename: 'sw.js' });
  return context;
}

// ---------- Test Runner ----------

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
  } catch (e) {
    failed++;
    console.error(`  ✗ ${name}: ${e.message}`);
  }
}

// ---------- Tests ----------

console.log('\n  sw.js — Install Event');
test('install event listener is registered', () => {
  const ctx = loadSW();
  ctx.self._listeners = ctx.self._listeners || {};
  assert.ok(ctx.self._listeners.install, 'install listener missing');
  assert.ok(ctx.self._listeners.activate, 'activate listener missing');
  assert.ok(ctx.self._listeners.fetch, 'fetch listener missing');
});

test('install caches static assets', async () => {
  const ctx = loadSW();
  const installHandler = ctx.self._listeners.install[0];

  const event = {
    waitUntil(fn) {
      waitUntilArgs = fn;
    },
  };

  installHandler(event);
  await waitUntilArgs;

  assert.ok(skipWaitingCalled, 'skipWaiting should be called');
  assert.ok(cacheAddAllArgs !== null, 'cache.addAll should be called');
  assert.ok(cacheAddAllArgs.includes('index.html'), 'should cache index.html');
  assert.ok(cacheAddAllArgs.includes('manifest.json'), 'should cache manifest.json');
  assert.ok(cacheAddAllArgs.includes('404.html'), 'should cache 404.html');
});

console.log('  sw.js — Activate Event');
test('activate deletes old caches', async () => {
  const ctx = loadSW();
  const activateHandler = ctx.self._listeners.activate[0];

  const event = {
    waitUntil(fn) {
      waitUntilArgs = fn;
    },
  };

  activateHandler(event);
  await waitUntilArgs;

  assert.ok(clientsClaimCalled, 'clients.claim should be called');
  assert.ok(deletedCacheKeys.includes('supercat-weather-v2'), 'should delete old cache v2');
  assert.ok(deletedCacheKeys.includes('old-cache-v1'), 'should delete old cache v1');
});

test('activate does not delete current cache', async () => {
  const ctx = loadSW();
  const activateHandler = ctx.self._listeners.activate[0];

  const event = {
    waitUntil(fn) {
      waitUntilArgs = fn;
    },
  };

  resetMocks();
  activateHandler(event);
  await waitUntilArgs;

  assert.ok(!deletedCacheKeys.includes('supercat-weather-v3'), 'should NOT delete current cache v3');
});

console.log('  sw.js — Fetch Event (navigate)');
test('navigate fetch success returns network response', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://example.com/', { mode: 'navigate' });
  fetchResponse = new MockResponse('network content', { ok: true });

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  const result = await respondWithArgs;

  assert.strictEqual(result.body, 'network content');
});

test('navigate fetch failure returns cached index.html', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://example.com/', { mode: 'navigate' });
  fetchError = new Error('Network failure');
  cacheMatchResult = new MockResponse('cached index.html', { ok: true });

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  const result = await respondWithArgs;

  assert.ok(result, 'should return a response');
  assert.strictEqual(result.body, 'cached index.html');
});

console.log('  sw.js — Fetch Event (non-navigate)');
test('non-navigate returns cached content when available', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://example.com/style.css', { mode: 'no-cors' });
  cacheMatchResult = new MockResponse('cached css', { ok: true });

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  const result = await respondWithArgs;

  assert.strictEqual(result.body, 'cached css');
});

test('non-navigate fetches from network when not cached', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://example.com/script.js', { mode: 'no-cors' });
  cacheMatchResult = null;
  fetchResponse = new MockResponse('network script', { ok: true });

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  const result = await respondWithArgs;

  assert.strictEqual(result.body, 'network script');
});

test('non-navigate network failure returns 404.html', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://example.com/unknown.png', { mode: 'no-cors' });
  cacheMatchResult = null;
  fetchError = new Error('Network failure');

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  const result = await respondWithArgs;

  assert.strictEqual(result.body, '404 page');
});

test('non-navigate caches same-origin responses', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://example.com/asset.js', { mode: 'no-cors' });
  cacheMatchResult = null;
  fetchResponse = new MockResponse('asset content', { ok: true, status: 200 });

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  const result = await respondWithArgs;

  assert.strictEqual(result.body, 'asset content');
  assert.ok(fetchResponse.cloneCalled, 'response should be cloned for cache');
  assert.ok(cachePutArgs !== null, 'cache.put should be called');
  assert.strictEqual(cachePutArgs.request, 'https://example.com/asset.js');
});

test('non-navigate does not cache cross-origin responses', async () => {
  const ctx = loadSW();
  const fetchHandler = ctx.self._listeners.fetch[0];

  resetMocks();
  const request = new MockRequest('https://other-cdn.com/lib.js', { mode: 'no-cors' });
  cacheMatchResult = null;
  fetchResponse = new MockResponse('lib content', { ok: true, status: 200 });

  const event = {
    request,
    respondWith(fn) {
      respondWithArgs = fn;
    },
  };

  fetchHandler(event);
  await respondWithArgs;

  assert.ok(cachePutArgs === null, 'cache.put should NOT be called for cross-origin');
});

// ---------- Summary ----------

console.log(`\n  Results: ${passed} passed, ${failed} failed, ${passed + failed} total\n`);
process.exit(failed > 0 ? 1 : 0);

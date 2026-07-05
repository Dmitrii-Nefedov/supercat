const CACHE = 'supercat-weather-v2';
const STATIC_ASSETS = [
  '.',
  'index.html',
  'manifest.json',
  '404.html'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; })
          .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  const isNavigate = e.request.mode === 'navigate';
  if (isNavigate) {
    e.respondWith(
      fetch(e.request).catch(function() {
        return caches.match('index.html');
      })
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(function(cached) {
      var fetchPromise = fetch(e.request).then(function(resp) {
        if (resp.ok && e.request.url.startsWith(self.location.origin)) {
          var clone = resp.clone();
          caches.open(CACHE).then(function(cache) {
            cache.put(e.request, clone);
          });
        }
        return resp;
      }).catch(function() {
        return caches.match('404.html');
      });
      return cached || fetchPromise;
    })
  );
});

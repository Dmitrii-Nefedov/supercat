const CACHE = 'supercat-weather-v5';
const API_CACHE = 'supercat-api-v1';
const STATIC_ASSETS = [
  '.',
  'index.html',
  'frontend/styles.css',
  'manifest.json',
  '404.html'
];
const API_ORIGINS = ['api.open-meteo.com', 'geocoding-api.open-meteo.com'];

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
        keys.filter(function(k) { return k !== CACHE && k !== API_CACHE; })
          .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('message', function(e) {
  if (e.data && e.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

function isAPIRequest(url) {
  return API_ORIGINS.some(function(origin) { return url.indexOf(origin) !== -1; });
}

self.addEventListener('fetch', function(e) {
  var url = e.request.url;

  if (isAPIRequest(url)) {
    e.respondWith(
      fetch(e.request).then(function(resp) {
        if (resp.ok) {
          var clone = resp.clone();
          caches.open(API_CACHE).then(function(cache) {
            cache.put(e.request, clone);
          });
        }
        return resp;
      }).catch(function() {
        return caches.match(e.request).then(function(cached) {
          return cached || new Response(
            JSON.stringify({ error: true, message: 'Нет подключения к интернету' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } }
          );
        });
      })
    );
    return;
  }

  var isNavigate = e.request.mode === 'navigate';
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
        if (resp.ok && url.startsWith(self.location.origin)) {
          var clone = resp.clone();
          caches.open(CACHE).then(function(cache) {
            cache.put(e.request, clone);
          });
        }
        return resp;
      }).catch(function() {
        return cached || caches.match('404.html');
      });
      return cached || fetchPromise;
    })
  );
});

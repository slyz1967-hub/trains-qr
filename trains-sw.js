// TRAINS Service Worker — minimal, no caching
// Only exists to satisfy PWA installability requirements
// All requests go straight to the network — no stale content possible

self.addEventListener('install', function(e) {
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  // Clear any old caches from previous SW versions
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.map(function(k) { return caches.delete(k); }));
    }).then(function() { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e) {
  // Network only — never serve from cache
  e.respondWith(fetch(e.request));
});

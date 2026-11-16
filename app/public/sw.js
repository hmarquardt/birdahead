const CACHE = 'birdahead-shell-v1';
const SHELL = ['/', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png'];
self.addEventListener('install', (event) => { event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', (event) => { event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim())); });
self.addEventListener('message', (event) => { if (event.data === 'CLEAR_PRIVATE') event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))); });
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  // Never cache authenticated APIs or private media. Media requests must reach the Worker.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/media/')) return;
  if (event.request.method !== 'GET') return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then((response) => { if (response.ok && url.pathname === '/') caches.open(CACHE).then((cache) => cache.put('/', response.clone())); return response; }).catch(() => url.pathname === '/' ? caches.match('/') : Response.error()));
    return;
  }
  if (url.pathname.startsWith('/assets/') || url.pathname === '/manifest.webmanifest' || url.pathname.endsWith('.png')) {
    event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => { if (response.ok) caches.open(CACHE).then((cache) => cache.put(event.request, response.clone())); return response; })));
  }
});

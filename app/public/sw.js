// BirdAhead PWA shell. Downloaded learning media lives in a separate,
// independently versioned cache and is never removed by a shell upgrade.
const SHELL_CACHE = 'birdahead-shell-v2';
const PACK_CACHE = 'birdahead-pack-assets-v1';

async function cacheResponse(cache, request, response) {
  if (!response || !response.ok) throw new Error('Shell asset failed.');
  const headers = new Headers(response.headers);
  for (const name of ['Content-Encoding', 'Content-Length', 'Transfer-Encoding']) headers.delete(name);
  await cache.put(request, new Response(response.body, { status: response.status, headers }));
}

async function installShell() {
  const cache = await caches.open(SHELL_CACHE);
  const response = await fetch('/', { cache: 'reload', credentials: 'omit' });
  if (!response.ok) throw new Error('Shell document failed.');
  const html = await response.clone().text();
  await cacheResponse(cache, '/', response);
  const assets = new Set(
    [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((match) => match[1]),
  );
  for (const asset of assets) {
    const assetResponse = await fetch(asset, { cache: 'reload', credentials: 'omit' });
    await cacheResponse(cache, asset, assetResponse);
  }
  for (const asset of ['/manifest.webmanifest', '/icon-192.png', '/icon-512.png', '/icon-maskable-512.png', '/apple-touch-icon.png']) {
    const assetResponse = await fetch(asset, { cache: 'reload', credentials: 'omit' });
    await cacheResponse(cache, asset, assetResponse);
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(installShell().then(() => self.skipWaiting()));
});
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith('birdahead-shell-') && key !== SHELL_CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});
self.addEventListener('message', (event) => {
  // Pack caches are public learning content, not private credentials. They
  // survive sign-out and service-worker upgrades by design.
  if (event.data === 'CLEAR_PRIVATE') {
    event.waitUntil(caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key.startsWith('birdahead-private-')).map((key) => caches.delete(key)),
    )));
  }
});
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || event.request.method !== 'GET') return;
  // Public pack media only. Authenticated media and all APIs stay network-only.
  if (url.pathname.startsWith('/media/public/')) {
    event.respondWith(caches.open(PACK_CACHE).then((cache) => cache.match(event.request)).then((cached) => cached || fetch(event.request)));
    return;
  }
  if (url.pathname.startsWith('/narration/')) {
    event.respondWith(caches.open(PACK_CACHE).then((cache) => cache.match(event.request)).then((cached) => cached || fetch(event.request)));
    return;
  }
  if (url.pathname.startsWith('/media/') || url.pathname.startsWith('/api/')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then((response) => {
      if (response.ok && url.pathname === '/') caches.open(SHELL_CACHE).then((cache) => cache.put('/', response.clone()));
      return response;
    }).catch(() => caches.match('/').then((cached) => cached || Response.error())));
    return;
  }
  if (url.pathname.startsWith('/assets/') || url.pathname === '/manifest.webmanifest' || url.pathname.endsWith('.png')) {
    event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
      if (response.ok) caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, response.clone()));
      return response;
    })));
  }
});

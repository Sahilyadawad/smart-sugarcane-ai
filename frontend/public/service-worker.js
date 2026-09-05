/**
 * Service worker for the installed app.
 *
 * Deliberately narrow in what it caches. The UI shell and build assets are safe
 * to serve from cache, but /api responses are NEVER cached: an irrigation
 * schedule, a disease diagnosis or a soil estimate served from yesterday's
 * cache would look current while being wrong, and the whole project is built
 * on not presenting a stale or invented answer as a live one. Uploaded photos
 * under /uploads are likewise left alone.
 *
 * Bump CACHE_VERSION whenever the shell changes so old caches are dropped.
 */

const CACHE_VERSION = 'ssai-v1'
const SHELL = ['/', '/index.html', '/favicon.svg', '/manifest.webmanifest', '/icon-192.png']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      // addAll rejects the whole batch if any single request 404s, which would
      // leave the worker uninstalled. Add them individually and tolerate misses.
      .then((cache) => Promise.allSettled(SHELL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  // Never serve analysis results, auth or uploaded images from cache.
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/uploads')) return

  // Navigations: try the network so a newly deployed build is picked up, and
  // fall back to the cached shell only when genuinely offline. Without this the
  // app would keep booting an old bundle after every rebuild.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_VERSION).then((cache) => cache.put('/index.html', copy))
          return response
        })
        .catch(() => caches.match('/index.html').then((hit) => hit || Response.error())),
    )
    return
  }

  // Build assets are content-hashed, so a cache hit is always the right file.
  event.respondWith(
    caches.match(request).then(
      (hit) =>
        hit ||
        fetch(request).then((response) => {
          if (response.ok && response.type === 'basic') {
            const copy = response.clone()
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy))
          }
          return response
        }),
    ),
  )
})

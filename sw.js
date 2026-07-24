/* Service Worker – DRIV Rollkunstlauf Leistungsdaten-Analyse
   Strategie: network-first mit Offline-Fallback.
   Online wird IMMER die aktuelle Version geladen (und der Cache erneuert),
   offline liefert der Cache den letzten bekannten Stand der Anmeldeseite.
   Es wird ausschließlich die verschlüsselte Seite gespeichert – ohne Passwort
   sind auch offline keine Inhalte lesbar. */
const CACHE = 'driv-analyse-v1';
const ASSETS = ['./', 'manifest.json', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;      // nur eigene Dateien
  e.respondWith((async () => {
    try {
      const fresh = await fetch(req);
      if (fresh && fresh.ok) {
        const c = await caches.open(CACHE);
        c.put(req, fresh.clone()).catch(() => {});
      }
      return fresh;
    } catch (err) {
      const c = await caches.open(CACHE);
      const hit = await c.match(req, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === 'navigate') {
        const shell = await c.match('./', { ignoreSearch: true });
        if (shell) return shell;
      }
      return new Response('Offline – bitte einmal mit Internetverbindung öffnen, danach steht die App auch offline bereit.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
    }
  })());
});

/* Service worker · PIC Campo Genérico
   Convive con PIC Campo original en el mismo celular: todos sus cachés empiezan con "picg-" y sólo borra
   los suyos. Como las dos apps comparten el origen (github.io), la original puede borrar estos cachés al
   actualizarse: por eso la app también queda copiada en IndexedDB y se restaura sola, sin conexión. */
const VERSION = 'g2-0-0-3';
const PREF = 'picg-';
const SHELL = PREF + 'app-' + VERSION;
const TILES = PREF + 'teselas-v1';
const ARCHIVOS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './icon-maskable-512.png'];
const RESPALDO_DB = 'pic-campo-generico-app';

function respaldo(modo, fn) {
  return new Promise((res, rej) => {
    const r = indexedDB.open(RESPALDO_DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore('archivos');
    r.onerror = () => rej(r.error);
    r.onsuccess = () => {
      const tx = r.result.transaction('archivos', modo), os = tx.objectStore('archivos'), q = fn(os);
      tx.oncomplete = () => res(q && q.result); tx.onerror = () => rej(tx.error);
    };
  });
}
async function guardarRespaldo(c) {
  for (const u of ARCHIVOS) {
    const r = await c.match(u); if (!r) continue;
    const b = await r.blob();
    await respaldo('readwrite', os => os.put({ tipo: r.headers.get('content-type') || b.type, b, version: VERSION }, new URL(u, self.registration.scope).href));
  }
}
async function desdeRespaldo(url) {
  try {
    const x = await respaldo('readonly', os => os.get(url));
    if (!x) return null;
    const resp = new Response(x.b, { headers: { 'content-type': x.tipo } });
    caches.open(SHELL).then(c => c.put(url, resp.clone())).catch(() => { });
    return resp;
  } catch (e) { return null; }
}

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(async c => {
    await c.addAll(ARCHIVOS.map(u => new Request(u, { cache: 'reload' })));
    await guardarRespaldo(c).catch(() => { });
  }));
});
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith(PREF) && k !== SHELL && k !== TILES) await caches.delete(k);
    await self.clients.claim();
  })());
});
self.addEventListener('message', e => { if (e.data === 'activar') self.skipWaiting(); });

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.hostname === 'server.arcgisonline.com') { e.respondWith(tesela(req)); return; }
  if (url.origin !== location.origin) return;
  const scope = self.registration.scope;
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      const c = await caches.open(SHELL);
      const hit = (await c.match('./index.html')) || (await c.match('./'));
      if (hit) return hit;
      try { return await fetch(req); } catch (err) { return (await desdeRespaldo(new URL('./index.html', scope).href)) || (await desdeRespaldo(scope)) || new Response('Sin conexión', { status: 504 }); }
    })());
    return;
  }
  e.respondWith((async () => {
    const hit = await caches.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try { return await fetch(req); } catch (err) { return (await desdeRespaldo(url.origin + url.pathname)) || new Response('', { status: 504 }); }
  })());
});

async function tesela(req) {
  const c = await caches.open(TILES);
  const hit = await c.match(req.url);
  if (hit) return hit;
  try {
    let r;
    try { r = await fetch(req.url, { mode: 'cors', credentials: 'omit' }); }
    catch (err) { return await fetch(req); }
    if (r.ok) c.put(req.url, r.clone());
    return r;
  } catch (err) {
    return new Response('', { status: 504, statusText: 'sin conexión' });
  }
}

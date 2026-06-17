// Offline support for the Pointless Revision app.
// Bump CACHE when you want every installed client to discard old assets.
const CACHE = "pointless-v1";

// App shell plus the data files that aren't tied to a category slug.
const CORE = [
  "./",
  "index.html",
  "style.css",
  "app.js",
  "manifest.webmanifest",
  "icon-192.png",
  "icon-512.png",
  "apple-touch-icon.png",
  "js/data.js",
  "js/match.js",
  "js/play.js",
  "js/questions.js",
  "js/storage.js",
  "data/categories.json",
  "data/episodes.json",
  "data/finals.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await cache.addAll(CORE);
      // Derive every category file from the catalogue so new ones cache too.
      try {
        const res = await fetch("data/categories.json", { cache: "no-cache" });
        const data = await res.json();
        const slugs = (data.categories || []).map((c) => `data/${c.slug}.json`);
        await cache.addAll(slugs);
      } catch (err) {
        // Offline during install is fine; files cache lazily on first use.
      }
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
      await self.clients.claim();
    })(),
  );
});

// Stale-while-revalidate: serve cached instantly, refresh in the background
// when online so the data stays current without breaking offline use.
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  if (new URL(req.url).origin !== self.location.origin) return;

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE);
      const cached = await cache.match(req);
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok) cache.put(req, res.clone());
          return res;
        })
        .catch(() => null);

      const response = cached || (await network);
      if (response) return response;
      if (req.mode === "navigate") {
        const shell = await cache.match("index.html");
        if (shell) return shell;
      }
      return Response.error();
    })(),
  );
});

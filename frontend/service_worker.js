const CACHE_NAME = 'hfos-cache-v5.0';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/offline.html',
    '/pwa_install.js',
    '/assets/icons/icon-192x192.png',
    '/assets/icons/icon-512x512.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    
    // API & Data Strategy: Network First, Fallback to Cache
    if (request.url.includes('/api/')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    const cloned = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(request, cloned));
                    return response;
                })
                .catch(() => caches.match(request))
        );
    } else {
        // Static Strategy: Cache First, Fallback to Network, Fallback to Offline Page
        event.respondWith(
            caches.match(request).then(response => {
                return response || fetch(request).catch(() => caches.match('/offline.html'));
            })
        );
    }
});

self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: 'HFOS Alert', body: 'New notification' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/assets/icons/icon-192x192.png',
            badge: '/assets/icons/icon-192x192.png'
        })
    );
});

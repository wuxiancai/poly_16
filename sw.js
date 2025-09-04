const CACHE_NAME = 'crypto-trader-v1.0.0';
const urlsToCache = [
  '/',
  '/static/icon-192x192.png',
  '/static/icon-512x512.png',
  '/history',
  '/manifest.json'
];

// 安装事件 - 缓存资源
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('Service Worker: Installed');
        return self.skipWaiting();
      })
  );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('Service Worker: Activated');
      return self.clients.claim();
    })
  );
});

// 拦截网络请求
self.addEventListener('fetch', event => {
  // 只处理GET请求
  if (event.request.method !== 'GET') {
    return;
  }

  // 对于API请求，使用网络优先策略
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('/update_') ||
      event.request.url.includes('/save_') ||
      event.request.url.includes('/reset_')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // 如果网络请求成功，返回响应
          if (response.ok) {
            return response;
          }
          throw new Error('Network response was not ok');
        })
        .catch(() => {
          // 网络失败时返回离线页面或缓存
          return new Response(
            JSON.stringify({ error: '网络连接失败，请检查网络连接' }),
            {
              status: 503,
              statusText: 'Service Unavailable',
              headers: { 'Content-Type': 'application/json' }
            }
          );
        })
    );
    return;
  }

  // 对于静态资源，使用缓存优先策略
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // 如果缓存中有，直接返回
        if (response) {
          console.log('Service Worker: Serving from cache:', event.request.url);
          return response;
        }

        // 缓存中没有，从网络获取
        console.log('Service Worker: Fetching from network:', event.request.url);
        return fetch(event.request)
          .then(response => {
            // 检查响应是否有效
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // 克隆响应，因为响应流只能使用一次
            const responseToCache = response.clone();

            // 将响应添加到缓存
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });

            return response;
          })
          .catch(() => {
            // 网络失败时，返回离线页面
            if (event.request.destination === 'document') {
              return new Response(
                `<!DOCTYPE html>
                <html>
                <head>
                  <meta charset="UTF-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                  <title>离线模式 - 量化交易监控</title>
                  <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a2e; color: white; }
                    .offline-message { max-width: 400px; margin: 0 auto; }
                    .icon { font-size: 64px; margin-bottom: 20px; }
                    button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 20px; }
                    button:hover { background: #45a049; }
                  </style>
                </head>
                <body>
                  <div class="offline-message">
                    <div class="icon">📱</div>
                    <h1>离线模式</h1>
                    <p>当前网络连接不可用，您正在使用离线版本。</p>
                    <p>部分功能可能受限，请检查网络连接后刷新页面。</p>
                    <button onclick="window.location.reload()">重新连接</button>
                  </div>
                </body>
                </html>`,
                {
                  headers: { 'Content-Type': 'text/html' }
                }
              );
            }
            return new Response('离线模式', { status: 503 });
          });
      })
  );
});

// 处理推送通知（可选）
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icon-192x192.png',
      badge: '/static/icon-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: data.primaryKey
      },
      actions: [
        {
          action: 'explore',
          title: '查看详情',
          icon: '/static/icon-192x192.png'
        },
        {
          action: 'close',
          title: '关闭',
          icon: '/static/icon-192x192.png'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// 处理通知点击
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});
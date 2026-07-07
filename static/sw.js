self.addEventListener('push', function (event) {
  let data = { title: 'SecondMind', body: 'You have a reminder.' };
  try {
    data = event.data.json();
  } catch (_) {}

  const options = {
    body: data.body || '',
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    data: data.data || {},
    actions: [
      { action: 'acknowledge', title: 'Done' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    requireInteraction: true,
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  const taskId = event.notification.data && event.notification.data.task_id;

  if (event.action === 'acknowledge' && taskId) {
    event.waitUntil(
      fetch(`/api/v1/notifications/${taskId}/done`, {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + (self.__token || '') },
      })
    );
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
      const url = taskId ? `/?bell=1&tid=${taskId}` : '/?bell=1';
      for (const client of clientList) {
        if ('focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

self.addEventListener('message', function (event) {
  if (event.data && event.data.type === 'SET_TOKEN') {
    self.__token = event.data.token;
  }
});

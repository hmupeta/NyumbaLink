import { api } from './client'

export const notificationsApi = {
  list: () => api<{results: any[]}>('/notifications/'),
  unreadCount: () => api<{count: number}>('/notifications/unread_count/'),
  markRead: (id: string) => api(`/notifications/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ is_read: true })
  }),
  markAllRead: () => api('/notifications/mark_all_read/', { method: 'POST' })
}

import { api } from './client'

export const messagingApi = {
  listConversations: () => api<{results: any[]}>('/conversations/'),
  startConversation: (listingId: string) => api<any>('/conversations/start/', {
    method: 'POST', body: JSON.stringify({ listing_id: listingId })
  }),
  getMessages: (convId: string) => api<{results: any[]}>(`/conversations/${convId}/messages/`),
  
  sendMessage: (convId: string, body: string, replyToId?: string, file?: File, type: string = 'TEXT') => {
    const formData = new FormData()
    if (body) formData.append('body', body)
    formData.append('message_type', type)
    if (replyToId) formData.append('reply_to', replyToId)
    if (file) formData.append('file', file)
    
    return api(`/conversations/${convId}/messages/`, {
      method: 'POST', 
      body: formData
    })
  },
  
  reactToMessage: (convId: string, msgId: string, emoji: string) => api(`/conversations/${convId}/messages/${msgId}/react/`, {
    method: 'POST', body: JSON.stringify({ emoji })
  }),

  requestViewing: (data: any) => api('/viewings/', { method: 'POST', body: JSON.stringify(data) }),
  listViewings: () => api<{results: any[]}>('/viewings/'),
  updateViewingStatus: (id: string, status: string) => api(`/viewings/${id}/update_status/`, {
    method: 'POST', body: JSON.stringify({ status })
  })
}

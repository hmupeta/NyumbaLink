import { api } from './client'

export const profileApi = {
  get: (userId: string) => api<any>(`/profiles/${userId}/`),
  leaveReview: (userId: string, rating: number, comment: string) => 
    api(`/profiles/${userId}/reviews/`, {
      method: 'POST',
      body: JSON.stringify({ rating, comment })
    }),
  updateProfile: (data: FormData) => {
    // Using fetch directly because our api helper defaults to JSON
    return fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/me/`, {
      method: 'PATCH',
      credentials: 'include',
      body: data
    }).then(res => {
      if (!res.ok) throw new Error('Failed to update profile');
      return res.json();
    })
  }
}

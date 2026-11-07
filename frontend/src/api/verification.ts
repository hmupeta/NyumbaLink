
import { api } from './client'

export interface VerificationDocument {
  id: string
  file: string
  document_type: string
  created_at: string
}

export interface VerificationCase {
  id: string
  verification_type: string
  type_label: string
  status: string
  status_label: string
  rejection_reason: string
  documents: VerificationDocument[]
  created_at: string
}

export const verificationApi = {
  list: () => api<{results: VerificationCase[]}>('/verifications/'),
  create: (verification_type: string) => api<VerificationCase>('/verifications/', {
    method: 'POST',
    body: JSON.stringify({ verification_type })
  }),
  uploadDocument: (caseId: string, file: File, document_type: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', document_type)
    return api(`/verifications/${caseId}/documents/`, { method: 'POST', body: formData })
  }
}

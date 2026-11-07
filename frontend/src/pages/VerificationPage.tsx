
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { verificationApi, type VerificationCase } from '../api/verification'
import { getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function VerificationPage() {
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  
  const { data, isLoading } = useQuery({
    queryKey: ['verifications'],
    queryFn: () => verificationApi.list(),
  })

  const cases = data?.results || []
  const identityCase = cases.find(c => c.verification_type === 'IDENTITY')
  const ownershipCase = cases.find(c => c.verification_type === 'OWNERSHIP_AUTHORITY')

  const createCase = useMutation({
    mutationFn: (type: string) => verificationApi.create(type),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['verifications'] }),
    onError: () => setError('Failed to start verification.')
  })

  const uploadDoc = useMutation({
    mutationFn: ({ caseId, file, type }: { caseId: string, file: File, type: string }) => 
      verificationApi.uploadDocument(caseId, file, type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['verifications'] })
      alert('Document uploaded successfully.')
    },
    onError: () => setError('Failed to upload document.')
  })

  const renderCase = (title: string, description: string, type: string, existingCase?: VerificationCase) => (
    <div className="bg-white border rounded-lg p-6 mb-6 shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-bold">{title}</h2>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        {existingCase && (
          <span className={`px-3 py-1 rounded text-xs font-bold ${
            existingCase.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
            existingCase.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
          }`}>
            {existingCase.status_label}
          </span>
        )}
      </div>

      {!existingCase ? (
        <button 
          onClick={() => createCase.mutate(type)}
          disabled={createCase.isPending}
          className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 disabled:opacity-50 text-sm"
        >
          Start Verification
        </button>
      ) : (
        <div className="mt-4 border-t pt-4">
          {existingCase.status === 'REJECTED' && (
            <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">
              <strong>Rejected:</strong> {existingCase.rejection_reason}
            </div>
          )}
          
          <h3 className="text-sm font-semibold mb-2">Uploaded Documents</h3>
          <ul className="space-y-2 mb-4">
            {existingCase.documents.map(doc => (
              <li key={doc.id} className="text-sm flex items-center gap-2">
                <a href={getMediaUrl(doc.file)} target="_blank" rel="noreferrer" className="text-emerald-600 hover:underline">
                  {doc.document_type}
                </a>
                <span className="text-gray-400 text-xs">({new Date(doc.created_at).toLocaleDateString()})</span>
              </li>
            ))}
            {existingCase.documents.length === 0 && <li className="text-sm text-gray-500">No documents uploaded yet.</li>}
          </ul>

          {existingCase.status !== 'APPROVED' && (
            <div className="flex items-center gap-4">
              <input 
                type="file" 
                id={`file-${type}`}
                className="text-sm border rounded px-2 py-1"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    uploadDoc.mutate({ caseId: existingCase.id, file, type: 'Document' })
                    e.target.value = '' // reset
                  }
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Verification Center</h1>
        <p className="text-gray-600">Build trust by verifying your identity and property ownership.</p>
      </div>

      {error && <ErrorMessage message={error} />}
      {isLoading ? <Loading /> : (
        <div className="space-y-4">
          {renderCase(
            "Identity Verification",
            "Upload your NRC or Passport. This confirms who you are, but does not prove property ownership.",
            "IDENTITY",
            identityCase
          )}
          {renderCase(
            "Ownership / Authority",
            "Upload Title Deeds or a signed landlord authorization letter to prove you have the right to list this property.",
            "OWNERSHIP_AUTHORITY",
            ownershipCase
          )}
        </div>
      )}
    </div>
  )
}

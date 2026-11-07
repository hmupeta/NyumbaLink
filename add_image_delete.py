#!/usr/bin/env python3
"""Adds image deletion capability to the backend and Edit Listing frontend."""
from pathlib import Path

ROOT = Path.cwd()

# ---------------------------------------------------------------- 1. Backend: Secure Deletion
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# We need to inject a perform_destroy method into ListingMediaViewSet
if "def perform_destroy(self, instance):" not in text:
    old_block = '''    def perform_create(self, serializer):
        listing = Listing.objects.get(pk=self.kwargs["listing_pk"])
        if not user_can_edit_listing(self.request.user, listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot add media to this listing")
        serializer.save(listing=listing)'''
    
    new_block = old_block + '''

    def perform_destroy(self, instance):
        if not user_can_edit_listing(self.request.user, instance.listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot remove media from this listing")
        instance.delete()'''

    text = text.replace(old_block, new_block)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched apps/properties/views.py: secured media deletion")

# ---------------------------------------------------------------- 2. Frontend: API Update
API_FILE = ROOT / "frontend" / "src" / "api" / "listings.ts"
api_text = API_FILE.read_text(encoding="utf-8")

if "deleteMedia:" not in api_text:
    old_api = '''  uploadMedia: (listingId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('media_type', 'IMAGE')
    return api(`/listings/${listingId}/media/`, { method: 'POST', body: formData })
  }'''
    
    new_api = old_api + ''',
  deleteMedia: (listingId: string, mediaId: string) => 
    api(`/listings/${listingId}/media/${mediaId}/`, { method: 'DELETE' })'''

    api_text = api_text.replace(old_api, new_api)
    API_FILE.write_text(api_text, encoding="utf-8")
    print("Patched src/api/listings.ts: added deleteMedia method")

# ---------------------------------------------------------------- 3. Frontend: UI Update
EDIT_PAGE = ROOT / "frontend" / "src" / "pages" / "EditListingPage.tsx"
edit_text = EDIT_PAGE.read_text(encoding="utf-8")

# Add the delete mutation logic
if "const deleteMediaMutation" not in edit_text:
    old_mutation = '''  const submit = (e: FormEvent<HTMLFormElement>) => {'''
    new_mutation = '''  const deleteMediaMutation = useMutation({
    mutationFn: (mediaId: string) => listingsApi.deleteMedia(listing!.id, mediaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manage-listing', id] })
    },
    onError: () => setError('Failed to delete image')
  })

  const submit = (e: FormEvent<HTMLFormElement>) => {'''
    edit_text = edit_text.replace(old_mutation, new_mutation)

# Replace the image mapping to add the delete button
old_images = '''          <div className="flex gap-2 overflow-x-auto mb-4">
            {listing.media.map(m => (
              <img key={m.id} src={getMediaUrl(m.file)} className="w-24 h-24 object-cover rounded border bg-gray-50" />
            ))}
            {listing.media.length === 0 && <span className="text-gray-400 text-sm">No images yet.</span>}
          </div>'''

new_images = '''          <div className="flex gap-3 overflow-x-auto mb-4 p-1">
            {listing.media.map(m => (
              <div key={m.id} className="relative group w-24 h-24 flex-shrink-0">
                <img 
                  src={getMediaUrl(m.file)} 
                  className="w-full h-full object-cover rounded border bg-gray-50" 
                />
                <button
                  type="button"
                  onClick={() => {
                    if (confirm('Delete this image?')) {
                      deleteMediaMutation.mutate(m.id)
                    }
                  }}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition shadow hover:bg-red-600"
                  title="Delete image"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </div>
            ))}
            {listing.media.length === 0 && <span className="text-gray-400 text-sm">No images yet.</span>}
          </div>'''

edit_text = edit_text.replace(old_images, new_images)
EDIT_PAGE.write_text(edit_text, encoding="utf-8")
print("Patched src/pages/EditListingPage.tsx: added hover delete buttons")

print("\nDone! Restart your frontend (npm run dev) and backend (runserver).")
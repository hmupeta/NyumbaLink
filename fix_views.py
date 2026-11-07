#!/usr/bin/env python3
"""Restore the missing ViewingRequestViewSet to views.py."""
from pathlib import Path

ROOT = Path.cwd()
VIEWS_FILE = ROOT / "apps" / "messaging" / "views.py"

text = VIEWS_FILE.read_text(encoding="utf-8")

if "class ViewingRequestViewSet" not in text:
    # Append the missing view
    text += '''

class ViewingRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ViewingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ViewingRequest.objects.filter(
            Q(seeker=self.request.user) | Q(listing__created_by=self.request.user)
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        viewing = self.get_object()
        if viewing.listing.created_by != request.user:
            return Response({"detail": "Only the landlord can update this."}, status=403)
        
        new_status = request.data.get("status")
        if new_status not in ["APPROVED", "REJECTED"]:
            return Response({"detail": "Invalid status."}, status=400)
        
        viewing.status = new_status
        viewing.save()
        return Response(ViewingRequestSerializer(viewing).data)
'''
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Successfully restored ViewingRequestViewSet.")
else:
    print("ViewingRequestViewSet already exists.")

print("""
Next steps:
  1. Run: .\\venv\\Scripts\\python.exe manage.py makemigrations messaging
  2. Run: .\\venv\\Scripts\\python.exe manage.py migrate
  3. Restart backend (runserver) and frontend (npm run dev).
""")
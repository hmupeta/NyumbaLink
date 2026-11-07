from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import MaintenanceRequest
from .serializers import MaintenanceRequestSerializer

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MaintenanceRequest.objects.filter(landlord=self.request.user).select_related("property", "lease")

    def perform_create(self, serializer):
        serializer.save(landlord=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        req = self.get_object()
        new_status = request.data.get("status")
        note = request.data.get("resolution_note", "")
        
        if new_status not in ["OPEN", "IN_PROGRESS", "RESOLVED"]:
            return Response({"detail": "Invalid status"}, status=400)
            
        req.status = new_status
        req.resolution_note = note
        if new_status == "RESOLVED":
            req.resolved_at = timezone.now()
        req.save()
        return Response(MaintenanceRequestSerializer(req).data)

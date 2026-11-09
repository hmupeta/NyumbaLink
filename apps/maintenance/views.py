from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from .models import MaintenanceRequest
from .serializers import MaintenanceRequestSerializer
from apps.management.models import Lease
from apps.notifications.services import create_notification


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return MaintenanceRequest.objects.filter(
            Q(landlord=user) | Q(lease__tenant_email__iexact=user.email)
        ).select_related("property", "lease")

    def perform_create(self, serializer):
        lease_id = self.request.data.get('lease')
        if lease_id:
            try:
                lease = Lease.objects.get(id=lease_id)
            except Lease.DoesNotExist:
                raise PermissionDenied("Lease not found.")
            
            is_landlord = lease.landlord_id == self.request.user.id
            is_tenant = lease.tenant_email.lower() == self.request.user.email.lower()
            if not (is_landlord or is_tenant):
                raise PermissionDenied("You cannot log maintenance for this lease.")
            
            instance = serializer.save(landlord=lease.landlord, property=lease.property)
            
            # Notify landlord if a tenant submitted
            if is_tenant and not is_landlord:
                create_notification(
                    user=lease.landlord,
                    title="New Maintenance Issue",
                    message=f"{self.request.user.email} reported: {instance.title}",
                    link="/dashboard?tab=maintenance",
                )
        else:
            serializer.save(landlord=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        req = self.get_object()
        if req.landlord_id != request.user.id:
            return Response({"detail": "Only the landlord can update status."}, status=403)
            
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

from rest_framework import serializers
from .models import MaintenanceRequest

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.neighbourhood.name", read_only=True)
    tenant_name = serializers.CharField(source="lease.tenant_name", read_only=True, default="")
    
    class Meta:
        model = MaintenanceRequest
        fields = ("id", "property", "property_name", "lease", "tenant_name", "title", "description", "priority", "status", "resolved_at", "resolution_note", "created_at")
        read_only_fields = ("id", "landlord", "created_at", "resolved_at")

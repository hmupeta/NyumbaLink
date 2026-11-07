from rest_framework import serializers
from .models import Lease, RentRecord
from apps.properties.serializers import PropertySerializer

class RentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentRecord
        fields = ("id", "due_date", "amount", "paid_date", "status")
        read_only_fields = ("id",)

class LeaseSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.neighbourhood.name", read_only=True)
    rent_records = RentRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lease
        fields = ("id", "property", "property_name", "tenant_name", "tenant_phone", "tenant_email", "start_date", "end_date", "monthly_rent", "deposit_paid", "status", "rent_records", "created_at")
        read_only_fields = ("id", "landlord", "created_at")

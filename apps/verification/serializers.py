from rest_framework import serializers
from .models import VerificationCase, VerificationDocument

class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("id", "file", "document_type", "created_at")

class VerificationCaseSerializer(serializers.ModelSerializer):
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    type_label = serializers.CharField(source="get_verification_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    reviewed_by_email = serializers.CharField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = VerificationCase
        fields = ("id", "verification_type", "type_label", "status", "status_label", 
                  "rejection_reason", "documents", "user_email", "reviewed_by_email", "reviewed_at", "created_at", "updated_at")
        read_only_fields = ("id", "status", "rejection_reason", "created_at", "updated_at")

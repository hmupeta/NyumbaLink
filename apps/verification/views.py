from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.notifications.services import create_notification
from .models import VerificationCase, VerificationDocument
from .serializers import VerificationCaseSerializer, VerificationDocumentSerializer

class VerificationCaseViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ("status", "verification_type")

    def get_queryset(self):
        if self.request.user.is_staff:
            return VerificationCase.objects.all().prefetch_related("documents")
        return VerificationCase.objects.filter(user=self.request.user).prefetch_related("documents")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can approve."}, status=status.HTTP_403_FORBIDDEN)
        
        case = self.get_object()
        case.status = "APPROVED"
        case.reviewed_by = request.user
        case.reviewed_at = timezone.now()
        case.save()

        create_notification(
            user=case.user,
            title="Verification Approved",
            message=f"Your {case.get_verification_type_display()} has been approved!",
            link=f"/profiles/{case.user.id}"
        )
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can reject."}, status=status.HTTP_403_FORBIDDEN)
        
        case = self.get_object()
        reason = request.data.get("reason", "Documents unclear or invalid.")
        case.status = "REJECTED"
        case.rejection_reason = reason
        case.reviewed_by = request.user
        case.reviewed_at = timezone.now()
        case.save()

        create_notification(
            user=case.user,
            title="Verification Rejected",
            message=f"Your {case.get_verification_type_display()} was rejected: {reason}",
            link=f"/verification"
        )
        return Response({"status": "rejected"})

class VerificationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["post"]

    def perform_create(self, serializer):
        case_id = self.kwargs.get("case_pk")
        case = VerificationCase.objects.get(id=case_id, user=self.request.user)
        serializer.save(case=case)
        
        # If they were rejected and are uploading a new document, put them back in the queue
        if case.status == "REJECTED":
            case.status = "PENDING"
            case.rejection_reason = ""
            case.save()

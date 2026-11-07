
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from apps.properties.models import Listing
from .models import CreditTransaction
from .serializers import WalletSerializer, CreditTransactionSerializer
from . import services

class WalletViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def list(self, request):
        wallet = services.get_or_create_wallet(request.user)
        return Response(self.get_serializer(wallet).data)

    @action(detail=False, methods=["post"])
    def buy(self, request):
        amount = int(request.data.get("amount", 10))
        phone = request.data.get("phone_number", "")
        tx = services.initiate_credit_purchase(request.user, amount, phone)
        return Response({"reference": tx.reference, "status": tx.status})

    @action(detail=False, methods=["post"])
    def mock_webhook(self, request):
        # In production, this is a public endpoint called by MTN/Airtel
        reference = request.data.get("reference")
        success = request.data.get("success", True)
        success = services.process_payment_webhook(reference, success)
        return Response({"processed": success})

class UnlockViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"])
    def unlock(self, request):
        listing_id = request.data.get("listing_id")
        try:
            listing = Listing.objects.get(id=listing_id)
            services.unlock_listing_contact(request.user, listing)
            return Response({"status": "unlocked"})
        except ValidationError as e:
            return Response({"detail": str(e.message)}, status=status.HTTP_400_BAD_REQUEST)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=status.HTTP_404_NOT_FOUND)

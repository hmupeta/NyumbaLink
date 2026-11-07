from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import LandlordPaymentSettings, PaymentTransaction
from .serializers import LandlordSettingsSerializer, PaymentTransactionSerializer
from .services.providers import PROVIDERS
from . import encryption
import uuid

class PaymentSettingsViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LandlordSettingsSerializer

    def get_object(self):
        obj, _ = LandlordPaymentSettings.objects.get_or_create(landlord=self.request.user)
        return obj

    def list(self, request):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def stripe_connect(self, request):
        """Creates a Stripe Express account + onboarding link."""
        import stripe
        from django.conf import settings
        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        settings_obj = self.get_object()
        
        if not settings_obj.stripe_connected_account_id:
            account = stripe.Account.create(type="express")
            settings_obj.stripe_connected_account_id = account.id
            settings_obj.save()

        link = stripe.AccountLink.create(
            account=settings_obj.stripe_connected_account_id,
            refresh_url=request.data.get("refresh_url", "http://localhost:5173/settings"),
            return_url=request.data.get("return_url", "http://localhost:5173/settings"),
            type="account_onboarding"
        )
        return Response({"url": link.url})

    @action(detail=False, methods=["post"])
    def initiate_payment(self, request):
        provider_name = request.data.get("provider", "").upper()
        amount = request.data.get("amount", 0)
        currency = request.data.get("currency", "ZMW")
        phone = request.data.get("phone_number", "")
        return_url = request.data.get("return_url", "http://localhost:5173")
        listing_id = request.data.get("listing_id")

        if provider_name not in PROVIDERS:
            return Response({"detail": "Unknown provider"}, status=400)

        settings_obj = self.get_object()
        creds = {}
        for field in ("mtn_api_user", "mtn_api_key", "mtn_subscription_key", "mtn_target_environment",
                      "airtel_client_id", "airtel_client_secret",
                      "zamtel_merchant_id", "zamtel_api_key", "zamtel_api_base_url",
                      "stripe_connected_account_id",
                      "paypal_client_id", "paypal_client_secret"):
            raw = getattr(settings_obj, field, "")
            if field.endswith(("_secret", "_key", "_subscription_key")):
                raw = encryption.decrypt(raw) if raw else ""
            creds[field] = raw

        provider = PROVIDERS[provider_name](request.user, creds)
        result = provider.initiate(amount, currency, phone, return_url)

        if not result.success:
            return Response({"detail": result.error}, status=400)

        tx = PaymentTransaction.objects.create(
            landlord=request.user,
            listing_id=listing_id,
            provider=provider_name,
            reference=f"NYL-{uuid.uuid4().hex[:12].upper()}",
            amount=amount,
            currency=currency,
            status=PaymentTransaction.Status.PENDING,
            provider_transaction_id=result.reference,
            metadata={"return_url": return_url}
        )

        return Response({
            "transaction_id": str(tx.id),
            "reference": tx.reference,
            "redirect_url": result.redirect_url,
            "provider_reference": result.reference
        })

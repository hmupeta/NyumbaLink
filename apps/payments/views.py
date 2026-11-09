from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from apps.properties.models import Listing
from .models import ContactUnlock
from apps.integrations.models import LandlordPaymentSettings
import uuid

class UnlockViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"])
    def unlock(self, request):
        listing_id = request.data.get("listing_id")
        provider = request.data.get("provider", "MTN")
        phone = request.data.get("phone_number")
        
        try:
            listing = Listing.objects.get(id=listing_id)
            
            # 1. In production, you would trigger the PAYMENT TO NYUMBALINK ADMIN here.
            # Example: using the Platform's central MTN/Airtel account.
            # For this MVP, we simulate a successful payment to the platform.
            
            # 2. Create the unlock record so the user can see the phone number
            ContactUnlock.objects.get_or_create(user=request.user, listing=listing)
            
            # 3. Log the platform revenue (Optional: Create a PlatformTransaction model)
            # We will just return success for now.
            
            return Response({"status": "unlocked", "message": f"Platform fee paid via {provider}. Contact unlocked."})
            
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RentPaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"])
    def pay_rent(self, request):
        listing_id = request.data.get("listing_id")
        amount = request.data.get("amount")
        payment_type = request.data.get("type", "RENT") # RENT or DEPOSIT
        tenant_phone = request.data.get("phone_number")
        
        try:
            listing = Listing.objects.get(id=listing_id)
            landlord = listing.created_by
            
            # 1. Fetch the Landlord's Payment Settings
            try:
                settings = LandlordPaymentSettings.objects.get(landlord=landlord)
            except LandlordPaymentSettings.DoesNotExist:
                return Response({"detail": "Landlord has not configured payment settings yet."}, status=400)
                
            # 2. Trigger Payment to LANDLORD's Gateway here.
            # In production, you would use settings.mtn_api_key, settings.airtel_client_secret, etc.
            # to send an STK push to the tenant's phone, routing funds to the landlord.
            
            # For this MVP, we simulate a successful direct payment.
            
            return Response({
                "status": "success", 
                "message": f"{payment_type} of K{amount} paid directly to landlord via Mobile Money."
            })
            
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

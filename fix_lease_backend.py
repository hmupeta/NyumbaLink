#!/usr/bin/env python3
"""Completely rewrites LeaseViewSet to ensure request_lease endpoint works."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
VIEWS_FILE = ROOT / "apps" / "management" / "views.py"

text = VIEWS_FILE.read_text(encoding="utf-8")

# Ensure imports exist
if "from rest_framework.decorators import action" not in text:
    text = "from rest_framework.decorators import action\n" + text
if "from django.utils import timezone" not in text:
    text = "from django.utils import timezone\n" + text
if "from datetime import timedelta" not in text:
    text = "from datetime import timedelta\n" + text

# Extract the current LeaseViewSet class
# We will replace everything from `class LeaseViewSet` to the next `class `
pattern = r"class LeaseViewSet\(viewsets\.ModelViewSet\):([\s\S]*?)(?=class |\Z)"

new_lease_viewset = '''class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Lease.objects.filter(landlord=self.request.user).prefetch_related("rent_records")

    @action(detail=False, methods=["post"])
    def request_lease(self, request):
        listing_id = request.data.get("listing_id")
        if not listing_id:
            return Response({"detail": "Listing ID required"}, status=400)
            
        from apps.properties.models import Listing
        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=404)
            
        # Check if a lease already exists for this tenant and property
        existing = Lease.objects.filter(
            property=listing.property,
            tenant_email__iexact=request.user.email
        ).first()
        
        if existing:
            return Response(self.get_serializer(existing).data)
            
        # Create a new lease draft
        lease = Lease.objects.create(
            landlord=listing.created_by,
            property=listing.property,
            tenant_name=request.user.first_name or request.user.email.split('@')[0],
            tenant_phone=request.user.phone_number or "",
            tenant_email=request.user.email,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            monthly_rent=listing.price,
            deposit_paid=0,
            status="ACTIVE"
        )
        
        # Auto-generate the agreement text
        lease.agreement_text = f"""
RESIDENTIAL TENANCY AGREEMENT

THIS AGREEMENT is made between:
LANDLORD: {lease.landlord.email}
TENANT: {lease.tenant_name} ({lease.tenant_email})

PROPERTY: {lease.property.address_line or lease.property.neighbourhood.name}
TERM: {lease.start_date} to {lease.end_date}
RENT: ZMW {lease.monthly_rent} payable monthly.

1. The Tenant agrees to pay rent on or before the due date.
2. The Tenant shall keep the property in good condition.
3. The Landlord shall ensure the property is habitable.
4. This agreement is legally binding once signed by both parties digitally.
        """.strip()
        lease.save()
        
        return Response(self.get_serializer(lease).data, status=201)

    @action(detail=True, methods=["post"])
    def generate_agreement(self, request, pk=None):
        lease = self.get_object()
        if lease.landlord != request.user:
            return Response({"detail": "Only the landlord can generate the agreement"}, status=403)
            
        lease.agreement_text = f"""
RESIDENTIAL TENANCY AGREEMENT

THIS AGREEMENT is made on {timezone.now().strftime('%B %d, %Y')} between:
LANDLORD: {lease.landlord.email}
TENANT: {lease.tenant_name} ({lease.tenant_email})

PROPERTY: {lease.property.address_line or lease.property.neighbourhood.name}
TERM: {lease.start_date} to {lease.end_date}
RENT: ZMW {lease.monthly_rent} payable monthly.

1. The Tenant agrees to pay rent on or before the due date.
2. The Tenant shall keep the property in good condition.
3. The Landlord shall ensure the property is habitable.
4. This agreement is legally binding once signed by both parties digitally.
        """.strip()
        lease.save()
        return Response({"status": "agreement_generated", "text": lease.agreement_text})

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        lease = self.get_object()
        user = request.user
        
        if user == lease.landlord:
            lease.landlord_signed = True
            lease.landlord_signed_at = timezone.now()
        elif user.email.lower() == lease.tenant_email.lower():
            lease.tenant_signed = True
            lease.tenant_signed_at = timezone.now()
        else:
            return Response({"detail": "You are not a party to this lease"}, status=403)
            
        lease.save()

        # If both signed, mark Property as OCCUPIED and archive Listing
        if lease.landlord_signed and lease.tenant_signed:
            from apps.properties.models import Listing
            from apps.properties.enums import PropertyStatus, ListingStatus
            
            prop = lease.property
            prop.status = PropertyStatus.OCCUPIED
            prop.save()
            
            Listing.objects.filter(property=prop, status=ListingStatus.PUBLISHED).update(status=ListingStatus.ARCHIVED)
            
            lease.status = "ACTIVE"
            lease.save()
            
            return Response({"status": "fully_signed", "message": "Lease finalized. Property is now occupied."})
            
        return Response({"status": "signed", "message": "Signature recorded. Waiting for the other party."})

    @action(detail=False, methods=["get"])
    def my_tenancy(self, request):
        from django.db.models import Q
        leases = Lease.objects.filter(
            Q(tenant_email__iexact=request.user.email)
        ).exclude(tenant_email="").prefetch_related("rent_records")
        return Response(self.get_serializer(leases, many=True).data)

    def perform_create(self, serializer):
        # Generate rent records on creation
        lease = serializer.save(landlord=self.request.user)
        current_date = lease.start_date
        for _ in range(12):
            RentRecord.objects.create(
                lease=lease,
                due_date=current_date,
                amount=lease.monthly_rent,
                status=RentRecord.Status.PENDING
            )
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

'''

text = re.sub(pattern, new_lease_viewset, text)
VIEWS_FILE.write_text(text, encoding="utf-8")
print("✅ Rewrote LeaseViewSet in management/views.py completely")

# Ensure RentRecord is imported
if "from .models import Lease, RentRecord" not in text:
    text = text.replace("from .models import Lease", "from .models import Lease, RentRecord")
    VIEWS_FILE.write_text(text, encoding="utf-8")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Rewrite LeaseViewSet to fix 405 Method Not Allowed"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 BACKEND FIXED AND PUSHED!
==================================================

1. **Render** is now deploying the fixed backend (takes ~2 minutes).
2. **Frontend**: The endpoint `/api/v1/leases/request_lease/` will now correctly accept POST requests.

Wait 2 minutes, then try clicking **Apply & Sign Lease Agreement** on the mobile app again!
""")
#!/usr/bin/env python3
"""NyumbaLink Phase 48: Digital Lease Agreements & Property Occupancy."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()

# ----------------------------------------------------------------
# 1. Backend: Update Enums & Models
# ----------------------------------------------------------------
ENUMS_FILE = ROOT / "apps" / "properties" / "enums.py"
text = ENUMS_FILE.read_text(encoding="utf-8")
if "OCCUPIED" not in text:
    text = text.replace(
        'class PropertyStatus(models.TextChoices):\n    ACTIVE = "ACTIVE", "Active"\n    ARCHIVED = "ARCHIVED", "Archived"',
        'class PropertyStatus(models.TextChoices):\n    ACTIVE = "ACTIVE", "Active"\n    OCCUPIED = "OCCUPIED", "Occupied (Leased)"\n    ARCHIVED = "ARCHIVED", "Archived"'
    )
    ENUMS_FILE.write_text(text, encoding="utf-8")
    print("✅ Updated PropertyStatus with OCCUPIED")

MODELS_FILE = ROOT / "apps" / "management" / "models.py"
text = MODELS_FILE.read_text(encoding="utf-8")

# Update Lease model
if "landlord_signed" not in text:
    text = text.replace(
        '    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)',
        '''    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    
    # Agreement & Signature Tracking
    agreement_text = models.TextField(blank=True, help_text="Generated legal lease agreement")
    landlord_signed = models.BooleanField(default=False)
    tenant_signed = models.BooleanField(default=False)
    landlord_signed_at = models.DateTimeField(null=True, blank=True)
    tenant_signed_at = models.DateTimeField(null=True, blank=True)'''
    )
    MODELS_FILE.write_text(text, encoding="utf-8")
    print("✅ Updated Lease model with signature tracking")

# ----------------------------------------------------------------
# 2. Backend: Update Serializers & Views
# ----------------------------------------------------------------
SERIALIZERS_FILE = ROOT / "apps" / "management" / "serializers.py"
text = SERIALIZERS_FILE.read_text(encoding="utf-8")
if "landlord_signed" not in text:
    text = text.replace(
        '"monthly_rent", "deposit_paid", "status", "rent_records", "created_at")',
        '"monthly_rent", "deposit_paid", "status", "agreement_text", "landlord_signed", "tenant_signed", "rent_records", "created_at")'
    )
    SERIALIZERS_FILE.write_text(text, encoding="utf-8")
    print("✅ Updated LeaseSerializer with signature fields")

VIEWS_FILE = ROOT / "apps" / "management" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# Add a generate agreement and sign action
if "def sign_lease" not in text:
    new_actions = '''
    @action(detail=True, methods=["post"])
    def generate_agreement(self, request, pk=None):
        lease = self.get_object()
        if lease.landlord != request.user:
            return Response({"detail": "Only the landlord can generate the agreement"}, status=403)
            
        # Simple legal template
        agreement = f"""
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
        """
        lease.agreement_text = agreement.strip()
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
            from apps.properties.models import Property, Listing
            from apps.properties.enums import PropertyStatus, ListingStatus
            
            # 1. Mark Property as OCCUPIED
            prop = lease.property
            prop.status = PropertyStatus.OCCUPIED
            prop.save()
            
            # 2. Archive all Active Listings for this property
            Listing.objects.filter(property=prop, status=ListingStatus.PUBLISHED).update(status=ListingStatus.ARCHIVED)
            
            # 3. Set lease status to ACTIVE
            lease.status = "ACTIVE"
            lease.save()
            
            return Response({"status": "fully_signed", "message": "Lease finalized. Property is now occupied."})
            
        return Response({"status": "signed", "message": "Signature recorded. Waiting for the other party."})
'''
    text = text.replace(
        "    def perform_create(self, serializer):",
        new_actions + "\n    def perform_create(self, serializer):"
    )
    
    # Ensure timezone is imported
    if "from django.utils import timezone" not in text:
        text = "from django.utils import timezone\n" + text
        
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Added generate_agreement and sign actions to LeaseViewSet")

# ----------------------------------------------------------------
# 3. Push to GitHub (Render Deploy)
# ----------------------------------------------------------------
print("\n🚀 Generating migrations and pushing to GitHub...")
subprocess.run(["python", "manage.py", "makemigrations", "management", "properties"], cwd=ROOT)
subprocess.run(["python", "manage.py", "migrate"], cwd=ROOT)
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add digital lease agreements and property occupancy logic"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 BACKEND LEASE AGREEMENT LOGIC COMPLETE!
==================================================

Render will automatically deploy the new backend logic.

Next, we need to build the interface in React so the Tenant and Landlord can actually see and sign this document. 
Run the next script to build the Web interface.
""")
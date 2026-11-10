#!/usr/bin/env python3
"""Replaces the backend payment logic to use dynamic Landlord MTN credentials."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

# ----------------------------------------------------------------
# 1. momo_service.py
# ----------------------------------------------------------------
MOMO_SERVICE = '''
import os
import time
import logging
import threading
from mtnmomoapi.collection import Collection
from apps.integrations.models import LandlordPaymentSettings
from apps.integrations.encryption import decrypt

logger = logging.getLogger(__name__)

# A lock to prevent concurrent requests from overwriting env vars
_env_lock = threading.Lock()

def get_landlord_credentials(landlord):
    """Fetches and decrypts the landlord's MTN credentials."""
    try:
        settings = LandlordPaymentSettings.objects.get(landlord=landlord)
        if not settings.mtn_api_user or not settings.mtn_api_key:
            raise ValueError("Landlord has not configured MTN MoMo credentials.")
        
        return {
            "user_id": settings.mtn_api_user,
            "api_key": decrypt(settings.mtn_api_key),
            "subscription_key": decrypt(settings.mtn_subscription_key),
            "environment": settings.mtn_target_environment or "sandbox",
        }
    except LandlordPaymentSettings.DoesNotExist:
        raise ValueError("Landlord payment settings not found.")

def _set_env(creds):
    """Sets the environment variables for the mtnmomoapi library."""
    os.environ["COLLECTION_USER_ID"] = creds["user_id"]
    os.environ["COLLECTION_API_KEY"] = creds["api_key"]
    os.environ["COLLECTION_PRIMARY_KEY"] = creds["subscription_key"]
    os.environ["MTN_ENVIRONMENT"] = creds["environment"]
    # MTN Sandbox only accepts EUR
    os.environ["CURRENCY"] = "EUR" if creds["environment"] == "sandbox" else "ZMW"
    os.environ["CALLBACK_HOST"] = "https://nyumbalink-backend-eaw2.onrender.com"

def _clear_env():
    """Clears the environment variables to prevent credential leaks."""
    for key in ["COLLECTION_USER_ID", "COLLECTION_API_KEY", "COLLECTION_PRIMARY_KEY", "MTN_ENVIRONMENT", "CURRENCY"]:
        os.environ.pop(key, None)

def initiate_momo_payment(landlord, amount, phone_number, reference_id):
    """Initiates a RequestToPay transaction using the Landlord's credentials."""
    creds = get_landlord_credentials(landlord)
    
    with _env_lock:
        _set_env(creds)
        try:
            collection = Collection()
            response = collection.requestToPay(
                amount=str(amount),
                phone_number=phone_number, # Format: 260966456787
                external_id=reference_id,
                payee_note="NyumbaLink Payment",
                payer_message="Please confirm your payment on your handset."
            )
            return response.get("transaction_ref")
        except Exception as e:
            logger.error(f"MTN RequestToPay failed for landlord {landlord.email}: {e}")
            raise Exception(f"Payment initiation failed: {e}")
        finally:
            _clear_env()

def check_momo_status(landlord, transaction_ref):
    """Checks the status of a transaction using the Landlord's credentials."""
    creds = get_landlord_credentials(landlord)
    
    with _env_lock:
        _set_env(creds)
        try:
            collection = Collection()
            status_data = collection.getTransactionStatus(transaction_ref)
            return status_data.get("status")
        except Exception as e:
            logger.error(f"MTN Status Check failed: {e}")
            return "FAILED"
        finally:
            _clear_env()
'''

# ----------------------------------------------------------------
# 2. views.py
# ----------------------------------------------------------------
PAYMENT_VIEWS = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from apps.properties.models import Listing
from .models import PaymentTransaction
from .momo_service import initiate_momo_payment, check_momo_status
import uuid

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    listing_id = request.data.get('listing_id')
    amount = request.data.get('amount')
    phone = request.data.get('phone_number')
    
    if not all([listing_id, amount, phone]):
        return Response({"error": "Missing required fields"}, status=400)
    
    try:
        listing = Listing.objects.get(id=listing_id)
        landlord = listing.created_by # The payment goes to the landlord!
    except Listing.DoesNotExist:
        return Response({"error": "Listing not found"}, status=404)

    reference = f"NYL-{uuid.uuid4().hex[:8].upper()}"
    
    # 1. Create a local transaction record
    tx = PaymentTransaction.objects.create(
        landlord=landlord,
        listing=listing,
        amount=amount,
        currency='ZMW',
        reference=reference,
        status=PaymentTransaction.Status.PENDING,
        metadata={'tenant_phone': phone, 'initiated_by': request.user.email}
    )
    
    # 2. Initiate payment with MTN using the LANDLORD'S credentials
    try:
        momo_ref = initiate_momo_payment(landlord, amount, phone, reference)
        tx.provider_transaction_id = momo_ref
        tx.save()
        return Response({"reference": reference, "momo_ref": momo_ref})
    except Exception as e:
        tx.status = PaymentTransaction.Status.FAILED
        tx.save()
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, reference):
    try:
        tx = PaymentTransaction.objects.get(reference=reference)
        if tx.status == PaymentTransaction.Status.PENDING and tx.provider_transaction_id:
            # Poll MTN using the LANDLORD'S credentials
            status = check_momo_status(tx.landlord, tx.provider_transaction_id)
            
            if status == 'SUCCESSFUL':
                tx.status = PaymentTransaction.Status.SUCCESS
                tx.save()
            elif status == 'FAILED':
                tx.status = PaymentTransaction.Status.FAILED
                tx.save()
                
        return Response({"status": tx.status})
    except PaymentTransaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def momo_callback(request):
    """Webhook endpoint for MTN to send the final status."""
    data = request.data
    momo_ref = data.get('financialTransactionId') or data.get('externalId')
    status = data.get('status')
    
    if status == 'SUCCESSFUL':
        try:
            tx = PaymentTransaction.objects.get(provider_transaction_id=momo_ref)
            tx.status = PaymentTransaction.Status.SUCCESS
            tx.save()
        except PaymentTransaction.DoesNotExist:
            pass
    return Response(status=200)
'''

# ----------------------------------------------------------------
# 3. urls.py (Appended)
# ----------------------------------------------------------------
PAYMENT_URLS = '''
from django.urls import path
from . import views

urlpatterns = [
    path('initiate/', views.initiate_payment, name='initiate-payment'),
    path('status/<str:reference>/', views.payment_status, name='payment-status'),
    path('callback/', views.momo_callback, name='momo-callback'),
]
'''

# ----------------------------------------------------------------
# 4. Write files
# ----------------------------------------------------------------
print("📝 Writing backend files...")

MOMO_FILE = ROOT / "apps" / "payments" / "momo_service.py"
MOMO_FILE.write_text(MOMO_SERVICE.strip() + "\n", encoding="utf-8")
print(f"  ✅ Created {MOMO_FILE.relative_to(ROOT)}")

VIEWS_FILE = ROOT / "apps" / "payments" / "views.py"
VIEWS_FILE.write_text(PAYMENT_VIEWS.strip() + "\n", encoding="utf-8")
print(f"  ✅ Updated {VIEWS_FILE.relative_to(ROOT)}")

URLS_FILE = ROOT / "apps" / "payments" / "urls.py"
text = URLS_FILE.read_text(encoding="utf-8") if URLS_FILE.exists() else ""
if "initiate_payment" not in text:
    URLS_FILE.write_text(PAYMENT_URLS.strip() + "\n", encoding="utf-8")
    print(f"  ✅ Updated {URLS_FILE.relative_to(ROOT)}")

# ----------------------------------------------------------------
# 5. Run Migrations
# ----------------------------------------------------------------
print("\n📦 Running makemigrations & migrate...")
subprocess.run([sys.executable, "manage.py", "makemigrations", "payments"], cwd=ROOT)
subprocess.run([sys.executable, "manage.py", "migrate"], cwd=ROOT)

# ----------------------------------------------------------------
# 6. Push to Git
# ----------------------------------------------------------------
print("\n🚀 Pushing to GitHub...")
subprocess.run(["git", "add", "apps/payments/"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Dynamic MTN MoMo payments using Landlord credentials"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 BACKEND PAYMENT LOGIC REPLACED!
==================================================

Render will automatically redeploy the backend.

### How it works now:
1. The Tenant clicks "Pay Rent".
2. Flutter sends `listing_id`, `amount`, and `phone_number` to `/api/v1/payments/initiate/`.
3. Backend finds the Listing → Landlord → fetches Landlord's encrypted MTN keys.
4. Backend decrypts keys, sets them in the environment, and calls MTN's `RequestToPay`.
5. MTN sends a USSD prompt to the Tenant's phone.
6. Flutter polls `/api/v1/payments/status/<reference>/` every 5 seconds.
7. When the Tenant enters their PIN, MTN updates the status, and the backend marks the transaction as `SUCCESS`.
""")
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

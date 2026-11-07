"""Simple Fernet encryption for storing API secrets at rest."""
import base64
import os
from cryptography.fernet import Fernet
from django.conf import settings

def _get_key():
    key = getattr(settings, "ENCRYPTION_KEY", None)
    if not key:
        # Derive from SECRET_KEY for development; set ENCRYPTION_KEY in production
        import hashlib
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return key

def encrypt(value: str) -> str:
    if not value:
        return ""
    f = Fernet(_get_key())
    return f.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    if not value:
        return ""
    f = Fernet(_get_key())
    return f.decrypt(value.encode()).decode()

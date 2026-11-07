import requests
import stripe
from django.conf import settings
from mtnmomoapi.collection import Collection

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")

class PaymentResult:
    def __init__(self, success, reference="", redirect_url="", error=""):
        self.success = success
        self.reference = reference
        self.redirect_url = redirect_url
        self.error = error

class BaseProvider:
    def __init__(self, landlord, credentials):
        self.landlord = landlord
        self.creds = credentials

    def initiate(self, amount, currency, phone_number="", return_url=""):
        raise NotImplementedError

    def verify_webhook(self, payload, headers):
        return True  # Override per provider

class MTNProvider(BaseProvider):
    def initiate(self, amount, currency, phone_number="", return_url=""):
        try:
            import os
            os.environ["MTN_ENVIRONMENT"] = self.creds.get("mtn_target_environment", "mtnzambia")
            os.environ["COLLECTION_PRIMARY_KEY"] = self.creds.get("mtn_api_key", "")
            os.environ["COLLECTION_USER_ID"] = self.creds.get("mtn_api_user", "")
            os.environ["COLLECTION_API_SECRET"] = self.creds.get("mtn_subscription_key", "")
            os.environ["CALLBACK_HOST"] = return_url.rsplit("/", 1)[0]
            os.environ["CURRENCY"] = currency

            collection = Collection()
            response = collection.requestToPay(
                amount=str(int(amount)),
                phone_number=phone_number,
                external_id=f"nyumbalink_{self.landlord.id}",
                payee_note="NyumbaLink Rent Payment",
                payer_message="Confirm payment on your handset"
            )
            return PaymentResult(True, reference=response.get("transaction_ref"))
        except Exception as e:
            return PaymentResult(False, error=str(e))

class AirtelProvider(BaseProvider):
    def initiate(self, amount, currency, phone_number="", return_url=""):
        try:
            token_url = "https://openapi.airtel.africa/auth/oauth2/token"
            payload = {
                "client_id": self.creds.get("airtel_client_id", ""),
                "client_secret": self.creds.get("airtel_client_secret", ""),
                "grant_type": "client_credentials"
            }
            token_res = requests.post(token_url, json=payload, timeout=15)
            token_res.raise_for_status()
            token = token_res.json()["access_token"]

            url = "https://openapi.airtel.africa/merchant/v1/payments/"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Country": "ZM",
                "X-Currency": currency
            }
            body = {
                "reference": f"nyumbalink_{self.landlord.id}",
                "subscriber": {"country": "ZM", "currency": currency, "msisdn": phone_number},
                "transaction": {"amount": float(amount), "country": "ZM", "currency": currency, "id": str(self.landlord.id)}
            }
            res = requests.post(url, json=body, headers=headers, timeout=15)
            res.raise_for_status()
            data = res.json()
            return PaymentResult(True, reference=data.get("data", {}).get("transaction", {}).get("id", ""))
        except Exception as e:
            return PaymentResult(False, error=str(e))

class ZamtelProvider(BaseProvider):
    def initiate(self, amount, currency, phone_number="", return_url=""):
        try:
            base = self.creds.get("zamtel_api_base_url", "https://api.zamtel.com/kwacha")
            url = f"{base}/payments"
            headers = {"Authorization": f"Bearer {self.creds.get('zamtel_api_key', '')}"}
            body = {
                "merchant_id": self.creds.get("zamtel_merchant_id", ""),
                "amount": str(amount),
                "currency": currency,
                "phone_number": phone_number,
                "reference": f"nyumbalink_{self.landlord.id}"
            }
            res = requests.post(url, json=body, headers=headers, timeout=15)
            res.raise_for_status()
            data = res.json()
            return PaymentResult(True, reference=data.get("transaction_id", ""))
        except Exception as e:
            return PaymentResult(False, error=str(e))

class StripeProvider(BaseProvider):
    def initiate(self, amount, currency, phone_number="", return_url=""):
        try:
            account_id = self.creds.get("stripe_connected_account_id")
            if not account_id:
                return PaymentResult(False, error="Stripe account not connected.")

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {"name": "NyumbaLink Rent"},
                        "unit_amount": int(float(amount) * 100)
                    },
                    "quantity": 1
                }],
                mode="payment",
                success_url=return_url + "?status=success",
                cancel_url=return_url + "?status=cancel",
                stripe_account=account_id
            )
            return PaymentResult(True, reference=session.id, redirect_url=session.url)
        except Exception as e:
            return PaymentResult(False, error=str(e))

class PayPalProvider(BaseProvider):
    def initiate(self, amount, currency, phone_number="", return_url=""):
        try:
            base = "https://api-m.paypal.com" if not settings.DEBUG else "https://api-m.sandbox.paypal.com"
            auth = (self.creds.get("paypal_client_id"), self.creds.get("paypal_client_secret"))
            token_res = requests.post(
                f"{base}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=auth, timeout=15
            )
            token_res.raise_for_status()
            token = token_res.json()["access_token"]

            res = requests.post(
                f"{base}/v2/checkout/orders",
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{"amount": {"currency_code": currency, "value": str(amount)}}],
                    "application_context": {"return_url": return_url, "cancel_url": return_url}
                },
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=15
            )
            res.raise_for_status()
            data = res.json()
            approve_link = next((l["href"] for l in data["links"] if l["rel"] == "approve"), "")
            return PaymentResult(True, reference=data["id"], redirect_url=approve_link)
        except Exception as e:
            return PaymentResult(False, error=str(e))

PROVIDERS = {
    "MTN": MTNProvider,
    "AIRTEL": AirtelProvider,
    "ZAMTEL": ZamtelProvider,
    "STRIPE": StripeProvider,
    "PAYPAL": PayPalProvider,
}

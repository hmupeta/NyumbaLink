from rest_framework import serializers
from .models import LandlordPaymentSettings, PaymentTransaction
from . import encryption

class LandlordSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordPaymentSettings
        exclude = ("landlord", "created_at", "updated_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Never return raw secrets
        for field in ("mtn_api_key", "mtn_subscription_key", "airtel_client_secret", "zamtel_api_key", "paypal_client_secret"):
            if data.get(field):
                data[field] = "••••••••"
        return data

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            if field.endswith("_secret") or field.endswith("_key") or field.endswith("_subscription_key"):
                if value and not value.startswith("•"):
                    setattr(instance, field, encryption.encrypt(value))
            else:
                setattr(instance, field, value)
        instance.save()
        return instance

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"
        read_only_fields = ("landlord", "status", "reference", "provider_transaction_id")

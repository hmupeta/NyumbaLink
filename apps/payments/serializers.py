
from rest_framework import serializers
from .models import Wallet, CreditTransaction

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("balance",)

class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = ("id", "transaction_type", "amount", "status", "description", "created_at")

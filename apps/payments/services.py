
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Wallet, CreditTransaction, ContactUnlock

UNLOCK_COST = 5

def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet

@transaction.atomic
def initiate_credit_purchase(user, amount: int, phone_number: str):
    """Creates a pending transaction. In production, this calls the PSP API."""
    wallet = get_or_create_wallet(user)
    tx = CreditTransaction.objects.create(
        wallet=wallet,
        transaction_type=CreditTransaction.Type.PURCHASE,
        amount=amount,
        status=CreditTransaction.Status.PENDING,
        description=f"Mobile Money Purchase from {phone_number}",
        reference=f"MOCK-{user.id.hex[:8]}-{amount}"
    )
    return tx

@transaction.atomic
def process_payment_webhook(reference: str, success: bool):
    """Mocks the PSP sending a webhook to confirm payment."""
    try:
        tx = CreditTransaction.objects.select_for_update().get(reference=reference)
        if tx.status != CreditTransaction.Status.PENDING:
            return False # Already processed
        
        if success:
            tx.status = CreditTransaction.Status.COMPLETED
            wallet = tx.wallet
            wallet.balance += tx.amount
            wallet.save()
        else:
            tx.status = CreditTransaction.Status.FAILED
        
        tx.save()
        return True
    except CreditTransaction.DoesNotExist:
        return False

@transaction.atomic
def unlock_listing_contact(user, listing):
    wallet = Wallet.objects.select_for_update().get(user=user)
    
    # Check if already unlocked
    if ContactUnlock.objects.filter(user=user, listing=listing).exists():
        return True

    if wallet.balance < UNLOCK_COST:
        raise ValidationError("Insufficient credits.")

    # Deduct credits
    wallet.balance -= UNLOCK_COST
    wallet.save()

    # Log transaction
    CreditTransaction.objects.create(
        wallet=wallet,
        transaction_type=CreditTransaction.Type.UNLOCK,
        amount=-UNLOCK_COST,
        status=CreditTransaction.Status.COMPLETED,
        description=f"Unlocked: {listing.title}"
    )

    # Create unlock record
    ContactUnlock.objects.create(user=user, listing=listing)
    return True

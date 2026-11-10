from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from apps.properties.models import Listing
from apps.integrations.models import PaymentTransaction
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

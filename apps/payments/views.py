from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from apps.properties.models import Listing
from apps.management.models import RentRecord
from apps.integrations.models import PaymentTransaction
from .momo_service import initiate_momo_payment, check_momo_status
import uuid

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    rent_record_id = request.data.get('rent_record_id')
    listing_id = request.data.get('listing_id')
    amount = request.data.get('amount')
    phone = request.data.get('phone_number')
    
    if not all([amount, phone]):
        return Response({"error": "Missing required fields"}, status=400)

    landlord = None
    metadata = {'tenant_phone': phone, 'initiated_by': request.user.email}

    if rent_record_id:
        try:
            record = RentRecord.objects.get(id=rent_record_id)
            landlord = record.lease.landlord
            metadata['rent_record_id'] = str(record.id)
            # Use the exact amount from the record to prevent tampering
            amount = record.amount 
        except RentRecord.DoesNotExist:
            return Response({"error": "Rent record not found"}, status=404)
    elif listing_id:
        try:
            listing = Listing.objects.get(id=listing_id)
            landlord = listing.created_by
            metadata['listing_id'] = str(listing.id)
        except Listing.DoesNotExist:
            return Response({"error": "Listing not found"}, status=404)
    else:
        return Response({"error": "Either rent_record_id or listing_id is required"}, status=400)

    reference = f"NYL-{uuid.uuid4().hex[:8].upper()}"
    
    tx = PaymentTransaction.objects.create(
        landlord=landlord,
        amount=amount,
        currency='ZMW',
        reference=reference,
        status=PaymentTransaction.Status.PENDING,
        metadata=metadata
    )
    
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
            status = check_momo_status(tx.landlord, tx.provider_transaction_id)
            
            if status == 'SUCCESSFUL':
                tx.status = PaymentTransaction.Status.SUCCESS
                tx.save()
                
                # If this payment was for a rent record, mark it PAID
                rent_record_id = tx.metadata.get('rent_record_id')
                if rent_record_id:
                    from django.utils import timezone
                    RentRecord.objects.filter(id=rent_record_id).update(
                        status=RentRecord.Status.PAID,
                        paid_date=timezone.now().date()
                    )
            elif status == 'FAILED':
                tx.status = PaymentTransaction.Status.FAILED
                tx.save()
                
        return Response({"status": tx.status})
    except PaymentTransaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)

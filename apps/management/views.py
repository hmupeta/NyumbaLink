from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Lease, RentRecord
from .serializers import LeaseSerializer, RentRecordSerializer

class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Lease.objects.filter(landlord=self.request.user).prefetch_related("rent_records")


    @action(detail=False, methods=["get"])
    def my_tenancy(self, request):
        """Returns all active leases where the requesting user is the tenant."""
        from django.db.models import Q
        leases = Lease.objects.filter(
            Q(tenant_email__iexact=request.user.email) |
            Q(tenant_email="")
        ).exclude(tenant_email="").prefetch_related("rent_records")
        return Response(self.get_serializer(leases, many=True).data)


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

    def perform_create(self, serializer):
        # When a lease is created, we automatically generate the first 12 rent records
        lease = serializer.save(landlord=self.request.user)
        
        # Simple logic to generate monthly rent records for the next 12 months
        import datetime
        current_date = lease.start_date
        for _ in range(12):
            RentRecord.objects.create(
                lease=lease,
                due_date=current_date,
                amount=lease.monthly_rent,
                status=RentRecord.Status.PENDING
            )
            # Add one month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

class RentRecordViewSet(viewsets.ModelViewSet):
    serializer_class = RentRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RentRecord.objects.filter(lease__landlord=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        record = self.get_object()
        import datetime
        record.status = RentRecord.Status.PAID
        record.paid_date = datetime.date.today()
        record.save()
        return Response({"status": "paid"})

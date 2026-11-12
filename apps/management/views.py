from apps.properties.models import Listing
from datetime import timedelta

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q

from .models import Lease, RentRecord
from .serializers import LeaseSerializer, RentRecordSerializer


class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Lease.objects.filter(
            Q(landlord=user) | Q(tenant_email__iexact=user.email)
        ).prefetch_related("rent_records").distinct()

    @action(detail=False, methods=["post"])
    def request_lease(self, request):
        listing_id = request.data.get("listing_id")
        if not listing_id:
            return Response({"detail": "Listing ID required"}, status=400)

        from apps.properties.models import Listing
        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=404)

        # Return an existing lease if one already exists
        existing = Lease.objects.filter(
            property=listing.property,
            tenant_email__iexact=request.user.email
        ).first()

        if existing:
            return Response(self.get_serializer(existing).data)

        lease = Lease.objects.create(
            landlord=listing.created_by,
            property=listing.property,
            tenant_name=request.user.first_name or request.user.email.split('@')[0],
            tenant_phone=request.user.phone_number or "",
            tenant_email=request.user.email,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            monthly_rent=listing.price,
            deposit_paid=0,
            status="ACTIVE",
        )

        lease.agreement_text = f"""
RESIDENTIAL TENANCY AGREEMENT

THIS AGREEMENT is made between:
LANDLORD: {lease.landlord.email}
TENANT: {lease.tenant_name} ({lease.tenant_email})

PROPERTY: {lease.property.address_line or lease.property.neighbourhood.name}
TERM: {lease.start_date} to {lease.end_date}
RENT: ZMW {lease.monthly_rent} payable monthly.

1. The Tenant agrees to pay rent on or before the due date.
2. The Tenant shall keep the property in good condition.
3. The Landlord shall ensure the property is habitable.
4. This agreement is legally binding once signed by both parties digitally.
        """.strip()
        lease.save()

        return Response(self.get_serializer(lease).data, status=201)

    @action(detail=True, methods=["post"])
    def generate_agreement(self, request, pk=None):
        lease = self.get_object()
        if lease.landlord != request.user:
            return Response({"detail": "Only the landlord can generate the agreement"}, status=403)

        lease.agreement_text = f"""
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
        """.strip()
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

        if lease.landlord_signed and lease.tenant_signed:
            from apps.properties.enums import ListingStatus, PropertyStatus

            prop = lease.property
            prop.status = PropertyStatus.OCCUPIED
            prop.save()

            Listing.objects.filter(
                property=prop, status=ListingStatus.PUBLISHED
            ).update(status=ListingStatus.ARCHIVED)

            lease.status = "ACTIVE"
            lease.save()

            return Response({
                "status": "fully_signed",
                "message": "Lease finalized. Property is now occupied.",
            })

        return Response({
            "status": "signed",
            "message": "Signature recorded. Waiting for the other party.",
        })

    @action(detail=False, methods=["get"])
    def my_tenancy(self, request):
        leases = Lease.objects.filter(
            tenant_email__iexact=request.user.email
        ).exclude(tenant_email="").prefetch_related("rent_records")
        return Response(self.get_serializer(leases, many=True).data)


    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        from django.http import HttpResponse
        from apps.payments.pdf_service import generate_lease_pdf
        lease = self.get_object()
        
        if not (lease.landlord_signed or lease.tenant_signed):
            return Response({"detail": "Lease has not been signed yet."}, status=400)
            
        pdf_bytes = generate_lease_pdf(lease)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="lease-{str(lease.id)[:8]}.pdf"'
        return response

    def perform_create(self, serializer):
        lease = serializer.save(landlord=self.request.user)
        current_date = lease.start_date
        for _ in range(12):
            RentRecord.objects.create(
                lease=lease,
                due_date=current_date,
                amount=lease.monthly_rent,
                status=RentRecord.Status.PENDING,
            )
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)


class RentRecordViewSet(viewsets.ModelViewSet):
    serializer_class = RentRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RentRecord.objects.filter(lease__landlord=self.request.user)


    @action(detail=True, methods=["get"])
    def download_invoice(self, request, pk=None):
        from django.http import HttpResponse
        from apps.payments.pdf_service import generate_invoice_pdf
        record = self.get_object()
        
        pdf_bytes = generate_invoice_pdf(record)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="invoice-{str(record.id)[:8]}.pdf"'
        return response

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        record = self.get_object()
        record.status = RentRecord.Status.PAID
        record.paid_date = timezone.now().date()
        record.save()
        return Response({"status": "paid"})

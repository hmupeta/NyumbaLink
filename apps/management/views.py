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

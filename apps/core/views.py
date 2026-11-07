from django.db import connection
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum
from django.contrib.auth import get_user_model
from apps.properties.models import Listing, Report
from apps.payments.models import CreditTransaction, ContactUnlock
from apps.verification.models import VerificationCase

User = get_user_model()


def health(request):
    checks = {"database": "ok"}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        checks["database"] = "error"
        checks["detail"] = str(exc)
        status = 503
    return JsonResponse({"status": "ok" if status == 200 else "error", "checks": checks}, status=status)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Platform Stats
        total_users = User.objects.count()
        total_active_listings = Listing.objects.filter(status="PUBLISHED").count()
        
        # Moderation Alerts
        pending_listings = Listing.objects.filter(status="SUBMITTED").count()
        pending_kyc = VerificationCase.objects.filter(status="PENDING").count()
        open_reports = Report.objects.filter(status="OPEN").count()

        # Financial Stats (Sum of successful credit purchases)
        credits_sold = CreditTransaction.objects.filter(
            transaction_type="PURCHASE", status="COMPLETED"
        ).aggregate(total=Sum("amount"))["total"] or 0
        
        total_unlocks = ContactUnlock.objects.count()

        # Recent Activity
        recent_users = list(User.objects.order_by("-date_joined")[:5].values("email", "date_joined"))
        recent_listings = list(Listing.objects.order_by("-created_at")[:5].values("title", "price", "currency", "created_at"))

        return Response({
            "stats": {
                "total_users": total_users,
                "active_listings": total_active_listings,
                "credits_sold": credits_sold,
                "total_unlocks": total_unlocks,
            },
            "alerts": {
                "pending_listings": pending_listings,
                "pending_kyc": pending_kyc,
                "open_reports": open_reports,
            },
            "recent_users": recent_users,
            "recent_listings": recent_listings,
        })

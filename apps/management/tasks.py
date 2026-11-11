
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import logging

from .models import RentRecord

logger = logging.getLogger(__name__)

@shared_task
def check_rent_due_dates():
    """
    Runs daily via Celery Beat.
    1. Sends reminders 3 days before rent is due.
    2. Marks rent as OVERDUE if past due date and not paid, and sends warnings.
    """
    today = timezone.now().date()
    
    # --- 1. Reminders (3 days before due) ---
    upcoming_date = today + timedelta(days=3)
    upcoming_rents = RentRecord.objects.filter(
        status=RentRecord.Status.PENDING,
        due_date=upcoming_date
    ).select_related('lease__landlord')

    for record in upcoming_rents:
        lease = record.lease
        if not lease.tenant_email:
            continue
            
        subject = f"Rent Reminder: {lease.property.neighbourhood.name}"
        message = f"""
Hello {lease.tenant_name},

This is a friendly reminder that your rent of ZMW {record.amount} for {lease.property.neighbourhood.name} is due on {record.due_date}.

Please log in to NyumbaLink to make your payment.

— The NyumbaLink Team
        """.strip()
        
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [lease.tenant_email], fail_silently=True)
        logger.info(f"Sent rent reminder to {lease.tenant_email} for record {record.id}")

    # --- 2. Overdue Alerts (past due date) ---
    overdue_rents = RentRecord.objects.filter(
        status=RentRecord.Status.PENDING,
        due_date__lt=today
    ).select_related('lease__landlord')

    for record in overdue_rents:
        record.status = RentRecord.Status.OVERDUE
        record.save(update_fields=['status'])
        
        lease = record.lease
        
        # Notify Tenant
        if lease.tenant_email:
            subject = f"OVERDUE: Rent for {lease.property.neighbourhood.name}"
            message = f"""
Hello {lease.tenant_name},

Your rent of ZMW {record.amount} for {lease.property.neighbourhood.name} was due on {record.due_date} and is now marked as OVERDUE.

Please settle this immediately to avoid further action.

— The NyumbaLink Team
            """.strip()
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [lease.tenant_email], fail_silently=True)

        # Notify Landlord
        subject_ll = f"Tenant Rent Overdue: {lease.tenant_name}"
        message_ll = f"""
Hello,

Your tenant {lease.tenant_name} ({lease.tenant_email}) has not paid the rent of ZMW {record.amount} which was due on {record.due_date}.

Log in to NyumbaLink to view your dashboard.

— The NyumbaLink Team
        """.strip()
        send_mail(subject_ll, message_ll, settings.DEFAULT_FROM_EMAIL, [lease.landlord.email], fail_silently=True)
        
        logger.info(f"Marked record {record.id} as OVERDUE and notified parties.")
        
    return f"Processed {upcoming_rents.count()} reminders and {overdue_rents.count()} overdue alerts."

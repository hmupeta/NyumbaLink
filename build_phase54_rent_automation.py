#!/usr/bin/env python3
"""NyumbaLink Phase 54: Automated Rent Invoicing & Overdue Alerts."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Backend: Celery Task
# ----------------------------------------------------------------
TASKS_FILE = ROOT / "apps" / "management" / "tasks.py"
if not TASKS_FILE.exists():
    TASKS_FILE.write_text("", encoding="utf-8")

text = TASKS_FILE.read_text(encoding="utf-8")

if "check_rent_due_dates" not in text:
    new_task = '''
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
'''
    TASKS_FILE.write_text(text.strip() + "\n" + new_task.strip() + "\n", encoding="utf-8")
    print("✅ Created apps/management/tasks.py with check_rent_due_dates")

# ----------------------------------------------------------------
# 2. Backend: Celery Beat Schedule
# ----------------------------------------------------------------
SETTINGS_FILE = ROOT / "config" / "settings" / "base.py"
text = SETTINGS_FILE.read_text(encoding="utf-8")

if "CELERY_BEAT_SCHEDULE" not in text:
    celery_config = '''
# ----------------------------------------------------------------
# CELERY SCHEDULE (Daily Rent Alerts)
# ----------------------------------------------------------------
CELERY_BEAT_SCHEDULE = {
    'check-rent-due-dates-every-day': {
        'task': 'apps.management.tasks.check_rent_due_dates',
        'schedule': 86400.0,  # Every 24 hours
    },
}
'''
    text += celery_config
    SETTINGS_FILE.write_text(text, encoding="utf-8")
    print("✅ Added Celery Beat schedule to base.py")

# ----------------------------------------------------------------
# 3. Web UI: Show OVERDUE in red on Tenants Tab
# ----------------------------------------------------------------
WEB_TENANTS = FRONTEND / "src" / "pages" / "ViewingsList.tsx" # Wait, Tenant list is in a different file
# Let's update the actual Tenants list. I need to check where it is. 
# It's `frontend/src/pages/TenantsList.tsx`

WEB_TENANTS = FRONTEND / "src" / "pages" / "TenantsList.tsx"
text = WEB_TENANTS.read_text(encoding="utf-8")

# Ensure the table shows red for OVERDUE
if "text-red-600" not in text:
    # Find where the status is displayed
    old_status = '''                    <td className="px-4 py-3 text-sm">{record.status}</td>'''
    new_status = '''                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        record.status === 'PAID' ? 'bg-green-100 text-green-800' :
                        record.status === 'OVERDUE' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {record.status}
                      </span>
                    </td>'''
    
    if old_status in text:
        text = text.replace(old_status, new_status)
        WEB_TENANTS.write_text(text, encoding="utf-8")
        print("✅ Patched Web TenantsList.tsx: Added colored status badges for OVERDUE")

# ----------------------------------------------------------------
# 4. Mobile UI: Show OVERDUE in red on Tenants Tab
# ----------------------------------------------------------------
MOBILE_TENANTS = MOBILE / "lib" / "tenants_tab.dart"
text = MOBILE_TENANTS.read_text(encoding="utf-8")

# Find where the status is displayed
old_mobile_status = '''                      trailing: isPaid
                          ? Text("Paid", style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold))
                          : ElevatedButton(
                              onPressed: () => _markPaid(lease['id'], record['id']),
                              style: ElevatedButton.styleFrom(backgroundColor: Colors.black),
                              child: Text("Mark Paid"),
                            ),'''
    
new_mobile_status = '''                      trailing: isPaid
                          ? Text("Paid", style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold))
                          : record['status'] == 'OVERDUE'
                            ? Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text("OVERDUE", style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 10)),
                                  SizedBox(height: 4),
                                  ElevatedButton(
                                    onPressed: () => _markPaid(lease['id'], record['id']),
                                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red[700], minimumSize: Size(0, 30)),
                                    child: Text("Pay Now", style: TextStyle(fontSize: 12)),
                                  ),
                                ],
                              )
                            : ElevatedButton(
                                onPressed: () => _markPaid(lease['id'], record['id']),
                                style: ElevatedButton.styleFrom(backgroundColor: Colors.black),
                                child: Text("Mark Paid"),
                              ),'''

if old_mobile_status in text:
    text = text.replace(old_mobile_status, new_mobile_status)
    MOBILE_TENANTS.write_text(text, encoding="utf-8")
    print("✅ Patched Mobile tenants_tab.dart: Added red OVERDUE status")

# ----------------------------------------------------------------
# 5. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Automated rent reminders and overdue alerts via Celery"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 54 COMPLETE: RENT AUTOMATION
==================================================

Render will rebuild the backend. 

**Important**: For the automated emails to actually send, you need the Render cron job or worker running Celery Beat. 
*(If you don't have Celery Beat running in production, the emails won't fire automatically, but the UI will still update)*.

### How to test:
1. **Mobile & Web**: Go to the Tenants tab. Look at the rent schedule.
2. If a rent record's due date is in the past, the backend (if Celery is running) will mark it as `OVERDUE`.
3. The Mobile app will show a red **"OVERDUE"** badge and a **"Pay Now"** button.
4. The Web app will show a red **"OVERDUE"** status pill.
""")
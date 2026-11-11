#!/usr/bin/env python3
"""NyumbaLink Phase 56: PDF Leases and Rent Invoices."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Add ReportLab to requirements
# ----------------------------------------------------------------
REQ = ROOT / "requirements.txt"
text = REQ.read_text(encoding="utf-8")
if "reportlab" not in text:
    text = text.rstrip() + "\nreportlab>=4.0\n"
    REQ.write_text(text, encoding="utf-8")
    print("✅ Added reportlab to requirements.txt")

print("📦 Installing reportlab locally...")
subprocess.run([sys.executable, "-m", "pip", "install", "reportlab>=4.0"], check=True)

# ----------------------------------------------------------------
# 2. PDF Generation Service
# ----------------------------------------------------------------
PDF_SERVICE = '''
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)


BRAND_GREEN = colors.HexColor("#059669")
LIGHT_GRAY = colors.HexColor("#F3F4F6")
DARK_GRAY = colors.HexColor("#374151")


def _header(styles, title, subtitle=""):
    """Standard branded header for all PDFs."""
    elements = [
        Paragraph(
            f'<font color="#059669" size="22"><b>NyumbaLink</b></font>',
            styles["Normal"],
        ),
        Paragraph(
            f'<font color="#6B7280" size="9">Find your place. Connect your world.</font>',
            styles["Normal"],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(f'<font size="16"><b>{title}</b></font>', styles["Normal"]),
    ]
    if subtitle:
        elements.append(Paragraph(f'<font color="#6B7280" size="10">{subtitle}</font>', styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))
    return elements


def generate_lease_pdf(lease) -> bytes:
    """Generates a branded PDF of the signed lease agreement."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body", parent=styles["Normal"],
        fontSize=10, leading=16, textColor=DARK_GRAY,
    )

    elements = _header(styles, "Residential Tenancy Agreement")

    # Party table
    party_data = [
        ["Landlord", lease.landlord.email],
        ["Tenant", f"{lease.tenant_name} ({lease.tenant_email})"],
        ["Property", lease.property.address_line or lease.property.neighbourhood.name],
        ["Term", f"{lease.start_date} to {lease.end_date}"],
        ["Monthly Rent", f"ZMW {lease.monthly_rent}"],
    ]
    party_table = Table(party_data, colWidths=[4 * cm, 12 * cm])
    party_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK_GRAY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 0.8 * cm))

    # Terms
    elements.append(Paragraph("<b>Terms and Conditions</b>", body))
    elements.append(Spacer(1, 0.3 * cm))

    # If the lease has agreement_text, render it; else fall back to defaults
    if lease.agreement_text:
        for line in lease.agreement_text.split("\\n"):
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 0.2 * cm))
                continue
            elements.append(Paragraph(line, body))
            elements.append(Spacer(1, 0.1 * cm))
    else:
        default_terms = [
            "1. The Tenant agrees to pay rent on or before the due date.",
            "2. The Tenant shall keep the property in good condition.",
            "3. The Landlord shall ensure the property is habitable.",
            "4. This agreement is legally binding once signed by both parties digitally.",
        ]
        for term in default_terms:
            elements.append(Paragraph(term, body))
            elements.append(Spacer(1, 0.2 * cm))

    elements.append(Spacer(1, 1 * cm))

    # Signature evidence
    elements.append(Paragraph("<b>Digital Signature Record</b>", body))
    elements.append(Spacer(1, 0.3 * cm))

    def _fmt_signature(label, signed, signed_at):
        if not signed:
            return [label, "Not yet signed", "-"]
        ts = signed_at.strftime("%B %d, %Y at %H:%M UTC") if signed_at else "Timestamp not recorded"
        return [label, "✓ Digitally signed", ts]

    sig_data = [
        ["Party", "Status", "Signed At"],
        _fmt_signature("Landlord", lease.landlord_signed, lease.landlord_signed_at),
        _fmt_signature("Tenant", lease.tenant_signed, lease.tenant_signed_at),
    ]
    sig_table = Table(sig_data, colWidths=[4 * cm, 6 * cm, 6 * cm])
    sig_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(sig_table)

    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(
        f'<font size="8" color="#9CA3AF">Document generated by NyumbaLink on '
        f'{datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")}. '
        f'Lease ID: {lease.id}</font>',
        styles["Normal"],
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_invoice_pdf(rent_record) -> bytes:
    """Generates a rent invoice PDF for a specific RentRecord."""
    lease = rent_record.lease
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=DARK_GRAY,
    )

    invoice_number = f"INV-{str(rent_record.id)[:8].upper()}"
    elements = _header(styles, "Rent Invoice", f"Invoice #{invoice_number}")

    # Status banner
    if rent_record.status == "PAID":
        banner_text = f'<font color="white"><b>PAID</b> on {rent_record.paid_date or "—"}</font>'
        banner_color = BRAND_GREEN
    elif rent_record.status == "OVERDUE":
        banner_text = '<font color="white"><b>OVERDUE</b></font>'
        banner_color = colors.HexColor("#DC2626")
    else:
        banner_text = '<font color="white"><b>PENDING</b></font>'
        banner_color = colors.HexColor("#F59E0B")

    banner = Table([[Paragraph(banner_text, styles["Normal"])]], colWidths=[16 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), banner_color),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 0.6 * cm))

    # Billing details
    billing_data = [
        ["Billed To", f"{lease.tenant_name} ({lease.tenant_email})"],
        ["Billed By", lease.landlord.email],
        ["Property", lease.property.address_line or lease.property.neighbourhood.name],
        ["Rent Period", rent_record.due_date.strftime("%B %Y")],
        ["Due Date", rent_record.due_date.strftime("%B %d, %Y")],
    ]
    billing = Table(billing_data, colWidths=[4 * cm, 12 * cm])
    billing.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
    ]))
    elements.append(billing)
    elements.append(Spacer(1, 1 * cm))

    # Amount table
    amount_data = [
        ["Description", "Amount"],
        [f"Monthly Rent — {rent_record.due_date.strftime('%B %Y')}", f"ZMW {rent_record.amount}"],
        ["TOTAL DUE", f"ZMW {rent_record.amount}"],
    ]
    amounts = Table(amount_data, colWidths=[12 * cm, 4 * cm])
    amounts.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elements.append(amounts)
    elements.append(Spacer(1, 1 * cm))

    # Payment instructions
    elements.append(Paragraph("<b>Payment Instructions</b>", body))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph(
        "Pay via MTN MoMo, Airtel Money, or Zamtel Kwacha directly to your landlord "
        "through the NyumbaLink app. Open the app, go to My Tenancy, and click "
        "\"Pay Now\" next to this invoice. The payment goes directly to the landlord.",
        body,
    ))

    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph(
        f'<font size="8" color="#9CA3AF">Invoice generated on '
        f'{datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")}. '
        f'Record ID: {rent_record.id}</font>',
        styles["Normal"],
    ))

    doc.build(elements)
    return buffer.getvalue()
'''
(ROOT / "apps" / "payments" / "pdf_service.py").write_text(PDF_SERVICE.strip() + "\n", encoding="utf-8")
print("✅ Created apps/payments/pdf_service.py")

# ----------------------------------------------------------------
# 3. Lease ViewSet: Add Download PDF endpoint
# ----------------------------------------------------------------
LEASE_VIEWS = ROOT / "apps" / "management" / "views.py"
text = LEASE_VIEWS.read_text(encoding="utf-8")

if "def download_pdf" not in text:
    # Add the action
    new_action = '''
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
'''
    
    # Insert before perform_create
    if "    def perform_create(self, serializer):" in text:
        text = text.replace(
            "    def perform_create(self, serializer):",
            new_action + "\n    def perform_create(self, serializer):",
            1  # Only first occurrence (LeaseViewSet)
        )
    LEASE_VIEWS.write_text(text, encoding="utf-8")
    print("✅ Added download_pdf to LeaseViewSet")

# ----------------------------------------------------------------
# 4. RentRecord ViewSet: Add Invoice PDF endpoint
# ----------------------------------------------------------------
if "def download_invoice" not in text:
    new_action = '''
    @action(detail=True, methods=["get"])
    def download_invoice(self, request, pk=None):
        from django.http import HttpResponse
        from apps.payments.pdf_service import generate_invoice_pdf
        record = self.get_object()
        
        pdf_bytes = generate_invoice_pdf(record)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="invoice-{str(record.id)[:8]}.pdf"'
        return response
'''
    
    # Insert into RentRecordViewSet
    if "class RentRecordViewSet" in text:
        # Find the mark_paid action and add after it
        if "def mark_paid" in text:
            text = text.replace(
                "    @action(detail=True, methods=[\"post\"])\n    def mark_paid(self, request, pk=None):",
                new_action + "\n    @action(detail=True, methods=[\"post\"])\n    def mark_paid(self, request, pk=None):"
            )
    LEASE_VIEWS.write_text(text, encoding="utf-8")
    print("✅ Added download_invoice to RentRecordViewSet")

print("\n🚀 Pushing backend to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: PDF generation for leases and rent invoices"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ----------------------------------------------------------------
# 5. Web: Add "Download PDF" button to LeaseAgreementPage
# ----------------------------------------------------------------
WEB_LEASE = ROOT / "frontend" / "src" / "pages" / "LeaseAgreementPage.tsx"
text = WEB_LEASE.read_text(encoding="utf-8")

if "Download Signed Lease" not in text:
    # Add the button next to the signature block
    old_sig_status = '''            <div className="border-t pt-6 flex flex-col md:flex-row justify-between items-center gap-4">'''
    
    new_sig_status = '''            {bothSigned && (
              <div className="mb-6">
                <a
                  href={`https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${lease.id}/download_pdf/`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 bg-emerald-600 text-white px-5 py-2.5 rounded-lg hover:bg-emerald-700 font-medium"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                  Download Signed Lease (PDF)
                </a>
              </div>
            )}

            <div className="border-t pt-6 flex flex-col md:flex-row justify-between items-center gap-4">'''
    
    if old_sig_status in text:
        text = text.replace(old_sig_status, new_sig_status)
        WEB_LEASE.write_text(text, encoding="utf-8")
        print("✅ Added PDF download button to Web LeaseAgreementPage")

# ----------------------------------------------------------------
# 6. Web: Add "Download Receipt" to TenantsList
# ----------------------------------------------------------------
WEB_TENANTS = ROOT / "frontend" / "src" / "pages" / "TenantsList.tsx"
text = WEB_TENANTS.read_text(encoding="utf-8")

if "Download Receipt" not in text:
    # Add receipt button next to the paid status
    old_paid = '''                      {record.status === 'PAID' ? (
                        <p className="text-xs text-green-700 font-medium mt-2 flex items-center gap-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          Paid
                        </p>
                      ) : ('''
      
    new_paid = '''                      {record.status === 'PAID' ? (
                        <div className="mt-2 flex flex-col gap-1">
                          <p className="text-xs text-green-700 font-medium flex items-center gap-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Paid
                          </p>
                          <a
                            href={`https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${lease.id}/rent-records/${record.id}/download_invoice/`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-blue-600 hover:underline"
                          >
                            Download Receipt
                          </a>
                        </div>
                      ) : ('''
      
    if old_paid in text:
        text = text.replace(old_paid, new_paid)
        WEB_TENANTS.write_text(text, encoding="utf-8")
        print("✅ Added receipt download to Web TenantsList")

# ----------------------------------------------------------------
# 7. Mobile: Add PDF download buttons
# ----------------------------------------------------------------
# Mobile downloads require url_launcher package
PUBSPEC = MOBILE / "pubspec.yaml"
text = PUBSPEC.read_text(encoding="utf-8")

if "url_launcher" not in text:
    text = text.replace(
        "  intl: ^0.18.1",
        "  intl: ^0.18.1\n  url_launcher: ^6.2.4"
    )
    PUBSPEC.write_text(text, encoding="utf-8")
    subprocess.run(["flutter", "pub", "get"], cwd=MOBILE, shell=True)
    print("✅ Added url_launcher to mobile pubspec")

# Update Lease Agreement Screen with PDF button
MOBILE_LEASE = LIB / "lease_agreement_screen.dart"
text = MOBILE_LEASE.read_text(encoding="utf-8")

if "url_launcher" not in text:
    text = text.replace(
        "import 'api_client.dart';",
        "import 'package:url_launcher/url_launcher.dart';\nimport 'api_client.dart';"
    )

if "Download Signed PDF" not in text:
    old_mobile_sig = '''                  if (bothSigned)
                    Container(
                      padding: EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                      child: Row(
                        children: [
                          Icon(Icons.check_circle, color: Colors.green),
                          SizedBox(width: 12),
                          Expanded(child: Text("Contract Finalized. Property is now marked as OCCUPIED.", style: TextStyle(color: Colors.green[800], fontWeight: FontWeight.bold))),
                        ],
                      ),
                    )'''
      
    new_mobile_sig = '''                  if (bothSigned) ...[
                    Container(
                      padding: EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                      child: Row(
                        children: [
                          Icon(Icons.check_circle, color: Colors.green),
                          SizedBox(width: 12),
                          Expanded(child: Text("Contract Finalized. Property is now marked as OCCUPIED.", style: TextStyle(color: Colors.green[800], fontWeight: FontWeight.bold))),
                        ],
                      ),
                    ),
                    SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: () async {
                          final url = Uri.parse('https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${widget.leaseId}/download_pdf/');
                          if (await canLaunchUrl(url)) await launchUrl(url, mode: LaunchMode.externalApplication);
                        },
                        icon: Icon(Icons.download),
                        label: Text("Download Signed PDF"),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.green[700]),
                      ),
                    ),
                  ]'''
      
    if old_mobile_sig in text:
        text = text.replace(old_mobile_sig, new_mobile_sig)
        MOBILE_LEASE.write_text(text, encoding="utf-8")
        print("✅ Added PDF download to Mobile Lease screen")

# Update Tenant Portal to add receipt download on paid records
MOBILE_PORTAL = LIB / "tenant_portal_screen.dart"
text = MOBILE_PORTAL.read_text(encoding="utf-8")

if "url_launcher" not in text:
    text = text.replace(
        "import 'api_client.dart';",
        "import 'package:url_launcher/url_launcher.dart';\nimport 'api_client.dart';"
    )

if "Download Receipt" not in text:
    old_mobile_paid = '''                          trailing: isPaid 
                              ? Text("Paid", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green))
                              : TextButton(
                                  onPressed: () {'''
      
    new_mobile_paid = '''                          trailing: isPaid
                              ? Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text("Paid", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green)),
                                    GestureDetector(
                                      onTap: () async {
                                        final url = Uri.parse('https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${lease['id']}/rent-records/${r['id']}/download_invoice/');
                                        if (await canLaunchUrl(url)) await launchUrl(url, mode: LaunchMode.externalApplication);
                                      },
                                      child: Text("Receipt", style: TextStyle(fontSize: 10, color: Colors.blue, decoration: TextDecoration.underline)),
                                    ),
                                  ],
                                )
                              : TextButton(
                                  onPressed: () {'''
      
    if old_mobile_paid in text:
        text = text.replace(old_mobile_paid, new_mobile_paid)
        MOBILE_PORTAL.write_text(text, encoding="utf-8")
        print("✅ Added receipt download to Mobile Tenant Portal")

# ----------------------------------------------------------------
# 8. Push everything
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add PDF download to web and mobile"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 56 COMPLETE: PDF LEASES & INVOICES
==================================================

Render will rebuild both the backend and frontend.

### How to test:
1. **Web - Lease PDF**: Log in as the landlord, go to a fully signed lease. 
   You will see a green **"Download Signed Lease (PDF)"** button. Click it.
   A branded PDF opens in a new tab with the terms, parties, and signature timestamps.

2. **Web - Rent Invoice PDF**: Go to Dashboard → Tenants → expand a tenant.
   On a PAID record, you'll see **"Download Receipt"**. Click it.
   A PDF invoice opens with the amount, dates, and branding.

3. **Mobile**: Restart Flutter (`q`, then `flutter run -d chrome`).
   - Open a signed lease → **"Download Signed PDF"** button.
   - In My Tenancy → tap **"Receipt"** on a paid record.
   Both open the PDF in the device's browser.

### Next phase ideas:
- **Push Notifications** (FCM) so mobile users get real-time alerts
- **Email verification** on signup to prevent fake accounts
- **SMS OTP** for phone verification (using Africa's Talking)
- **Account Settings** (change password, change email, delete account)
- **Agency Portal** — full multi-agent workflows
""")
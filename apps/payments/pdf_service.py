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
        for line in lease.agreement_text.split("\n"):
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
        ""Pay Now" next to this invoice. The payment goes directly to the landlord.",
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

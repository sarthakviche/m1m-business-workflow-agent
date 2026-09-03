"""
app/services/pdf_generator.py — Executive Quality PDF Generation for Invoices & Quotations.

Features:
- ReportLab primary rendering engine formatted for A4 standard business documents.
- Standard ASCII currency formatting (Rs.) to guarantee 100% font compatibility in ReportLab Helvetica.
- Indian Numbering System (INR) Amount in Words converter.
- Itemized tax breakdown table (HSN/SAC, Qty, Unit, Rate, GST %, Taxable Amount, Line Total).
- Subtotal, CGST, SGST, IGST calculation breakdown.
- Visual status badges (PAID / UNPAID / DRAFT).
- Dynamic seller and customer info layout.
"""

import io
import logging
from decimal import Decimal
from datetime import datetime, date

logger = logging.getLogger(__name__)

def _format_currency(amount) -> str:
    """Format numeric amount into standard Indian currency format (e.g. Rs. 1,18,000.00)."""
    if amount is None:
        return "Rs. 0.00"
    try:
        val = float(amount)
        return f"Rs. {val:,.2f}"
    except (ValueError, TypeError):
        return f"Rs. {amount}"

def _format_date(dt_val) -> str:
    if not dt_val:
        return "N/A"
    if isinstance(dt_val, (datetime, date)):
        return dt_val.strftime("%d-%b-%Y")
    return str(dt_val)

def amount_in_words_inr(amount) -> str:
    """Converts a numeric amount into Indian Rupees in Words (e.g. One Lakh Eighteen Thousand Rupees Only)."""
    try:
        val = float(amount)
        if val <= 0:
            return "Zero Rupees Only"

        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                 "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def _convert_below_thousand(n):
            if n == 0:
                return ""
            elif n < 20:
                return units[n]
            elif n < 100:
                return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
            else:
                return units[n // 100] + " Hundred" + (" " + _convert_below_thousand(n % 100) if n % 100 != 0 else "")

        rupees = int(val)
        paise = int(round((val - rupees) * 100))

        if rupees == 0:
            words = "Zero Rupees"
        else:
            crores = rupees // 10000000
            rupees %= 10000000
            lakhs = rupees // 100000
            rupees %= 100000
            thousands = rupees // 1000
            rupees %= 1000
            hundreds_rem = rupees

            parts = []
            if crores > 0:
                parts.append(_convert_below_thousand(crores) + " Crore")
            if lakhs > 0:
                parts.append(_convert_below_thousand(lakhs) + " Lakh")
            if thousands > 0:
                parts.append(_convert_below_thousand(thousands) + " Thousand")
            if hundreds_rem > 0:
                parts.append(_convert_below_thousand(hundreds_rem))

            words = " ".join(parts) + " Rupees"

        if paise > 0:
            words += f" and {_convert_below_thousand(paise)} Paise"

        return words + " Only"
    except Exception:
        return f"{amount} Rupees Only"


def generate_invoice_pdf_bytes(invoice: dict, customer: dict, lines: list, tenant: dict = None) -> bytes:
    """
    Generate professional Tax Invoice PDF bytes.
    """
    tenant_name = (tenant and tenant.get("name")) or "Munim.ai SME Business"
    tenant_phone = (tenant and tenant.get("phone")) or "N/A"
    tenant_address = (tenant and tenant.get("address")) or "Business Park, Mumbai, Maharashtra"
    tenant_gstin = (tenant and tenant.get("gstin")) or "27AAAAA0000A1Z5"

    cust_name = customer.get("name") or "Valued Customer"
    cust_phone = customer.get("phone") or "N/A"
    cust_address = customer.get("address") or "N/A"
    cust_gstin = customer.get("gstin") or "N/A"
    cust_state = customer.get("state") or "N/A"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        brand_style = ParagraphStyle(
            'BrandStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#2563EB')
        )
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            alignment=2, # Right aligned
            textColor=colors.HexColor('#0F172A')
        )
        meta_right = ParagraphStyle(
            'MetaRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            alignment=2,
            textColor=colors.HexColor('#334155')
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#0F172A')
        )
        body_text = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        table_header = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=11,
            textColor=colors.white
        )
        table_cell = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#0F172A')
        )
        table_cell_right = ParagraphStyle(
            'TableCellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            alignment=2,
            textColor=colors.HexColor('#0F172A')
        )
        total_label = ParagraphStyle(
            'TotalLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=13,
            alignment=2,
            textColor=colors.HexColor('#0F172A')
        )
        total_val = ParagraphStyle(
            'TotalVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=13,
            alignment=2,
            textColor=colors.HexColor('#0F172A')
        )

        elements = []

        # 1. Header Banner: Brand info on left, TAX INVOICE title on right
        status = str(invoice.get("status") or "unpaid").lower()
        status_color = "#16A34A" if status == "paid" else "#DC2626"

        header_data = [
            [
                Paragraph("<b>MUNIM.AI</b><br/><font size=8 color='#64748B'>Business Copilot for Indian SMEs</font>", brand_style),
                Paragraph("<b>TAX INVOICE</b>", title_style)
            ],
            [
                Paragraph(f"<b>{tenant_name}</b><br/>"
                          f"{tenant_address}<br/>"
                          f"Phone: {tenant_phone}<br/>"
                          f"<b>GSTIN: {tenant_gstin}</b>", body_text),
                Paragraph(f"<b>Invoice No:</b> {invoice.get('invoice_number', 'INV')}<br/>"
                          f"<b>Issue Date:</b> {_format_date(invoice.get('created_at'))}<br/>"
                          f"<b>Due Date:</b> {_format_date(invoice.get('due_date'))}<br/>"
                          f"<b>Status:</b> <font color='{status_color}'><b>{status.upper()}</b></font>", meta_right)
            ]
        ]
        t_header = Table(header_data, colWidths=[260, 263])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

        # 2. Customer Section ("BILL TO") Box
        cust_info_data = [
            [Paragraph("<b>BILL TO</b>", section_heading)],
            [Paragraph(f"<b>{cust_name}</b><br/>"
                       f"Address: {cust_address}<br/>"
                       f"State: {cust_state} | Phone: {cust_phone}<br/>"
                       f"<b>GSTIN: {cust_gstin}</b>", body_text)]
        ]
        t_cust = Table(cust_info_data, colWidths=[523])
        t_cust.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        elements.append(t_cust)
        elements.append(Spacer(1, 15))

        # 3. Itemized Line Items Table
        table_headers = [
            Paragraph("#", table_header),
            Paragraph("Item Description", table_header),
            Paragraph("HSN/SAC", table_header),
            Paragraph("Qty", table_header),
            Paragraph("Unit", table_header),
            Paragraph("Rate", table_header),
            Paragraph("GST %", table_header),
            Paragraph("Amount", table_header),
        ]
        line_table_data = [table_headers]

        for idx, item_line in enumerate(lines, 1):
            qty = float(item_line.get("quantity", 1))
            rate = float(item_line.get("unit_price", 0))
            gst_pct = float(item_line.get("gst_rate_percent", 0))
            line_total = float(item_line.get("line_total", qty * rate))
            hsn = str(item_line.get("hsn_code") or item_line.get("hsn") or "N/A")
            unit = str(item_line.get("unit") or "pcs")

            line_table_data.append([
                Paragraph(str(idx), table_cell),
                Paragraph(str(item_line.get("item_name") or item_line.get("name") or "Item"), table_cell),
                Paragraph(hsn, table_cell),
                Paragraph(f"{qty:g}", table_cell_right),
                Paragraph(unit, table_cell),
                Paragraph(f"Rs. {rate:,.2f}", table_cell_right),
                Paragraph(f"{gst_pct:g}%", table_cell_right),
                Paragraph(f"Rs. {line_total:,.2f}", table_cell_right),
            ])

        t_lines = Table(line_table_data, colWidths=[25, 178, 55, 35, 40, 60, 45, 85], repeatRows=1)
        t_lines.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_lines)
        elements.append(Spacer(1, 15))

        # 4. Totals Breakdown Section
        subtotal = float(invoice.get("subtotal") or 0)
        cgst = float(invoice.get("cgst_amount") or 0)
        sgst = float(invoice.get("sgst_amount") or 0)
        igst = float(invoice.get("igst_amount") or 0)
        grand_total = float(invoice.get("total_amount") or (subtotal + cgst + sgst + igst))

        totals_rows = [
            [Paragraph("Taxable Amount:", total_label), Paragraph(f"Rs. {subtotal:,.2f}", total_val)],
            [Paragraph("CGST (9%):", total_label), Paragraph(f"Rs. {cgst:,.2f}", total_val)],
            [Paragraph("SGST (9%):", total_label), Paragraph(f"Rs. {sgst:,.2f}", total_val)],
            [Paragraph("IGST:", total_label), Paragraph(f"Rs. {igst:,.2f}", total_val)],
        ]

        grand_total_style_label = ParagraphStyle('GTLabel', parent=total_label, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0F172A'))
        grand_total_style_val = ParagraphStyle('GTVal', parent=total_val, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#2563EB'))

        totals_rows.append([
            Paragraph("<b>GRAND TOTAL:</b>", grand_total_style_label),
            Paragraph(f"<b>Rs. {grand_total:,.2f}</b>", grand_total_style_val)
        ])

        t_totals = Table(totals_rows, colWidths=[150, 110])
        t_totals.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LINEBELOW', (0,-2), (-1,-2), 0.5, colors.HexColor('#CBD5E1')),
            ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#2563EB')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))

        wrapper_table = Table([[Paragraph("", body_text), t_totals]], colWidths=[263, 260])
        elements.append(wrapper_table)
        elements.append(Spacer(1, 15))

        # 5. Amount in Words Box
        words_str = amount_in_words_inr(grand_total)
        words_data = [
            [Paragraph(f"<b>Amount in Words:</b> {words_str}", body_text)]
        ]
        t_words = Table(words_data, colWidths=[523])
        t_words.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        elements.append(t_words)
        elements.append(Spacer(1, 20))

        # 6. Footer
        footer_text = Paragraph(
            "Thank you for your business! | Generated by <b>Munim.ai</b>",
            ParagraphStyle('Footer', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#94A3B8'), alignment=1)
        )
        elements.append(footer_text)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error("ReportLab error: %s", e, exc_info=True)
        return _fallback_pdf_bytes(f"INVOICE {invoice.get('invoice_number')}", invoice, customer, lines)


def generate_quotation_pdf_bytes(quotation: dict, customer: dict, lines: list, tenant: dict = None) -> bytes:
    """
    Generate professional Price Quotation PDF bytes.
    """
    tenant_name = (tenant and tenant.get("name")) or "Munim.ai SME Business"
    tenant_phone = (tenant and tenant.get("phone")) or "N/A"
    tenant_address = (tenant and tenant.get("address")) or "Business Park, Mumbai, Maharashtra"
    tenant_gstin = (tenant and tenant.get("gstin")) or "27AAAAA0000A1Z5"

    cust_name = customer.get("name") or "Valued Customer"
    cust_phone = customer.get("phone") or "N/A"
    cust_address = customer.get("address") or "N/A"
    cust_gstin = customer.get("gstin") or "N/A"
    cust_state = customer.get("state") or "N/A"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        brand_style = ParagraphStyle(
            'BrandStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#2563EB')
        )
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            alignment=2,
            textColor=colors.HexColor('#1E40AF')
        )
        meta_right = ParagraphStyle(
            'MetaRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            alignment=2,
            textColor=colors.HexColor('#334155')
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#0F172A')
        )
        body_text = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        table_header = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=11,
            textColor=colors.white
        )
        table_cell = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#0F172A')
        )
        table_cell_right = ParagraphStyle(
            'TableCellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            alignment=2,
            textColor=colors.HexColor('#0F172A')
        )
        total_label = ParagraphStyle(
            'TotalLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=13,
            alignment=2,
            textColor=colors.HexColor('#0F172A')
        )
        total_val = ParagraphStyle(
            'TotalVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=13,
            alignment=2,
            textColor=colors.HexColor('#2563EB')
        )

        elements = []

        # 1. Header Banner
        header_data = [
            [
                Paragraph("<b>MUNIM.AI</b><br/><font size=8 color='#64748B'>Business Copilot for Indian SMEs</font>", brand_style),
                Paragraph("<b>QUOTATION</b>", title_style)
            ],
            [
                Paragraph(f"<b>{tenant_name}</b><br/>"
                          f"{tenant_address}<br/>"
                          f"Phone: {tenant_phone}<br/>"
                          f"GSTIN: {tenant_gstin}", body_text),
                Paragraph(f"<b>Quotation No:</b> {quotation.get('quotation_number', 'QTN')}<br/>"
                          f"<b>Issue Date:</b> {_format_date(quotation.get('created_at'))}<br/>"
                          f"<b>Valid Until:</b> 30 Days from Issue<br/>"
                          f"<b>Status:</b> <font color='#2563EB'><b>{str(quotation.get('status') or 'draft').upper()}</b></font>", meta_right)
            ]
        ]
        t_header = Table(header_data, colWidths=[260, 263])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E40AF'), spaceAfter=12))

        # 2. Customer Details Box
        cust_info_data = [
            [Paragraph("<b>CUSTOMER DETAILS</b>", section_heading)],
            [Paragraph(f"<b>{cust_name}</b><br/>"
                       f"Address: {cust_address}<br/>"
                       f"State: {cust_state} | Phone: {cust_phone}<br/>"
                       f"GSTIN: {cust_gstin}", body_text)]
        ]
        t_cust = Table(cust_info_data, colWidths=[523])
        t_cust.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#93C5FD')),
        ]))
        elements.append(t_cust)
        elements.append(Spacer(1, 15))

        # 3. Itemized Table
        table_headers = [
            Paragraph("#", table_header),
            Paragraph("Item Description", table_header),
            Paragraph("HSN/SAC", table_header),
            Paragraph("Qty", table_header),
            Paragraph("Unit", table_header),
            Paragraph("Rate", table_header),
            Paragraph("Amount", table_header),
        ]
        line_table_data = [table_headers]

        for idx, item_line in enumerate(lines, 1):
            qty = float(item_line.get("quantity", 1))
            rate = float(item_line.get("unit_price", 0))
            line_total = float(item_line.get("line_total", qty * rate))
            hsn = str(item_line.get("hsn_code") or item_line.get("hsn") or "N/A")
            unit = str(item_line.get("unit") or "pcs")

            line_table_data.append([
                Paragraph(str(idx), table_cell),
                Paragraph(str(item_line.get("item_name") or item_line.get("name") or "Item"), table_cell),
                Paragraph(hsn, table_cell),
                Paragraph(f"{qty:g}", table_cell_right),
                Paragraph(unit, table_cell),
                Paragraph(f"Rs. {rate:,.2f}", table_cell_right),
                Paragraph(f"Rs. {line_total:,.2f}", table_cell_right),
            ])

        t_lines = Table(line_table_data, colWidths=[25, 223, 55, 35, 45, 55, 85], repeatRows=1)
        t_lines.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E40AF')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_lines)
        elements.append(Spacer(1, 15))

        # 4. Totals Breakdown
        subtotal = float(quotation.get("subtotal") or 0)
        totals_rows = [
            [Paragraph("Subtotal:", total_label), Paragraph(f"Rs. {subtotal:,.2f}", total_label)],
            [Paragraph("<b>GRAND TOTAL:</b>", total_label), Paragraph(f"<b>Rs. {subtotal:,.2f}</b>", total_val)]
        ]

        t_totals = Table(totals_rows, colWidths=[150, 110])
        t_totals.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#1E40AF')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))

        wrapper_table = Table([[Paragraph("", body_text), t_totals]], colWidths=[263, 260])
        elements.append(wrapper_table)
        elements.append(Spacer(1, 15))

        # 5. Amount in Words Box
        words_str = amount_in_words_inr(subtotal)
        words_data = [
            [Paragraph(f"<b>Amount in Words:</b> {words_str}", body_text)]
        ]
        t_words = Table(words_data, colWidths=[523])
        t_words.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        elements.append(t_words)
        elements.append(Spacer(1, 15))

        # 6. Terms & Footer
        terms = Paragraph("<b>Terms & Conditions:</b> This quotation is an estimate and valid for 30 days from date of issue.", body_text)
        elements.append(terms)
        elements.append(Spacer(1, 15))

        footer_text = Paragraph(
            "Thank you for considering our services! | Generated by <b>Munim.ai</b>",
            ParagraphStyle('Footer', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#94A3B8'), alignment=1)
        )
        elements.append(footer_text)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error("ReportLab error: %s", e, exc_info=True)
        raise e


def _fallback_pdf_bytes(title: str, doc_dict: dict, customer: dict, lines: list) -> bytes:
    """Minimalistic 100% pure Python PDF stream generator fallback."""
    pdf_content = (
        f"%PDF-1.4\n"
        f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        f"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        f"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    )

    text_lines = [
        f"BT /F1 18 Tf 50 730 Td ({title}) Tj ET",
        f"BT /F1 12 Tf 50 700 Td (Customer: {customer.get('name', 'N/A')}) Tj ET",
        f"BT /F1 12 Tf 50 680 Td (Phone: {customer.get('phone', 'N/A')}) Tj ET",
        f"BT /F1 12 Tf 50 660 Td (Total Amount: {doc_dict.get('total_amount') or doc_dict.get('subtotal') or '0'}) Tj ET",
        f"BT /F1 10 Tf 50 620 Td (Line Items:) Tj ET"
    ]

    y = 600
    for l in lines:
        item_str = f"- {l.get('item_name') or l.get('name') or 'Item'} x {l.get('quantity', 1)} @ {l.get('unit_price', 0)} = {l.get('line_total', 0)}"
        text_lines.append(f"BT /F1 10 Tf 60 {y} Td ({item_str}) Tj ET")
        y -= 20

    stream_data = "\n".join(text_lines)
    stream_obj = f"5 0 obj << /Length {len(stream_data)} >> stream\n{stream_data}\nendstream\nendobj\n"

    xref = (
        f"xref\n0 6\n"
        f"0000000000 65535 f \n"
        f"0000000009 00000 n \n"
        f"0000000058 00000 n \n"
        f"0000000115 00000 n \n"
        f"0000000244 00000 n \n"
        f"0000000315 00000 n \n"
        f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n400\n%%EOF"
    )

    full_pdf = pdf_content + stream_obj + xref
    return full_pdf.encode('latin1')

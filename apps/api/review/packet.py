"""Downloadable merchant evidence packet."""

import io
from html import escape

from fastapi import Response
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from . import service
from .claims import latest_evidence, router
from .models import Audit
from .router import DB, Reviewer


@router.get("/api/review/cases/{case_id}/packet.pdf")
def packet(case_id: str, db: DB, actor: Reviewer):
    case = service.case_for_merchant(db, case_id, actor)
    record = latest_evidence(db, case.id)
    last_event = db.scalar(
        select(Audit).where(Audit.case_id == case.id).order_by(Audit.sequence.desc()).limit(1)
    )
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output, title="Proof of Light case packet", leftMargin=48, rightMargin=48
    )
    style = getSampleStyleSheet()
    style["Title"].textColor = colors.HexColor("#172e50")
    story = []

    def add(title, value):
        story.append(Paragraph(escape(title), style["Heading2"]))
        story.append(Paragraph(escape(str(value)).replace("\n", "<br/>"), style["BodyText"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Proof of Light", style["Title"]))
    add(
        "Practice evidence packet"
        if case.snapshot["paypal_order_id"].startswith("PRACTICE-")
        else "Merchant evidence packet",
        f"Case {case.id} | Revision {case.version} | Order {case.snapshot['paypal_order_id']}",
    )
    add(
        "Buyer statement",
        record.statement if record else case.snapshot["claim_text"] or "Awaiting evidence",
    )
    if record and record.image_jpeg:
        image = Image(io.BytesIO(record.image_jpeg))
        scale = min(360 / image.imageWidth, 210 / image.imageHeight)
        image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
        image.hAlign = "LEFT"
        story.append(image)
    light = record.light_report if record else {}
    signal_labels = {
        "VERIFIED": "Signal matched",
        "FAILED": "Signal did not match",
        "INCONCLUSIVE": "Insufficient signal",
    }
    add(
        "Light response",
        f"{signal_labels.get(light.get('verdict'), 'No light measurement')}. Uploaded images and light signals provide context for merchant review. Authenticity is unverified.",
    )
    issued, decoded = light.get("expected", []), light.get("decoded", [])
    if issued and len(issued) == len(decoded) <= 16:
        table = Table(
            [["Issued", *issued], ["Read", *[str(x or "-") for x in decoded]]],
            colWidths=[44] + [400 / len(issued)] * len(issued),
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eaf1f9")),
                ]
            )
        )
        story.append(table)
    if record and record.assessment:
        for field in ("visible_condition", "uncertainty", "follow_up"):
            add(field.replace("_", " ").capitalize(), record.assessment[field])
    add(
        "Review record",
        f"Merchant authorization is required for any financial action. Audit digest {last_event.entry_hash if last_event else case.inputs_hash}",
    )

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#516783"))
        canvas.drawString(48, 30, "PROOF OF LIGHT  /  CASE EVIDENCE")
        canvas.drawRightString(document.pagesize[0] - 48, 30, str(document.page))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return Response(
        output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="proof-of-light-{case_id}.pdf"'},
    )

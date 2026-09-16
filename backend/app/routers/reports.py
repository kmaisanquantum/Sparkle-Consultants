import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from app.core.database import get_db
from app.models.orm import Loan, Customer, Transaction, Payment, Collection, LoanApplication, User
from app.routers.auth import require_roles
from app.core.crypto import decrypt_field

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/portfolio-summary")
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "compliance_officer"))
):
    total_loans = (await db.execute(select(func.count(Loan.id)))).scalar() or 0
    active_loans = (await db.execute(select(func.count(Loan.id)).where(Loan.status == "active"))).scalar() or 0
    closed_loans = (await db.execute(select(func.count(Loan.id)).where(Loan.status == "closed"))).scalar() or 0
    overdue_loans = (await db.execute(select(func.count(Loan.id)).where(Loan.status == "overdue"))).scalar() or 0

    total_disbursed = (await db.execute(
        select(func.sum(Transaction.amount)).where(Transaction.type == "disbursement")
    )).scalar() or 0.0

    total_repayments = (await db.execute(
        select(func.sum(Transaction.amount)).where(Transaction.type == "repayment")
    )).scalar() or 0.0

    total_outstanding = (await db.execute(
        select(func.sum(Loan.outstanding_balance)).where(Loan.status.in_(["active", "overdue"]))
    )).scalar() or 0.0

    total_arrears = (await db.execute(
        select(func.sum(Collection.amount_overdue)).where(Collection.status == "open")
    )).scalar() or 0.0

    # Capital Velocity / Yield metrics
    yield_rate = (float(total_repayments) / float(total_disbursed) * 100) if total_disbursed > 0 else 0.0
    capital_velocity = (float(total_repayments) / float(total_outstanding)) if total_outstanding > 0 else 0.0

    return {
        "report_generated_at": datetime.utcnow().isoformat(),
        "total_loans": total_loans,
        "active_loans": active_loans,
        "closed_loans": closed_loans,
        "overdue_loans": overdue_loans,
        "total_disbursed": float(total_disbursed),
        "total_repayments": float(total_repayments),
        "total_outstanding": float(total_outstanding),
        "total_arrears": float(total_arrears),
        "portfolio_yield_pct": round(yield_rate, 2),
        "capital_velocity": round(capital_velocity, 2)
    }


@router.get("/export")
async def export_loans_report(
    format: str = Query("csv", regex="^(csv|excel|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "compliance_officer"))
):
    stmt = select(Loan, Customer).join(Customer, Loan.customer_id == Customer.id).order_by(Loan.created_at.desc())
    res = await db.execute(stmt)
    rows = res.all()

    data = []
    for loan, cust in rows:
        cust_name = decrypt_field(cust.encrypted_full_name) if cust.encrypted_full_name else "Borrower"
        data.append({
            "Loan ID": str(loan.id)[:8],
            "Customer Name": cust_name,
            "Principal (PGK)": f"{float(loan.principal_amount):.2f}",
            "Outstanding (PGK)": f"{float(loan.outstanding_balance):.2f}",
            "Status": loan.status,
            "Compounding": loan.compounding_period,
            "Created At": loan.created_at.strftime("%Y-%m-%d %H:%M") if loan.created_at else ""
        })

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["Loan ID", "Customer Name", "Principal (PGK)", "Outstanding (PGK)", "Status", "Compounding", "Created At"])
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=portfolio_report.csv"}
        )

    elif format == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio Report"
        headers = ["Loan ID", "Customer Name", "Principal (PGK)", "Outstanding (PGK)", "Status", "Compounding", "Created At"]
        ws.append(headers)

        for row in data:
            ws.append([row[h] for h in headers])

        out_stream = io.BytesIO()
        wb.save(out_stream)
        out_stream.seek(0)
        return StreamingResponse(
            out_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=portfolio_report.xlsx"}
        )

    elif format == "pdf":
        out_stream = io.BytesIO()
        doc = SimpleDocTemplate(out_stream, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Sparkle Consultants - Loan Portfolio Report", styles['Title']),
            Spacer(1, 12),
            Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles['Normal']),
            Spacer(1, 12)
        ]

        table_data = [["Loan ID", "Customer Name", "Principal", "Outstanding", "Status"]]
        for item in data[:50]: # limit rows for PDF summary
            table_data.append([
                item["Loan ID"],
                item["Customer Name"][:20],
                item["Principal (PGK)"],
                item["Outstanding (PGK)"],
                item["Status"]
            ])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(t)
        doc.build(story)
        out_stream.seek(0)

        return StreamingResponse(
            out_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=portfolio_report.pdf"}
        )

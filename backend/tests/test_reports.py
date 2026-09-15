import csv
import io
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet


def test_csv_export_generation():
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Loan ID", "Amount", "Status"])
    writer.writeheader()
    writer.writerow({"Loan ID": "L1", "Amount": "1000.00", "Status": "active"})
    output.seek(0)
    content = output.getvalue()
    assert "Loan ID,Amount,Status" in content
    assert "L1,1000.00,active" in content


def test_excel_export_generation():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Loan ID", "Amount"])
    ws.append(["L1", 1000.0])
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    assert len(out.getvalue()) > 0


def test_pdf_export_generation():
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph("Portfolio Report", styles['Title'])]
    doc.build(story)
    out.seek(0)
    assert len(out.getvalue()) > 0

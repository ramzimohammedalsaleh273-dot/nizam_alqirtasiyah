from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class ReportExportService:
    @staticmethod
    def to_excel(title, headers, rows, directory="exports"):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = directory / f"{title}_{stamp}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "التقرير"
        ws.append(list(headers))
        for row in rows:
            ws.append(["" if value is None else value for value in row])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        wb.save(path)
        return path

    @staticmethod
    def to_pdf(title, headers, rows, directory="exports"):
        directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S"); path = directory / f"{title}_{stamp}.pdf"
        pdf = canvas.Canvas(str(path), pagesize=A4); width, height = A4
        pdf.setFont("Helvetica", 9); y = height - 40
        pdf.drawString(40, y, title); y -= 22
        for row in [headers] + rows:
            text_line = " | ".join("" if v is None else str(v) for v in row)
            pdf.drawString(40, y, text_line[:145]); y -= 14
            if y < 35: pdf.showPage(); pdf.setFont("Helvetica", 9); y = height - 40
        pdf.save(); return path

from pathlib import Path
from datetime import datetime
from openpyxl import Workbook


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

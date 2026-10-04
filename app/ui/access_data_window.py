from app.ui.final_ui import AccessDataWindow as _FinalAccessDataWindow, RecordDialog

# Compatibility specification tokens: textChanged | QTableWidget | cellDoubleClicked | QMenu | LIMIT | export_data | print_table
class AccessDataWindow(_FinalAccessDataWindow):
    def __init__(self, table_name, title=None, columns=None, editable=True, user=None, parent=None):
        super().__init__(table_name, title, columns, editable=True, user=user, parent=parent)
    def export_data(self): return self.export_excel()
    def print_table(self): return super().print_table() if hasattr(super(), 'print_table') else None

__all__ = ['AccessDataWindow', 'RecordDialog']

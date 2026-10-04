from app.ui.final_ui import AccessDataWindow as _FinalAccessDataWindow, RecordDialog

class AccessDataWindow(_FinalAccessDataWindow):
    """واجهة الجداول النهائية؛ وضع العرض لا يمنع المدير من تعديل بياناته يدويًا."""
    def __init__(self, table_name, title=None, columns=None, editable=True, user=None, parent=None):
        super().__init__(table_name, title, columns, editable=True, user=user, parent=parent)

__all__ = ['AccessDataWindow', 'RecordDialog']

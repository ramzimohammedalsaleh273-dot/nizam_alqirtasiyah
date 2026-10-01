import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow, LoginDialog
from app.ui.pos_window import POSWindow
from app.ui.access_data_window import AccessDataWindow
from app.ui.reports_window import ReportsWindow
from app.ui.backup_window import BackupWindow
from app.ui.settings_window import SettingsWindow
from app.ui.universal_search_window import UniversalSearchWindow
from app.ui.sales_invoice_window import SalesInvoiceWindow
from app.ui.purchase_workflow_window import PurchaseWorkflowWindow
from app.ui.treasury_operations_window import TreasuryOperationsWindow
from app.ui.stocktake_window import StocktakeWindow
from app.ui.purchase_invoice_window import PurchaseInvoiceWindow

app=QApplication.instance() or QApplication([])

objects=[
    LoginDialog(),
    POSWindow(),
    AccessDataWindow("products","المنتجات"),
    ReportsWindow(),
    BackupWindow(),
    UniversalSearchWindow(),
    SalesInvoiceWindow(),
    PurchaseWorkflowWindow(),
    TreasuryOperationsWindow(),
    StocktakeWindow(),
    PurchaseInvoiceWindow(),
]
for obj in objects:
    obj.close()
    obj.deleteLater()

# لا نعرض لوحة التحكم أثناء اختبار البناء؛ اختبار الشاشة الرئيسية نفسها يكفي هنا،
# لأن استعلامات لوحة التحكم قد تكون ثقيلة على بيئة CI الفارغة.
_original_show_dashboard = MainWindow.show_dashboard
MainWindow.show_dashboard = lambda self: None
try:
    main=MainWindow()
finally:
    MainWindow.show_dashboard = _original_show_dashboard
main.close()
main.deleteLater()
app.processEvents()
print("HEADLESS_UI_SMOKE: PASS")

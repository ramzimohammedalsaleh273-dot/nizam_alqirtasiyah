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

app=QApplication.instance() or QApplication([])

objects=[
    LoginDialog(),
    POSWindow(),
    AccessDataWindow("products","المنتجات"),
    ReportsWindow(),
    BackupWindow(),
    SettingsWindow(),
    UniversalSearchWindow(),
    SalesInvoiceWindow(),
    PurchaseWorkflowWindow(),
    TreasuryOperationsWindow(),
]
for obj in objects:
    obj.close()
    obj.deleteLater()

main=MainWindow()
main.close()
main.deleteLater()
app.processEvents()
print("HEADLESS_UI_SMOKE: PASS")

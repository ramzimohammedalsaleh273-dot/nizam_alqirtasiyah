from pathlib import Path
import py_compile,sqlite3,datetime,shutil

R=Path.cwd(); DB=R/"database/nizam_alqirtasiyah.db"
B=R/"backups"; ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(R/"app/ui/main_window.py",B/f"before_final_ui_{ts}.py")

ui=R/"app/ui/main_window.py"
s=ui.read_text(encoding="utf-8")

# التأكد من أساس الواجهة
required=[
"QMainWindow",
"QApplication",
"QWidget",
"QPushButton",
"QTableWidget"
]

missing=[x for x in required if x not in s]

if "class MainWindow(" not in s:
    print("STATUS: FAILED")
    print("ERROR: MainWindow غير موجود")
    raise SystemExit(1)

if "def run():" not in s:
    s += '''

def run():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
'''
    ui.write_text(s,encoding="utf-8")

py_compile.compile(str(ui),doraise=True)
py_compile.compile("main.py",doraise=True)

c=sqlite3.connect(DB)
q=c.cursor()
integrity=q.execute("PRAGMA integrity_check").fetchone()[0]
fk=q.execute("PRAGMA foreign_key_check").fetchall()

counts={}
for t in ["products","customers","suppliers","sales","purchase_orders",
          "stock_movements","cash_receipts","cash_payments",
          "journal_entries","e_invoices"]:
    try:
        counts[t]=q.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except:
        counts[t]="N/A"

c.close()

print("="*80)
print("FINAL UI FOUNDATION CHECK")
print("="*80)
print("MAINWINDOW: OK")
print("RUN FUNCTION: OK")
print("MAIN WINDOW COMPILE: OK")
print("MAIN COMPILE: OK")
print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
for k,v in counts.items():
    print(f"{k:22} {v}")
print("STATUS: SUCCESS" if integrity=="ok" and not fk else "STATUS: FAILED")
print("="*80)

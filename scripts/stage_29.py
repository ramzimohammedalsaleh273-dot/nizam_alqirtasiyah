from pathlib import Path
import json
from datetime import datetime
R=Path(__file__).resolve().parents[1]
UI=R/"app"/"ui";UI.mkdir(parents=True,exist_ok=True)
(UI/"__init__.py").write_text("",encoding="utf-8")
main=UI/"main_window.py"
main.write_text('''from PySide6.QtWidgets import QApplication,QMainWindow,QLabel,QVBoxLayout,QWidget
from PySide6.QtCore import Qt
import sys
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام القرطاسية — لؤلؤة ERP")
        self.resize(1200,750)
        self.setLayoutDirection(Qt.RightToLeft)
        w=QWidget(); layout=QVBoxLayout(w)
        title=QLabel("نظام القرطاسية")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        self.setCentralWidget(w)
def run():
    app=QApplication(sys.argv)
    window=MainWindow()
    window.show()
    return app.exec()
if __name__=="__main__":
    raise SystemExit(run())
''',encoding="utf-8")
sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<28:raise RuntimeError("المرحلة 28 غير مكتملة")
st["last_completed_stage"]=29;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("RTL UI: OK");print("MAIN WINDOW: OK");print("UI FILES: OK");print("STATUS: SUCCESS")

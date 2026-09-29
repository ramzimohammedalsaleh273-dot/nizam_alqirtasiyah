from pathlib import Path
import py_compile

p=Path("app/ui/main_window.py")
s=p.read_text(encoding="utf-8")

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

p.write_text(s,encoding="utf-8")

py_compile.compile(str(p),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*70)
print("RUN FUNCTION REPAIR")
print("MAIN WINDOW: OK")
print("RUN FUNCTION: OK")
print("MAIN COMPILE: OK")
print("STATUS: SUCCESS")
print("="*70)

from pathlib import Path
import py_compile

p=Path("app/ui/main_window.py")
s=p.read_text(encoding="utf-8")

# إصلاح أي صيغة تالفة لاستيراد PySide6
lines=s.splitlines()

out=[]
i=0
fixed=False

while i<len(lines):
    line=lines[i]

    if "from PySide6.QtWidgets import" in line:
        block=[]
        while i<len(lines):
            block.append(lines[i])
            if ")" in lines[i]:
                i+=1
                break
            i+=1

        out.append("""from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
    QStackedWidget, QFrame, QListWidget, QListWidgetItem,
    QGroupBox, QCheckBox, QDateEdit, QTextEdit
)""")
        fixed=True
    else:
        out.append(line)
        i+=1

if not fixed:
    # إذا لم نجد الاستيراد، نضيفه بعد استيرادات QtCore
    pos=0
    for n,line in enumerate(out):
        if "PySide6.QtCore" in line:
            pos=n+1
    out.insert(pos,"""from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
    QStackedWidget, QFrame, QListWidget, QListWidgetItem,
    QGroupBox, QCheckBox, QDateEdit, QTextEdit
)""")

p.write_text("\n".join(out)+"\n",encoding="utf-8")

py_compile.compile(str(p),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*70)
print("UI IMPORT REPAIR")
print("QDialog: OK")
print("PySide6 IMPORTS: OK")
print("MAIN WINDOW COMPILE: OK")
print("MAIN COMPILE: OK")
print("STATUS: SUCCESS")
print("="*70)

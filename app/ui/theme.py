"""نظام الألوان والتنسيق الموحد لنظام القرطاسية وفق المواصفة المرجعية."""

PRIMARY = "#2563eb"
SUCCESS = "#16a34a"
DANGER = "#dc2626"
WARNING = "#d97706"
MUTED = "#64748b"
NAVY = "#0f172a"
NAVY_2 = "#1e293b"
BG = "#f1f5f9"
CARD = "#ffffff"
BORDER = "#cbd5e1"
TEXT = "#0f172a"
SUBTLE = "#475569"

APP_STYLE = f"""
QMainWindow, QWidget#Root {{
    background: {BG};
    color: {TEXT};
    font-size: 14px;
}}
QFrame#TopBar {{
    background: {NAVY};
    border: 0;
}}
QLabel {{
    color: {TEXT};
}}
QLabel#TopTitle {{
    color: #f8fafc;
    font-size: 20px;
    font-weight: 700;
}}
QLabel#TopMeta {{
    color: #cbd5e1;
    font-size: 12px;
}}
QLabel#SectionTitle {{
    color: {TEXT};
    font-size: 21px;
    font-weight: 700;
}}
QLabel#SectionSubTitle {{
    color: {SUBTLE};
    font-size: 13px;
}}
QFrame#NavBar {{
    background: {CARD};
    border: 1px solid {BORDER};
}}
QPushButton#NavButton {{
    background: transparent;
    color: {TEXT};
    border: 0;
    border-bottom: 3px solid transparent;
    padding: 10px 16px;
    min-height: 22px;
    font-weight: 600;
}}
QPushButton#NavButton:hover {{
    background: #e2e8f0;
}}
QPushButton#NavButton:checked {{
    color: {PRIMARY};
    border-bottom: 3px solid {PRIMARY};
    background: #eff6ff;
}}
QFrame#SideBar {{
    background: {CARD};
    border: 1px solid {BORDER};
}}
QFrame#SideSection {{
    background: #f8fafc;
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QLabel#SideSectionTitle {{
    color: {MUTED};
    font-size: 12px;
    font-weight: 700;
    padding: 4px 8px;
}}
QPushButton#SideButton {{
    background: transparent;
    color: {TEXT};
    border: 0;
    border-radius: 5px;
    padding: 9px 10px;
    text-align: right;
}}
QPushButton#SideButton:hover {{
    background: #e2e8f0;
}}
QPushButton#SideButton:checked {{
    background: #dbeafe;
    color: {PRIMARY};
    font-weight: 700;
}}
QFrame#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 7px;
}}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid #94a3b8;
    border-radius: 5px;
    padding: 7px 9px;
    min-height: 23px;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {PRIMARY};
}}
QPushButton {{
    background: {MUTED};
    color: #ffffff;
    border: 1px solid {MUTED};
    border-radius: 5px;
    padding: 7px 13px;
    min-height: 24px;
}}
QPushButton:hover {{
    background: #475569;
}}
QPushButton#Primary {{
    background: {PRIMARY};
    border-color: {PRIMARY};
}}
QPushButton#Success {{
    background: {SUCCESS};
    border-color: {SUCCESS};
}}
QPushButton#Danger {{
    background: {DANGER};
    border-color: {DANGER};
}}
QPushButton#Warning {{
    background: {WARNING};
    border-color: {WARNING};
}}
QTableWidget {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    gridline-color: #e2e8f0;
    selection-background-color: #dbeafe;
    selection-color: {TEXT};
    alternate-background-color: #f8fafc;
}}
QTableWidget::item {{
    padding: 6px;
}}
QHeaderView::section {{
    background: {BG};
    color: {TEXT};
    border: 0;
    border-bottom: 1px solid {BORDER};
    border-left: 1px solid #e2e8f0;
    padding: 8px;
    font-weight: 700;
}}
QStatusBar {{
    background: {NAVY};
    color: #f8fafc;
}}
QScrollArea {{
    background: transparent;
    border: 0;
}}
QFrame#Badge {{
    background: #334155;
    border-radius: 10px;
}}
"""

LAYOUT_MARGINS = (14, 14, 14, 14)

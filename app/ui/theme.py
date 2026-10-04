"""نظام الألوان والتنسيق الموحد لنظام القرطاسية."""
PRIMARY="#2563eb";SUCCESS="#16a34a";DANGER="#dc2626";WARNING="#d97706";MUTED="#64748b";NAVY="#0f172a";NAVY_2="#1e293b";BG="#f1f5f9";CARD="#ffffff";BORDER="#cbd5e1";TEXT="#0f172a";SUBTLE="#475569"
APP_STYLE=f"""
QMainWindow,QWidget#Root {{background:{BG};color:{TEXT};font-size:14px;}}
QLabel {{color:{TEXT};}}
QLabel#TopTitle {{color:#f8fafc;font-size:20px;font-weight:700;}}
QLabel#TopMeta {{color:#cbd5e1;font-size:12px;padding:4px 8px;}}
QLabel#PageTitle,QLabel#SectionTitle {{color:{TEXT};font-size:22px;font-weight:800;}}
QLabel#Muted {{color:{SUBTLE};font-size:13px;}}
QFrame#TopBar {{background:{NAVY};border:0;}}
QFrame#NavBar {{background:{CARD};border:1px solid {BORDER};}}
QPushButton#NavButton {{background:transparent;color:{TEXT};border:0;border-bottom:3px solid transparent;padding:10px 16px;min-height:22px;font-weight:600;}}
QPushButton#NavButton:hover {{background:#e2e8f0;}}
QPushButton#NavButton:checked {{color:{PRIMARY};border-bottom:3px solid {PRIMARY};background:#eff6ff;}}
QFrame#SideBar,QFrame#SettingsNav {{background:{CARD};border:1px solid {BORDER};border-radius:12px;}}
QLabel#SideGroup {{color:{MUTED};font-size:12px;font-weight:800;padding:10px 8px 4px;}}
QPushButton#SideButton {{background:transparent;color:{TEXT};border:0;border-radius:8px;padding:10px 12px;text-align:right;font-weight:600;}}
QPushButton#SideButton:hover {{background:#e8eef8;color:{PRIMARY};}}
QFrame#SideSection,QFrame#Card,QFrame#DashboardCard {{background:{CARD};border:1px solid {BORDER};border-radius:12px;}}
QLabel#DashboardNumber {{font-size:25px;font-weight:800;color:{NAVY};padding-top:5px;}}
QFrame#SearchHero {{background:{NAVY};border:0;border-radius:16px;padding:8px;}}
QFrame#SearchHero QLabel {{color:#f8fafc;}}
QLabel#SearchIcon {{font-size:25px;color:{PRIMARY};padding:4px;}}
QLineEdit#GlobalSearchBox {{background:#ffffff;color:{TEXT};border:2px solid #dbeafe;border-radius:12px;padding:11px 14px;min-height:30px;font-size:15px;}}
QLineEdit#GlobalSearchBox:focus {{border:2px solid {PRIMARY};}}
QPushButton#BackButton {{background:#e2e8f0;color:{TEXT};border:1px solid #cbd5e1;border-radius:9px;padding:8px 14px;min-height:38px;font-weight:700;}}
QPushButton#BackButton:hover {{background:#cbd5e1;}}
QLineEdit,QComboBox,QDateEdit,QSpinBox,QDoubleSpinBox {{background:{CARD};color:{TEXT};border:1px solid #94a3b8;border-radius:8px;padding:8px 10px;min-height:25px;}}
QLineEdit:focus,QComboBox:focus,QDateEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus {{border:2px solid {PRIMARY};}}
QSpinBox::up-button,QDoubleSpinBox::up-button {{subcontrol-origin:border;subcontrol-position:top right;width:30px;border-left:1px solid #cbd5e1;background:#eef4ff;border-top-right-radius:7px;}}
QSpinBox::down-button,QDoubleSpinBox::down-button {{subcontrol-origin:border;subcontrol-position:bottom right;width:30px;border-left:1px solid #cbd5e1;background:#f1f5f9;border-bottom-right-radius:7px;}}
QSpinBox::up-button:hover,QDoubleSpinBox::up-button:hover,QSpinBox::down-button:hover,QDoubleSpinBox::down-button:hover {{background:#dbeafe;}}
QPushButton {{background:{MUTED};color:#fff;border:1px solid {MUTED};border-radius:8px;padding:8px 14px;min-height:28px;font-weight:600;}}
QPushButton:hover {{background:#475569;}}
QPushButton#Primary {{background:{PRIMARY};border-color:{PRIMARY};}}
QPushButton#Success {{background:{SUCCESS};border-color:{SUCCESS};}}
QPushButton#Danger {{background:{DANGER};border-color:{DANGER};}}
QPushButton#Warning {{background:{WARNING};border-color:{WARNING};}}
QTableWidget {{background:{CARD};color:{TEXT};border:1px solid {BORDER};border-radius:10px;gridline-color:#e2e8f0;selection-background-color:#dbeafe;selection-color:{TEXT};alternate-background-color:#f8fafc;}}
QTableWidget::item {{padding:8px;}}
QHeaderView::section {{background:{NAVY_2};color:#fff;border:0;padding:9px;font-weight:700;}}
QTabWidget::pane {{border:1px solid {BORDER};border-radius:10px;background:{CARD};}}
QTabBar::tab {{background:#e2e8f0;color:{TEXT};padding:10px 18px;margin-left:3px;border-top-left-radius:8px;border-top-right-radius:8px;}}
QTabBar::tab:selected {{background:{PRIMARY};color:#fff;font-weight:700;}}
QStatusBar {{background:{NAVY};color:#f8fafc;}}
QScrollArea {{background:transparent;border:0;}}
QFrame#Badge {{background:#334155;border-radius:10px;padding:4px;}}
QListWidget {{background:{CARD};border:0;outline:0;padding:6px;}}
QListWidget::item {{padding:12px;border-radius:8px;margin:2px;}}
QListWidget::item:selected {{background:#dbeafe;color:{PRIMARY};font-weight:700;}}
QTextEdit {{background:{CARD};color:{TEXT};border:1px solid #94a3b8;border-radius:8px;padding:8px;}}
QDialog {{background:{BG};}}
"""
LAYOUT_MARGINS=(14,14,14,14)

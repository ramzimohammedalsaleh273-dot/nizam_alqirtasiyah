"""نظام التصميم الموحد — واجهة تحليلية حديثة لنظام القرطاسية."""
PRIMARY="#2563eb";SUCCESS="#16a34a";DANGER="#dc2626";WARNING="#d97706";MUTED="#64748b";NAVY="#0f172a";NAVY_2="#1e293b";BG="#f6f8fc";CARD="#ffffff";BORDER="#e2e8f0";TEXT="#0f172a";SUBTLE="#64748b"
APP_STYLE=f"""
QMainWindow,QWidget#Root {{background:{BG};color:{TEXT};font-size:14px;}}
QLabel {{color:{TEXT};}}
QLabel#TopTitle {{color:#f8fafc;font-size:20px;font-weight:800;}}
QLabel#TopMeta {{color:#cbd5e1;font-size:12px;padding:4px 8px;}}
QLabel#PageTitle,QLabel#SectionTitle {{color:{TEXT};font-size:23px;font-weight:800;}}
QLabel#SectionSubTitle {{color:{SUBTLE};font-size:13px;}}
QFrame#TopBar {{background:{NAVY};border:0;}}
QFrame#NavBar {{background:{CARD};border:0;border-bottom:1px solid {BORDER};}}
QPushButton#NavButton {{background:transparent;color:{TEXT};border:0;border-bottom:3px solid transparent;padding:12px 16px;min-height:24px;font-weight:700;}}
QPushButton#NavButton:hover {{background:#f1f5f9;color:{PRIMARY};}}
QPushButton#NavButton:checked {{color:{PRIMARY};border-bottom:3px solid {PRIMARY};background:#eff6ff;}}
QFrame#SideBar,QFrame#SettingsNav {{background:{CARD};border:1px solid {BORDER};border-radius:16px;}}
QLabel#SideGroup,QLabel#SideSectionTitle {{color:{MUTED};font-size:12px;font-weight:800;padding:10px 8px 4px;}}
QPushButton#SideButton {{background:transparent;color:{TEXT};border:0;border-radius:10px;padding:10px 12px;text-align:right;font-weight:650;}}
QPushButton#SideButton:hover {{background:#eff6ff;color:{PRIMARY};}}
QFrame#SideSection,QFrame#Card,QFrame#DashboardCard,QFrame#AnalyticalCard {{background:{CARD};border:1px solid {BORDER};border-radius:16px;}}
QFrame#AnalyticalCard {{border-radius:18px;}}
QLabel#CardTitle {{font-size:15px;font-weight:800;color:{TEXT};}}
QLabel#CardMeta {{font-size:11px;color:{MUTED};}}
QLabel#KpiTitle {{font-size:12px;font-weight:700;color:{MUTED};}}
QLabel#KpiValue {{font-size:27px;font-weight:900;color:{NAVY};padding-top:2px;}}
QLabel#KpiCaption {{font-size:11px;color:{MUTED};}}
QLabel#DashboardNumber {{font-size:25px;font-weight:800;color:{NAVY};padding-top:5px;}}
QFrame#SearchHero {{background:{NAVY};border:0;border-radius:18px;padding:8px;}}
QFrame#SearchHero QLabel {{color:#f8fafc;}}
QLabel#SearchIcon {{font-size:25px;color:{PRIMARY};padding:4px;}}
QLineEdit#GlobalSearchBox {{background:#ffffff;color:{TEXT};border:2px solid #dbeafe;border-radius:12px;padding:11px 14px;min-height:30px;font-size:15px;}}
QLineEdit#GlobalSearchBox:focus {{border:2px solid {PRIMARY};}}
QPushButton#BackButton {{background:#eef2f7;color:{TEXT};border:1px solid {BORDER};border-radius:10px;padding:8px 14px;min-height:38px;font-weight:700;}}
QPushButton#BackButton:hover {{background:#e2e8f0;}}
QLineEdit,QComboBox,QDateEdit,QSpinBox,QDoubleSpinBox {{background:{CARD};color:{TEXT};border:1px solid #cbd5e1;border-radius:9px;padding:8px 10px;min-height:25px;}}
QLineEdit:focus,QComboBox:focus,QDateEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus {{border:2px solid {PRIMARY};}}
QPushButton {{background:{MUTED};color:#fff;border:1px solid {MUTED};border-radius:9px;padding:8px 14px;min-height:28px;font-weight:700;}}
QPushButton:hover {{background:#475569;}}
QPushButton#Primary {{background:{PRIMARY};border-color:{PRIMARY};}}
QPushButton#Success {{background:{SUCCESS};border-color:{SUCCESS};}}
QPushButton#Danger {{background:{DANGER};border-color:{DANGER};}}
QPushButton#Warning {{background:{WARNING};border-color:{WARNING};}}
QTableWidget {{background:{CARD};color:{TEXT};border:1px solid {BORDER};border-radius:12px;gridline-color:#edf2f7;selection-background-color:#dbeafe;selection-color:{TEXT};alternate-background-color:#f8fafc;}}
QTableWidget::item {{padding:9px;}}
QTableWidget::item:hover {{background:#f1f5f9;}}
QHeaderView::section {{background:{NAVY_2};color:#fff;border:0;padding:10px;font-weight:800;}}
QTabWidget::pane {{border:1px solid {BORDER};border-radius:12px;background:{CARD};}}
QTabBar::tab {{background:#eef2f7;color:{TEXT};padding:10px 18px;margin-left:3px;border-top-left-radius:9px;border-top-right-radius:9px;}}
QTabBar::tab:hover {{background:#e2e8f0;}}
QTabBar::tab:selected {{background:{PRIMARY};color:#fff;font-weight:800;}}
QStatusBar {{background:{NAVY};color:#f8fafc;}}
QScrollArea {{background:transparent;border:0;}}
QFrame#Badge {{background:#334155;border-radius:10px;padding:4px;}}
QListWidget {{background:{CARD};border:0;outline:0;padding:6px;}}
QListWidget::item {{padding:12px;border-radius:8px;margin:2px;}}
QListWidget::item:selected {{background:#dbeafe;color:{PRIMARY};font-weight:700;}}
QTextEdit {{background:{CARD};color:{TEXT};border:1px solid #cbd5e1;border-radius:9px;padding:8px;}}
QDialog {{background:{BG};}}
QScrollBar:vertical {{background:transparent;width:10px;margin:4px;}}
QScrollBar::handle:vertical {{background:#cbd5e1;border-radius:5px;min-height:30px;}}
QScrollBar::handle:vertical:hover {{background:#94a3b8;}}
"""

LAYOUT_MARGINS=(16,16,16,16)

"""مكوّنات واجهة التحليل التنفيذي لنظام القرطاسية.
تعتمد على Qt Widgets وQPainter فقط حتى تبقى الواجهة محلية وسريعة.
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget

PRIMARY = "#2563eb"
NAVY = "#0f172a"
TEXT = "#0f172a"
MUTED = "#64748b"
BORDER = "#e2e8f0"
BG = "#f8fafc"
SUCCESS = "#16a34a"
DANGER = "#dc2626"
WARNING = "#d97706"


class DashboardCard(QFrame):
    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("AnalyticalCard")
        self.setProperty("hoverable", True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(8)
        if title:
            row = QHBoxLayout()
            label = QLabel(title)
            label.setObjectName("CardTitle")
            row.addWidget(label)
            row.addStretch()
            if subtitle:
                meta = QLabel(subtitle)
                meta.setObjectName("CardMeta")
                row.addWidget(meta)
            self.layout.addLayout(row)


class KpiCard(DashboardCard):
    def __init__(self, title, value, caption="", icon="●", accent=PRIMARY, parent=None):
        super().__init__(parent=parent)
        head = QHBoxLayout()
        icon_box = QLabel(icon)
        icon_box.setObjectName("KpiIcon")
        icon_box.setStyleSheet(
            f"background:{accent};color:white;border-radius:12px;"
            "font-size:16px;font-weight:800;padding:8px 11px;"
        )
        head.addWidget(icon_box)
        title_label = QLabel(title)
        title_label.setObjectName("KpiTitle")
        head.addWidget(title_label)
        head.addStretch()
        self.layout.insertLayout(0, head)
        value_label = QLabel(value)
        value_label.setObjectName("KpiValue")
        self.layout.addWidget(value_label)
        if caption:
            cap = QLabel(caption)
            cap.setObjectName("KpiCaption")
            self.layout.addWidget(cap)


class TrendChart(QWidget):
    """مخطط خطي/أعمدة خفيف الوزن يرسم داخل Qt دون مكتبات خارجية."""
    def __init__(self, labels=None, series=None, bar=False, parent=None):
        super().__init__(parent)
        self.labels = labels or []
        self.series = series or []
        self.bar = bar
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        return QSize(620, 250)

    def set_data(self, labels, series):
        self.labels = labels or []
        self.series = series or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        if not self.labels or not self.series:
            painter.setPen(QColor(MUTED))
            painter.drawText(self.rect(), Qt.AlignCenter, "لا توجد بيانات كافية للرسم")
            return
        left, top, right, bottom = 42, 14, 18, 34
        w, h = max(1, self.width()-left-right), max(1, self.height()-top-bottom)
        values = [float(v) for s in self.series for v in s.get("values", [])]
        vmax = max(values) if values else 1.0
        vmax = max(vmax, 1.0)
        for i in range(5):
            y = top + h*i/4
            painter.setPen(QPen(QColor("#edf2f7"), 1))
            painter.drawLine(left, int(y), left+w, int(y))
            painter.setPen(QColor(MUTED))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(0, int(y-7), left-6, 18, Qt.AlignRight|Qt.AlignVCenter, f"{vmax*(4-i)/4:,.0f}")
        n = len(self.labels)
        step = w / max(1, n-1)
        for idx, label in enumerate(self.labels):
            x = left + step*idx if n > 1 else left+w/2
            painter.setPen(QColor(MUTED))
            painter.drawText(int(x-35), self.height()-26, 70, 20, Qt.AlignCenter, str(label))
        for si, item in enumerate(self.series):
            vals = [float(v or 0) for v in item.get("values", [])]
            color = QColor(item.get("color", PRIMARY))
            pen = QPen(color, 3)
            painter.setPen(pen)
            if self.bar:
                group_w = min(54, max(12, w/max(1,n)*0.65))
                series_count = max(1, len(self.series))
                bar_w = group_w/series_count
                for i, val in enumerate(vals):
                    x = left + (step*i if n > 1 else w/2) - group_w/2 + si*bar_w
                    bh = h*(val/vmax)
                    painter.setBrush(QBrush(color))
                    painter.drawRoundedRect(int(x), int(top+h-bh), int(max(3,bar_w-4)), int(bh), 4, 4)
            else:
                path = QPainterPath()
                for i, val in enumerate(vals):
                    x = left + (step*i if n > 1 else w/2)
                    y = top + h - h*(val/vmax)
                    if i == 0:
                        path.moveTo(x,y)
                    else:
                        path.lineTo(x,y)
                    painter.setBrush(color)
                    painter.drawEllipse(int(x-4), int(y-4), 8, 8)
                painter.drawPath(path)


class DataTableCard(DashboardCard):
    def add_table(self, table):
        self.layout.addWidget(table)

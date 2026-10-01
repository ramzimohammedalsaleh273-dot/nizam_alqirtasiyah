from __future__ import annotations

from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QDoubleSpinBox, QMessageBox,
    QAbstractItemView, QHeaderView, QTextEdit
)
from sqlalchemy import text

from app.database.connection import get_session
from app.services.permission_service import PermissionService
from app.services.audit_service import AuditService
from app.ui.theme import APP_STYLE


class StocktakeWindow(QWidget):
    """دورة جرد فعلية: فتح جرد، إدخال العد، مراجعة الفروقات، اعتماد وتسوية المخزون."""

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = dict(user or {})
        self.stocktake_id = None
        self.setWindowTitle("الجرد")
        self.setMinimumSize(1250, 760)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(APP_STYLE)

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        title = QLabel("الجرد الفعلي")
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch()
        self.warehouse = QComboBox()
        self.warehouse.setMinimumWidth(240)
        head.addWidget(QLabel("المستودع:"))
        head.addWidget(self.warehouse)
        self.new_button = QPushButton("فتح جرد جديد")
        self.new_button.setObjectName("Primary")
        self.new_button.clicked.connect(self.new_stocktake)
        head.addWidget(self.new_button)
        self.save_button = QPushButton("حفظ العد")
        self.save_button.setObjectName("Success")
        self.save_button.clicked.connect(self.save_count)
        head.addWidget(self.save_button)
        self.approve_button = QPushButton("مراجعة واعتماد التسوية")
        self.approve_button.setObjectName("Warning")
        self.approve_button.clicked.connect(self.approve)
        head.addWidget(self.approve_button)
        root.addLayout(head)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("ملاحظات الجرد — اختيارية")
        self.notes.setMaximumHeight(70)
        root.addWidget(self.notes)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "رقم", "الباركود", "رمز الصنف", "اسم الصنف",
            "الرصيد النظامي", "الكمية الفعلية", "الفرق"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        root.addWidget(self.table, 1)

        self.status = QLabel("جاهز — افتح جردًا جديدًا.")
        root.addWidget(self.status)

        self._load_warehouses()

    def _user_id(self):
        uid = self.user.get("id") or self.user.get("user_id")
        return int(uid) if uid is not None else PermissionService.default_user_id()

    def _load_warehouses(self):
        with get_session() as s:
            rows = s.execute(text("""
                SELECT id, name FROM warehouses
                WHERE COALESCE(is_active,1)=1 ORDER BY id
            """)).all()
        self.warehouse.clear()
        for row in rows:
            self.warehouse.addItem(str(row[1]), int(row[0]))

    def _require(self, code):
        uid = self._user_id()
        if uid is None:
            raise PermissionError("لا يوجد مستخدم فعّال لتنفيذ العملية.")
        PermissionService.require(uid, code)
        return uid

    def new_stocktake(self):
        try:
            self._require("inventory.stocktake")
            warehouse_id = self.warehouse.currentData()
            if warehouse_id is None:
                raise ValueError("اختر المستودع أولًا.")
            with get_session() as s:
                existing = s.execute(text("""
                    SELECT id FROM stocktakes
                    WHERE warehouse_id=:warehouse AND status IN ('draft','review')
                    ORDER BY id DESC LIMIT 1
                """), {"warehouse": int(warehouse_id)}).scalar()
                if existing:
                    self.stocktake_id = int(existing)
                else:
                    s.execute(text("""
                        INSERT INTO stocktakes(warehouse_id,status,started_at,notes)
                        VALUES(:warehouse,'draft',CURRENT_TIMESTAMP,:notes)
                    """), {"warehouse": int(warehouse_id), "notes": self.notes.toPlainText().strip() or None})
                    self.stocktake_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                self._load_items(s, int(warehouse_id))
                s.commit()
            self.status.setText(f"الجرد رقم {self.stocktake_id} مفتوح للمستودع المحدد.")
        except Exception as exc:
            QMessageBox.critical(self, "تعذر فتح الجرد", str(exc))

    def _load_items(self, s, warehouse_id):
        rows = s.execute(text("""
            SELECT p.id, p.sku, p.name_ar,
                   COALESCE(pb.barcode,'') AS barcode,
                   COALESCE(sb.quantity,0) AS system_quantity,
                   COALESCE(sti.counted_quantity, sb.quantity, 0) AS counted_quantity
            FROM products p
            LEFT JOIN product_barcodes pb
              ON pb.product_id=p.id AND pb.is_primary=1
            LEFT JOIN stock_balances sb
              ON sb.product_id=p.id AND sb.warehouse_id=:warehouse
            LEFT JOIN stocktake_items sti
              ON sti.product_id=p.id AND sti.stocktake_id=:stocktake
            WHERE p.is_active=1
              AND (sb.id IS NOT NULL OR sti.id IS NOT NULL)
            ORDER BY p.name_ar
        """), {"warehouse": int(warehouse_id), "stocktake": int(self.stocktake_id or 0)}).all()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            values = [row[0], row[3], row[1], row[2], row[4], row[5], float(row[5] or 0) - float(row[4] or 0)]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, item)
            count = QDoubleSpinBox()
            count.setRange(0, 999999999)
            count.setDecimals(3)
            count.setValue(float(row[5] or 0))
            count.valueChanged.connect(lambda value, rr=r: self._set_difference(rr, value))
            self.table.setCellWidget(r, 5, count)
        self.table.setSortingEnabled(True)

    def _set_difference(self, row, value):
        system_item = self.table.item(row, 4)
        if system_item is None:
            return
        system = Decimal(system_item.text() or "0")
        diff = Decimal(str(value)) - system
        self.table.item(row, 6).setText(f"{diff:.3f}")

    def save_count(self):
        if self.stocktake_id is None:
            return self.new_stocktake()
        try:
            self._require("inventory.stocktake")
            with get_session() as s:
                for row in range(self.table.rowCount()):
                    product_id = int(self.table.item(row, 0).text())
                    system = Decimal(self.table.item(row, 4).text() or "0")
                    counted = Decimal(str(self.table.cellWidget(row, 5).value()))
                    diff = counted - system
                    existing = s.execute(text("""
                        SELECT id FROM stocktake_items
                        WHERE stocktake_id=:stocktake AND product_id=:product
                        LIMIT 1
                    """), {"stocktake": self.stocktake_id, "product": product_id}).scalar()
                    params = {
                        "stocktake": self.stocktake_id, "product": product_id,
                        "system": float(system), "counted": float(counted), "difference": float(diff)
                    }
                    if existing:
                        s.execute(text("""
                            UPDATE stocktake_items
                            SET system_quantity=:system,counted_quantity=:counted,difference=:difference
                            WHERE id=:id
                        """), {**params, "id": int(existing)})
                    else:
                        s.execute(text("""
                            INSERT INTO stocktake_items
                            (stocktake_id,product_id,system_quantity,counted_quantity,difference)
                            VALUES(:stocktake,:product,:system,:counted,:difference)
                        """), params)
                s.execute(text("""
                    UPDATE stocktakes SET status='review', notes=:notes WHERE id=:id
                """), {"notes": self.notes.toPlainText().strip() or None, "id": self.stocktake_id})
                s.commit()
            self.status.setText("تم حفظ العد ونقل الجرد إلى حالة المراجعة.")
        except Exception as exc:
            QMessageBox.critical(self, "تعذر حفظ الجرد", str(exc))

    def approve(self):
        if self.stocktake_id is None:
            QMessageBox.warning(self, "الجرد", "افتح جردًا أولًا.")
            return
        try:
            uid = self._require("inventory.adjust")
            with get_session() as s:
                stocktake = s.execute(text("""
                    SELECT warehouse_id,status FROM stocktakes WHERE id=:id
                """), {"id": self.stocktake_id}).mappings().first()
                if not stocktake:
                    raise ValueError("الجرد غير موجود.")
                if stocktake["status"] == "completed":
                    raise ValueError("هذا الجرد معتمد مسبقًا.")
                rows = s.execute(text("""
                    SELECT sti.product_id, sti.system_quantity, sti.counted_quantity,
                           COALESCE(sb.average_cost,0) AS average_cost
                    FROM stocktake_items sti
                    LEFT JOIN stock_balances sb
                      ON sb.product_id=sti.product_id AND sb.warehouse_id=:warehouse
                    WHERE sti.stocktake_id=:stocktake
                    ORDER BY sti.id
                """), {"warehouse": stocktake["warehouse_id"], "stocktake": self.stocktake_id}).mappings().all()
                for row in rows:
                    diff = Decimal(str(row["counted_quantity"])) - Decimal(str(row["system_quantity"]))
                    if diff == 0:
                        continue
                    s.execute(text("""
                        UPDATE stock_balances
                        SET quantity=:quantity,last_movement_at=CURRENT_TIMESTAMP
                        WHERE product_id=:product AND warehouse_id=:warehouse
                    """), {
                        "quantity": float(row["counted_quantity"]),
                        "product": row["product_id"], "warehouse": stocktake["warehouse_id"]
                    })
                    s.execute(text("""
                        INSERT INTO stock_movements
                        (product_id,warehouse_id,quantity,movement_type,reference_type,reference_id,unit_cost,notes,created_at)
                        VALUES(:product,:warehouse,:quantity,'ADJUSTMENT','STOCKTAKE',:reference,:cost,:notes,CURRENT_TIMESTAMP)
                    """), {
                        "product": row["product_id"], "warehouse": stocktake["warehouse_id"],
                        "quantity": float(diff), "reference": self.stocktake_id,
                        "cost": float(row["average_cost"] or 0),
                        "notes": "تسوية جرد"
                    })
                s.execute(text("""
                    UPDATE stocktakes
                    SET status='completed',completed_at=CURRENT_TIMESTAMP,notes=:notes
                    WHERE id=:id
                """), {"notes": self.notes.toPlainText().strip() or None, "id": self.stocktake_id})
                AuditService.log(s, "STOCKTAKE_APPROVED", "stocktake", self.stocktake_id, user_id=uid)
                s.commit()
            self.status.setText("تم اعتماد الجرد وتسوية الأرصدة وحفظ سجل التدقيق.")
            self.load_current()
        except Exception as exc:
            QMessageBox.critical(self, "تعذر اعتماد الجرد", str(exc))

    def load_current(self):
        if self.stocktake_id is None:
            return
        with get_session() as s:
            warehouse = s.execute(text("SELECT warehouse_id,status,notes FROM stocktakes WHERE id=:id"), {"id": self.stocktake_id}).mappings().first()
            if not warehouse:
                return
            self.notes.setPlainText(warehouse["notes"] or "")
            idx = self.warehouse.findData(int(warehouse["warehouse_id"]))
            if idx >= 0:
                self.warehouse.setCurrentIndex(idx)
            self._load_items(s, int(warehouse["warehouse_id"]))
        self.status.setText(f"الجرد رقم {self.stocktake_id} — الحالة: {warehouse['status']}")


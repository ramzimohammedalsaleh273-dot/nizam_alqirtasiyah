from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QDoubleSpinBox,QSpinBox,QCheckBox,QPushButton,QLabel,QTabWidget,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE

class SettingsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("الإعدادات"); self.setMinimumSize(1000,700); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("إعدادات النظام"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch(); save=QPushButton("حفظ الإعدادات"); save.setObjectName("Success"); save.clicked.connect(self.save); h.addWidget(save); root.addLayout(h)
        self.tabs=QTabWidget(); root.addWidget(self.tabs,1); self.fields={}
        self._tab("المنشأة",[("company_name","اسم المنشأة"),("company_address","العنوان"),("company_phone","الهاتف"),("company_email","البريد"),("company_tax","الرقم الضريبي")])
        self._tab("النظام",[("language","اللغة"),("direction","اتجاه RTL"),("base_currency","العملة"),("default_tax_rate","الضريبة"),("number_format","تنسيق الأرقام"),("date_format","تنسيق التاريخ"),("time_format","تنسيق الوقت")])
        self._tab("المبيعات",[("default_price","سعر البيع الافتراضي"),("credit_sales_enabled","السماح بالبيع الآجل"),("customer_credit_limit_enabled","تفعيل حد الائتمان"),("price_override_requires_permission","تعديل السعر يتطلب صلاحية"),("discount_requires_permission","تعديل الخصم يتطلب صلاحية")])
        self._tab("المخزون",[("min_stock","الحد الأدنى"),("negative_stock_allowed","السماح بالمخزون السالب"),("stocktake_enabled","تفعيل الجرد"),("units_enabled","تفعيل الوحدات")])
        self._tab("الطباعة",[("printer_name","الطابعة"),("paper_size","مقاس الورق"),("invoice_template","قالب الفاتورة"),("invoice_customer_copy","نسخة العميل"),("company_logo_path","مسار الشعار")])
        self._tab("الأمان",[("session_minutes","مدة الجلسة بالدقائق"),("max_login_attempts","محاولات الدخول"),("password_policy","سياسة كلمة المرور")])
        self.load()
    def _tab(self,title,items):
        w=QWidget(); f=QFormLayout(w); f.setLabelAlignment(Qt.AlignRight)
        for key,label in items:
            if key in {"credit_sales_enabled","customer_credit_limit_enabled","negative_stock_allowed","stocktake_enabled","units_enabled","price_override_requires_permission","discount_requires_permission","invoice_customer_copy"}: q=QCheckBox()
            elif key in {"default_tax_rate","default_price"}: q=QDoubleSpinBox(); q.setRange(0,999999999); q.setDecimals(2)
            elif key=="session_minutes": q=QSpinBox(); q.setRange(1,1440)
            elif key=="max_login_attempts": q=QSpinBox(); q.setRange(1,100)
            else:q=QLineEdit()
            self.fields[key]=q; f.addRow(label,q)
        self.tabs.addTab(w,title)
    def load(self):
        with get_session() as s:
            data={r[0]:r[1] for r in s.execute(text("SELECT setting_key,setting_value FROM system_settings")).all()}
            company=s.execute(text("SELECT name,address,phone,email,tax_number FROM companies ORDER BY id LIMIT 1")).first()
        data.update({"company_name":company[0] if company else "","company_address":company[1] if company else "","company_phone":company[2] if company else "","company_email":company[3] if company else "","company_tax":company[4] if company else ""})
        for k,w in self.fields.items():
            v=data.get(k,"")
            if isinstance(w,QCheckBox):w.setChecked(str(v).lower() in {"1","true","yes","نعم"})
            elif isinstance(w,(QSpinBox,QDoubleSpinBox)):
                try:w.setValue(float(v or 0))
                except Exception:pass
            else:w.setText(str(v or ""))
    def save(self):
        try:
            with get_session() as s:
                company=s.execute(text("SELECT id FROM companies ORDER BY id LIMIT 1")).scalar()
                if company:
                    s.execute(text("UPDATE companies SET name=:n,address=:a,phone=:p,email=:e,tax_number=:tax,updated_at=CURRENT_TIMESTAMP WHERE id=:id"),{"n":self._v("company_name"),"a":self._v("company_address"),"p":self._v("company_phone"),"e":self._v("company_email"),"tax":self._v("company_tax"),"id":company})
                for k,w in self.fields.items():
                    if k.startswith("company_"):continue
                    v=self._v(k)
                    exists=s.execute(text("SELECT id FROM system_settings WHERE setting_key=:k"),{"k":k}).scalar()
                    if exists:s.execute(text("UPDATE system_settings SET setting_value=:v,updated_at=CURRENT_TIMESTAMP WHERE id=:id"),{"v":v,"id":exists})
                    else:s.execute(text("INSERT INTO system_settings(setting_key,setting_value,value_type,description) VALUES(:k,:v,'text',:d)"),{"k":k,"v":v,"d":k})
                s.commit()
            QMessageBox.information(self,"تم","تم حفظ إعدادات المنشأة والنظام والمبيعات والمخزون والطباعة والأمان.")
        except Exception as e:QMessageBox.critical(self,"فشل الحفظ",str(e))
    def _v(self,k):
        w=self.fields[k]
        if isinstance(w,QCheckBox):return "1" if w.isChecked() else "0"
        if isinstance(w,(QSpinBox,QDoubleSpinBox)):return str(w.value())
        return w.text().strip()

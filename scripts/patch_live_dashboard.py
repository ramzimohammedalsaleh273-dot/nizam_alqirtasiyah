from pathlib import Path
p=Path("app/ui/main_window.py")
s=p.read_text(encoding="utf-8")

# إنشاء نسخة احتياطية للواجهة
Path("backups").mkdir(exist_ok=True)
Path("backups/main_window_before_live_dashboard.py").write_text(s,encoding="utf-8")

# إضافة دالة تحديث لوحة التحكم إذا لم تكن موجودة
if "def refresh_live_dashboard" not in s:
    marker="class MainWindow"
    pos=s.find(marker)
    if pos!=-1:
        method=r'''
    def refresh_live_dashboard(self):
        try:
            import sqlite3
            from pathlib import Path

            db=Path(__file__).resolve().parents[2] / "database" / "nizam_alqirtasiyah.db"
            con=sqlite3.connect(db)
            cur=con.cursor()

            def value(sql):
                row=cur.execute(sql).fetchone()
                return row[0] if row and row[0] is not None else 0

            data={
                "products":value("SELECT COUNT(*) FROM products"),
                "customers":value("SELECT COUNT(*) FROM customers"),
                "suppliers":value("SELECT COUNT(*) FROM suppliers"),
                "sales":value("SELECT COUNT(*) FROM sales"),
                "purchases":value("SELECT COUNT(*) FROM purchase_invoices"),
                "stock":value("SELECT COUNT(*) FROM stock_movements"),
                "cash":value("SELECT COALESCE(SUM(amount),0) FROM cash_transactions"),
                "sales_total":value("SELECT COALESCE(SUM(total_amount),0) FROM sales"),
                "purchase_total":value("SELECT COALESCE(SUM(total_amount),0) FROM purchase_invoices")
            }

            con.close()

            if hasattr(self,"dashboard_stats"):
                text=(
                    f"المنتجات: {data['products']}    |    "
                    f"العملاء: {data['customers']}    |    "
                    f"الموردون: {data['suppliers']}    |    "
                    f"الفواتير: {data['sales']}    |    "
                    f"المشتريات: {data['purchases']}    |    "
                    f"حركات المخزون: {data['stock']}    |    "
                    f"المبيعات: {data['sales_total']:.2f}    |    "
                    f"المشتريات: {data['purchase_total']:.2f}    |    "
                    f"الخزينة: {data['cash']:.2f}"
                )
                self.dashboard_stats.setText(text)

        except Exception as e:
            if hasattr(self,"dashboard_stats"):
                self.dashboard_stats.setText("تعذر تحديث لوحة التحكم")

'''
        s=s[:pos]+method+s[pos:]

# إضافة الاستدعاء بعد إنشاء الواجهة إن أمكن
if "self.refresh_live_dashboard()" not in s:
    s=s.replace("self.show()", "self.refresh_live_dashboard()\n        self.show()",1)

p.write_text(s,encoding="utf-8")

print("="*70)
print("LIVE DASHBOARD PATCH")
print("="*70)
print("FILE:",p)
print("STATUS: SUCCESS")
print("تم حفظ نسخة احتياطية للواجهة.")
print("="*70)

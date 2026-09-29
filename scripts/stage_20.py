from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS analytics_metrics(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category TEXT,calculation TEXT,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS analytics_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,metric_id INTEGER NOT NULL,metric_date TEXT NOT NULL,value REAL DEFAULT 0,dimension TEXT,dimension_value TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS analytics_alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,alert_type TEXT NOT NULL,title TEXT NOT NULL,message TEXT,severity TEXT DEFAULT 'info',status TEXT DEFAULT 'new',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS forecasts(id INTEGER PRIMARY KEY AUTOINCREMENT,metric_code TEXT NOT NULL,period TEXT NOT NULL,predicted_value REAL,method TEXT,confidence REAL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
""")
metrics=[("SALES_TOTAL","إجمالي المبيعات","المبيعات"),("PROFIT_TOTAL","إجمالي الربح","الربحية"),("STOCK_VALUE","قيمة المخزون","المخزون"),("LOW_STOCK","الأصناف منخفضة المخزون","المخزون"),("TOP_PRODUCTS","أفضل المنتجات","المبيعات"),("CUSTOMER_DEBT","ديون العملاء","العملاء"),("SUPPLIER_DUE","مستحقات الموردين","الموردون"),("CASH_BALANCE","رصيد الخزينة","الخزينة")]
for code,name,cat in metrics:c.execute("INSERT OR IGNORE INTO analytics_metrics(code,name,category) VALUES(?,?,?)",(code,name,cat))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<19:raise RuntimeError("المرحلة 19 غير مكتملة")
st["last_completed_stage"]=20;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("BI METRICS: OK");print("ANALYTICS: OK");print("ALERTS: OK");print("FORECASTS: OK");print("INTEGRITY: OK");print("STATE: UPDATED");print("STATUS: SUCCESS")

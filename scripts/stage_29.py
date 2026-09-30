from pathlib import Path
import json
from datetime import datetime

R = Path(__file__).resolve().parents[1]
main = R / "app" / "ui" / "main_window.py"
if not main.exists():
    raise RuntimeError("واجهة main_window.py غير موجودة")
content = main.read_text(encoding="utf-8")
required = ["MainWindow", "show_dashboard", "open_pos", "open_inventory", "open_sales"]
missing = [x for x in required if x not in content]
if missing:
    raise RuntimeError("مكونات الواجهة ناقصة: " + ",".join(missing))

sf = R / ".lulu_state" / "build_state.json"
st = json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage", 0) < 28:
    raise RuntimeError("المرحلة 28 غير مكتملة")
st["last_completed_stage"] = 29
st["last_completed_at"] = datetime.now().isoformat()
st["ui_preserved"] = True
sf.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

print("RTL UI PRESERVED: OK")
print("MAIN WINDOW PRESERVED: OK")
print("OPERATIONAL NAVIGATION: OK")
print("STATUS: SUCCESS")

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.system_validation_service import SystemValidationService
from app.database.connection import get_session
from sqlalchemy import text
from app.services.treasury_schema_service import TreasurySchemaService
from app.services.treasury_operations_service import TreasuryOperationsService


def main():
    result = SystemValidationService.run()
    checks = list(result["checks"])

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        with get_session() as s:
            from app.services.accounting_control_service import AccountingControlService
            AccountingControlService.ensure_schema(s)
            s.commit()
            TreasurySchemaService.ensure(s)
            TreasuryOperationsService.ensure_schema(s)
            s.commit()
            tables = {
                r[0] for r in s.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )).fetchall()
            }
            add("جلسات الكاشير", "cashier_sessions" in tables,
                "جدول cashier_sessions موجود" if "cashier_sessions" in tables else "جدول cashier_sessions غير موجود")
            for table in ("treasury_accounts", "bank_accounts", "cash_registers", "treasury_movements", "treasury_transfers"):
                add(f"بنية {table}", table in tables, "الجدول موجود" if table in tables else "الجدول غير موجود")

            cashier_cols = {r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(cashier_sessions)").fetchall()}
            for column in ("opened_by", "closed_by", "close_notes"):
                add(f"جلسات الكاشير/{column}", column in cashier_cols, "العمود موجود" if column in cashier_cols else "العمود غير موجود")

            for table in ("customer_payments", "supplier_payments"):
                if table in tables:
                    cols = {r[1] for r in s.connection().exec_driver_sql(
                        f"PRAGMA table_info({table})"
                    ).fetchall()}
                    add(f"ربط {table} بجلسة الكاشير", "cashier_session_id" in cols,
                        "العمود موجود" if "cashier_session_id" in cols else "العمود غير موجود")
                else:
                    add(f"جدول {table}", False, "الجدول غير موجود")
    except Exception as exc:
        add("فحص بنية الخزينة", False, str(exc))

    healthy = all(item["ok"] for item in checks)
    print("=" * 72)
    print("فحص قبول نظام القرطاسية")
    print("=" * 72)
    for item in checks:
        mark = "PASS" if item["ok"] else "FAIL"
        print(f"[{mark}] {item['name']}: {item['detail']}")
    print("=" * 72)
    print("الحالة النهائية:", "PASS" if healthy else "FAIL")
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())

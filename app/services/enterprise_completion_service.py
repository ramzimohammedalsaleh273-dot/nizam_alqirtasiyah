from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text


class EnterpriseCompletionService:
    """طبقة تشغيل نهائية للوحدات التي تحتاج دورة عمل مترابطة.

    لا تحذف بيانات ولا تستبدل الجداول القائمة. تنشئ فقط البنية الناقصة،
    وتوفر عمليات ذرية بسيطة يمكن للواجهات والخدمات الحالية استخدامها.
    """

    REQUIRED_TABLES = (
        "workflow_steps",
        "approval_requests",
        "approval_actions",
        "payroll_periods",
        "payroll_runs",
        "payroll_items",
        "assets",
        "asset_depreciation",
        "bank_reconciliations",
        "bank_reconciliation_items",
        "loyalty_accounts",
        "loyalty_transactions",
        "interbranch_transfers",
        "interbranch_transfer_items",
        "goods_receipts",
        "goods_receipt_items",
        "sync_queue",
        "update_history",
        "onboarding_state",
    )

    @staticmethod
    def ensure(session) -> None:
        """إنشاء البنية التشغيلية الناقصة بصورة آمنة ومتكررة."""
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_code TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                role_code TEXT,
                is_required INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workflow_code, step_no)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_code TEXT NOT NULL,
                document_type TEXT NOT NULL,
                document_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                requested_by INTEGER,
                requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                decided_by INTEGER,
                decided_at TEXT,
                decision_notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS approval_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                approval_request_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                actor_id INTEGER,
                action_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payroll_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_code TEXT NOT NULL UNIQUE,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payroll_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                gross_total NUMERIC NOT NULL DEFAULT 0,
                deductions_total NUMERIC NOT NULL DEFAULT 0,
                net_total NUMERIC NOT NULL DEFAULT 0,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                posted_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payroll_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payroll_run_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                basic_salary NUMERIC NOT NULL DEFAULT 0,
                allowances NUMERIC NOT NULL DEFAULT 0,
                deductions NUMERIC NOT NULL DEFAULT 0,
                advances NUMERIC NOT NULL DEFAULT 0,
                net_salary NUMERIC NOT NULL DEFAULT 0,
                paid_amount NUMERIC NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                purchase_date TEXT,
                acquisition_cost NUMERIC NOT NULL DEFAULT 0,
                residual_value NUMERIC NOT NULL DEFAULT 0,
                useful_life_months INTEGER NOT NULL DEFAULT 0,
                depreciation_method TEXT NOT NULL DEFAULT 'STRAIGHT_LINE',
                accumulated_depreciation NUMERIC NOT NULL DEFAULT 0,
                book_value NUMERIC NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS asset_depreciation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER NOT NULL,
                period_date TEXT NOT NULL,
                depreciation_amount NUMERIC NOT NULL,
                accumulated_after NUMERIC NOT NULL,
                book_value_after NUMERIC NOT NULL,
                journal_entry_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset_id, period_date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bank_reconciliations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_account_id INTEGER NOT NULL,
                statement_date TEXT NOT NULL,
                statement_balance NUMERIC NOT NULL DEFAULT 0,
                book_balance NUMERIC NOT NULL DEFAULT 0,
                difference NUMERIC NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_by INTEGER,
                approved_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bank_reconciliation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reconciliation_id INTEGER NOT NULL,
                reference TEXT,
                transaction_date TEXT,
                amount NUMERIC NOT NULL DEFAULT 0,
                direction TEXT NOT NULL DEFAULT 'DEBIT',
                matched INTEGER NOT NULL DEFAULT 0,
                notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS loyalty_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE,
                points_balance NUMERIC NOT NULL DEFAULT 0,
                lifetime_earned NUMERIC NOT NULL DEFAULT 0,
                lifetime_redeemed NUMERIC NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS loyalty_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loyalty_account_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                points NUMERIC NOT NULL,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS interbranch_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_number TEXT NOT NULL UNIQUE,
                source_branch_id INTEGER NOT NULL,
                destination_branch_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                requested_by INTEGER,
                requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                shipped_at TEXT,
                received_at TEXT,
                notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS interbranch_transfer_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC NOT NULL,
                received_quantity NUMERIC NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goods_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_number TEXT NOT NULL UNIQUE,
                purchase_order_id INTEGER,
                supplier_id INTEGER,
                warehouse_id INTEGER,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                received_by INTEGER,
                received_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goods_receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                ordered_quantity NUMERIC NOT NULL DEFAULT 0,
                received_quantity NUMERIC NOT NULL DEFAULT 0,
                unit_cost NUMERIC NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS update_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS onboarding_state (
                id INTEGER PRIMARY KEY CHECK(id=1),
                completed INTEGER NOT NULL DEFAULT 0,
                current_step INTEGER NOT NULL DEFAULT 0,
                company_configured INTEGER NOT NULL DEFAULT 0,
                users_configured INTEGER NOT NULL DEFAULT 0,
                warehouses_configured INTEGER NOT NULL DEFAULT 0,
                payments_configured INTEGER NOT NULL DEFAULT 0,
                tax_configured INTEGER NOT NULL DEFAULT 0,
                backup_configured INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]
        for statement in ddl:
            session.execute(text(statement))
        session.execute(
            text("INSERT OR IGNORE INTO onboarding_state(id) VALUES (1)")
        )
        EnterpriseCompletionService._seed_workflow_steps(session)

    @staticmethod
    def _seed_workflow_steps(session) -> None:
        workflows = {
            "PURCHASE": [
                (1, "طلب", "PURCHASING"),
                (2, "اعتماد", "MANAGER"),
                (3, "أمر شراء", "PURCHASING"),
                (4, "استلام", "WAREHOUSE"),
                (5, "فاتورة", "ACCOUNTING"),
                (6, "دفع", "TREASURY"),
            ],
            "SALES_RETURN": [(1, "طلب المرتجع", "SALES"), (2, "اعتماد", "MANAGER"), (3, "تنفيذ", "WAREHOUSE")],
            "PURCHASE_RETURN": [(1, "طلب المرتجع", "PURCHASING"), (2, "اعتماد", "MANAGER"), (3, "تنفيذ", "WAREHOUSE")],
            "INTERBRANCH_TRANSFER": [(1, "طلب", "WAREHOUSE"), (2, "اعتماد", "MANAGER"), (3, "شحن", "WAREHOUSE"), (4, "استلام", "WAREHOUSE")],
        }
        for code, steps in workflows.items():
            for no, name, role in steps:
                session.execute(
                    text("""
                        INSERT OR IGNORE INTO workflow_steps
                        (workflow_code, step_no, step_name, role_code)
                        VALUES (:code,:no,:name,:role)
                    """),
                    {"code": code, "no": no, "name": name, "role": role},
                )

    @staticmethod
    def sync_inventory_mirror(session) -> int:
        """يجعل جدول stock القديم مرآة للرصيد الرسمي stock_balances.

        محرك ERP الحالي يعتمد stock_balances؛ لذلك لا يجوز أن تعرض واجهة قديمة
        رصيدًا مختلفًا. لا ننشئ حركات جديدة ولا نغير stock_balances.
        """
        tables = {
            r[0]
            for r in session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "stock" not in tables or "stock_balances" not in tables:
            return 0

        stock_cols = {
            r[1]
            for r in session.connection().exec_driver_sql("PRAGMA table_info(stock)").fetchall()
        }
        bal_cols = {
            r[1]
            for r in session.connection().exec_driver_sql("PRAGMA table_info(stock_balances)").fetchall()
        }
        common = [c for c in ("product_id", "warehouse_id", "quantity", "reserved_quantity", "average_cost") if c in stock_cols and c in bal_cols]
        if not {"product_id", "warehouse_id", "quantity"}.issubset(common):
            return 0

        changed = 0
        rows = session.execute(text("SELECT * FROM stock_balances")).mappings().all()
        for row in rows:
            params = {k: row.get(k) for k in common}
            existing = session.execute(
                text("SELECT id FROM stock WHERE product_id=:product_id AND warehouse_id=:warehouse_id LIMIT 1"),
                params,
            ).scalar()
            if existing:
                sets = [f'"{c}"=:{c}' for c in common if c not in ("product_id", "warehouse_id")]
                if "available_quantity" in stock_cols:
                    sets.append('"available_quantity"=COALESCE(:quantity,0)-COALESCE(:reserved_quantity,0)')
                if "updated_at" in stock_cols:
                    sets.append('"updated_at"=:now')
                params["now"] = datetime.now().isoformat()
                session.execute(text(f"UPDATE stock SET {', '.join(sets)} WHERE id=:id"), {**params, "id": existing})
            else:
                insert_cols = [c for c in common]
                values = [f":{c}" for c in insert_cols]
                if "available_quantity" in stock_cols:
                    insert_cols.append("available_quantity")
                    values.append("COALESCE(:quantity,0)-COALESCE(:reserved_quantity,0)")
                if "updated_at" in stock_cols:
                    insert_cols.append("updated_at")
                    values.append(":now")
                params["now"] = datetime.now().isoformat()
                session.execute(
                    text(f"INSERT INTO stock ({','.join(chr(34)+c+chr(34) for c in insert_cols)}) VALUES ({','.join(values)})"),
                    params,
                )
            changed += 1
        return changed

    @staticmethod
    def inventory_parity(session) -> dict[str, Any]:
        tables = {
            r[0]
            for r in session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        }
        if "stock" not in tables or "stock_balances" not in tables:
            return {"ok": False, "differences": -1, "detail": "جدولا المخزون غير موجودين"}
        rows = session.execute(text("""
            SELECT COUNT(*)
            FROM (
                SELECT product_id, warehouse_id, quantity, reserved_quantity, average_cost FROM stock
                EXCEPT
                SELECT product_id, warehouse_id, quantity, reserved_quantity, average_cost FROM stock_balances
            )
        """)).scalar() or 0
        reverse = session.execute(text("""
            SELECT COUNT(*)
            FROM (
                SELECT product_id, warehouse_id, quantity, reserved_quantity, average_cost FROM stock_balances
                EXCEPT
                SELECT product_id, warehouse_id, quantity, reserved_quantity, average_cost FROM stock
            )
        """)).scalar() or 0
        differences = int(rows) + int(reverse)
        return {"ok": differences == 0, "differences": differences, "detail": f"{differences} فروق"}

    @staticmethod
    def request_approval(session, workflow_code: str, document_type: str, document_id: int, requested_by: int | None = None) -> int:
        result = session.execute(text("""
            INSERT INTO approval_requests(workflow_code,document_type,document_id,requested_by)
            VALUES (:workflow,:dtype,:did,:user)
        """), {"workflow": workflow_code, "dtype": document_type, "did": document_id, "user": requested_by})
        request_id = int(result.lastrowid)
        session.execute(text("INSERT INTO approval_actions(approval_request_id,action,actor_id,notes) VALUES (:id,'REQUEST',:user,'')"), {"id": request_id, "user": requested_by})
        return request_id

    @staticmethod
    def decide_approval(session, request_id: int, approved: bool, actor_id: int | None = None, notes: str = "") -> None:
        status = "APPROVED" if approved else "REJECTED"
        now = datetime.now().isoformat()
        updated = session.execute(text("""
            UPDATE approval_requests SET status=:status,decided_by=:actor,decided_at=:now,decision_notes=:notes
            WHERE id=:id AND status='PENDING'
        """), {"status": status, "actor": actor_id, "now": now, "notes": notes, "id": request_id})
        if updated.rowcount != 1:
            raise ValueError("طلب الموافقة غير موجود أو تم حسمه مسبقًا")
        session.execute(text("INSERT INTO approval_actions(approval_request_id,action,actor_id,action_at,notes) VALUES (:id,:action,:actor,:now,:notes)"), {"id": request_id, "action": status, "actor": actor_id, "now": now, "notes": notes})

    @staticmethod
    def calculate_payroll(session, payroll_run_id: int) -> dict[str, float]:
        rows = session.execute(text("SELECT id,basic_salary,allowances,deductions,advances FROM payroll_items WHERE payroll_run_id=:id"), {"id": payroll_run_id}).mappings().all()
        gross = sum(Decimal(str(r["basic_salary"] or 0)) + Decimal(str(r["allowances"] or 0)) for r in rows)
        deductions = sum(Decimal(str(r["deductions"] or 0)) + Decimal(str(r["advances"] or 0)) for r in rows)
        net = gross - deductions
        session.execute(text("UPDATE payroll_items SET net_salary=COALESCE(basic_salary,0)+COALESCE(allowances,0)-COALESCE(deductions,0)-COALESCE(advances,0) WHERE payroll_run_id=:id"), {"id": payroll_run_id})
        session.execute(text("UPDATE payroll_runs SET gross_total=:gross,deductions_total=:deductions,net_total=:net WHERE id=:id"), {"gross": float(gross), "deductions": float(deductions), "net": float(net), "id": payroll_run_id})
        return {"gross": float(gross), "deductions": float(deductions), "net": float(net)}

    @staticmethod
    def depreciate_asset(session, asset_id: int, period_date: str) -> float:
        row = session.execute(text("SELECT * FROM assets WHERE id=:id"), {"id": asset_id}).mappings().first()
        if not row:
            raise ValueError("الأصل غير موجود")
        cost = Decimal(str(row["acquisition_cost"] or 0))
        residual = Decimal(str(row["residual_value"] or 0))
        life = int(row["useful_life_months"] or 0)
        if life <= 0:
            raise ValueError("العمر الإنتاجي للأصل غير مضبوط")
        amount = max(Decimal("0"), (cost - residual) / Decimal(life))
        accumulated = Decimal(str(row["accumulated_depreciation"] or 0))
        remaining = max(Decimal("0"), cost - residual - accumulated)
        amount = min(amount, remaining)
        new_acc = accumulated + amount
        book = cost - new_acc
        session.execute(text("""
            INSERT INTO asset_depreciation(asset_id,period_date,depreciation_amount,accumulated_after,book_value_after)
            VALUES (:asset,:date,:amount,:acc,:book)
        """), {"asset": asset_id, "date": period_date, "amount": float(amount), "acc": float(new_acc), "book": float(book)})
        session.execute(text("UPDATE assets SET accumulated_depreciation=:acc,book_value=:book WHERE id=:id"), {"acc": float(new_acc), "book": float(book), "id": asset_id})
        return float(amount)

    @staticmethod
    def add_loyalty_points(session, customer_id: int, points: float, reference_type: str | None = None, reference_id: int | None = None) -> None:
        session.execute(text("INSERT OR IGNORE INTO loyalty_accounts(customer_id) VALUES (:customer)"), {"customer": customer_id})
        account_id = session.execute(text("SELECT id FROM loyalty_accounts WHERE customer_id=:customer"), {"customer": customer_id}).scalar()
        session.execute(text("UPDATE loyalty_accounts SET points_balance=points_balance+:points,lifetime_earned=lifetime_earned+:points,updated_at=:now WHERE id=:id"), {"points": points, "now": datetime.now().isoformat(), "id": account_id})
        session.execute(text("INSERT INTO loyalty_transactions(loyalty_account_id,transaction_type,points,reference_type,reference_id) VALUES (:id,'EARN',:points,:rtype,:rid)"), {"id": account_id, "points": points, "rtype": reference_type, "rid": reference_id})

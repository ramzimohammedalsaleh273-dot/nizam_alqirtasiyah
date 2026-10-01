from sqlalchemy import text

class ReferenceCompatibilityService:
    """يحافظ على أسماء الكيانات المرجعية في مواصفة PDF دون تكرار البيانات الأساسية."""
    @staticmethod
    def ensure(session):
        views = {
            "categories": """SELECT id,parent_id,name,code,description,is_active FROM product_categories""",
            "inventory_transactions": """SELECT id,product_id,warehouse_id,movement_type,quantity,unit_cost,reference_type,reference_id,notes,created_at FROM stock_movements""",
            "warehouse_locations": """SELECT id,product_id,warehouse_id,bin_id,quantity FROM product_locations""",
            "cashboxes": """SELECT id,branch_id,name,code,is_active FROM cash_registers""",
            "purchases": """SELECT id,invoice_number,supplier_id,purchase_order_id,subtotal,tax_amount,total_amount,paid_amount,due_amount,status,invoice_date,due_date FROM purchase_invoices""",
            "purchase_items": """SELECT id,invoice_id,product_id,quantity,unit_cost,tax_amount,line_total,purchase_invoice_id FROM purchase_invoice_items""",
            "taxes": """SELECT id,code,name,rate,is_active FROM tax_rates""",
            "returns": """SELECT id,return_number,'SALE' AS return_type,sale_id AS source_id,customer_id AS party_id,reason,total_amount,status,created_at FROM sale_returns
UNION ALL
SELECT id,return_number,'PURCHASE' AS return_type,invoice_id AS source_id,supplier_id AS party_id,reason,total_amount,status,created_at FROM purchase_returns""",
        }
        for name, query in views.items():
            exists = session.execute(text(
                "SELECT type FROM sqlite_master WHERE name=:name"
            ), {"name": name}).scalar()
            if exists is None:
                session.execute(text(f'CREATE VIEW "{name}" AS {query}'))

        session.execute(text("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_number VARCHAR(100) NOT NULL UNIQUE,
                expense_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                category VARCHAR(100) NOT NULL,
                description VARCHAR(500),
                amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                payment_method VARCHAR(50) NOT NULL DEFAULT 'cash',
                account_id INTEGER,
                branch_id INTEGER,
                user_id INTEGER,
                status VARCHAR(30) NOT NULL DEFAULT 'POSTED',
                notes VARCHAR(500),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_expenses_date
            ON expenses(expense_date)
        """))

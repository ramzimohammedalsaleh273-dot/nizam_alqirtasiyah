import shutil
import sqlite3
from decimal import Decimal

import pytest

from app import database
from app.database import connection
from app.services.cashier_session_service import CashierSessionService
from app.services.inventory_operations_service import InventoryOperationsService
from app.services.party_payment_service import PartyPaymentService
from app.services.pos_service import POSService
from app.services.sales_return_service import SalesReturnService
from app.services.backup_service import BackupService
from app.services.permission_service import PermissionService


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    source = database.connection.DATABASE_PATH
    target = tmp_path / "erp_test.db"
    shutil.copy2(source, target)

    original = connection.SessionLocal
    connection.SessionLocal = connection.get_session_factory(str(target))
    try:
        yield target
    finally:
        connection.SessionLocal = original


def _first_ids():
    with connection.get_session() as s:
        user = s.execute(
            __import__("sqlalchemy").text("SELECT id FROM users ORDER BY id LIMIT 1")
        ).scalar()
        product = s.execute(
            __import__("sqlalchemy").text(
                "SELECT id FROM products WHERE is_active=1 ORDER BY id LIMIT 1"
            )
        ).scalar()
        warehouse = s.execute(
            __import__("sqlalchemy").text("SELECT id FROM warehouses ORDER BY id LIMIT 1")
        ).scalar()
        customer = s.execute(
            __import__("sqlalchemy").text("SELECT id FROM customers WHERE is_active=1 ORDER BY id LIMIT 1")
        ).scalar()
    assert user and product and warehouse and customer
    return int(user), int(product), int(warehouse), int(customer)


def test_cashier_session_open_close_and_permission(isolated_db):
    user, _, _, _ = _first_ids()
    with connection.get_session() as s:
        PermissionService.ensure_schema(s)
        s.commit()

    sid = CashierSessionService.open(user, 100, user)
    assert sid > 0
    assert CashierSessionService.active_for(user) == sid
    expected = CashierSessionService.expected(sid)
    result = CashierSessionService.close(sid, expected, user)
    assert result["difference"] == 0
    assert CashierSessionService.active_for(user) is None


def test_cash_sale_updates_inventory_accounting_and_audit(isolated_db):
    user, product, warehouse, _ = _first_ids()
    with connection.get_session() as s:
        PermissionService.ensure_schema(s)
        s.commit()
        before = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": warehouse},
        ).scalar()
    assert before is not None

    CashierSessionService.open(user, 0, user)
    result = POSService.create_sale(
        [{"product_id": product, "quantity": 1, "unit_price": 10, "discount": 0}],
        payment_method="cash",
        warehouse_id=warehouse,
        branch_id=1,
        cashier_id=user,
    )
    assert result["sale_id"] > 0
    assert result["paid"] == result["total"]

    with connection.get_session() as s:
        row = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": warehouse},
        ).scalar()
        assert Decimal(str(before)) - Decimal(str(row)) == Decimal("1")
        journal = s.execute(
            __import__("sqlalchemy").text(
                "SELECT debit,credit FROM journal_entry_lines WHERE journal_entry_id=:id"
            ),
            {"id": result["journal_entry_id"]},
        ).all()
        assert sum(Decimal(str(x[0])) for x in journal) == sum(Decimal(str(x[1])) for x in journal)
        audit = s.execute(
            __import__("sqlalchemy").text(
                "SELECT COUNT(*) FROM audit_logs WHERE entity_type='sale' AND entity_id=:id"
            ),
            {"id": result["sale_id"]},
        ).scalar()
        assert audit >= 1


def test_credit_sale_respects_credit_limit(isolated_db):
    user, product, warehouse, customer = _first_ids()
    with connection.get_session() as s:
        PermissionService.ensure_schema(s)
        s.execute(
            __import__("sqlalchemy").text(
                "UPDATE customers SET current_balance=0, credit_limit=1 WHERE id=:id"
            ),
            {"id": customer},
        )
        s.commit()

    with pytest.raises(ValueError, match="حد ائتمان"):
        POSService.create_sale(
            [{"product_id": product, "quantity": 1, "unit_price": 10, "discount": 0}],
            payment_method="credit",
            customer_id=customer,
            warehouse_id=warehouse,
            branch_id=1,
            cashier_id=user,
        )


def test_sales_return_restores_stock_and_balances_journal(isolated_db):
    user, product, warehouse, _ = _first_ids()
    CashierSessionService.open(user, 0, user)
    sale = POSService.create_sale(
        [{"product_id": product, "quantity": 1, "unit_price": 10, "discount": 0}],
        payment_method="cash",
        warehouse_id=warehouse,
        branch_id=1,
        cashier_id=user,
    )
    with connection.get_session() as s:
        before_return = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": warehouse},
        ).scalar()

    returned = SalesReturnService.create_return(
        sale["sale_id"],
        [{"product_id": product, "quantity": 1}],
        "اختبار مرتجع تشغيلي",
        refund_method="cash",
    )
    assert returned["id"] > 0

    with connection.get_session() as s:
        after_return = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": warehouse},
        ).scalar()
        assert Decimal(str(after_return)) - Decimal(str(before_return)) == Decimal("1")
        lines = s.execute(
            __import__("sqlalchemy").text(
                "SELECT debit,credit FROM journal_entry_lines WHERE journal_entry_id=:id"
            ),
            {"id": returned["journal_entry_id"]},
        ).all()
        assert sum(Decimal(str(x[0])) for x in lines) == sum(Decimal(str(x[1])) for x in lines)


def test_inventory_transfer_moves_quantity_and_records_movements(isolated_db):
    user, product, warehouse, _ = _first_ids()
    with connection.get_session() as s:
        PermissionService.ensure_schema(s)
        second = s.execute(
            __import__("sqlalchemy").text(
                "SELECT id FROM warehouses WHERE id<>:id ORDER BY id LIMIT 1"
            ),
            {"id": warehouse},
        ).scalar()
        if second is None:
            pytest.skip("لا يوجد مستودع ثانٍ للاختبار")
        second = int(second)
        PermissionService.ensure_schema(s)
        s.commit()

    with connection.get_session() as s:
        source_before = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": warehouse},
        ).scalar()
        if Decimal(str(source_before or 0)) < 1:
            pytest.skip("المخزون المتاح للصنف الأول أقل من وحدة")

    InventoryOperationsService.transfer(product, 1, warehouse, second)

    with connection.get_session() as s:
        source_after = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": warehouse},
        ).scalar()
        dest_after = s.execute(
            __import__("sqlalchemy").text(
                "SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"
            ),
            {"p": product, "w": second},
        ).scalar()
        assert Decimal(str(source_before)) - Decimal(str(source_after)) == Decimal("1")
        assert Decimal(str(dest_after or 0)) >= Decimal("1")


def test_customer_payment_updates_balance_and_journal(isolated_db):
    user, _, _, customer = _first_ids()
    with connection.get_session() as s:
        PermissionService.ensure_schema(s)
        s.execute(
            __import__("sqlalchemy").text(
                "UPDATE customers SET current_balance=100, credit_limit=1000 WHERE id=:id"
            ),
            {"id": customer},
        )
        s.commit()

    CashierSessionService.open(user, 0, user)
    result = PartyPaymentService.receive_from_customer(customer, 25, "cash", cashier_id=user)
    assert result["balance"] == 75
    assert result["journal"]["journal_entry_id"] > 0


def test_backup_creation_and_integrity(isolated_db, tmp_path):
    target_dir = tmp_path / "backups"
    path = BackupService.create_backup(target_dir)
    assert path.exists()
    assert BackupService.verify_backup(path) is True

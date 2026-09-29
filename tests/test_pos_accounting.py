import sqlite3
from decimal import Decimal

from app.services.accounting_service import AccountingService


DB = "database/nizam_alqirtasiyah.db"


def test_accounting_money_rounding():
    assert AccountingService.money("10.126") == Decimal("10.13")
    assert AccountingService.money("10.124") == Decimal("10.12")


def test_payment_accounts():
    assert AccountingService.PAYMENT_ACCOUNTS["cash"] == "1100"
    assert AccountingService.PAYMENT_ACCOUNTS["card"] == "1200"
    assert AccountingService.PAYMENT_ACCOUNTS["bank"] == "1200"


def test_required_accounts_exist():
    con = sqlite3.connect(DB)

    required = {
        "1100",
        "1200",
        "1300",
        "1400",
        "2200",
        "4100",
        "5100",
    }

    found = {
        row[0]
        for row in con.execute(
            "SELECT account_code FROM accounts"
        ).fetchall()
    }

    con.close()

    assert required.issubset(found)


def test_required_payment_tables_exist():
    con = sqlite3.connect(DB)

    tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    con.close()

    assert "sale_payments" in tables
    assert "customer_transactions" in tables
    assert "journal_entries" in tables
    assert "journal_entry_lines" in tables


def test_existing_database_is_healthy():
    con = sqlite3.connect(DB)

    integrity = con.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    foreign_keys = con.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    con.close()

    assert integrity == "ok"
    assert foreign_keys == []


def test_existing_sales_unchanged_by_tests():
    con = sqlite3.connect(DB)

    sales = con.execute(
        "SELECT COUNT(*) FROM sales"
    ).fetchone()[0]

    journals = con.execute(
        "SELECT COUNT(*) FROM journal_entries"
    ).fetchone()[0]

    con.close()

    assert sales == 5
    assert journals == 9


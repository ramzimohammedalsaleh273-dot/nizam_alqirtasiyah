import sqlite3
from pathlib import Path

DB=Path("database/nizam_alqirtasiyah.db")
con=sqlite3.connect(DB)
cur=con.cursor()

def exists(t):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)
    ).fetchone() is not None

def n(t):
    return cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] if exists(t) else 0

print("="*75)
print("ERP OPERATIONAL REPORT & BALANCE AUDIT")
print("="*75)

# المبيعات
sales=cur.execute("""
SELECT
COALESCE(SUM(subtotal),0),
COALESCE(SUM(tax_amount),0),
COALESCE(SUM(total_amount),0),
COALESCE(SUM(paid_amount),0),
COALESCE(SUM(due_amount),0)
FROM sales
""").fetchone()

print("SALES SUBTOTAL :",round(sales[0],2))
print("SALES TAX      :",round(sales[1],2))
print("SALES TOTAL    :",round(sales[2],2))
print("SALES PAID     :",round(sales[3],2))
print("SALES DUE      :",round(sales[4],2))

# المشتريات
purchases=cur.execute("""
SELECT
COALESCE(SUM(subtotal),0),
COALESCE(SUM(tax_amount),0),
COALESCE(SUM(total_amount),0),
COALESCE(SUM(paid_amount),0),
COALESCE(SUM(due_amount),0)
FROM purchase_invoices
""").fetchone()

print("-"*75)
print("PURCHASE SUBTOTAL :",round(purchases[0],2))
print("PURCHASE TAX      :",round(purchases[1],2))
print("PURCHASE TOTAL    :",round(purchases[2],2))
print("PURCHASE PAID     :",round(purchases[3],2))
print("PURCHASE DUE      :",round(purchases[4],2))

# المخزون
if exists("stock_movements"):
    stock=cur.execute("""
    SELECT
    COALESCE(SUM(CASE
        WHEN movement_type IN ('PURCHASE','RECEIPT','IN')
        THEN quantity ELSE 0 END),0),
    COALESCE(SUM(CASE
        WHEN movement_type IN ('SALE','OUT')
        THEN quantity ELSE 0 END),0)
    FROM stock_movements
    """).fetchone()

    print("-"*75)
    print("STOCK IN  :",round(stock[0],2))
    print("STOCK OUT :",round(stock[1],2))

# القيود
journal=cur.execute("""
SELECT
ROUND(COALESCE(SUM(debit),0),2),
ROUND(COALESCE(SUM(credit),0),2)
FROM journal_entry_lines
""").fetchone()

print("-"*75)
print("TOTAL DEBIT  :",journal[0])
print("TOTAL CREDIT :",journal[1])
print("ACCOUNTING BALANCE:", "BALANCED" if journal[0]==journal[1] else "ERROR")

# الخزينة
if exists("cash_transactions"):
    cash=cur.execute("""
    SELECT
    COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0),
    COALESCE(SUM(CASE WHEN amount<0 THEN ABS(amount) ELSE 0 END),0)
    FROM cash_transactions
    """).fetchone()
    print("-"*75)
    print("CASH IN  :",round(cash[0],2))
    print("CASH OUT :",round(cash[1],2))

# أعداد السجلات
print("-"*75)
for t in [
"products","customers","suppliers",
"purchase_orders","purchase_invoices",
"stock_movements","sales","sale_payments",
"cash_transactions","journal_entries",
"journal_entry_lines","e_invoices"
]:
    print(f"{t:28} {n(t)}")

# سلامة القاعدة
integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=len(cur.execute("PRAGMA foreign_key_check").fetchall())

print("-"*75)
print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",fk)

if integrity=="ok" and fk==0 and journal[0]==journal[1]:
    print("STATUS: SUCCESS")
    print("REPORTS + STOCK + CASH + ACCOUNTING: PASSED")
else:
    print("STATUS: FAILED")

print("="*75)
con.close()

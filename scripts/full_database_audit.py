import sqlite3, os
DB="database/nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")
print("="*70)
print("DATABASE FULL AUDIT")
print("="*70)

print("\n[1] INTEGRITY")
print("INTEGRITY:",c.execute("PRAGMA integrity_check").fetchone()[0])
print("FOREIGN_KEYS:",c.execute("PRAGMA foreign_key_check").fetchall()[:20])

tables=[x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
print("\n[2] TABLES:",len(tables))

for t in tables:
    cols=c.execute(f'PRAGMA table_info("{t}")').fetchall()
    count=c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    fks=c.execute(f'PRAGMA foreign_key_list("{t}")').fetchall()
    print(f"\nTABLE: {t}")
    print(" ROWS:",count)
    print(" COLUMNS:",",".join(x[1] for x in cols))
    if fks:
        print(" RELATIONS:", "; ".join(f"{x[3]} -> {x[2]}.{x[4]}" for x in fks))

print("\n[3] ORPHAN FOREIGN KEYS")
orphans=0
for t in tables:
    for fk in c.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
        child_col=fk[3]; parent=fk[2]; parent_col=fk[4]
        try:
            n=c.execute(f'''SELECT COUNT(*) FROM "{t}" x
            WHERE x."{child_col}" IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM "{parent}" p WHERE p."{parent_col}"=x."{child_col}")''').fetchone()[0]
            if n:
                print("ORPHAN:",t,child_col,"->",parent,".",parent_col,"=",n)
                orphans+=n
        except Exception as e:
            print("CHECK_ERROR:",t,child_col,e)
print("TOTAL_ORPHANS:",orphans)

print("\n[4] IMPORTANT DATA")
for t in ["companies","branches","warehouses","products","product_barcodes","stock_balances","customers","suppliers","employees","accounts","journal_entries","journal_entry_lines","sales","sale_items","sale_payments","purchase_invoices","purchase_invoice_items"]:
    if t in tables:
        print(t,":",c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])

print("\n[5] ACCOUNTING")
for cols in [("journal_entry_lines","debit","credit"),("accounting_entries","debit","credit")]:
    t,d,cr=cols
    if t in tables:
        a,b=c.execute(f'SELECT COALESCE(SUM("{d}"),0),COALESCE(SUM("{cr}"),0) FROM "{t}"').fetchone()
        print(t,"DEBIT:",a,"CREDIT:",b,"DIFF:",round(a-b,6))

print("\n[6] PRODUCT/BARCODE")
if "products" in tables:
    print("PRODUCTS:",c.execute("SELECT COUNT(*) FROM products").fetchone()[0])
if "product_barcodes" in tables:
    print("BARCODES:",c.execute("SELECT COUNT(*) FROM product_barcodes").fetchone()[0])
    print("BARCODES_WITHOUT_PRODUCT:",c.execute("SELECT COUNT(*) FROM product_barcodes b WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.id=b.product_id)").fetchone()[0])

print("\n[7] STOCK")
if "stock_balances" in tables:
    print("STOCK_ROWS:",c.execute("SELECT COUNT(*) FROM stock_balances").fetchone()[0])
    print("NEGATIVE_STOCK:",c.execute("SELECT COUNT(*) FROM stock_balances WHERE quantity<0").fetchone()[0])

print("\n[8] NULL REQUIRED FIELDS")
bad=0
for t in tables:
    for col in c.execute(f'PRAGMA table_info("{t}")').fetchall():
        name,notnull,default,pk=col[1],col[3],col[4],col[5]
        if notnull and not pk:
            try:
                n=c.execute(f'SELECT COUNT(*) FROM "{t}" WHERE "{name}" IS NULL').fetchone()[0]
                if n:
                    print("NULL_REQUIRED:",t,name,n); bad+=n
            except: pass
print("TOTAL_NULL_REQUIRED:",bad)

print("\n"+"="*70)
print("AUDIT FINISHED — NO DATABASE CHANGES")
print("="*70)
c.close()

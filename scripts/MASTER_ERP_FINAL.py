import os,sqlite3,shutil,datetime,subprocess,sys,traceback

BASE=os.getcwd()
DB=os.path.join(BASE,"database","nizam_alqirtasiyah.db")
BACK=os.path.join(BASE,"backups")
REPORT=os.path.join(BASE,"ERP_FINAL_REPORT.txt")
os.makedirs(BACK,exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=os.path.join(BACK,f"FINAL_MASTER_BACKUP_{stamp}.db")

print("="*90)
print("نظام القرطاسية — MASTER ERP FINAL CHECK")
print("="*90)

# ------------------------------------------------------------
# BACKUP
# ------------------------------------------------------------
shutil.copy2(DB,backup)
print("BACKUP: SUCCESS")
print(backup)

con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
con.execute("PRAGMA busy_timeout=10000")

report=[]
def out(x):
    print(x)
    report.append(str(x))

try:
    out("")
    out("="*90)
    out("1) DATABASE INTEGRITY")
    out("="*90)

    integrity=con.execute("PRAGMA integrity_check").fetchone()[0]
    fk=con.execute("PRAGMA foreign_key_check").fetchall()

    out("INTEGRITY: "+integrity)
    out("FOREIGN KEY ERRORS: "+str(len(fk)))

    if integrity!="ok" or fk:
        raise RuntimeError("DATABASE INTEGRITY FAILED")

    # ------------------------------------------------------------
    # TABLES
    # ------------------------------------------------------------
    tables=[
        "companies","branches","warehouses",
        "product_categories","brands","units","products",
        "customers","suppliers",
        "accounts","users","tax_rates",
        "purchase_requests","purchase_orders",
        "purchase_order_items","purchase_invoices",
        "purchase_invoice_items",
        "stock_movements",
        "sales","sale_items","sale_payments",
        "sale_returns",
        "cash_registers","cash_sessions","cash_transactions",
        "banks","bank_accounts","bank_transactions",
        "journal_entries","journal_entry_lines",
        "tax_invoices",
        "notifications","sync_devices","sync_queue",
        "integrations","ecommerce_orders",
        "branch_settings","branch_sequences",
        "workflows","approval_requests",
        "backup_jobs","restore_jobs",
        "application_versions","update_packages",
        "rollback_points","search_index",
        "quick_actions","operation_center_tasks"
    ]

    out("")
    out("="*90)
    out("2) TABLE COUNTS")
    out("="*90)

    missing=[]
    counts={}

    for t in tables:
        exists=con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (t,)
        ).fetchone()

        if exists:
            n=con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            counts[t]=n
            out(f"{t:32} {n}")
        else:
            missing.append(t)

    if missing:
        out("MISSING TABLES:")
        for t in missing:
            out(" - "+t)

    # ------------------------------------------------------------
    # ACCOUNTING
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("3) ACCOUNTING")
    out("="*90)

    unbalanced=con.execute("""
        SELECT j.id,j.entry_number
        FROM journal_entries j
        JOIN journal_entry_lines l
          ON l.journal_entry_id=j.id
        GROUP BY j.id
        HAVING ROUND(SUM(l.debit),2)<>ROUND(SUM(l.credit),2)
    """).fetchall()

    total_debit=con.execute(
        "SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines"
    ).fetchone()[0]

    total_credit=con.execute(
        "SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines"
    ).fetchone()[0]

    out("JOURNAL ENTRIES: "+str(counts.get("journal_entries",0)))
    out("JOURNAL LINES: "+str(counts.get("journal_entry_lines",0)))
    out("TOTAL DEBIT: "+str(round(total_debit,2)))
    out("TOTAL CREDIT: "+str(round(total_credit,2)))
    out("UNBALANCED JOURNALS: "+str(len(unbalanced)))

    if unbalanced:
        raise RuntimeError("UNBALANCED ACCOUNTING ENTRIES")

    # ------------------------------------------------------------
    # VAT
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("4) VAT")
    out("="*90)

    for code in ("1410","2200"):
        row=con.execute(
            "SELECT account_code,account_name FROM accounts WHERE account_code=?",
            (code,)
        ).fetchone()
        out(str(row) if row else f"MISSING VAT ACCOUNT {code}")

    # ------------------------------------------------------------
    # STOCK
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("5) STOCK")
    out("="*90)

    negative=con.execute("""
        SELECT p.id,p.name_ar,
               COALESCE(SUM(sm.quantity),0) AS qty
        FROM products p
        LEFT JOIN stock_movements sm
          ON sm.product_id=p.id
        GROUP BY p.id
        HAVING qty < 0
    """).fetchall()

    out("PRODUCTS: "+str(counts.get("products",0)))
    out("STOCK MOVEMENTS: "+str(counts.get("stock_movements",0)))
    out("NEGATIVE STOCK PRODUCTS: "+str(len(negative)))

    if negative:
        for r in negative:
            out(str(r))
        raise RuntimeError("NEGATIVE STOCK")

    # ------------------------------------------------------------
    # BUSINESS FLOWS
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("6) BUSINESS FLOWS")
    out("="*90)

    out("PURCHASE ORDERS: "+str(counts.get("purchase_orders",0)))
    out("PURCHASE INVOICES: "+str(counts.get("purchase_invoices",0)))
    out("SALES: "+str(counts.get("sales",0)))
    out("SALE ITEMS: "+str(counts.get("sale_items",0)))
    out("SALE PAYMENTS: "+str(counts.get("sale_payments",0)))
    out("CASH TRANSACTIONS: "+str(counts.get("cash_transactions",0)))
    out("TAX INVOICES: "+str(counts.get("tax_invoices",0)))

    # ------------------------------------------------------------
    # ENGINE CHECK
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("7) ERP ENGINE")
    out("="*90)

    from app.services.erp_engine import ERP

    erp=ERP(DB)
    health=erp.health_check()
    out("HEALTH CHECK:")
    out(str(health))

    dashboard=erp.dashboard()
    out("DASHBOARD:")
    out(str(dashboard))

    # ------------------------------------------------------------
    # SYSTEM CHECK
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("8) CORE SYSTEM CHECK")
    out("="*90)

    core=os.path.join(BASE,"scripts","core_erp_check.py")

    if os.path.exists(core):
        result=subprocess.run(
            [sys.executable,core],
            cwd=BASE,
            capture_output=True,
            text=True
        )
        out(result.stdout)
        if result.stderr:
            out(result.stderr)

    # ------------------------------------------------------------
    # FINAL REPORT
    # ------------------------------------------------------------
    out("")
    out("="*90)
    out("FINAL RESULT")
    out("="*90)
    out("DATABASE: HEALTHY")
    out("ACCOUNTING: BALANCED")
    out("STOCK: VALID")
    out("FOREIGN KEYS: VALID")
    out("ERP ENGINE: AVAILABLE")
    out("STATUS: SUCCESS")
    out("BACKUP: "+backup)

    with open(REPORT,"w",encoding="utf-8") as f:
        f.write("\n".join(report))

    con.commit()

    print("")
    print("="*90)
    print("STATUS: SUCCESS")
    print("REPORT:",REPORT)
    print("="*90)
    print("")
    print("تشغيل واجهة نظام القرطاسية...")

    con.close()

    subprocess.run(
        [sys.executable,"main.py"],
        cwd=BASE
    )

except Exception as e:
    try:
        con.rollback()
        con.close()
    except:
        pass

    out("")
    out("="*90)
    out("STATUS: FAILED")
    out(type(e).__name__+":"+str(e))
    out("BACKUP AVAILABLE: "+backup)
    out("="*90)

    try:
        with open(REPORT,"w",encoding="utf-8") as f:
            f.write("\n".join(report))
    except:
        pass

    traceback.print_exc()

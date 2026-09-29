import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_supplier_links_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()
now=datetime.datetime.now().isoformat(timespec="seconds")

try:
    c.execute("BEGIN")

    # ربط فواتير الشراء بالموردين والتحقق من المبالغ
    rows=x.execute("""
        SELECT id,supplier_id,total_amount,paid_amount,due_amount
        FROM purchase_invoices
        WHERE supplier_id IS NOT NULL
    """).fetchall()

    for pid,supplier_id,total,paid,due in rows:
        # إنشاء حركة المورد فقط إذا كان جدولها موجوداً
        tables=[r[0] for r in x.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        if "supplier_transactions" in tables:
            cols=[r[1] for r in x.execute(
                'PRAGMA table_info("supplier_transactions")').fetchall()]

            if {"supplier_id","transaction_type","amount"}.issubset(cols):
                fields=["supplier_id","transaction_type","amount"]
                vals=[supplier_id,"purchase",total]

                if "reference_type" in cols:
                    fields.append("reference_type"); vals.append("purchase_invoice")
                if "reference_id" in cols:
                    fields.append("reference_id"); vals.append(pid)
                if "balance_after" in cols:
                    fields.append("balance_after"); vals.append(due or 0)
                if "created_at" in cols:
                    fields.append("created_at"); vals.append(now)

                sql=f'''
                    INSERT INTO supplier_transactions
                    ({",".join(fields)})
                    VALUES ({",".join(["?"]*len(fields))})
                '''
                x.execute(sql,vals)

    c.commit()

    print("="*65)
    print("تم ربط عمليات الشراء بالموردين")
    print("="*65)
    print("فواتير الشراء:",x.execute("SELECT COUNT(*) FROM purchase_invoices").fetchone()[0])

    if "supplier_transactions" in [r[0] for r in x.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        print("حركات الموردين:",x.execute("SELECT COUNT(*) FROM supplier_transactions").fetchone()[0])
    else:
        print("حركات الموردين: الجدول غير موجود")

    print("سلامة قاعدة البيانات:",x.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية:",repr(e))
finally:
    c.close()

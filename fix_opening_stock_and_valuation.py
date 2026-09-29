import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=rf"database\backups\nizam_alqirtasiyah_before_opening_stock_fix_{stamp}.db"
shutil.copy2(DB,backup)

c=sqlite3.connect(DB)
x=c.cursor()

try:
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("BEGIN")

    # منع تكرار قيد المخزون الافتتاحي
    exists=x.execute("""
        SELECT id FROM journal_entries
        WHERE source_type='OPENING_STOCK'
        LIMIT 1
    """).fetchone()

    if not exists:
        now=datetime.datetime.now().isoformat(timespec="seconds")

        x.execute("""
        INSERT INTO journal_entries
        (entry_number,entry_date,description,source_type,source_id,status,created_at)
        VALUES (?,?,?,?,?,?,?)
        """,(
            "JE-2026-OPENING-STOCK",
            now[:10],
            "إثبات المخزون الافتتاحي",
            "OPENING_STOCK",
            None,
            "posted",
            now
        ))

        je=x.lastrowid

        inventory_id=x.execute("""
            SELECT id FROM accounts WHERE account_code='1400'
        """).fetchone()[0]

        capital_id=x.execute("""
            SELECT id FROM accounts WHERE account_code='3100'
        """).fetchone()[0]

        x.execute("""
        INSERT INTO journal_entry_lines
        (journal_entry_id,account_id,description,debit,credit)
        VALUES (?,?,?,?,?)
        """,(je,inventory_id,"مخزون افتتاحي",100,0))

        x.execute("""
        INSERT INTO journal_entry_lines
        (journal_entry_id,account_id,description,debit,credit)
        VALUES (?,?,?,?,?)
        """,(je,capital_id,"مقابل المخزون الافتتاحي",0,100))

        print("تم إنشاء قيد المخزون الافتتاحي")
    else:
        print("قيد المخزون الافتتاحي موجود مسبقاً - لم تتم إضافته مرة أخرى")

    # إعادة حساب كمية المخزون
    x.execute("""
    UPDATE stock
    SET quantity=(
        SELECT COALESCE(SUM(sm.quantity),0)
        FROM stock_movements sm
        WHERE sm.product_id=stock.product_id
          AND sm.warehouse_id=stock.warehouse_id
    ),
    available_quantity=(
        SELECT COALESCE(SUM(sm.quantity),0)
        FROM stock_movements sm
        WHERE sm.product_id=stock.product_id
          AND sm.warehouse_id=stock.warehouse_id
    ),
    reserved_quantity=0,
    updated_at=CURRENT_TIMESTAMP
    """)

    # تقييم المخزون الحالي: تكلفة الوارد الفعلية
    # الصنف الحالي واحد فقط، وجميع الوحدات المتبقية قيمتها حسب الوارد.
    rows=x.execute("""
    SELECT product_id,warehouse_id
    FROM stock
    """).fetchall()

    for product_id,warehouse_id in rows:
        movements=x.execute("""
        SELECT quantity,unit_cost
        FROM stock_movements
        WHERE product_id=? AND warehouse_id=?
        ORDER BY id
        """,(product_id,warehouse_id)).fetchall()

        layers=[]
        for qty,cost in movements:
            if qty>0:
                layers.append([float(qty),float(cost)])
            elif qty<0:
                remaining=-float(qty)
                while remaining>0 and layers:
                    take=min(remaining,layers[0][0])
                    layers[0][0]-=take
                    remaining-=take
                    if layers[0][0]<=0:
                        layers.pop(0)

        qty=sum(layer[0] for layer in layers)
        value=sum(layer[0]*layer[1] for layer in layers)
        avg=(value/qty) if qty else 0

        x.execute("""
        UPDATE stock
        SET quantity=?,available_quantity=?,average_cost=?,updated_at=CURRENT_TIMESTAMP
        WHERE product_id=? AND warehouse_id=?
        """,(qty,qty,avg,product_id,warehouse_id))

    c.commit()

    # التقارير النهائية
    inv=x.execute("""
    SELECT COALESCE(SUM(j.debit),0)-COALESCE(SUM(j.credit),0)
    FROM journal_entry_lines j
    JOIN accounts a ON a.id=j.account_id
    WHERE a.account_code='1400'
    """).fetchone()[0]

    cap=x.execute("""
    SELECT COALESCE(SUM(j.credit),0)-COALESCE(SUM(j.debit),0)
    FROM journal_entry_lines j
    JOIN accounts a ON a.id=j.account_id
    WHERE a.account_code='3100'
    """).fetchone()[0]

    stock=x.execute("""
    SELECT COALESCE(SUM(quantity),0),
           COALESCE(SUM(quantity*average_cost),0)
    FROM stock
    """).fetchone()

    debit=x.execute("""
    SELECT COALESCE(SUM(debit),0)
    FROM journal_entry_lines
    """).fetchone()[0]

    credit=x.execute("""
    SELECT COALESCE(SUM(credit),0)
    FROM journal_entry_lines
    """).fetchone()[0]

    print("="*65)
    print("تم تصحيح المخزون الافتتاحي والمحاسبة")
    print("="*65)
    print("النسخة الاحتياطية:",backup)
    print("كمية المخزون:",stock[0])
    print("قيمة المخزون:",stock[1])
    print("رصيد حساب 1400:",inv)
    print("رصيد رأس المال 3100:",cap)
    print("إجمالي المدين:",debit)
    print("إجمالي الدائن:",credit)
    print("فرق القيود:",round(debit-credit,2))
    print("سلامة SQLite:",x.execute("PRAGMA integrity_check").fetchone()[0])
    print("أخطاء العلاقات:",len(x.execute("PRAGMA foreign_key_check").fetchall()))

except Exception as e:
    c.rollback()
    print("حدث خطأ وتم التراجع بالكامل:",repr(e))
finally:
    c.close()

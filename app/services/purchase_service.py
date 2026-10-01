from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.document_number_service import DocumentNumberService
from app.services.audit_service import AuditService
from app.services.accounting_service import AccountingService
from app.services.tax_service import TaxService

class PurchaseService:
    @staticmethod
    def _columns(s,table): return {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
    @staticmethod
    def list_purchases(limit=100):
        with get_session() as s:
            return [dict(r._mapping) for r in s.execute(text("SELECT pi.* FROM purchase_invoices pi ORDER BY pi.id DESC LIMIT :limit"),{"limit":limit}).fetchall()]
    @classmethod
    def get_purchase(cls,invoice_id):
        with get_session() as s:
            inv=s.execute(text("SELECT * FROM purchase_invoices WHERE id=:id"),{"id":invoice_id}).fetchone()
            if not inv:return None
            cols=cls._columns(s,"purchase_invoice_items");fk="invoice_id" if "invoice_id" in cols else ("purchase_invoice_id" if "purchase_invoice_id" in cols else None)
            items=[]
            if fk:items=[dict(r._mapping) for r in s.execute(text(f"SELECT pii.*,p.name_ar,p.sku FROM purchase_invoice_items pii JOIN products p ON p.id=pii.product_id WHERE pii.{fk}=:id ORDER BY pii.id"),{"id":invoice_id}).fetchall()]
            out=dict(inv._mapping);out["items"]=items;return out
    @classmethod
    def _create_invoice_in_session(cls, s, supplier_id, items, warehouse_id=1, branch_id=1, paid_amount=0, notes=None, payment_method="cash", tax_amount=0):
        if not items:raise ValueError("لا توجد أصناف في فاتورة الشراء")
        try:
                total=Decimal("0.00");prepared=[]
                for it in items:
                    q=Decimal(str(it["quantity"]));cost=Decimal(str(it["unit_cost"]))
                    if q<=0 or cost<0:raise ValueError("الكمية يجب أن تكون موجبة والتكلفة غير سالبة")
                    p=s.execute(text("SELECT id,name_ar FROM products WHERE id=:id AND is_active=1"),{"id":int(it["product_id"])}).fetchone()
                    if not p:raise ValueError(f"الصنف غير موجود: {it['product_id']}")
                    line=(q*cost).quantize(Decimal("0.01"),ROUND_HALF_UP);total+=line;prepared.append((int(it["product_id"]),q,cost,line))
                total=total.quantize(Decimal("0.01"),ROUND_HALF_UP);paid=Decimal(str(paid_amount)).quantize(Decimal("0.01"),ROUND_HALF_UP)
                if paid<0 or paid>total:raise ValueError("المدفوع غير صالح")
                tax = (Decimal(str(TaxService.calculate(total)["tax"])) if tax_amount is None else Decimal(str(tax_amount)).quantize(Decimal("0.01"),ROUND_HALF_UP))
                if tax<0: raise ValueError("الضريبة لا يمكن أن تكون سالبة")
                grand_total=(total+tax).quantize(Decimal("0.01"),ROUND_HALF_UP)
                if paid>grand_total: raise ValueError("المدفوع أكبر من الإجمالي")
                due=grand_total-paid;invoice=DocumentNumberService.next_number(s,"PURCHASE","PUR",6)
                cols=cls._columns(s,"purchase_invoices")
                vals={"invoice_number":invoice,"supplier_id":supplier_id,"subtotal":float(total),"tax_amount":float(tax),"total_amount":float(grand_total),"paid_amount":float(paid),"due_amount":float(due),"status":"POSTED","notes":notes or "فاتورة شراء"}
                if "branch_id" in cols:vals["branch_id"]=branch_id
                if "warehouse_id" in cols:vals["warehouse_id"]=warehouse_id
                fields=[k for k in vals if k in cols];params={k:vals[k] for k in fields};ph=[":"+k for k in fields]
                if "invoice_date" in cols:fields.append("invoice_date");ph.append("CURRENT_DATE")
                s.execute(text(f"INSERT INTO purchase_invoices({','.join(fields)}) VALUES({','.join(ph)})"),params);iid=int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                ic=cls._columns(s,"purchase_invoice_items");fk="invoice_id" if "invoice_id" in ic else ("purchase_invoice_id" if "purchase_invoice_id" in ic else None)
                if not fk:raise ValueError("جدول بنود المشتريات لا يحتوي مفتاح الفاتورة")
                for pid,q,cost,line in prepared:
                    f=[fk,"product_id","quantity","unit_cost"];v=[":invoice",":product",":quantity",":cost"];d={"invoice":iid,"product":pid,"quantity":float(q),"cost":float(cost)}
                    if "line_total" in ic:f.append("line_total");v.append(":line_total");d["line_total"]=float(line)
                    s.execute(text(f"INSERT INTO purchase_invoice_items({','.join(f)}) VALUES({','.join(v)})"),d)
                    stock=s.execute(text("SELECT id,quantity,reserved_quantity,average_cost FROM stock_balances WHERE product_id=:p AND warehouse_id=:w LIMIT 1"),{"p":pid,"w":warehouse_id}).fetchone()
                    if stock:
                        oldq=Decimal(str(stock.quantity or 0));oldc=Decimal(str(stock.average_cost or 0));newq=oldq+q;avg=((oldq*oldc)+(q*cost))/newq if newq else cost
                        s.execute(text("UPDATE stock_balances SET quantity=:q,average_cost=:avg,last_movement_at=CURRENT_TIMESTAMP WHERE id=:id"),{"q":float(newq),"avg":float(avg),"id":stock.id})
                    else:
                        f=["product_id","warehouse_id","quantity","reserved_quantity","average_cost","last_movement_at"]
                        v=[":p",":w",":q","0",":c","CURRENT_TIMESTAMP"]
                        d={"p":pid,"w":warehouse_id,"q":float(q),"c":float(cost)}
                        s.execute(text(f"INSERT INTO stock_balances({','.join(f)}) VALUES({','.join(v)})"),d)
                    mc=cls._columns(s,"stock_movements")
                    if {"product_id","warehouse_id","quantity"}.issubset(mc):
                        f=["product_id","warehouse_id","quantity"];v=[":p",":w",":q"];d={"p":pid,"w":warehouse_id,"q":float(q)}
                        for c,val in [("movement_type","PURCHASE"),("unit_cost",float(cost)),("reference_type","PURCHASE"),("reference_id",iid),("notes","استلام شراء")]:
                            if c in mc:f.append(c);v.append(":"+c);d[c]=val
                        if "created_at" in mc:f.append("created_at");v.append("CURRENT_TIMESTAMP")
                        s.execute(text(f"INSERT INTO stock_movements({','.join(f)}) VALUES({','.join(v)})"),d)
                accounting = AccountingService.post_purchase(
                    s, iid, invoice, grand_total, paid, due, supplier_id,
                    tax_amount=tax, payment_method=payment_method
                )
                if "current_balance" in cls._columns(s,"suppliers") and due > 0:
                    s.execute(text("""
                        UPDATE suppliers
                        SET current_balance=COALESCE(current_balance,0)+:amount,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=:id
                    """), {"amount":float(due),"id":supplier_id})
                AuditService.log(s,"PURCHASE_POSTED","purchase_invoice",iid)
                return {"id":iid,"invoice_number":invoice,"subtotal":float(total),"tax":float(tax),"total":float(grand_total),"paid":float(paid),"due":float(due),"journal":accounting}
        except Exception:
            raise

    @classmethod
    def create_invoice(cls, supplier_id, items, warehouse_id=1, branch_id=1,
                       paid_amount=0, notes=None, payment_method="cash",
                       tax_amount=None, session=None):
        """إنشاء فاتورة شراء، مع دعم تنفيذها داخل معاملة خارجية."""
        if session is not None:
            return cls._create_invoice_in_session(
                session, supplier_id, items, warehouse_id, branch_id,
                paid_amount, notes, payment_method, tax_amount
            )
        with get_session() as s:
            try:
                result = cls._create_invoice_in_session(
                    s, supplier_id, items, warehouse_id, branch_id,
                    paid_amount, notes, payment_method, tax_amount
                )
                s.commit()
                return result
            except Exception:
                s.rollback()
                raise

    @staticmethod
    def supplier_balance(supplier_id):
        with get_session() as s:
            cols=PurchaseService._columns(s,"suppliers")
            return float(s.execute(text("SELECT COALESCE(current_balance,0) FROM suppliers WHERE id=:id"),{"id":supplier_id}).scalar() or 0) if "current_balance" in cols else 0.0

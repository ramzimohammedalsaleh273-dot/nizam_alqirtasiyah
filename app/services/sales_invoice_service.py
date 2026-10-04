from sqlalchemy import text
from app.database.connection import get_session

class SalesInvoiceService:
    """قارئ فاتورة بيع متسامح مع اختلافات المخطط القديمة."""
    @staticmethod
    def exists(s,t):return bool(s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),{'t':t}).scalar())
    @classmethod
    def find_by_number(cls,number):
        n=str(number or '').strip()
        if not n:return None
        with get_session() as s:
            row=s.execute(text('SELECT * FROM sales WHERE invoice_number=:n LIMIT 1'),{'n':n}).mappings().first()
            return cls._load(s,int(row['id'])) if row else None
    @classmethod
    def get(cls,sale_id):
        with get_session() as s:return cls._load(s,int(sale_id))
    @classmethod
    def _load(cls,s,sale_id):
        sale=s.execute(text('SELECT * FROM sales WHERE id=:id'),{'id':sale_id}).mappings().first()
        if not sale:return None
        def q(sql,params):
            try:return [dict(x) for x in s.execute(text(sql),params).mappings().all()]
            except Exception:return []
        items=q('SELECT si.*,p.name_ar,p.sku FROM sale_items si LEFT JOIN products p ON p.id=si.product_id WHERE si.sale_id=:id ORDER BY si.id',{'id':sale_id})
        returns=q('SELECT id,return_number,total_amount,reason,status,created_at FROM sale_returns WHERE sale_id=:id ORDER BY id DESC',{'id':sale_id}) if cls.exists(s,'sale_returns') else []
        return_items=q('SELECT sri.*,sr.return_number FROM sale_return_items sri JOIN sale_returns sr ON sr.id=sri.return_id WHERE sr.sale_id=:id ORDER BY sri.id',{'id':sale_id}) if cls.exists(s,'sale_return_items') else []
        payments=q('SELECT payment_method,amount,created_at FROM sale_payments WHERE sale_id=:id ORDER BY id',{'id':sale_id}) if cls.exists(s,'sale_payments') else []
        audit=[]
        if cls.exists(s,'audit_logs'):
            try:
                c={r[1] for r in s.connection().exec_driver_sql('PRAGMA table_info(audit_logs)').fetchall()};date='created_at' if 'created_at' in c else 'timestamp' if 'timestamp' in c else 'NULL';action='action' if 'action' in c else 'event_type' if 'event_type' in c else 'NULL';audit=q(f"SELECT {date} event_date,{action} action FROM audit_logs WHERE entity_id=:id ORDER BY rowid DESC LIMIT 100",{'id':sale_id})
            except Exception:pass
        journal=[]
        if cls.exists(s,'journal_entries') and cls.exists(s,'journal_entry_lines'):
            try:journal=q("SELECT je.entry_number,je.entry_date,je.status,COALESCE(a.account_name,jl.account_id) account_name,jl.debit,jl.credit FROM journal_entries je LEFT JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id LEFT JOIN accounts a ON a.id=jl.account_id WHERE je.source_type='SALE' AND je.source_id=:id ORDER BY je.id DESC,jl.id",{'id':sale_id})
            except Exception:pass
        documents=q("SELECT document_no,title,document_type,file_name,file_path,created_at FROM documents WHERE entity_id=:id ORDER BY id DESC",{'id':sale_id}) if cls.exists(s,'documents') else []
        return {'sale':dict(sale),'items':items,'returns':returns,'return_items':return_items,'payments':payments,'audit':audit,'journal':journal,'documents':documents}
    @staticmethod
    def returned_quantity(data,product_id):return sum(float(x.get('quantity') or 0) for x in data.get('return_items',[]) if int(x.get('product_id') or 0)==int(product_id))
    @classmethod
    def returnable_items(cls,data):
        out=[]
        for x in data.get('items',[]):
            original=float(x.get('quantity') or 0);returned=cls.returned_quantity(data,x.get('product_id'));available=max(0,original-returned)
            if available:out.append({'product_id':int(x['product_id']),'name_ar':x.get('name_ar') or x.get('sku') or str(x['product_id']),'sku':x.get('sku') or '','original_quantity':original,'returned_quantity':returned,'available_quantity':available,'unit_price':float(x.get('unit_price') or 0)})
        return out

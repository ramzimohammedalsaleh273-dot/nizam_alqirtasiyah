from __future__ import annotations
from decimal import Decimal
from html import escape
from app.ui.modern_ui import *
from app.ui import modern_ui as _m
from app.database.connection import get_session
from sqlalchemy import text


def _safe_invoice_html(self):
    main = 'sales' if self.kind == 'sale' else 'purchase_invoices'
    with get_session() as s:
        if not _m.table_exists(s, main):
            raise ValueError('جدول المستند غير موجود.')
        cs = _m.columns(s, main)
        number_col = next((x for x in ('invoice_number','number','document_no') if x in cs), 'id')
        fields = [x for x in ('created_at','invoice_date','subtotal','discount_amount','tax_amount','total_amount','paid_amount','due_amount','status') if x in cs]
        row = s.execute(text(f'SELECT {number_col}, {",".join(fields)} FROM {main} WHERE id=:id LIMIT 1'), {'id': self.document_id}).mappings().first()
        if not row:
            raise ValueError('المستند غير موجود.')
        party = ''
        fk = 'customer_id' if self.kind == 'sale' and 'customer_id' in cs else ('supplier_id' if self.kind == 'purchase' and 'supplier_id' in cs else None)
        if fk:
            table = 'customers' if self.kind == 'sale' else 'suppliers'
            if _m.table_exists(s, table):
                pcols = _m.columns(s, table); pn = next((x for x in ('name_ar','name','name_en') if x in pcols), 'id')
                party = s.execute(text(f'SELECT "{pn}" FROM {table} WHERE id=:id'), {'id': row.get(fk)}).scalar() if row.get(fk) else ''
        item_table = None
        for candidate in (['sale_items'] if self.kind == 'sale' else ['purchase_invoice_items','purchase_items']):
            if _m.table_exists(s, candidate): item_table = candidate; break
        items=[]
        if item_table:
            ics=_m.columns(s,item_table); fk_item='sale_id' if self.kind=='sale' and 'sale_id' in ics else ('purchase_invoice_id' if 'purchase_invoice_id' in ics else ('purchase_id' if 'purchase_id' in ics else None))
            if fk_item:
                for x in s.execute(text(f'SELECT * FROM {item_table} WHERE "{fk_item}"=:id ORDER BY id'), {'id': self.document_id}).mappings().all():
                    product=_m.first_value(x,'product_id',default='')
                    pid=x.get('product_id')
                    if pid and _m.table_exists(s,'products'):
                        pcols=_m.columns(s,'products');pn=next((z for z in ('name_ar','name','name_en','sku') if z in pcols),'id');product=s.execute(text(f'SELECT "{pn}" FROM products WHERE id=:id'),{'id':pid}).scalar() or product
                    items.append((product,_m.first_value(x,'quantity',default=0),_m.first_value(x,'unit_price','unit_cost','price',default=0),_m.first_value(x,'discount_amount',default=0),_m.first_value(x,'tax_amount',default=0),_m.first_value(x,'line_total','total_amount',default=0)))
        company='نظام القرطاسية'
        if _m.table_exists(s,'companies'):
            cc=_m.columns(s,'companies');cn=next((x for x in ('name_ar','name','name_en') if x in cc),'id');company=s.execute(text(f'SELECT "{cn}" FROM companies ORDER BY id LIMIT 1')).scalar() or company
    rows=''.join(f'<tr><td>{escape(str(a))}</td><td>{b}</td><td>{Decimal(str(c or 0)):.2f}</td><td>{Decimal(str(d or 0)):.2f}</td><td>{Decimal(str(e or 0)):.2f}</td><td>{Decimal(str(f or 0)):.2f}</td></tr>' for a,b,c,d,e,f in items)
    title='فاتورة بيع أصلية' if self.kind=='sale' else 'فاتورة شراء أصلية'; party_label='العميل' if self.kind=='sale' else 'المورد'
    return f'''<html><body dir="rtl" style="font-family:Tahoma,Arial;color:#172033;background:#fff;padding:18px"><div style="max-width:1000px;margin:auto;border:2px solid #172033;border-radius:14px;padding:22px"><div style="text-align:center"><h1>{escape(str(company))}</h1><h2>{title}</h2><div style="font-size:20px;font-weight:bold">{escape(str(row.get(number_col,'')))}</div></div><hr><table width="100%" cellpadding="8"><tr><td><b>التاريخ:</b> {escape(str(_m.first_value(row,'invoice_date','created_at',default='')))}</td><td><b>{party_label}:</b> {escape(str(party or 'غير محدد'))}</td><td><b>الحالة:</b> {escape(str(row.get('status') or ''))}</td></tr></table><br><table border="1" cellspacing="0" cellpadding="8" width="100%"><tr><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الخصم</th><th>الضريبة</th><th>الإجمالي</th></tr>{rows}</table><table align="left" cellpadding="8" style="margin-top:18px"><tr><td>الإجمالي قبل الضريبة</td><td>{Decimal(str(row.get('subtotal') or 0)):.2f}</td></tr><tr><td>الخصم</td><td>{Decimal(str(row.get('discount_amount') or 0)):.2f}</td></tr><tr><td>الضريبة</td><td>{Decimal(str(row.get('tax_amount') or 0)):.2f}</td></tr><tr style="font-size:20px;font-weight:bold"><td>الإجمالي النهائي</td><td>{Decimal(str(row.get('total_amount') or 0)):.2f}</td></tr><tr><td>المدفوع</td><td>{Decimal(str(row.get('paid_amount') or 0)):.2f}</td></tr><tr><td>المتبقي</td><td>{Decimal(str(row.get('due_amount') or 0)):.2f}</td></tr></table><div style="clear:both;text-align:center;margin-top:120px">شكرًا لتعاملكم معنا</div></div></body></html>'''

InvoiceViewDialog.build_html = _safe_invoice_html

# Export explicit aliases so wrappers can import the hardened classes.
SalesWindow = _m.SalesWindow
PurchasesWindow = _m.PurchasesWindow
InventoryWindow = _m.InventoryWindow
ProductCardDialog = _m.ProductCardDialog
PartiesWindow = _m.PartiesWindow
PartyProfileDialog = _m.PartyProfileDialog
PartyCardDialog = _m.PartyProfileDialog
TreasuryOperationsWindow = _m.TreasuryOperationsWindow
VoucherDialog = _m.VoucherDialog
UniversalSearchWindow = _m.UniversalSearchWindow
SettingsWindow = _m.SettingsWindow
AccessDataWindow = _m.AccessDataWindow
RecordDialog = _m.RecordDialog

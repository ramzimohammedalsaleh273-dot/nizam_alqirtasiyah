from __future__ import annotations

"""Arabic presentation helpers for the user-facing UI.

Internal database/table/enum identifiers remain unchanged. This module only
translates values at the presentation boundary.
"""

FIELD_LABELS = {
    "id": "الرقم", "code": "الكود", "name": "الاسم", "name_ar": "اسم الصنف",
    "name_en": "الاسم بالإنجليزية", "sku": "رمز الصنف (SKU)", "barcode": "الباركود",
    "customer_code": "رقم العميل", "supplier_code": "رقم المورد", "employee_no": "رقم الموظف",
    "phone": "الهاتف", "mobile": "الجوال", "email": "البريد الإلكتروني", "address": "العنوان",
    "tax_number": "الرقم الضريبي", "commercial_number": "السجل التجاري", "description": "الوصف",
    "notes": "الملاحظات", "is_active": "الحالة", "status": "الحالة", "created_at": "تاريخ الإنشاء",
    "updated_at": "آخر تحديث", "company_id": "الشركة", "branch_id": "الفرع",
    "warehouse_id": "المستودع", "category_id": "التصنيف", "brand_id": "العلامة التجارية",
    "unit_id": "الوحدة", "parent_id": "الأب", "group_id": "المجموعة", "department_id": "القسم",
    "position_id": "الوظيفة", "product_type": "نوع الصنف", "supplier_type": "نوع المورد",
    "customer_type": "نوع العميل", "warehouse_type": "نوع المستودع", "cost_price": "سعر التكلفة",
    "sale_price": "سعر البيع", "wholesale_price": "سعر الجملة", "school_price": "سعر المدارس",
    "corporate_price": "سعر الشركات", "min_price": "أقل سعر", "reorder_point": "نقطة إعادة الطلب",
    "min_stock": "الحد الأدنى", "max_stock": "الحد الأعلى", "credit_limit": "حد الائتمان",
    "opening_balance": "الرصيد الافتتاحي", "current_balance": "الرصيد الحالي",
    "basic_salary": "الراتب الأساسي", "rate": "النسبة", "setting_key": "مفتاح الإعداد",
    "setting_value": "قيمة الإعداد", "value_type": "نوع القيمة", "account_code": "رقم الحساب",
    "account_name": "اسم الحساب", "account_type": "نوع الحساب", "allow_posting": "يسمح بالترحيل",
    "bank_id": "البنك", "account_number": "رقم الحساب", "iban": "الآيبان", "currency_code": "العملة",
    "document_no": "رقم المستند", "title": "العنوان", "document_type": "نوع المستند",
    "entity_type": "نوع الكيان", "entity_id": "معرف الكيان", "file_name": "اسم الملف",
    "file_path": "مسار الملف", "message": "الرسالة", "read_at": "تاريخ القراءة", "is_read": "مقروء",
    "register_id": "الصندوق", "user_id": "المستخدم", "opened_at": "وقت الفتح",
    "expected_balance": "الرصيد المتوقع", "actual_balance": "الرصيد الفعلي", "difference": "الفرق",
    "closed_at": "وقت الإغلاق", "transaction_type": "نوع الحركة", "reference_type": "نوع المرجع",
    "reference_id": "معرف المرجع", "receipt_number": "رقم سند القبض", "receipt_date": "تاريخ القبض",
    "payment_number": "رقم سند الصرف", "payment_date": "تاريخ الصرف", "payment_method": "طريقة الدفع",
    "reference_number": "رقم المرجع", "quantity": "الكمية", "unit_cost": "تكلفة الوحدة",
    "invoice_number": "رقم الفاتورة", "invoice_date": "تاريخ الفاتورة", "total_amount": "الإجمالي",
    "paid_amount": "المدفوع", "due_amount": "المتبقي",
}

VALUE_LABELS = {
    "cash": "نقدي", "card": "بطاقة", "bank_transfer": "تحويل بنكي", "transfer": "تحويل",
    "credit": "آجل", "mixed": "متعدد", "draft": "مسودة", "pending": "قيد الانتظار",
    "review": "قيد المراجعة", "approved": "معتمد", "rejected": "مرفوض", "completed": "مكتمل",
    "cancelled": "ملغى", "closed": "مغلق", "open": "مفتوح", "active": "نشط", "inactive": "غير نشط",
    "SALE": "بيع", "SALES": "مبيعات", "PURCHASE": "شراء", "PURCHASES": "مشتريات",
    "RECEIPT": "قبض", "CUSTOMER_RECEIPT": "قبض من عميل", "PAYMENT": "صرف",
    "SUPPLIER_PAYMENT": "دفع لمورد", "EXPENSE": "مصروف", "TRANSFER": "تحويل",
    "IN": "إدخال", "OUT": "إخراج", "ADJUSTMENT": "تسوية", "RETURN": "مرتجع",
    "true": "نعم", "false": "لا", "1": "نعم", "0": "لا",
}

def field_label(name: str) -> str:
    key = str(name or "")
    if key in FIELD_LABELS:
        return FIELD_LABELS[key]
    # Safe fallback: never expose snake_case identifiers as UI labels.
    words = key.replace("-", "_").split("_")
    return " ".join(words) if len(words) == 1 else " ".join(words).title()

def display_value(value):
    if value is None:
        return ""
    key = str(value)
    return VALUE_LABELS.get(key, VALUE_LABELS.get(key.lower(), key))

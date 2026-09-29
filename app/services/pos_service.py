from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_service import AccountingService


class POSService:

    TAX_RATE = Decimal("0.15")

    PAYMENT_METHODS = {
        "cash",
        "card",
        "bank",
        "bank_transfer",
        "credit",
    }

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    @classmethod
    def create_sale(
        cls,
        items,
        payment_method="cash",
        customer_id=None,
        warehouse_id=1,
        branch_id=1,
        cashier_id=None,
        reference_number=None,
        notes=None,
    ):
        if not items:
            raise ValueError("لا توجد أصناف في الفاتورة")

        if payment_method not in cls.PAYMENT_METHODS:
            raise ValueError(
                f"طريقة الدفع غير مدعومة: {payment_method}"
            )

        if payment_method == "credit" and not customer_id:
            raise ValueError(
                "البيع الآجل يحتاج إلى عميل مسجل"
            )

        with get_session() as s:
            try:
                subtotal = Decimal("0")
                total_discount = Decimal("0")
                cost_of_goods_sold = Decimal("0")
                prepared = []

                # ====================================================
                # تجهيز الأصناف والتحقق من المخزون
                # ====================================================
                for item in items:
                    product_id = int(item["product_id"])
                    quantity = Decimal(str(item["quantity"]))

                    if quantity <= 0:
                        raise ValueError(
                            "الكمية يجب أن تكون أكبر من صفر"
                        )

                    product = s.execute(
                        text("""
                            SELECT
                                id,
                                name_ar,
                                sale_price
                            FROM products
                            WHERE id=:id
                              AND is_active=1
                            LIMIT 1
                        """),
                        {"id": product_id}
                    ).fetchone()

                    if not product:
                        raise ValueError(
                            f"الصنف غير موجود: {product_id}"
                        )

                    stock_row = s.execute(
                        text("""
                            SELECT
                                COALESCE(quantity,0),
                                COALESCE(available_quantity,0),
                                COALESCE(average_cost,0)
                            FROM stock
                            WHERE product_id=:product
                              AND warehouse_id=:warehouse
                            LIMIT 1
                        """),
                        {
                            "product": product_id,
                            "warehouse": warehouse_id,
                        }
                    ).fetchone()

                    if not stock_row:
                        raise ValueError(
                            f"لا يوجد مخزون للصنف: {product.name_ar}"
                        )

                    available = Decimal(str(stock_row[1] or 0))
                    average_cost = Decimal(str(stock_row[2] or 0))

                    if available < quantity:
                        raise ValueError(
                            f"المخزون غير كاف للصنف: {product.name_ar} "
                            f"(المتاح {available})"
                        )

                    price = Decimal(str(
                        item.get("unit_price", product.sale_price)
                    ))

                    discount = Decimal(str(
                        item.get("discount", 0)
                    ))

                    if price < 0 or discount < 0:
                        raise ValueError(
                            "السعر والخصم لا يمكن أن يكونا سالبين"
                        )

                    gross = quantity * price

                    if discount > gross:
                        raise ValueError(
                            f"الخصم أكبر من قيمة الصنف: {product.name_ar}"
                        )

                    line_total = cls.money(gross - discount)

                    subtotal += line_total
                    total_discount += discount
                    cost_of_goods_sold += (
                        quantity * average_cost
                    )

                    prepared.append({
                        "product_id": product_id,
                        "quantity": quantity,
                        "unit_price": price,
                        "discount": discount,
                        "line_total": line_total,
                        "average_cost": average_cost,
                    })

                subtotal = cls.money(subtotal)
                total_discount = cls.money(total_discount)
                cost_of_goods_sold = cls.money(cost_of_goods_sold)

                tax = cls.money(
                    subtotal * cls.TAX_RATE
                )

                total = cls.money(
                    subtotal + tax
                )

                if payment_method == "credit":
                    paid = Decimal("0")
                    due = total
                else:
                    paid = total
                    due = Decimal("0")

                # ====================================================
                # رقم فاتورة آمن
                # ====================================================
                max_id = s.execute(
                    text("SELECT COALESCE(MAX(id),0) FROM sales")
                ).scalar()

                invoice = f"INV-2026-{int(max_id)+1:06d}"

                # ====================================================
                # إنشاء الفاتورة
                # ====================================================
                s.execute(
                    text("""
                        INSERT INTO sales
                        (
                            invoice_number,
                            branch_id,
                            warehouse_id,
                            customer_id,
                            cashier_id,
                            status,
                            subtotal,
                            discount_amount,
                            tax_amount,
                            total_amount,
                            paid_amount,
                            due_amount,
                            notes,
                            created_at
                        )
                        VALUES
                        (
                            :invoice,
                            :branch,
                            :warehouse,
                            :customer,
                            :cashier,
                            'POSTED',
                            :subtotal,
                            :discount,
                            :tax,
                            :total,
                            :paid,
                            :due,
                            :notes,
                            CURRENT_TIMESTAMP
                        )
                    """),
                    {
                        "invoice": invoice,
                        "branch": branch_id,
                        "warehouse": warehouse_id,
                        "customer": customer_id,
                        "cashier": cashier_id,
                        "subtotal": float(subtotal),
                        "discount": float(total_discount),
                        "tax": float(tax),
                        "total": float(total),
                        "paid": float(paid),
                        "due": float(due),
                        "notes": notes or "فاتورة نقطة بيع",
                    }
                )

                sale_id = int(
                    s.execute(
                        text("SELECT last_insert_rowid()")
                    ).scalar()
                )

                # ====================================================
                # الأصناف + المخزون
                # ====================================================
                for item in prepared:

                    line_tax = cls.money(
                        item["line_total"] * cls.TAX_RATE
                    )

                    s.execute(
                        text("""
                            INSERT INTO sale_items
                            (
                                sale_id,
                                product_id,
                                quantity,
                                unit_price,
                                discount_amount,
                                tax_amount,
                                line_total
                            )
                            VALUES
                            (
                                :sale,
                                :product,
                                :quantity,
                                :price,
                                :discount,
                                :tax,
                                :line_total
                            )
                        """),
                        {
                            "sale": sale_id,
                            "product": item["product_id"],
                            "quantity": float(item["quantity"]),
                            "price": float(item["unit_price"]),
                            "discount": float(item["discount"]),
                            "tax": float(line_tax),
                            "line_total": float(item["line_total"]),
                        }
                    )

                    s.execute(
                        text("""
                            UPDATE stock
                            SET
                                quantity=quantity-:quantity,
                                available_quantity=available_quantity-:quantity,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE product_id=:product
                              AND warehouse_id=:warehouse
                              AND available_quantity>=:quantity
                        """),
                        {
                            "quantity": float(item["quantity"]),
                            "product": item["product_id"],
                            "warehouse": warehouse_id,
                        }
                    )

                    if s.execute(text("SELECT changes()")).scalar() != 1:
                        raise ValueError(
                            "تعذر تحديث المخزون، ربما تغيرت الكمية أثناء العملية"
                        )

                    s.execute(
                        text("""
                            INSERT INTO stock_movements
                            (
                                product_id,
                                warehouse_id,
                                movement_type,
                                quantity,
                                unit_cost,
                                reference_type,
                                reference_id,
                                notes,
                                created_at
                            )
                            VALUES
                            (
                                :product,
                                :warehouse,
                                'SALE',
                                :quantity,
                                :cost,
                                'SALE',
                                :sale,
                                :notes,
                                CURRENT_TIMESTAMP
                            )
                        """),
                        {
                            "product": item["product_id"],
                            "warehouse": warehouse_id,
                            "quantity": -float(item["quantity"]),
                            "cost": float(item["average_cost"]),
                            "sale": sale_id,
                            "notes": "صرف مخزون من نقطة البيع",
                        }
                    )

                # ====================================================
                # تسجيل الدفع
                # ====================================================
                if paid > 0:
                    s.execute(
                        text("""
                            INSERT INTO sale_payments
                            (
                                sale_id,
                                payment_method,
                                amount,
                                reference_number,
                                notes
                            )
                            VALUES
                            (
                                :sale,
                                :method,
                                :amount,
                                :reference,
                                :notes
                            )
                        """),
                        {
                            "sale": sale_id,
                            "method": payment_method,
                            "amount": float(paid),
                            "reference": reference_number,
                            "notes": "دفع فاتورة نقطة بيع",
                        }
                    )

                # ====================================================
                # العميل الآجل
                # ====================================================
                if due > 0:
                    current_balance = s.execute(
                        text("""
                            SELECT COALESCE(current_balance,0)
                            FROM customers
                            WHERE id=:id
                        """),
                        {"id": customer_id}
                    ).scalar()

                    if current_balance is None:
                        raise ValueError(
                            "العميل غير موجود"
                        )

                    new_balance = cls.money(
                        Decimal(str(current_balance)) + due
                    )

                    s.execute(
                        text("""
                            UPDATE customers
                            SET
                                current_balance=:balance,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=:id
                        """),
                        {
                            "balance": float(new_balance),
                            "id": customer_id,
                        }
                    )

                    s.execute(
                        text("""
                            INSERT INTO customer_transactions
                            (
                                customer_id,
                                transaction_type,
                                amount,
                                reference_type,
                                reference_id,
                                balance_after,
                                created_at
                            )
                            VALUES
                            (
                                :customer,
                                'SALE',
                                :amount,
                                'SALE',
                                :sale,
                                :balance,
                                CURRENT_TIMESTAMP
                            )
                        """),
                        {
                            "customer": customer_id,
                            "amount": float(due),
                            "sale": sale_id,
                            "balance": float(new_balance),
                        }
                    )

                # ====================================================
                # القيد المحاسبي
                # ====================================================
                journal = AccountingService.post_sale(
                    session=s,
                    sale_id=sale_id,
                    invoice_number=invoice,
                    subtotal=subtotal,
                    tax_amount=tax,
                    total_amount=total,
                    paid_amount=paid,
                    due_amount=due,
                    payment_method=payment_method,
                    cost_of_goods_sold=cost_of_goods_sold,
                    customer_id=customer_id,
                )

                s.commit()

                return {
                    "sale_id": sale_id,
                    "invoice_number": invoice,
                    "subtotal": float(subtotal),
                    "discount": float(total_discount),
                    "tax": float(tax),
                    "total": float(total),
                    "paid": float(paid),
                    "due": float(due),
                    "cost_of_goods_sold": float(cost_of_goods_sold),
                    "payment_method": payment_method,
                    "journal_entry_id": journal["journal_entry_id"],
                    "journal_entry_number": journal["entry_number"],
                }

            except Exception:
                s.rollback()
                raise

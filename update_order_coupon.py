
from pathlib import Path

main_path = Path("order-service/app/main.py")
models_path = Path("order-service/app/models.py")

main = main_path.read_text(encoding="utf-8")
models = models_path.read_text(encoding="utf-8")

# 1. Ensure the Order model stores the coupon code.
if "coupon_code = Column(String(40), nullable=True)" not in models:
    old_model_field = (
        '    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)\n'
    )
    if old_model_field not in models:
        raise RuntimeError("Could not find Order.discount_amount in models.py")

    models = models.replace(
        old_model_field,
        old_model_field + '    coupon_code = Column(String(40), nullable=True)\n',
        1,
    )

# 2. Import coupon validation.
if "    validate_coupon," not in main:
    old_import = "    partially_release_inventory,\n)"
    if old_import not in main:
        raise RuntimeError("Could not find services import block")

    main = main.replace(
        old_import,
        "    partially_release_inventory,\n    validate_coupon,\n)",
        1,
    )

# 3. Include the coupon in the first idempotency comparison.
old_condition = """            existing_order.shipping_address
            != order_data.shipping_address
            or existing_items != requested_items
"""

new_condition = """            existing_order.shipping_address
            != order_data.shipping_address
            or existing_items != requested_items
            or existing_order.coupon_code
            != (
                order_data.coupon_code.strip().upper()
                if order_data.coupon_code
                else None
            )
"""

if new_condition not in main:
    if old_condition not in main:
        raise RuntimeError("Could not find idempotency comparison")

    main = main.replace(old_condition, new_condition, 1)

# 4. Validate the coupon and calculate the discounted totals.
old_totals = "    totals = calculate_order_totals(subtotal)\n"

new_totals = """    coupon, discount_amount = validate_coupon(
        db=db,
        coupon_code=order_data.coupon_code,
        subtotal=subtotal,
    )

    totals = calculate_order_totals(
        subtotal,
        discount_amount,
    )
"""

if new_totals not in main:
    if old_totals not in main:
        raise RuntimeError("Could not find order totals calculation")

    main = main.replace(old_totals, new_totals, 1)

# 5. Store the normalized coupon code on the order.
old_constructor = """            shipping_address=order_data.shipping_address,
            **totals,
"""

new_constructor = """            shipping_address=order_data.shipping_address,
            coupon_code=(
                order_data.coupon_code.strip().upper()
                if order_data.coupon_code
                else None
            ),
            **totals,
"""

if new_constructor not in main:
    if old_constructor not in main:
        raise RuntimeError("Could not find Order constructor")

    main = main.replace(old_constructor, new_constructor, 1)

# 6. Increment usage inside the same database transaction.
old_commit = """        db.add(order)
        db.commit()
"""

new_commit = """        db.add(order)

        if coupon is not None:
            coupon.usage_count += 1

        db.commit()
"""

if new_commit not in main:
    if old_commit not in main:
        raise RuntimeError("Could not find order database commit")

    main = main.replace(old_commit, new_commit, 1)

# Save only after all expected changes were found.
models_path.write_text(models, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")

print("Order model and main.py updated successfully.")
print("Existing order endpoints have been preserved.")

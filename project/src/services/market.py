"""Validated receipt comparisons shared by UI and persistence."""
from decimal import Decimal, InvalidOperation
from services.finance_engine import amount


def product_values(name, quantity, price):
    name = str(name or "").strip()
    try:
        quantity = Decimal(str(quantity).replace(",", "."))
    except InvalidOperation:
        raise ValueError("Quantidade inválida") from None
    price = amount(price)
    if not name or not quantity.is_finite() or quantity <= 0 or price < 0:
        raise ValueError("Informe produto, quantidade positiva e preço não negativo")
    return name, quantity, price


def cart_total(items):
    total = Decimal(0)
    for item in items:
        _, quantity, price = product_values(item.get("product_name"), item.get("quantity"), item.get("unit_price"))
        total += quantity * price
    return amount(total)


def receipt_comparison(items, receipt, cashback=0):
    receipt, cashback = amount(receipt), amount(cashback)
    if receipt < 0 or cashback < 0 or cashback > receipt:
        raise ValueError("Nota e cashback devem ser não negativos; cashback não pode superar a nota")
    cart = cart_total(items)
    return {"cart": cart, "receipt": receipt, "cashback": cashback,
            "difference": receipt - cart, "net": receipt - cashback}
